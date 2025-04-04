import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from queue import Queue
from threading import Thread, Event
from datetime import datetime

from app.config.settings import BASE_DIR, OUTPUT_DIR
from app.core.utilities import logger
from app.core.ai_engine import generate_music
from app.core.audio_utils import save_generated_audio

class BatchJob:
    """คลาสเก็บข้อมูลงาน batch"""
    def __init__(self,
                 name: str,
                 tasks: List[Dict[str, Any]],
                 status_callback: Optional[Callable] = None):
        self.name = name
        self.tasks = tasks
        self.total_tasks = len(tasks)
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.start_time = None
        self.end_time = None
        self.status = "pending"  # pending, running, completed, failed
        self.status_callback = status_callback
        self.results = []
        
    def to_dict(self) -> Dict[str, Any]:
        """แปลงข้อมูลเป็น dict สำหรับบันทึก"""
        return {
            "name": self.name,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "results": self.results
        }

class BatchGenerator:
    """จัดการการสร้างเพลงแบบ batch"""
    
    def __init__(self):
        self.jobs_dir = BASE_DIR / "batch_jobs"
        self.jobs_dir.mkdir(exist_ok=True)
        
        self.current_job = None
        self.job_queue = Queue()
        self.stop_event = Event()
        self.worker_thread = None
        
        # โหลดงานที่ยังไม่เสร็จ
        self._load_pending_jobs()
        
    def _load_pending_jobs(self):
        """โหลดงานที่ยังไม่เสร็จจากไฟล์"""
        for job_file in self.jobs_dir.glob("*.json"):
            try:
                with open(job_file, 'r', encoding='utf-8') as f:
                    job_data = json.load(f)
                    
                if job_data['status'] in ['pending', 'running']:
                    # สร้าง BatchJob จากข้อมูล
                    job = BatchJob(
                        name=job_data['name'],
                        tasks=job_data['tasks'],
                        status_callback=None  # ไม่มี callback สำหรับงานที่โหลดมา
                    )
                    job.status = 'pending'  # รีเซ็ตเป็น pending
                    
                    # ใส่เข้าคิว
                    self.job_queue.put(job)
                    
            except Exception as e:
                logger.error(f"ไม่สามารถโหลดงาน batch {job_file}: {e}")
                
    def _save_job(self, job: BatchJob):
        """บันทึกข้อมูลงานลงไฟล์"""
        job_file = self.jobs_dir / f"{job.name}_{int(time.time())}.json"
        try:
            with open(job_file, 'w', encoding='utf-8') as f:
                json.dump(job.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"ไม่สามารถบันทึกงาน batch {job.name}: {e}")
            
    def add_job(self, 
                name: str,
                tasks: List[Dict[str, Any]],
                status_callback: Optional[Callable] = None) -> bool:
        """เพิ่มงานใหม่เข้าคิว"""
        # ตรวจสอบรูปแบบข้อมูล
        for task in tasks:
            if not all(k in task for k in ['prompt', 'instruments', 'mood', 'duration']):
                return False
                
        # สร้าง BatchJob
        job = BatchJob(name, tasks, status_callback)
        
        # ใส่เข้าคิว
        self.job_queue.put(job)
        
        # บันทึกข้อมูลงาน
        self._save_job(job)
        
        # เริ่ม worker thread ถ้ายังไม่ได้เริ่ม
        self._ensure_worker_running()
        
        return True
        
    def _ensure_worker_running(self):
        """ตรวจสอบและเริ่ม worker thread ถ้าจำเป็น"""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.stop_event.clear()
            self.worker_thread = Thread(target=self._process_jobs)
            self.worker_thread.daemon = True
            self.worker_thread.start()
            
    def _process_jobs(self):
        """ประมวลผลงานในคิว"""
        while not self.stop_event.is_set():
            try:
                # ดึงงานจากคิว
                job = self.job_queue.get(timeout=1)
                self.current_job = job
                
                # เริ่มทำงาน
                job.status = "running"
                job.start_time = datetime.now()
                
                # แจ้ง callback
                if job.status_callback:
                    job.status_callback(job)
                    
                # ประมวลผลแต่ละ task
                for task in job.tasks:
                    if self.stop_event.is_set():
                        break
                        
                    try:
                        # สร้างเพลง
                        result = self._generate_music(task)
                        
                        # เพิ่มผลลัพธ์
                        job.results.append({
                            "task": task,
                            "success": True,
                            "output_file": str(result['file_path'])
                        })
                        
                        job.completed_tasks += 1
                        
                    except Exception as e:
                        logger.error(f"เกิดข้อผิดพลาดในการสร้างเพลง: {e}")
                        job.results.append({
                            "task": task,
                            "success": False,
                            "error": str(e)
                        })
                        job.failed_tasks += 1
                        
                    # แจ้ง callback
                    if job.status_callback:
                        job.status_callback(job)
                        
                # จบงาน
                job.end_time = datetime.now()
                job.status = "completed" if job.failed_tasks == 0 else "failed"
                
                # บันทึกข้อมูลงาน
                self._save_job(job)
                
                # แจ้ง callback ครั้งสุดท้าย
                if job.status_callback:
                    job.status_callback(job)
                    
            except Exception as e:
                if isinstance(e, TimeoutError):
                    continue
                logger.error(f"เกิดข้อผิดพลาดในการประมวลผลงาน batch: {e}")
                
        self.current_job = None
                
    def _generate_music(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """สร้างเพลงจาก task ที่กำหนด"""
        # สร้างเพลง
        music_result = generate_music(
            prompt=task['prompt'],
            duration=task['duration'],
            instruments=task['instruments'],
            mood=task['mood']
        )
        
        # บันทึกไฟล์
        file_path = save_generated_audio(
            audio_data=music_result['audio_data'],
            metadata=music_result['metadata']
        )
        
        return {
            "file_path": file_path,
            "metadata": music_result['metadata']
        }
        
    def stop(self):
        """หยุดการทำงาน"""
        self.stop_event.set()
        if self.worker_thread:
            self.worker_thread.join()
            self.worker_thread = None
            
    def get_current_job(self) -> Optional[BatchJob]:
        """ดึงข้อมูลงานที่กำลังทำ"""
        return self.current_job
        
    def get_queue_size(self) -> int:
        """ดึงจำนวนงานในคิว"""
        return self.job_queue.qsize()
        
# สร้าง singleton instance
batch_generator = BatchGenerator()
