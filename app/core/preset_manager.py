import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.config.settings import BASE_DIR
from app.core.utilities import logger

class PresetManager:
    """จัดการ presets สำหรับการสร้างเพลง"""
    
    def __init__(self):
        self.presets_dir = BASE_DIR / "presets"
        self.presets_dir.mkdir(exist_ok=True)
        self.presets_file = self.presets_dir / "music_presets.json"
        self._load_presets()
        
    def _load_presets(self):
        """โหลด presets จากไฟล์"""
        if not self.presets_file.exists():
            self.presets = {
                "user": [],  # presets ที่ผู้ใช้สร้าง
                "favorites": [],  # presets ที่ถูกบันทึกเป็น favorites
                "recent": []  # presets ที่ใช้ล่าสุด
            }
            self._save_presets()
        else:
            try:
                with open(self.presets_file, 'r', encoding='utf-8') as f:
                    self.presets = json.load(f)
            except Exception as e:
                logger.error(f"ไม่สามารถโหลด presets ได้: {e}")
                self.presets = {"user": [], "favorites": [], "recent": []}
                
    def _save_presets(self):
        """บันทึก presets ลงไฟล์"""
        try:
            with open(self.presets_file, 'w', encoding='utf-8') as f:
                json.dump(self.presets, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"ไม่สามารถบันทึก presets ได้: {e}")
            
    def add_preset(self, 
                  name: str,
                  prompt: str,
                  instruments: List[str],
                  mood: str,
                  duration: int,
                  description: Optional[str] = None,
                  is_favorite: bool = False) -> bool:
        """เพิ่ม preset ใหม่"""
        # ตรวจสอบว่ามีชื่อซ้ำหรือไม่
        if any(p['name'] == name for p in self.presets['user']):
            return False
            
        # สร้าง preset ใหม่
        preset = {
            'name': name,
            'prompt': prompt,
            'instruments': instruments,
            'mood': mood,
            'duration': duration,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'use_count': 0
        }
        
        # เพิ่มเข้า list
        self.presets['user'].append(preset)
        
        # ถ้าเป็น favorite ให้เพิ่มเข้า favorites ด้วย
        if is_favorite:
            self.add_to_favorites(name)
            
        self._save_presets()
        return True
        
    def update_preset(self,
                     name: str,
                     prompt: Optional[str] = None,
                     instruments: Optional[List[str]] = None,
                     mood: Optional[str] = None,
                     duration: Optional[int] = None,
                     description: Optional[str] = None) -> bool:
        """อัพเดต preset ที่มีอยู่แล้ว"""
        # หา preset ที่ต้องการอัพเดต
        preset = None
        for p in self.presets['user']:
            if p['name'] == name:
                preset = p
                break
                
        if preset is None:
            return False
            
        # อัพเดตค่าที่กำหนด
        if prompt is not None:
            preset['prompt'] = prompt
        if instruments is not None:
            preset['instruments'] = instruments
        if mood is not None:
            preset['mood'] = mood
        if duration is not None:
            preset['duration'] = duration
        if description is not None:
            preset['description'] = description
            
        self._save_presets()
        return True
        
    def delete_preset(self, name: str) -> bool:
        """ลบ preset"""
        # ลบจาก user presets
        self.presets['user'] = [p for p in self.presets['user'] if p['name'] != name]
        
        # ลบจาก favorites ถ้ามี
        self.remove_from_favorites(name)
        
        # ลบจาก recent ถ้ามี
        self.presets['recent'] = [p for p in self.presets['recent'] if p['name'] != name]
        
        self._save_presets()
        return True
        
    def add_to_favorites(self, name: str) -> bool:
        """เพิ่ม preset เข้า favorites"""
        # หา preset ที่ต้องการ
        preset = None
        for p in self.presets['user']:
            if p['name'] == name:
                preset = p
                break
                
        if preset is None:
            return False
            
        # ตรวจสอบว่ามีใน favorites แล้วหรือยัง
        if not any(p['name'] == name for p in self.presets['favorites']):
            self.presets['favorites'].append(preset)
            self._save_presets()
            
        return True
        
    def remove_from_favorites(self, name: str) -> bool:
        """ลบ preset ออกจาก favorites"""
        self.presets['favorites'] = [p for p in self.presets['favorites'] if p['name'] != name]
        self._save_presets()
        return True
        
    def get_preset(self, name: str) -> Optional[Dict[str, Any]]:
        """ดึงข้อมูล preset ตามชื่อ"""
        for p in self.presets['user']:
            if p['name'] == name:
                return p
        return None
        
    def add_to_recent(self, name: str):
        """เพิ่ม preset เข้า recent"""
        preset = self.get_preset(name)
        if preset is None:
            return
            
        # อัพเดตจำนวนการใช้งาน
        preset['use_count'] += 1
        
        # ลบออกจาก recent ถ้ามีอยู่แล้ว
        self.presets['recent'] = [p for p in self.presets['recent'] if p['name'] != name]
        
        # เพิ่มเข้า recent
        self.presets['recent'].insert(0, preset)
        
        # เก็บแค่ 10 อันล่าสุด
        self.presets['recent'] = self.presets['recent'][:10]
        
        self._save_presets()
        
    def get_all_presets(self) -> List[Dict[str, Any]]:
        """ดึงข้อมูล presets ทั้งหมด"""
        return self.presets['user']
        
    def get_favorites(self) -> List[Dict[str, Any]]:
        """ดึงข้อมูล presets ที่เป็น favorites"""
        return self.presets['favorites']
        
    def get_recent(self) -> List[Dict[str, Any]]:
        """ดึงข้อมูล presets ที่ใช้ล่าสุด"""
        return self.presets['recent']
        
# สร้าง singleton instance
preset_manager = PresetManager()
