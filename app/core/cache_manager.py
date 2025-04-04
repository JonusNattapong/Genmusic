import os
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import numpy as np

from app.config.settings import BASE_DIR
from app.core.utilities import logger

class CacheManager:
    """จัดการ cache สำหรับผลลัพธ์การสร้างเพลง"""
    
    def __init__(self):
        self.cache_dir = BASE_DIR / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        self.index_file = self.cache_dir / "cache_index.json"
        self.cache_index: Dict[str, Dict[str, Any]] = {}
        
        # โหลด cache index
        self._load_index()
        
        # ทำความสะอาด cache เก่า
        self._cleanup_old_cache()
        
    def _load_index(self):
        """โหลด cache index จากไฟล์"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    self.cache_index = json.load(f)
            except Exception as e:
                logger.error(f"ไม่สามารถโหลด cache index ได้: {e}")
                self.cache_index = {}
        
    def _save_index(self):
        """บันทึก cache index ลงไฟล์"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"ไม่สามารถบันทึก cache index ได้: {e}")
            
    def _generate_cache_key(self, params: Dict[str, Any]) -> str:
        """สร้าง cache key จากพารามิเตอร์"""
        # เรียงลำดับคีย์เพื่อให้ได้ค่าเดียวกันเสมอ
        sorted_params = dict(sorted(params.items()))
        
        # แปลงเป็น string
        param_str = json.dumps(sorted_params, ensure_ascii=False, sort_keys=True)
        
        # สร้าง hash
        return hashlib.sha256(param_str.encode()).hexdigest()
        
    def _get_cache_file(self, cache_key: str) -> Path:
        """สร้าง path สำหรับไฟล์ cache"""
        return self.cache_dir / f"{cache_key}.npz"
        
    def _cleanup_old_cache(self, max_age_days: int = 7):
        """ลบ cache ที่เก่าเกินกำหนด"""
        now = datetime.now()
        cutoff = now - timedelta(days=max_age_days)
        
        # ลบ cache ที่เก่าเกิน max_age_days
        removed = []
        for key, meta in list(self.cache_index.items()):
            cache_time = datetime.fromisoformat(meta['timestamp'])
            if cache_time < cutoff:
                cache_file = self._get_cache_file(key)
                if cache_file.exists():
                    try:
                        cache_file.unlink()
                        removed.append(key)
                    except Exception as e:
                        logger.error(f"ไม่สามารถลบไฟล์ cache {cache_file} ได้: {e}")
                        
        # อัพเดต index
        for key in removed:
            del self.cache_index[key]
            
        if removed:
            logger.info(f"ลบ cache ที่เก่าแล้ว {len(removed)} รายการ")
            self._save_index()
            
    def get(self, 
           params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """ดึงผลลัพธ์จาก cache ถ้ามี"""
        cache_key = self._generate_cache_key(params)
        
        # ตรวจสอบว่ามี cache หรือไม่
        if cache_key not in self.cache_index:
            return None
            
        # ตรวจสอบว่าไฟล์ยังมีอยู่หรือไม่
        cache_file = self._get_cache_file(cache_key)
        if not cache_file.exists():
            del self.cache_index[cache_key]
            self._save_index()
            return None
            
        try:
            # โหลดข้อมูลจาก cache
            data = np.load(cache_file)
            audio_data = data['audio_data']
            metadata = data['metadata'].item()  # แปลง numpy array เป็น dict
            
            # อัพเดตเวลาเข้าถึงล่าสุด
            self.cache_index[cache_key]['last_access'] = datetime.now().isoformat()
            self._save_index()
            
            return {
                'audio_data': audio_data,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"ไม่สามารถโหลด cache ได้: {e}")
            return None
            
    def set(self,
            params: Dict[str, Any],
            result: Dict[str, Any]):
        """บันทึกผลลัพธ์ลง cache"""
        cache_key = self._generate_cache_key(params)
        cache_file = self._get_cache_file(cache_key)
        
        try:
            # บันทึกข้อมูล
            np.savez(
                cache_file,
                audio_data=result['audio_data'],
                metadata=result['metadata']
            )
            
            # อัพเดต index
            self.cache_index[cache_key] = {
                'params': params,
                'timestamp': datetime.now().isoformat(),
                'last_access': datetime.now().isoformat()
            }
            
            self._save_index()
            
        except Exception as e:
            logger.error(f"ไม่สามารถบันทึก cache ได้: {e}")
            
    def clear(self):
        """ล้าง cache ทั้งหมด"""
        # ลบไฟล์ทั้งหมด
        for cache_file in self.cache_dir.glob("*.npz"):
            try:
                cache_file.unlink()
            except Exception as e:
                logger.error(f"ไม่สามารถลบไฟล์ cache {cache_file} ได้: {e}")
                
        # รีเซ็ต index
        self.cache_index = {}
        self._save_index()
        
        logger.info("ล้าง cache เรียบร้อยแล้ว")
        
    def get_stats(self) -> Dict[str, Any]:
        """ดึงสถิติการใช้งาน cache"""
        total_size = 0
        for cache_file in self.cache_dir.glob("*.npz"):
            total_size += cache_file.stat().st_size
            
        return {
            'total_entries': len(self.cache_index),
            'total_size_mb': total_size / (1024 * 1024),
            'cache_dir': str(self.cache_dir)
        }
        
# สร้าง singleton instance
cache_manager = CacheManager()
