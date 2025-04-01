import time
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QProgressBar, QFrame
)
from PyQt6.QtGui import QFont

from app.core.utilities import get_system_info

class ResourceMonitor(QFrame):
    """วิดเจ็ตสำหรับแสดงการใช้ทรัพยากรระบบ (CPU, RAM, Disk)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setMinimumHeight(100)
        self.setMaximumHeight(150)
        
        # ตั้งค่า UI
        self._init_ui()
        
        # ตั้งเวลาอัพเดตทุก 2 วินาที
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(2000)  # 2 วินาที
        
        # อัพเดตครั้งแรก
        self.update_stats()
        
    def _init_ui(self):
        """สร้างส่วนประกอบ UI"""
        main_layout = QVBoxLayout(self)
        
        # หัวข้อ
        title_label = QLabel("ทรัพยากรระบบ")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        main_layout.addWidget(title_label)
        
        # CPU
        cpu_layout = QHBoxLayout()
        cpu_label = QLabel("CPU:")
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setRange(0, 100)
        self.cpu_value = QLabel("0%")
        self.cpu_value.setMinimumWidth(50)
        cpu_layout.addWidget(cpu_label)
        cpu_layout.addWidget(self.cpu_progress)
        cpu_layout.addWidget(self.cpu_value)
        main_layout.addLayout(cpu_layout)
        
        # RAM
        ram_layout = QHBoxLayout()
        ram_label = QLabel("RAM:")
        self.ram_progress = QProgressBar()
        self.ram_progress.setRange(0, 100)
        self.ram_value = QLabel("0 GB / 0 GB")
        self.ram_value.setMinimumWidth(100)
        ram_layout.addWidget(ram_label)
        ram_layout.addWidget(self.ram_progress)
        ram_layout.addWidget(self.ram_value)
        main_layout.addLayout(ram_layout)
        
        # Disk
        disk_layout = QHBoxLayout()
        disk_label = QLabel("Disk:")
        self.disk_progress = QProgressBar()
        self.disk_progress.setRange(0, 100)
        self.disk_value = QLabel("0 GB free")
        self.disk_value.setMinimumWidth(100)
        disk_layout.addWidget(disk_label)
        disk_layout.addWidget(self.disk_progress)
        disk_layout.addWidget(self.disk_value)
        main_layout.addLayout(disk_layout)
        
        # สถานะการอัพเดต
        status_layout = QHBoxLayout()
        self.update_time = QLabel("อัพเดตล่าสุด: -")
        self.update_time.setAlignment(Qt.AlignmentFlag.AlignRight)
        status_layout.addWidget(self.update_time)
        main_layout.addLayout(status_layout)
        
    def update_stats(self):
        """อัพเดตข้อมูลทรัพยากรระบบ"""
        info = get_system_info()
        
        # อัพเดต CPU
        self.cpu_progress.setValue(int(info['cpu']))
        self.cpu_value.setText(f"{info['cpu']:.1f}%")
        
        # อัพเดต RAM
        self.ram_progress.setValue(int(info['ram']))
        self.ram_value.setText(f"{info['ram_gb']:.1f} GB / {info['total_ram_gb']:.1f} GB")
        
        # อัพเดต Disk
        self.disk_progress.setValue(int(info['disk']))
        self.disk_value.setText(f"{info['disk_free_gb']:.1f} GB free")
        
        # อัพเดตเวลา
        self.update_time.setText(f"อัพเดตล่าสุด: {info['timestamp']}")
        
        # ปรับสีตามการใช้งาน
        self._update_progress_colors()
        
    def _update_progress_colors(self):
        """ปรับสีของ progress bar ตามการใช้งาน"""
        # CPU
        self._set_progress_color(self.cpu_progress, self.cpu_progress.value())
        
        # RAM
        self._set_progress_color(self.ram_progress, self.ram_progress.value())
        
        # Disk
        self._set_progress_color(self.disk_progress, self.disk_progress.value())
        
    def _set_progress_color(self, progress_bar, value):
        """กำหนดสีของ progress bar ตามค่า"""
        stylesheet = ""
        if value < 60:
            # สีเขียว - ปกติ
            stylesheet = """
                QProgressBar::chunk {
                    background-color: #4CAF50;
                }
            """
        elif value < 80:
            # สีเหลือง - ต้องระวัง
            stylesheet = """
                QProgressBar::chunk {
                    background-color: #FFC107;
                }
            """
        else:
            # สีแดง - สูงมาก
            stylesheet = """
                QProgressBar::chunk {
                    background-color: #F44336;
                }
            """
        progress_bar.setStyleSheet(stylesheet)
        
    def stop_monitoring(self):
        """หยุดการติดตามทรัพยากร"""
        self.timer.stop() 