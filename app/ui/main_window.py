import os
import sys
import time
from pathlib import Path
from PyQt6.QtCore import Qt, QSize, pyqtSlot, pyqtSignal
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QStatusBar, QProgressBar, 
    QSplitter, QTabWidget, QMessageBox, QDialog,
    QMenuBar, QMenu, QToolBar, QApplication
)
from PyQt6.QtGui import QIcon, QAction, QFont, QPixmap

# นำเข้าคอมโพเนนต์ต่างๆ
from app.ui.components.resource_monitor import ResourceMonitor
from app.ui.components.music_generator_form import MusicGeneratorForm
from app.ui.components.music_player import MusicPlayer

# นำเข้าโมดูลหลัก
from app.core.ai_engine import load_ai_model, generate_music
from app.core.audio_utils import save_generated_audio
from app.core.utilities import logger

class MainWindow(QMainWindow):
    """หน้าต่างหลักของโปรแกรม Generative Music"""
    
    def __init__(self):
        super().__init__()
        
        # ตั้งค่าคุณสมบัติหน้าต่าง
        self.setWindowTitle("Generative Music")
        self.setMinimumSize(1000, 700)
        
        # สถานะการโหลดโมเดล
        self.model_loaded = False
        
        # สร้างส่วนประกอบ UI
        self._init_ui()
        
        # เชื่อมต่อสัญญาณ
        self._connect_signals()
        
        # โหลดโมเดล AI
        self._load_ai_model()
        
    def _init_ui(self):
        """สร้างส่วนประกอบ UI"""
        # สร้าง central widget
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # สร้าง toolbar
        self._create_toolbar()
        
        # สร้าง menubar
        self._create_menu()
        
        # แบ่งพื้นที่หน้าต่างด้วย Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # ด้านซ้าย: ฟอร์มสร้างเพลง
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # เพิ่ม resource monitor และฟอร์มสร้างเพลง
        self.resource_monitor = ResourceMonitor()
        self.music_gen_form = MusicGeneratorForm()
        
        left_layout.addWidget(self.resource_monitor)
        left_layout.addWidget(self.music_gen_form)
        
        # ด้านขวา: เครื่องเล่นเพลง
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        self.music_player = MusicPlayer()
        right_layout.addWidget(self.music_player)
        
        # เพิ่มทั้งสองส่วนไปที่ splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        
        # ตั้งค่าขนาดเริ่มต้น (40% ซ้าย, 60% ขวา)
        splitter.setSizes([400, 600])
        
        # เพิ่ม splitter ไปที่ main layout
        main_layout.addWidget(splitter)
        
        # สร้าง status bar
        self._create_status_bar()
        
        # ตั้ง central widget
        self.setCentralWidget(central_widget)
        
    def _create_menu(self):
        """สร้างเมนูบาร์"""
        menubar = self.menuBar()
        
        # เมนูไฟล์
        file_menu = menubar.addMenu("ไฟล์")
        
        # สร้างเพลงใหม่
        new_action = QAction("สร้างเพลงใหม่", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._focus_music_gen_form)
        
        # จัดการ Presets
        manage_presets_action = QAction("จัดการ Presets", self)
        manage_presets_action.setShortcut("Ctrl+P")
        manage_presets_action.triggered.connect(self._show_preset_manager)
        
        # สร้างเพลงแบบ Batch
        batch_generate_action = QAction("สร้างเพลงแบบ Batch", self)
        batch_generate_action.setShortcut("Ctrl+B")
        batch_generate_action.triggered.connect(self._show_batch_generator)
        
        # แต่งเพลงแบบมีส่วนร่วม
        interactive_action = QAction("แต่งเพลงแบบมีส่วนร่วม", self)
        interactive_action.setShortcut("Ctrl+I")
        interactive_action.triggered.connect(self._show_interactive_generator)
        
        # ส่งออกเพลง
        export_action = QAction("ส่งออกเพลง", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(lambda: self.music_player._on_export_clicked())
        
        # ออกจากโปรแกรม
        exit_action = QAction("ออกจากโปรแกรม", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        
        file_menu.addAction(new_action)
        file_menu.addAction(manage_presets_action)
        file_menu.addAction(batch_generate_action)
        file_menu.addAction(interactive_action)
        file_menu.addSeparator()
        file_menu.addAction(export_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)
        
        # เมนู AI
        ai_menu = menubar.addMenu("AI")
        
        # โหลดโมเดลใหม่
        reload_model_action = QAction("โหลดโมเดลใหม่", self)
        reload_model_action.triggered.connect(self._load_ai_model)
        
        ai_menu.addAction(reload_model_action)
        
        # เมนูเกี่ยวกับ
        help_menu = menubar.addMenu("ช่วยเหลือ")
        
        # เกี่ยวกับโปรแกรม
        about_action = QAction("เกี่ยวกับโปรแกรม", self)
        about_action.triggered.connect(self._show_about_dialog)
        
        help_menu.addAction(about_action)
        
    def _create_toolbar(self):
        """สร้าง toolbar"""
        toolbar = QToolBar("เครื่องมือหลัก")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # ปุ่มสร้างเพลง
        new_music_action = QAction("🎵 สร้างเพลง", self)
        new_music_action.triggered.connect(self._focus_music_gen_form)
        toolbar.addAction(new_music_action)
        
        # ปุ่มจัดการ Presets
        presets_action = QAction("⚙️ Presets", self)
        presets_action.triggered.connect(self._show_preset_manager)
        toolbar.addAction(presets_action)
        
        # ปุ่มสร้างเพลงแบบ Batch 
        batch_action = QAction("📑 Batch", self)
        batch_action.triggered.connect(self._show_batch_generator)
        toolbar.addAction(batch_action)
        
        # ปุ่มแต่งเพลงแบบมีส่วนร่วม
        interactive_action = QAction("🎹 Interactive", self)
        interactive_action.triggered.connect(self._show_interactive_generator)
        toolbar.addAction(interactive_action)
        
        toolbar.addSeparator()
        
        # ปุ่มรายการเพลง
        playlist_action = QAction("🎶 รายการเพลง", self)
        playlist_action.triggered.connect(self._focus_music_player)
        toolbar.addAction(playlist_action)
        
        toolbar.addSeparator()
        
        # ปุ่มเล่นเพลง
        play_action = QAction("▶️ เล่น", self)
        play_action.triggered.connect(lambda: self.music_player._on_play_clicked())
        toolbar.addAction(play_action)
        
        # ปุ่มหยุดเพลง
        stop_action = QAction("⏹️ หยุด", self)
        stop_action.triggered.connect(lambda: self.music_player._on_stop_clicked())
        toolbar.addAction(stop_action)
        
    def _create_status_bar(self):
        """สร้าง status bar"""
        status_bar = QStatusBar()
        
        # ข้อความสถานะ
        self.status_label = QLabel("พร้อมใช้งาน")
        status_bar.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)
        status_bar.addPermanentWidget(self.progress_bar)
        
        # AI Model status
        self.model_status_label = QLabel("โมเดล AI: กำลังโหลด...")
        status_bar.addPermanentWidget(self.model_status_label)
        
        self.setStatusBar(status_bar)
        
    def _connect_signals(self):
        """เชื่อมต่อสัญญาณ"""
        # เชื่อมต่อฟอร์มสร้างเพลงกับฟังก์ชันสร้างเพลง
        self.music_gen_form.generation_requested.connect(self._on_generation_requested)
        
    def _focus_music_gen_form(self):
        """โฟกัสไปที่ฟอร์มสร้างเพลง"""
        self.music_gen_form.setFocus()
        self.music_gen_form.prompt_input.setFocus()
        
    def _focus_music_player(self):
        """โฟกัสไปที่เครื่องเล่นเพลง"""
        self.music_player.setFocus()
        self.music_player.playlist.setFocus()
        
    # Signal สำหรับการโหลดโมเดล
    model_loaded_signal = pyqtSignal(bool)
    
    def _load_ai_model(self):
        """โหลดโมเดล AI"""
        # อัพเดตสถานะ
        self.model_status_label.setText("โมเดล AI: กำลังโหลด...")
        self.status_label.setText("กำลังโหลดโมเดล AI...")
        self.model_loaded = False
        self.music_gen_form.setEnabled(False)
        
        # เชื่อมต่อ signal กับ slot
        self.model_loaded_signal.connect(self._on_model_loaded)
        
        # โหลดโมเดลโดยส่ง signal callback
        load_ai_model(lambda success: self.model_loaded_signal.emit(success))
        
    @pyqtSlot(bool)
    def _on_model_loaded(self, success):
        """เรียกเมื่อโหลดโมเดลเสร็จ (เรียกใน UI thread)"""
        if success:
            self.model_status_label.setText("โมเดล AI: พร้อมใช้งาน")
            self.status_label.setText("พร้อมใช้งาน")
            self.model_loaded = True
            self.music_gen_form.setEnabled(True)
            self._focus_music_gen_form()
        else:
            self.model_status_label.setText("โมเดล AI: โหลดไม่สำเร็จ")
            self.status_label.setText("ไม่สามารถโหลดโมเดลได้ กรุณาลองใหม่")
            self.model_loaded = False
            
            # แสดงข้อความข้อผิดพลาด
            QMessageBox.critical(
                self, 
                "เกิดข้อผิดพลาด", 
                "ไม่สามารถโหลดโมเดล AI ได้ กรุณาตรวจสอบการเชื่อมต่ออินเตอร์เน็ตและลองใหม่อีกครั้ง"
            )
            
    def _on_generation_requested(self, params):
        """เรียกเมื่อมีการขอสร้างเพลง"""
        # ตรวจสอบว่าโมเดลพร้อมใช้งานหรือยัง
        if not self.model_loaded:
            QMessageBox.warning(
                self, 
                "โมเดลยังไม่พร้อม", 
                "กำลังโหลดโมเดล AI กรุณารอสักครู่..."
            )
            self.music_gen_form.unlock_form()
            return
            
        # แสดงสถานะกำลังสร้างเพลง
        is_preview = params.get('is_preview', False)
        
        if is_preview:
            self.status_label.setText(f"กำลังสร้างตัวอย่างเพลง...")
        else:
            self.status_label.setText(f"กำลังสร้างเพลง {params['mood']} ความยาว {params['duration']} วินาที...")
            
        # แสดง progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)  # เริ่มต้นที่ 10%
        
        # เรียกฟังก์ชันสร้างเพลง
        generate_music(
            prompt=params['prompt'],
            duration=params['duration'],
            instruments=params['instruments'],
            mood=params['mood'],
            callback=self._on_generation_completed
        )
        
    def _on_generation_completed(self, success, result):
        """เรียกเมื่อสร้างเพลงเสร็จ"""
        # อัพเดต progress bar
        self.progress_bar.setValue(70)
        
        if not success:
            # แสดงข้อความข้อผิดพลาด
            QMessageBox.critical(
                self, 
                "เกิดข้อผิดพลาด", 
                f"ไม่สามารถสร้างเพลงได้: {result}"
            )
            self.status_label.setText("เกิดข้อผิดพลาดในการสร้างเพลง")
            self.progress_bar.setVisible(False)
            self.music_gen_form.unlock_form()
            return
            
        # บันทึกไฟล์เพลง
        self.status_label.setText("กำลังบันทึกไฟล์เพลง...")
        
        # แยกข้อมูลเสียงและ metadata
        audio_data = result['audio_data']
        metadata = result['metadata']
        
        # บันทึกไฟล์
        file_path = save_generated_audio(audio_data, metadata)
        
        # อัพเดต progress bar
        self.progress_bar.setValue(90)
        
        # อัพเดตรายการเพลง
        self.music_player._load_playlist()
        
        # เล่นเพลงที่สร้างเสร็จ
        if file_path.exists():
            self.music_player.play_file(file_path)
            
        # อัพเดตสถานะ
        duration = int(metadata['duration'])
        self.status_label.setText(f"สร้างเพลงเสร็จแล้ว (ความยาว {duration} วินาที)")
        
        # ซ่อน progress bar
        self.progress_bar.setValue(100)
        QApplication.processEvents()  # อัพเดต UI
        time.sleep(0.5)  # แสดง 100% สักครู่
        self.progress_bar.setVisible(False)
        
        # ปลดล็อคฟอร์ม
        self.music_gen_form.unlock_form()
        
    def _show_preset_manager(self):
        """แสดงหน้าจัดการ presets"""
        from app.ui.components.preset_manager_dialog import PresetManagerDialog
        dialog = PresetManagerDialog(self)
        dialog.preset_selected.connect(self._on_preset_selected)
        dialog.exec()
        
    def _show_batch_generator(self):
        """แสดงหน้าสร้างเพลงแบบ batch"""
        from app.ui.components.batch_generator_dialog import BatchGeneratorDialog
        dialog = BatchGeneratorDialog(self)
        dialog.exec()
        
    def _show_interactive_generator(self):
        """แสดงหน้าแต่งเพลงแบบมีส่วนร่วม"""
        from app.ui.components.interactive_generator_dialog import InteractiveGeneratorDialog
        dialog = InteractiveGeneratorDialog(self)
        dialog.exec()
        
    def _on_preset_selected(self, preset):
        """เรียกเมื่อเลือก preset จากหน้าจัดการ presets"""
        # ใส่ข้อมูลจาก preset ลงในฟอร์ม
        self.music_gen_form.set_form_data(
            prompt=preset['prompt'],
            instruments=preset['instruments'],
            mood=preset['mood'],
            duration=preset['duration']
        )
        
    def _show_about_dialog(self):
        """แสดงไดอะล็อกเกี่ยวกับโปรแกรม"""
        QMessageBox.about(
            self,
            "เกี่ยวกับโปรแกรม",
            """<h1>Generative Music</h1>
            <p>โปรแกรมสร้างเพลงอัตโนมัติด้วย AI</p>
            <p>พัฒนาโดย Genmusic Team</p>
            <p>เวอร์ชัน 1.0.0</p>
            <p>ใช้ MusicGen จาก Meta AI Research</p>
            """
        )
        
    def closeEvent(self, event):
        """เรียกเมื่อปิดหน้าต่าง"""
        # แสดงคำถามยืนยันการปิดโปรแกรม
        reply = QMessageBox.question(
            self, 
            "ยืนยันการปิดโปรแกรม", 
            "คุณต้องการปิดโปรแกรมหรือไม่?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # หยุดเพลงที่กำลังเล่น
            self.music_player.media_player.stop()
            self.resource_monitor.stop_monitoring()
            logger.info("ปิดโปรแกรม")
            event.accept()
        else:
            event.ignore()
