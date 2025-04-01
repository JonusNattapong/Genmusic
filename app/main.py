import sys
import os
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

# เพิ่ม parent directory เข้าไปใน path เพื่อให้สามารถ import จาก app ได้
parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))

# นำเข้าส่วนประกอบหลัก
from app.ui.main_window import MainWindow
from app.core.utilities import logger

def init_app():
    """เตรียมการก่อนเริ่มแอพ"""
    # ตรวจสอบและสร้างโฟลเดอร์ที่จำเป็น
    from app.config.settings import MODELS_DIR, OUTPUT_DIR
    MODELS_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # ตั้งค่า logging
    logger.info("เริ่มต้นโปรแกรม Generative Music")

def main():
    """ฟังก์ชันหลักในการเริ่มโปรแกรม"""
    # เตรียมการก่อนเริ่มแอพ
    init_app()
    
    # สร้าง QApplication
    app = QApplication(sys.argv)
    
    # ตั้งค่าสไตล์สำหรับทั้งแอพ
    app.setStyle("Fusion")
    
    # ตั้งค่าฟอนต์หลัก
    font = QFont("Arial", 10)
    app.setFont(font)
    
    # ตั้งค่าสไตล์ทั่วไป
    app.setStyleSheet("""
        QMainWindow, QDialog {
            background-color: #f0f0f0;
        }
        QPushButton {
            padding: 4px 8px;
            border-radius: 3px;
            border: 1px solid #bbbbbb;
            background-color: #e0e0e0;
        }
        QPushButton:hover {
            background-color: #d0d0d0;
        }
        QPushButton:pressed {
            background-color: #c0c0c0;
        }
        QLineEdit, QTextEdit, QComboBox {
            border: 1px solid #bbbbbb;
            border-radius: 3px;
            padding: 3px;
            background-color: white;
        }
        QLabel {
            padding: 2px;
        }
    """)
    
    # สร้างและแสดงหน้าต่างหลัก
    window = MainWindow()
    window.show()
    
    # เริ่มการทำงานของแอพ
    sys.exit(app.exec())

# เริ่มโปรแกรมเมื่อรันไฟล์นี้โดยตรง
if __name__ == "__main__":
    main() 