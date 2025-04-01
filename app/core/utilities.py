import os
import time
import psutil
import shutil
import logging
from pathlib import Path
from datetime import datetime
from threading import Thread
from typing import List, Dict, Any, Optional, Tuple

from app.config.settings import OUTPUT_DIR, MAX_STORAGE_PERCENT, SAMPLE_RATE

# ตั้งค่า logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(OUTPUT_DIR.parent / "genmusic.log")
    ]
)
logger = logging.getLogger(__name__)

def get_system_info() -> Dict[str, Any]:
    """รวบรวมข้อมูลระบบเพื่อแสดงในโปรแกรม"""
    info = {
        "cpu": psutil.cpu_percent(interval=0.1),
        "ram": psutil.virtual_memory().percent,
        "ram_gb": round(psutil.virtual_memory().used / (1024 * 1024 * 1024), 2),
        "total_ram_gb": round(psutil.virtual_memory().total / (1024 * 1024 * 1024), 2),
        "disk": psutil.disk_usage('/').percent,
        "disk_free_gb": round(psutil.disk_usage('/').free / (1024 * 1024 * 1024), 2),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return info

def generate_filename(prompt: str, duration: int, instruments: List[str], mood: str) -> str:
    """สร้างชื่อไฟล์จากข้อมูลเพลง"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # สร้างชื่อจากข้อมูลเพลง
    instruments_str = "-".join([i.replace(" ", "") for i in instruments[:2]])  # แสดงเฉพาะ 2 เครื่องดนตรีแรก
    short_prompt = prompt.replace(" ", "_")[:20]  # ตัดให้ไม่ยาวเกินไป
    
    # สร้างชื่อไฟล์รูปแบบ YYYYMMDD_HHMMSS_instrument_mood_duration_prompt
    filename = f"{timestamp}_{instruments_str}_{mood}_{duration}s_{short_prompt}"
    return filename

def monitor_resource_usage(callback=None):
    """เฝ้าดูการใช้ทรัพยากรระบบและบันทึกลง log"""
    prev_info = get_system_info()
    logger.info(f"เริ่มติดตามทรัพยากร: CPU {prev_info['cpu']}%, RAM {prev_info['ram']}%")
    
    def _monitor():
        nonlocal prev_info
        while True:
            time.sleep(5)  # ตรวจสอบทุก 5 วินาที
            current_info = get_system_info()
            
            # บันทึกเมื่อมีการเปลี่ยนแปลงมากกว่า 10%
            if (abs(current_info['cpu'] - prev_info['cpu']) > 10 or 
                abs(current_info['ram'] - prev_info['ram']) > 10):
                logger.info(f"ทรัพยากรเปลี่ยนแปลง: CPU {current_info['cpu']}%, RAM {current_info['ram']}%")
                prev_info = current_info
                
            # เรียกฟังก์ชัน callback ถ้ามี
            if callback:
                callback(current_info)
                
    # เริ่ม thread แยกเพื่อไม่ให้กระทบกับการทำงานหลัก
    monitor_thread = Thread(target=_monitor, daemon=True)
    monitor_thread.start()
    return monitor_thread

def clean_old_files(min_free_percent: int = 10) -> int:
    """ลบไฟล์เพลงเก่าออกเมื่อพื้นที่ว่างน้อยกว่า min_free_percent%
    คืนค่าจำนวนไฟล์ที่ลบ"""
    # ตรวจสอบว่าพื้นที่ว่างน้อยกว่า min_free_percent% หรือไม่
    disk_usage = psutil.disk_usage('/')
    free_percent = 100 - disk_usage.percent
    
    if free_percent >= min_free_percent:
        return 0  # ยังมีพื้นที่ว่างพอ ไม่ต้องลบไฟล์
    
    logger.warning(f"พื้นที่ว่างเหลือน้อย ({free_percent}%), เริ่มลบไฟล์เก่า")
    
    # รวบรวมไฟล์เพลงทั้งหมดและเรียงตามเวลาที่สร้าง
    files = list(OUTPUT_DIR.glob("*.wav")) + list(OUTPUT_DIR.glob("*.mp3"))
    if not files:
        return 0
    
    files.sort(key=lambda x: x.stat().st_mtime)
    
    # ลบไฟล์เก่าสุดจนกว่าจะมีพื้นที่ว่างพอ
    deleted_count = 0
    for file in files:
        file.unlink()
        deleted_count += 1
        
        # ตรวจสอบว่ามีพื้นที่ว่างพอหรือยัง
        disk_usage = psutil.disk_usage('/')
        free_percent = 100 - disk_usage.percent
        if free_percent >= min_free_percent:
            break
            
    logger.info(f"ลบไฟล์เก่าแล้ว {deleted_count} ไฟล์, พื้นที่ว่างตอนนี้ {free_percent}%")
    return deleted_count

def seconds_to_time_format(seconds: int) -> str:
    """แปลงวินาทีเป็นรูปแบบ MM:SS"""
    minutes = seconds // 60
    seconds_remainder = seconds % 60
    return f"{minutes:02}:{seconds_remainder:02}"

def estimate_generation_time(duration: int, instruments_count: int) -> int:
    """ประมาณเวลาที่ใช้ในการสร้างเพลง (ในหน่วยวินาที)
    ค่าที่ได้เป็นการประมาณคร่าวๆ ขึ้นอยู่กับเครื่องที่ใช้"""
    # ค่าประมาณพื้นฐาน
    base_time = 10  # วินาที
    
    # เพิ่มเวลาตามความยาวเพลง (ประมาณการคร่าวๆ)
    time_per_second = 0.3  # การสร้างเพลง 1 วินาทีใช้เวลาประมาณ 0.3 วินาที
    
    # เพิ่มเวลาตามจำนวนเครื่องดนตรี
    instrument_factor = 1 + (instruments_count * 0.2)  # เครื่องดนตรีแต่ละชิ้นทำให้การสร้างช้าลง 20%
    
    # คำนวณเวลารวม
    estimated_time = base_time + (duration * time_per_second * instrument_factor)
    
    return max(5, int(estimated_time))  # อย่างน้อย 5 วินาที 