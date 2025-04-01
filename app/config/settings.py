import os
import psutil
import torch
from pathlib import Path

# ตำแหน่งไฟล์ต่างๆ
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = BASE_DIR / "models"
OUTPUT_DIR = BASE_DIR / "output"

# สร้างโฟลเดอร์ถ้ายังไม่มี
MODELS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# การตั้งค่าทรัพยากรระบบ
TOTAL_RAM = psutil.virtual_memory().total / (1024 * 1024 * 1024)  # GB
CPU_COUNT = psutil.cpu_count(logical=True)
PHYSICAL_CORES = psutil.cpu_count(logical=False)

# กำหนดทรัพยากรสูงสุดที่จะใช้
MAX_RAM_USAGE = min(TOTAL_RAM * 0.7, 11)  # ใช้ไม่เกิน 70% ของ RAM หรือ 11GB
MAX_CPU_USAGE = max(1, int(CPU_COUNT * 0.8))  # ใช้ไม่เกิน 80% ของ CPU cores

# การตั้งค่า PyTorch
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
if DEVICE == "cpu":
    # ถ้าไม่มี GPU ให้ใช้ Intel MKL ถ้ามี
    torch.set_num_threads(MAX_CPU_USAGE)

# การตั้งค่าโมเดล AI
MUSICGEN_MODEL_SIZE = "small"  # small, medium, large
MUSICGEN_MODEL_NAME = f"facebook/musicgen-{MUSICGEN_MODEL_SIZE}"

# ตัวเลือกเครื่องดนตรี (แยกตามประเภท)
INSTRUMENT_CATEGORIES = {
    "เปียโนและคีย์บอร์ด": ["Piano", "Electric Piano", "Organ", "Synth"],
    "เครื่องสาย": ["Violin", "Viola", "Cello", "Double Bass", "Guitar", "Acoustic Guitar", "Electric Guitar"],
    "เครื่องเป่า": ["Flute", "Clarinet", "Saxophone", "Trumpet", "Trombone"],
    "เครื่องตี": ["Drums", "Percussion", "Cymbals", "Timpani"],
    "อื่นๆ": ["Harp", "Bells", "Choir", "Ambient", "Electronic"]
}

# ตัวเลือกอารมณ์เพลง
MOODS = [
    "Calm", "Relaxing", "Peaceful",
    "Epic", "Dramatic", "Intense",
    "Happy", "Joyful", "Upbeat",
    "Sad", "Melancholic", "Dark",
    "Mysterious", "Ethereal", "Magical"
]

# ตัวเลือกความยาวเพลง (วินาที)
DURATION_PRESETS = [30, 60, 120, 180, 300]  # 30 วินาที ถึง 5 นาที
MAX_DURATION = 300  # สูงสุด 5 นาที

# การตั้งค่า Audio
SAMPLE_RATE = 44100  # Hz
AUDIO_FORMAT = "wav"  # wav หรือ mp3

# การตั้งค่าการแคช
CACHE_SIZE = 10  # จำนวนเพลงล่าสุดที่เก็บในแคช
MAX_STORAGE_PERCENT = 90  # ลบไฟล์เก่าเมื่อพื้นที่เหลือน้อยกว่า 10% 