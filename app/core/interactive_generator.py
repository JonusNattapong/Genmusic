import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app.config.settings import (
    OUTPUT_DIR, SAMPLE_RATE, INSTRUMENT_CATEGORIES,
    MOODS, MAX_DURATION
)
from app.core.utilities import logger, generate_filename
from app.core.ai_engine import generate_music
from app.core.audio_utils import (
    save_generated_audio, 
    audio_manager
)

class InteractiveMusicSession:
    """คลาสสำหรับ session การแต่งเพลงแบบมีส่วนร่วม"""
    
    def __init__(self, name: str):
        self.name = name
        self.session_dir = OUTPUT_DIR / "interactive_sessions" / name
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        self.history: List[Dict[str, Any]] = []
        self.current_version = 0
        self.base_prompt = ""
        self.current_audio = None
        self.current_metadata = None
        
        # โหลดข้อมูล session ถ้ามี
        self._load_session()
        
    def _load_session(self):
        """โหลดข้อมูล session จากไฟล์"""
        session_file = self.session_dir / "session.json"
        if session_file.exists():
            try:
                import json
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.history = data['history']
                self.current_version = data['current_version']
                self.base_prompt = data['base_prompt']
            except Exception as e:
                logger.error(f"ไม่สามารถโหลด session ได้: {e}")
                
    def _save_session(self):
        """บันทึกข้อมูล session"""
        session_file = self.session_dir / "session.json"
        try:
            import json
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'history': self.history,
                    'current_version': self.current_version,
                    'base_prompt': self.base_prompt
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"ไม่สามารถบันทึก session ได้: {e}")
            
    def start_new_track(self,
                       prompt: str,
                       instruments: List[str],
                       mood: str,
                       duration: int = 30) -> Dict[str, Any]:
        """เริ่มสร้างเพลงใหม่"""
        # เก็บ prompt เริ่มต้น
        self.base_prompt = prompt
        
        # สร้างเพลง
        result = generate_music(
            prompt=prompt,
            duration=duration,
            instruments=instruments,
            mood=mood
        )
        
        # บันทึกไฟล์
        file_path = save_generated_audio(
            audio_data=result['audio_data'],
            metadata=result['metadata']
        )
        
        # เก็บข้อมูลลงประวัติ
        entry = {
            'version': self.current_version,
            'type': 'new',
            'prompt': prompt,
            'instruments': instruments,
            'mood': mood,
            'duration': duration,
            'file_path': str(file_path),
            'timestamp': datetime.now().isoformat()
        }
        self.history.append(entry)
        
        # อัพเดตข้อมูลปัจจุบัน
        self.current_audio = result['audio_data']
        self.current_metadata = result['metadata']
        
        # บันทึก session
        self._save_session()
        
        return entry
        
    def adjust_instruments(self, 
                         instruments: List[str],
                         keep_elements: Optional[List[str]] = None) -> Dict[str, Any]:
        """ปรับเปลี่ยนเครื่องดนตรี"""
        # สร้าง prompt ใหม่
        prompt = self.base_prompt
        if keep_elements:
            prompt += f" Keep the {', '.join(keep_elements)}"
            
        # สร้างเพลงใหม่
        result = generate_music(
            prompt=prompt,
            duration=self.current_metadata['duration'],
            instruments=instruments,
            mood=self.current_metadata['mood']
        )
        
        # บันทึกไฟล์
        file_path = save_generated_audio(
            audio_data=result['audio_data'],
            metadata=result['metadata']
        )
        
        # เพิ่มเวอร์ชันและเก็บประวัติ
        self.current_version += 1
        entry = {
            'version': self.current_version,
            'type': 'adjust_instruments',
            'instruments': instruments,
            'keep_elements': keep_elements,
            'file_path': str(file_path),
            'timestamp': datetime.now().isoformat()
        }
        self.history.append(entry)
        
        # อัพเดตข้อมูลปัจจุบัน
        self.current_audio = result['audio_data']
        self.current_metadata = result['metadata']
        
        # บันทึก session
        self._save_session()
        
        return entry
        
    def adjust_mood(self, mood: str) -> Dict[str, Any]:
        """ปรับเปลี่ยนอารมณ์เพลง"""
        # สร้าง prompt ใหม่
        prompt = f"{self.base_prompt} but make it more {mood}"
        
        # สร้างเพลงใหม่
        result = generate_music(
            prompt=prompt,
            duration=self.current_metadata['duration'],
            instruments=self.current_metadata['instruments'],
            mood=mood
        )
        
        # บันทึกไฟล์
        file_path = save_generated_audio(
            audio_data=result['audio_data'],
            metadata=result['metadata']
        )
        
        # เพิ่มเวอร์ชันและเก็บประวัติ
        self.current_version += 1
        entry = {
            'version': self.current_version,
            'type': 'adjust_mood',
            'mood': mood,
            'file_path': str(file_path),
            'timestamp': datetime.now().isoformat()
        }
        self.history.append(entry)
        
        # อัพเดตข้อมูลปัจจุบัน
        self.current_audio = result['audio_data']
        self.current_metadata = result['metadata']
        
        # บันทึก session
        self._save_session()
        
        return entry
        
    def extend_duration(self, additional_seconds: int) -> Dict[str, Any]:
        """ต่อความยาวเพลง"""
        new_duration = self.current_metadata['duration'] + additional_seconds
        if new_duration > MAX_DURATION:
            raise ValueError(f"ความยาวเพลงเกิน {MAX_DURATION} วินาที")
            
        # สร้าง prompt ใหม่
        prompt = f"{self.base_prompt} extended version"
        
        # สร้างเพลงใหม่
        result = generate_music(
            prompt=prompt,
            duration=new_duration,
            instruments=self.current_metadata['instruments'],
            mood=self.current_metadata['mood']
        )
        
        # บันทึกไฟล์
        file_path = save_generated_audio(
            audio_data=result['audio_data'],
            metadata=result['metadata']
        )
        
        # เพิ่มเวอร์ชันและเก็บประวัติ
        self.current_version += 1
        entry = {
            'version': self.current_version,
            'type': 'extend_duration',
            'additional_seconds': additional_seconds,
            'file_path': str(file_path),
            'timestamp': datetime.now().isoformat()
        }
        self.history.append(entry)
        
        # อัพเดตข้อมูลปัจจุบัน
        self.current_audio = result['audio_data']
        self.current_metadata = result['metadata']
        
        # บันทึก session
        self._save_session()
        
        return entry
        
    def undo(self) -> Optional[Dict[str, Any]]:
        """ย้อนกลับไปเวอร์ชันก่อนหน้า"""
        if self.current_version <= 0:
            return None
            
        # หาเวอร์ชันก่อนหน้า
        prev_version = None
        for entry in reversed(self.history):
            if entry['version'] == self.current_version - 1:
                prev_version = entry
                break
                
        if prev_version is None:
            return None
            
        # โหลดไฟล์เสียง
        file_path = Path(prev_version['file_path'])
        if not file_path.exists():
            return None
            
        # อัพเดตเวอร์ชันปัจจุบัน
        self.current_version -= 1
        
        # บันทึก session
        self._save_session()
        
        return prev_version
        
    def redo(self) -> Optional[Dict[str, Any]]:
        """ทำซ้ำการเปลี่ยนแปลงที่ย้อนกลับ"""
        # หาเวอร์ชันถัดไป
        next_version = None
        for entry in self.history:
            if entry['version'] == self.current_version + 1:
                next_version = entry
                break
                
        if next_version is None:
            return None
            
        # โหลดไฟล์เสียง
        file_path = Path(next_version['file_path'])
        if not file_path.exists():
            return None
            
        # อัพเดตเวอร์ชันปัจจุบัน
        self.current_version += 1
        
        # บันทึก session
        self._save_session()
        
        return next_version
        
    def get_history(self) -> List[Dict[str, Any]]:
        """ดึงประวัติการแก้ไขทั้งหมด"""
        return self.history
        
    def get_current_version(self) -> Optional[Dict[str, Any]]:
        """ดึงข้อมูลเวอร์ชันปัจจุบัน"""
        for entry in reversed(self.history):
            if entry['version'] == self.current_version:
                return entry
        return None
        
class InteractiveGenerator:
    """จัดการ session การแต่งเพลงแบบมีส่วนร่วม"""
    
    def __init__(self):
        self.sessions_dir = OUTPUT_DIR / "interactive_sessions"
        self.sessions_dir.mkdir(exist_ok=True)
        self.active_sessions: Dict[str, InteractiveMusicSession] = {}
        
    def create_session(self, name: str) -> InteractiveMusicSession:
        """สร้าง session ใหม่"""
        if name in self.active_sessions:
            raise ValueError(f"Session {name} มีอยู่แล้ว")
            
        session = InteractiveMusicSession(name)
        self.active_sessions[name] = session
        return session
        
    def get_session(self, name: str) -> Optional[InteractiveMusicSession]:
        """ดึง session ตามชื่อ"""
        return self.active_sessions.get(name)
        
    def close_session(self, name: str):
        """ปิด session"""
        if name in self.active_sessions:
            del self.active_sessions[name]
            
    def get_all_sessions(self) -> List[str]:
        """ดึงรายชื่อ session ทั้งหมด"""
        return list(self.active_sessions.keys())
        
# สร้าง singleton instance
interactive_generator = InteractiveGenerator()
