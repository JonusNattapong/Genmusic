from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QLineEdit, QMessageBox,
    QFormLayout, QComboBox, QSpinBox, QTextEdit,
    QTableWidget, QTableWidgetItem, QProgressBar,
    QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.batch_generator import batch_generator
from app.core.preset_manager import preset_manager
from app.config.settings import INSTRUMENT_CATEGORIES, MOODS

class BatchGeneratorDialog(QDialog):
    """ไดอะล็อกสำหรับสร้างเพลงแบบ batch"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("สร้างเพลงแบบ Batch")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        self.tasks: List[Dict[str, Any]] = []
        self.current_job = None
        self._init_ui()
        
        # เริ่มตรวจสอบสถานะทุก 1 วินาที
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_status)
        self.update_timer.start(1000)
        
    def _init_ui(self):
        """สร้างส่วนประกอบ UI"""
        layout = QVBoxLayout(self)
        
        # ส่วนบน: การตั้งค่าและเพิ่มงาน
        top_layout = QHBoxLayout()
        
        # ด้านซ้าย: ฟอร์มเพิ่มงาน
        form_layout = QFormLayout()
        
        # ชื่องาน
        self.job_name = QLineEdit()
        form_layout.addRow("ชื่องาน:", self.job_name)
        
        # Prompt
        self.prompt_input = QTextEdit()
        self.prompt_input.setAcceptRichText(False)
        self.prompt_input.setMaximumHeight(100)
        form_layout.addRow("Prompt:", self.prompt_input)
        
        # เครื่องดนตรี
        self.instruments_list = QListWidget()
        self.instruments_list.setSelectionMode(
            QListWidget.SelectionMode.MultiSelection
        )
        for category, instruments in INSTRUMENT_CATEGORIES.items():
            for instrument in instruments:
                self.instruments_list.addItem(instrument)
        self.instruments_list.setMaximumHeight(150)
        form_layout.addRow("เครื่องดนตรี:", self.instruments_list)
        
        # อารมณ์
        self.mood_input = QComboBox()
        self.mood_input.addItems(MOODS)
        form_layout.addRow("อารมณ์:", self.mood_input)
        
        # ความยาว
        self.duration_input = QSpinBox()
        self.duration_input.setRange(10, 300)
        self.duration_input.setSingleStep(10)
        self.duration_input.setValue(30)
        form_layout.addRow("ความยาว (วินาที):", self.duration_input)
        
        # ปุ่มเพิ่มงาน
        add_btn = QPushButton("เพิ่มงาน")
        add_btn.clicked.connect(self._add_task)
        form_layout.addRow("", add_btn)
        
        # เพิ่ม layout ฟอร์มไปที่ด้านซ้าย
        left_widget = QVBoxLayout()
        left_widget.addLayout(form_layout)
        left_widget.addStretch()
        
        # ด้านขวา: รายการงาน
        right_widget = QVBoxLayout()
        
        task_label = QLabel("รายการงานที่จะสร้าง:")
        right_widget.addWidget(task_label)
        
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(5)
        self.task_table.setHorizontalHeaderLabels([
            "Prompt", "เครื่องดนตรี", "อารมณ์", "ความยาว", ""
        ])
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        right_widget.addWidget(self.task_table)
        
        # เพิ่ม layouts ทั้งสองฝั่งไปที่ส่วนบน
        top_layout.addLayout(left_widget, 1)
        top_layout.addLayout(right_widget, 2)
        
        # เพิ่มส่วนบนไปที่ layout หลัก
        layout.addLayout(top_layout)
        
        # ส่วนกลาง: สถานะการทำงาน
        status_group = QVBoxLayout()
        
        status_label = QLabel("สถานะการทำงาน:")
        status_group.addWidget(status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        status_group.addWidget(self.progress_bar)
        
        self.status_label = QLabel("พร้อมสร้างเพลง")
        status_group.addWidget(self.status_label)
        
        layout.addLayout(status_group)
        
        # ส่วนล่าง: ปุ่มดำเนินการ
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("เริ่มสร้างเพลง")
        self.start_btn.clicked.connect(self._start_generation)
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("หยุด")
        self.stop_btn.clicked.connect(self._stop_generation)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        close_btn = QPushButton("ปิด")
        close_btn.clicked.connect(self.reject)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
    def _add_task(self):
        """เพิ่มงานใหม่เข้ารายการ"""
        # ตรวจสอบข้อมูล
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "ข้อผิดพลาด", "กรุณาระบุ prompt")
            return
            
        instruments = [item.text() for item in self.instruments_list.selectedItems()]
        if not instruments:
            QMessageBox.warning(
                self, "ข้อผิดพลาด", 
                "กรุณาเลือกเครื่องดนตรีอย่างน้อย 1 ชิ้น"
            )
            return
            
        # สร้างข้อมูลงาน
        task = {
            'prompt': prompt,
            'instruments': instruments,
            'mood': self.mood_input.currentText(),
            'duration': self.duration_input.value()
        }
        
        # เพิ่มเข้ารายการ
        self.tasks.append(task)
        
        # เพิ่มลงตาราง
        row = self.task_table.rowCount()
        self.task_table.insertRow(row)
        
        self.task_table.setItem(row, 0, QTableWidgetItem(prompt))
        self.task_table.setItem(row, 1, QTableWidgetItem(", ".join(instruments)))
        self.task_table.setItem(row, 2, QTableWidgetItem(task['mood']))
        self.task_table.setItem(row, 3, QTableWidgetItem(f"{task['duration']} วินาที"))
        
        # ปุ่มลบ
        delete_btn = QPushButton("ลบ")
        delete_btn.clicked.connect(lambda: self._delete_task(row))
        self.task_table.setCellWidget(row, 4, delete_btn)
        
        # รีเซ็ตฟอร์ม
        self.prompt_input.clear()
        for i in range(self.instruments_list.count()):
            self.instruments_list.item(i).setSelected(False)
        self.duration_input.setValue(30)
        
    def _delete_task(self, row: int):
        """ลบงานออกจากรายการ"""
        self.task_table.removeRow(row)
        del self.tasks[row]
        
    def _start_generation(self):
        """เริ่มสร้างเพลง"""
        if not self.tasks:
            QMessageBox.warning(
                self, "ข้อผิดพลาด",
                "กรุณาเพิ่มงานที่ต้องการสร้างก่อน"
            )
            return
            
        # ตรวจสอบชื่องาน
        job_name = self.job_name.text().strip()
        if not job_name:
            QMessageBox.warning(self, "ข้อผิดพลาด", "กรุณาระบุชื่องาน")
            return
            
        # เริ่มสร้างเพลง
        batch_generator.add_job(
            name=job_name,
            tasks=self.tasks,
            status_callback=self._on_job_status_changed
        )
        
        # อัพเดต UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("กำลังสร้างเพลง...")
        
    def _stop_generation(self):
        """หยุดสร้างเพลง"""
        reply = QMessageBox.question(
            self,
            "ยืนยันการหยุด",
            "คุณต้องการหยุดการสร้างเพลงหรือไม่?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            batch_generator.stop()
            
            # อัพเดต UI
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_label.setText("หยุดการสร้างเพลง")
            self.progress_bar.setValue(0)
            
    def _on_job_status_changed(self, job):
        """เรียกเมื่อสถานะงานเปลี่ยน"""
        self.current_job = job
        
        # คำนวณความคืบหน้า
        if job.total_tasks > 0:
            progress = int((job.completed_tasks / job.total_tasks) * 100)
            self.progress_bar.setValue(progress)
            
        # อัพเดตสถานะ
        status = (
            f"สร้างเพลงแล้ว {job.completed_tasks} จาก {job.total_tasks} เพลง "
            f"(ล้มเหลว {job.failed_tasks} เพลง)"
        )
        self.status_label.setText(status)
        
        # ถ้าเสร็จแล้ว
        if job.status in ['completed', 'failed']:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            
            # แสดงผลลัพธ์
            title = "สร้างเพลงเสร็จสิ้น" if job.status == 'completed' else "สร้างเพลงไม่สำเร็จ"
            QMessageBox.information(self, title, status)
            
    def _update_status(self):
        """อัพเดตสถานะจาก batch generator"""
        # ดึงงานปัจจุบัน
        current_job = batch_generator.get_current_job()
        
        if current_job != self.current_job:
            self.current_job = current_job
            
            if current_job:
                # อัพเดตสถานะ
                progress = int((current_job.completed_tasks / current_job.total_tasks) * 100)
                self.progress_bar.setValue(progress)
                
                status = (
                    f"สร้างเพลงแล้ว {current_job.completed_tasks} "
                    f"จาก {current_job.total_tasks} เพลง "
                    f"(ล้มเหลว {current_job.failed_tasks} เพลง)"
                )
                self.status_label.setText(status)
                
    def closeEvent(self, event):
        """เรียกเมื่อปิดไดอะล็อก"""
        if self.current_job and self.current_job.status == 'running':
            reply = QMessageBox.question(
                self,
                "ยืนยันการปิด",
                "กำลังสร้างเพลง คุณต้องการปิดหรือไม่?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                batch_generator.stop()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
