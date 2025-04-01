import os
import time
import numpy as np
import soundfile as sf
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

# ดึงการตั้งค่าจาก settings
from app.config.settings import (
    OUTPUT_DIR, SAMPLE_RATE, AUDIO_FORMAT
)

# ใช้ utilities
from app.core.utilities import logger, generate_filename

class AudioManager:
    """คลาสสำหรับจัดการไฟล์เสียงที่สร้างขึ้น"""
    def __init__(self):
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(exist_ok=True)  # สร้างโฟลเดอร์ถ้ายังไม่มี
        self.sample_rate = SAMPLE_RATE
        self.audio_format = AUDIO_FORMAT
        self.recent_files = []  # เก็บไฟล์ล่าสุดที่สร้างขึ้น
        
    def save_audio(self, 
                  audio_data: np.ndarray, 
                  metadata: Dict[str, Any]) -> Path:
        """บันทึกไฟล์เสียงและคืนค่า Path ของไฟล์"""
        # สร้างชื่อไฟล์จาก metadata
        filename = generate_filename(
            prompt=metadata['prompt'],
            duration=int(metadata['duration']),
            instruments=metadata['instruments'],
            mood=metadata['mood']
        )
        
        # เพิ่มนามสกุลไฟล์
        full_filename = f"{filename}.{self.audio_format}"
        file_path = self.output_dir / full_filename
        
        # บันทึกไฟล์
        logger.info(f"กำลังบันทึกไฟล์เสียงที่ {file_path}")
        sf.write(
            file=file_path,
            data=audio_data,
            samplerate=self.sample_rate
        )
        
        # เก็บไฟล์ล่าสุด
        self.recent_files.append(file_path)
        if len(self.recent_files) > 10:  # เก็บแค่ 10 ไฟล์ล่าสุด
            self.recent_files.pop(0)
        
        return file_path
    
    def normalize_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """ปรับระดับเสียงให้ไม่เกิน 0 dB"""
        # ป้องกัน silent audio
        if np.abs(audio_data).max() < 1e-6:
            return audio_data
            
        # normalize โดยคงสัดส่วนของช่องสัญญาณถ้ามีหลายช่อง
        normalized = audio_data / np.abs(audio_data).max()
        # ทำให้เสียงดังขึ้นเล็กน้อย แต่ยังไม่เกิน 0 dB
        normalized = normalized * 0.95
        
        return normalized
    
    def trim_silence(self, audio_data: np.ndarray, threshold: float = 0.01) -> np.ndarray:
        """ตัดความเงียบที่จุดเริ่มต้นและจุดสิ้นสุดของเสียง"""
        # หาจุดที่มีเสียง
        amplitude = np.abs(audio_data)
        has_sound = amplitude > threshold
        
        # ถ้าเสียงเงียบทั้งหมด ให้คืนค่าเดิม
        if not np.any(has_sound):
            return audio_data
            
        # หาจุดเริ่มต้นและสิ้นสุดของเสียง
        start = np.argmax(has_sound)
        end = len(audio_data) - np.argmax(has_sound[::-1])
        
        # เพิ่ม margin เล็กน้อย (100 ms)
        margin = int(self.sample_rate * 0.1)
        start = max(0, start - margin)
        end = min(len(audio_data), end + margin)
        
        return audio_data[start:end]
    
    def fade_in_out(self, audio_data: np.ndarray, fade_ms: int = 100) -> np.ndarray:
        """เพิ่ม fade in/out เพื่อป้องกันเสียง click"""
        if len(audio_data) < 2:
            return audio_data
            
        fade_samples = int(self.sample_rate * fade_ms / 1000)
        fade_samples = min(fade_samples, len(audio_data) // 4)  # ไม่ให้ fade ยาวเกิน 1/4 ของเสียง
        
        # สร้าง fade in/out curve
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)
        
        # นำไปคูณกับข้อมูลเสียง
        audio_data_fade = audio_data.copy()
        audio_data_fade[:fade_samples] *= fade_in
        audio_data_fade[-fade_samples:] *= fade_out
        
        return audio_data_fade
    
    def process_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """ประมวลผลข้อมูลเสียงทั้งหมดก่อนบันทึก"""
        # ทำการประมวลผลตามลำดับ
        audio_data = self.normalize_audio(audio_data)
        audio_data = self.trim_silence(audio_data)
        audio_data = self.fade_in_out(audio_data)
        
        return audio_data
    
    def get_recent_files(self, count: int = 5) -> list:
        """คืนค่าไฟล์ล่าสุดที่สร้างขึ้น"""
        # ตรวจสอบว่าไฟล์ยังมีอยู่จริง
        exist_files = [f for f in self.recent_files if f.exists()]
        self.recent_files = exist_files  # อัพเดตรายการ
        
        return self.recent_files[-count:]
    
    def get_all_files(self, sort_by='date', reverse=True) -> list:
        """คืนค่าไฟล์ทั้งหมดในโฟลเดอร์ output"""
        files = list(self.output_dir.glob(f"*.{self.audio_format}"))
        
        if sort_by == 'date':
            files.sort(key=lambda x: x.stat().st_mtime, reverse=reverse)
        elif sort_by == 'name':
            files.sort(reverse=reverse)
        elif sort_by == 'size':
            files.sort(key=lambda x: x.stat().st_size, reverse=reverse)
            
        return files
        
    def delete_file(self, file_path: Path) -> bool:
        """ลบไฟล์และคืนค่า True ถ้าสำเร็จ"""
        if not file_path.exists():
            logger.warning(f"ไม่พบไฟล์ {file_path}")
            return False
            
        try:
            file_path.unlink()
            # ลบออกจากรายการไฟล์ล่าสุดด้วย
            if file_path in self.recent_files:
                self.recent_files.remove(file_path)
            logger.info(f"ลบไฟล์ {file_path} แล้ว")
            return True
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการลบไฟล์ {file_path}: {e}")
            return False

# สร้าง singleton instance
audio_manager = AudioManager()

# ฟังก์ชันสะดวกสำหรับการเรียกใช้งานนอกไฟล์นี้
def save_generated_audio(audio_data: np.ndarray, metadata: Dict[str, Any]) -> Path:
    """บันทึกเสียงที่สร้างขึ้นและคืนค่า Path ของไฟล์"""
    # ประมวลผลข้อมูลเสียงก่อนบันทึก
    processed_audio = audio_manager.process_audio(audio_data)
    # บันทึกไฟล์
    return audio_manager.save_audio(processed_audio, metadata)
    
def get_recent_audio_files(count: int = 5) -> list:
    """คืนค่าไฟล์เสียงล่าสุด"""
    return audio_manager.get_recent_files(count)
    
def get_all_audio_files(sort_by='date', reverse=True) -> list:
    """คืนค่าไฟล์เสียงทั้งหมด"""
    return audio_manager.get_all_files(sort_by, reverse)
    
def delete_audio_file(file_path: Path) -> bool:
    """ลบไฟล์เสียง"""
    return audio_manager.delete_file(file_path) 