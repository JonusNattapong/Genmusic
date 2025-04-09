# Genmusic

ระบบสร้างดนตรีอัตโนมัติ (Generative Music) สำหรับเครื่อง ASUS ExpertBook B1402CVA

## คุณสมบัติ

- สร้างเพลงบรรเลงจากคำสั่ง (text prompt)
- เลือกเครื่องดนตรีได้หลากหลาย
- กำหนดอารมณ์และความยาวเพลงได้
- ปรับแต่งให้เหมาะสมกับทรัพยากรเครื่อง (CPU/RAM)

## การติดตั้ง

1. ติดตั้ง Python 3.10 ขึ้นไป
2. ติดตั้งแพ็คเกจที่จำเป็น:

```
pip install -r requirements.txt
```

3. ดาวน์โหลดโมเดล MusicGen Small (จะดาวน์โหลดอัตโนมัติเมื่อรันโปรแกรมครั้งแรก)

## การใช้งาน

รันโปรแกรมด้วยคำสั่ง:

```
python -m app.main
```

## ข้อแนะนำสำหรับประสิทธิภาพสูงสุด

- ปิดโปรแกรมอื่นที่ไม่จำเป็นขณะรันโปรแกรม
- รองรับการสร้างเพลงตั้งแต่ 1 นาที ถึง 5 ชั่วโมง
- แนะนำให้เริ่มจากความยาวสั้นๆ ก่อนเพื่อทดสอบผลลัพธ์
- สำหรับเพลงที่ยาวกว่า 1 ชั่วโมง:
  * ควรมี RAM อย่างน้อย 32GB
  * อาจใช้เวลาสร้างหลายชั่วโมง
  * ควรเชื่อมต่อไฟฟ้าขณะสร้างเพลง
- เลือกใช้เครื่องดนตรีไม่เกิน 3 ชิ้นในแต่ละครั้ง

## ข้อกำหนดของระบบ

- CPU: Intel Core i5-1335U หรือสูงกว่า
- RAM: 16GB ขึ้นไป
- พื้นที่ว่าง: อย่างน้อย 5GB สำหรับโมเดลและไฟล์เพลง
