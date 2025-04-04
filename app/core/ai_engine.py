import os
import gc
import time
import torch
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from threading import Thread
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

# ดึงการตั้งค่าและ managers
from app.config.settings import (
    DEVICE, MUSICGEN_MODEL_NAME, MUSICGEN_MODEL_SIZE,
    MAX_DURATION, SAMPLE_RATE, AUDIO_FORMAT,
    MAX_CPU_USAGE
)

# ใช้ utilities และ managers
from app.core.utilities import logger, clean_old_files
from app.core.cache_manager import cache_manager

class MusicGenerator:
    """คลาสสำหรับการจัดการโมเดล AI สำหรับสร้างเพลง"""
    def __init__(self):
        self.model = None
        self.device = DEVICE
        self.model_name = MUSICGEN_MODEL_NAME
        self.sample_rate = SAMPLE_RATE
        self.is_loading = False
        self.is_ready = False
        self.progress_callback = None
        self._generation_queue = Queue()
        self._processing_thread = None
        
        # ThreadPool สำหรับ batch processing
        self.thread_pool = ThreadPoolExecutor(
            max_workers=min(MAX_CPU_USAGE, multiprocessing.cpu_count())
        )
        
    def load_model(self, callback=None):
        """โหลดโมเดล MusicGen"""
        if self.is_loading or self.is_ready:
            logger.warning("โมเดลกำลังโหลดอยู่แล้วหรือพร้อมแล้ว")
            return
            
        self.is_loading = True
        
        def _load():
            logger.info(f"กำลังโหลดโมเดล {self.model_name}...")
            try:
                # ทำ import ภายในฟังก์ชันเพื่อลดเวลาการโหลดตอนเริ่มโปรแกรม
                from transformers import AutoProcessor, MusicgenForConditionalGeneration
                
                # โหลดโมเดลและ processor
                start_time = time.time()
                
                # เรียกให้มีการแสดง log
                logger.info(f"กำลังโหลด processor จาก {self.model_name}...")
                self.processor = AutoProcessor.from_pretrained(self.model_name)
                
                logger.info(f"กำลังโหลด model จาก {self.model_name}...")
                self.model = MusicgenForConditionalGeneration.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float32
                )
                
                # ย้ายโมเดลไปยัง device ที่เหมาะสม
                self.model.to(self.device)
                
                # ถ้าใช้ CPU ปรับใช้ torch.compile ถ้ามี PyTorch 2.0+
                if self.device == "cpu" and hasattr(torch, 'compile'):
                    try:
                        logger.info("กำลังใช้ torch.compile เพื่อเพิ่มความเร็ว...")
                        self.model = torch.compile(self.model)
                    except Exception as e:
                        logger.warning(f"ไม่สามารถใช้ torch.compile ได้: {e}")
                
                load_time = time.time() - start_time
                logger.info(f"โหลดโมเดลเสร็จแล้ว ใช้เวลา {load_time:.2f} วินาที")
                
                self.is_ready = True
                
                # เริ่ม thread การประมวลผล
                self._start_processing_thread()
                
            except Exception as e:
                logger.error(f"เกิดข้อผิดพลาดในการโหลดโมเดล: {e}")
            finally:
                self.is_loading = False
                
            # เรียก callback ถ้ามี
            if callback:
                callback(self.is_ready)
        
        # โหลดโมเดลใน thread แยกเพื่อไม่ให้ UI ค้าง
        load_thread = Thread(target=_load)
        load_thread.start()
        
    def _start_processing_thread(self):
        """เริ่ม thread สำหรับประมวลผลคำขอในคิว"""
        def _process_queue():
            while True:
                if not self._generation_queue.empty():
                    # ดึงข้อมูลจากคิว
                    params, result_callback = self._generation_queue.get()
                    use_cache = params.pop('use_cache', True)
                    
                    # ตรวจสอบ cache ก่อน
                    if use_cache:
                        cached_result = cache_manager.get(params)
                        if cached_result:
                            logger.info("ใช้ผลลัพธ์จาก cache")
                            if result_callback:
                                result_callback(True, cached_result)
                            self._generation_queue.task_done()
                            continue
                    
                    # สร้างเพลง
                    try:
                        result = self._generate_music(**params)
                        
                        # เก็บลง cache
                        if use_cache:
                            cache_manager.set(params, result)
                            
                        if result_callback:
                            result_callback(True, result)
                    except Exception as e:
                        logger.error(f"เกิดข้อผิดพลาดในการสร้างเพลง: {e}")
                        if result_callback:
                            result_callback(False, str(e))
                    
                    # ทำความสะอาดหน่วยความจำ
                    gc.collect()
                    if self.device == "cuda":
                        torch.cuda.empty_cache()
                    
                    # เสร็จสิ้นงานในคิว
                    self._generation_queue.task_done()
                else:
                    # ถ้าไม่มีงานให้นอนรอสักครู่
                    time.sleep(0.5)
        
        self._processing_thread = Thread(target=_process_queue, daemon=True)
        self._processing_thread.start()
    
    def queue_music_generation(self, 
                             prompt: str, 
                             duration: int,
                             instruments: List[str],
                             mood: str,
                             result_callback=None,
                             use_cache: bool = True) -> bool:
        """เพิ่มคำขอการสร้างเพลงเข้าคิว"""
        if not self.is_ready:
            if result_callback:
                result_callback(False, "โมเดลยังไม่พร้อม กรุณารอให้โหลดเสร็จก่อน")
            return False
        
        # เตรียมพารามิเตอร์
        params = {
            "prompt": prompt,
            "duration": duration,
            "instruments": instruments,
            "mood": mood,
            "use_cache": use_cache
        }
        
        # เพิ่มเข้าคิว
        self._generation_queue.put((params, result_callback))
        logger.info(f"เพิ่มคำขอการสร้างเพลงเข้าคิว: {prompt}")
        return True
        
    def generate_batch(self,
                      tasks: List[Dict[str, Any]],
                      status_callback=None,
                      use_cache: bool = True) -> List[Dict[str, Any]]:
        """สร้างเพลงหลายเพลงพร้อมกันโดยใช้ ThreadPool"""
        results = []
        futures = []
        
        # สร้าง future สำหรับแต่ละงาน
        for task in tasks:
            task['use_cache'] = use_cache
            future = self.thread_pool.submit(
                self._generate_music,
                **task
            )
            futures.append((future, task))
        
        # รอผลลัพธ์และอัพเดตสถานะ
        completed = 0
        failed = 0
        total = len(tasks)
        
        for future, task in futures:
            try:
                result = future.result()
                results.append({
                    'task': task,
                    'success': True,
                    'result': result,
                })
                completed += 1
                
                # เก็บลง cache
                if use_cache:
                    cache_manager.set(task, result)
                    
            except Exception as e:
                logger.error(f"เกิดข้อผิดพลาดในการสร้างเพลง {task['prompt']}: {e}")
                results.append({
                    'task': task,
                    'success': False,
                    'error': str(e)
                })
                failed += 1
                
            # เรียก callback
            if status_callback:
                status_callback(completed, failed, total)
                
        return results
    
    def _generate_music(self, 
                       prompt: str, 
                       duration: int,
                       instruments: List[str],
                       mood: str) -> Dict[str, Any]:
        """สร้างเพลงตามพารามิเตอร์ที่กำหนด
        คืนค่า dictionary ที่มีข้อมูลเพลงและ metadata"""
        
        logger.info(f"เริ่มสร้างเพลง: {prompt}")
        start_time = time.time()
        
        # ปรับแต่ง prompt
        enhanced_prompt = self._enhance_prompt(prompt, instruments, mood)
        logger.info(f"Prompt ที่ปรับแล้ว: {enhanced_prompt}")
        
        # ตรวจสอบและปรับความยาว
        max_seconds = min(duration, MAX_DURATION)
        # MusicGen ใช้หน่วยเป็นวินาที
        max_seconds_tensor = torch.tensor([max_seconds])
        
        # สร้าง inputs จาก prompt
        inputs = self.processor(
            text=[enhanced_prompt],
            padding=True,
            return_tensors="pt",
        )
        
        # กำหนด generation parameters
        generation_kwargs = {
            "do_sample": True,
            "guidance_scale": 3.0,
            "max_new_tokens": max_seconds * 50,  # ประมาณ 50 tokens ต่อวินาที
        }
        
        # สร้างเพลง
        with torch.no_grad():
            audio_values = self.model.generate(
                **inputs.to(self.device),
                **generation_kwargs
            )
        
        # แปลงเป็น numpy array
        audio_data = audio_values[0, 0].cpu().numpy()
        
        # คำนวณเวลาที่ใช้
        generation_time = time.time() - start_time
        logger.info(f"สร้างเพลงเสร็จแล้ว ใช้เวลา {generation_time:.2f} วินาที")
        
        # เรียกให้ทำความสะอาดพื้นที่ถ้าจำเป็น
        clean_old_files()
        
        # สร้าง metadata
        metadata = {
            "prompt": prompt,
            "enhanced_prompt": enhanced_prompt,
            "duration": len(audio_data) / SAMPLE_RATE,
            "instruments": instruments,
            "mood": mood,
            "sample_rate": SAMPLE_RATE,
            "generation_time": generation_time,
            "model": self.model_name,
            "timestamp": time.time()
        }
        
        # คืนค่าทั้งข้อมูลเสียงและ metadata
        return {
            "audio_data": audio_data,
            "metadata": metadata
        }
    
    def _enhance_prompt(self, prompt: str, instruments: List[str], mood: str) -> str:
        """ปรับแต่ง prompt โดยเพิ่มเครื่องดนตรีและอารมณ์
        เพื่อให้ได้ผลลัพธ์ที่ดีขึ้น"""
        instruments_str = ", ".join(instruments)
        
        # ถ้า prompt ไม่มีข้อมูลเครื่องดนตรีให้เพิ่มเข้าไป
        if not any(inst.lower() in prompt.lower() for inst in instruments):
            prompt = f"{instruments_str}, {prompt}"
        
        # ถ้า prompt ไม่มีข้อมูลอารมณ์ให้เพิ่มเข้าไป
        if mood.lower() not in prompt.lower():
            prompt = f"{prompt}, {mood}"
        
        # เพิ่มคำเฉพาะที่ช่วยให้โมเดลสร้างเพลงได้ดีขึ้น
        enhancers = [
            "high quality",
            "instrumental music",
            "professional recording"
        ]
        
        # เพิ่มคำเสริมที่ไม่ซ้ำกับ prompt ปัจจุบัน
        for enhancer in enhancers:
            if enhancer not in prompt.lower():
                prompt = f"{prompt}, {enhancer}"
                
        return prompt
    
    def unload_model(self):
        """ปลดโหลดโมเดลเพื่อประหยัด RAM"""
        if self.model is not None:
            logger.info("กำลังปลดโหลดโมเดล...")
            self.model = None
            self.processor = None
            self.is_ready = False
            
            # บังคับ garbage collection
            gc.collect()
            if self.device == "cuda":
                torch.cuda.empty_cache()
                
            logger.info("ปลดโหลดโมเดลเสร็จสิ้น")
            
# สร้าง singleton instance
music_generator = MusicGenerator()

# ฟังก์ชันสะดวกสำหรับการเรียกใช้งานนอกไฟล์นี้
def load_ai_model(callback=None):
    """ฟังก์ชันสะดวกสำหรับโหลดโมเดล AI"""
    music_generator.load_model(callback)
    
def generate_music(prompt, duration, instruments, mood, callback=None, use_cache=True):
    """ฟังก์ชันสะดวกสำหรับสร้างเพลง"""
    return music_generator.queue_music_generation(
        prompt=prompt,
        duration=duration,
        instruments=instruments,
        mood=mood,
        result_callback=callback,
        use_cache=use_cache
    )
