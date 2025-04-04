from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QLineEdit, QMessageBox,
    QFormLayout, QComboBox, QSpinBox, QTextEdit,
    QTabWidget, QWidget, QProgressBar, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from app.core.interactive_generator import interactive_generator
from app.ui.components.music_player import MusicPlayer
from app.config.settings import INSTRUMENT_CATEGORIES, MOODS, MAX_DURATION

class InteractiveGeneratorDialog(QDialog):
    """ไดอะล็อกสำหรับแต่งเพลงแบบมีส่วนร่วม"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("แต่งเพลงแบบมีส่วนร่วม")
        self.setMinimumWidth(1000)
        self.setMinimumHeight(700)
        
        self.session = None
        self._init_ui()
        
    def _init_ui(self):
        """สร้างส่วนประกอบ UI"""
        layout = QVBoxLayout(self)
        
        # ส่วนบน: ชื่อ Session
        top_layout = QHBoxLayout()
        
        top_layout.addWidget(QLabel("ชื่อ Session:"))
        self.session_name = QLineEdit()
        top_layout.addWidget(self.session_name)
        
        start_btn = QPushButton("เริ่ม Session")
        start_btn.clicked.connect(self._start_session)
        top_layout.addWidget(start_btn)
        
        layout.addLayout(top_layout)
        
        # ส่วนกลาง: แท็บต่างๆ
        self.tab_widget = QTabWidget()
        
        # แท็บสร้างเพลงใหม่
        new_track_tab = QWidget()
        self._init_new_track_tab(new_track_tab)
        self.tab_widget.addTab(new_track_tab, "สร้างเพลงใหม่")
        
        # แท็บปรับแต่งเพลง
        adjust_tab = QWidget()
        self._init_adjust_tab(adjust_tab)
        self.tab_widget.addTab(adjust_tab, "ปรับแต่งเพลง")
        
        # แท็บประวัติการแก้ไข
        history_tab = QWidget()
        self._init_history_tab(history_tab)
        self.tab_widget.addTab(history_tab, "ประวัติการแก้ไข")
        
        layout.addWidget(self.tab_widget)
        
        # ส่วนล่าง: เครื่องเล่นเพลง
        self.music_player = MusicPlayer()
        layout.addWidget(self.music_player)
        
        # ล็อคแท็บจนกว่าจะเริ่ม session
        self.tab_widget.setEnabled(False)
        self.music_player.setEnabled(False)
        
    def _init_new_track_tab(self, tab: QWidget):
        """สร้าง UI สำหรับแท็บสร้างเพลงใหม่"""
        layout = QVBoxLayout(tab)
        
        # ฟอร์มข้อมูล
        form = QFormLayout()
        
        # Prompt
        self.prompt_input = QTextEdit()
        self.prompt_input.setAcceptRichText(False)
        self.prompt_input.setMaximumHeight(100)
        form.addRow("Prompt:", self.prompt_input)
        
        # เครื่องดนตรี
        self.instruments_list = QListWidget()
        self.instruments_list.setSelectionMode(
            QListWidget.SelectionMode.MultiSelection
        )
        for category, instruments in INSTRUMENT_CATEGORIES.items():
            for instrument in instruments:
                self.instruments_list.addItem(instrument)
        self.instruments_list.setMaximumHeight(150)
        form.addRow("เครื่องดนตรี:", self.instruments_list)
        
        # อารมณ์
        self.mood_input = QComboBox()
        self.mood_input.addItems(MOODS)
        form.addRow("อารมณ์:", self.mood_input)
        
        # ความยาว
        self.duration_input = QSpinBox()
        self.duration_input.setRange(10, 300)
        self.duration_input.setSingleStep(10)
        self.duration_input.setValue(30)
        form.addRow("ความยาว (วินาที):", self.duration_input)
        
        layout.addLayout(form)
        
        # ปุ่มสร้างเพลง
        generate_btn = QPushButton("สร้างเพลง")
        generate_btn.clicked.connect(self._generate_new_track)
        layout.addWidget(generate_btn)
        
        layout.addStretch()
        
    def _init_adjust_tab(self, tab: QWidget):
        """สร้าง UI สำหรับแท็บปรับแต่งเพลง"""
        layout = QVBoxLayout(tab)
        
        # ปุ่มดำเนินการ
        button_layout = QHBoxLayout()
        
        # ปรับเครื่องดนตรี
        instruments_btn = QPushButton("ปรับเครื่องดนตรี")
        instruments_btn.clicked.connect(self._show_adjust_instruments_dialog)
        button_layout.addWidget(instruments_btn)
        
        # ปรับอารมณ์
        mood_btn = QPushButton("ปรับอารมณ์")
        mood_btn.clicked.connect(self._show_adjust_mood_dialog)
        button_layout.addWidget(mood_btn)
        
        # ต่อความยาว
        extend_btn = QPushButton("ต่อความยาว")
        extend_btn.clicked.connect(self._show_extend_duration_dialog)
        button_layout.addWidget(extend_btn)
        
        layout.addLayout(button_layout)
        
        # ปุ่ม Undo/Redo
        history_layout = QHBoxLayout()
        
        undo_btn = QPushButton("ย้อนกลับ")
        undo_btn.clicked.connect(self._undo)
        history_layout.addWidget(undo_btn)
        
        redo_btn = QPushButton("ทำซ้ำ")
        redo_btn.clicked.connect(self._redo)
        history_layout.addWidget(redo_btn)
        
        layout.addLayout(history_layout)
        
        layout.addStretch()
        
    def _init_history_tab(self, tab: QWidget):
        """สร้าง UI สำหรับแท็บประวัติการแก้ไข"""
        layout = QVBoxLayout(tab)
        
        self.history_list = QListWidget()
        self.history_list.currentItemChanged.connect(self._on_history_selected)
        layout.addWidget(self.history_list)
        
    def _start_session(self):
        """เริ่ม session ใหม่"""
        name = self.session_name.text().strip()
        if not name:
            QMessageBox.warning(self, "ข้อผิดพลาด", "กรุณาระบุชื่อ session")
            return
            
        try:
            self.session = interactive_generator.create_session(name)
            
            # ปลดล็อคส่วนต่างๆ
            self.tab_widget.setEnabled(True)
            self.music_player.setEnabled(True)
            self.session_name.setEnabled(False)
            
            QMessageBox.information(
                self, "เริ่ม Session",
                f"เริ่ม session '{name}' แล้ว"
            )
            
        except ValueError as e:
            QMessageBox.critical(self, "ข้อผิดพลาด", str(e))
            
    def _generate_new_track(self):
        """สร้างเพลงใหม่"""
        if not self.session:
            return
            
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
            
        try:
            # สร้างเพลง
            result = self.session.start_new_track(
                prompt=prompt,
                instruments=instruments,
                mood=self.mood_input.currentText(),
                duration=self.duration_input.value()
            )
            
            # อัพเดตประวัติ
            self._update_history()
            
            # เล่นเพลง
            self.music_player.play_file(Path(result['file_path']))
            
            # เปลี่ยนไปแท็บปรับแต่ง
            self.tab_widget.setCurrentIndex(1)
            
        except Exception as e:
            QMessageBox.critical(self, "ข้อผิดพลาด", str(e))
            
    def _show_adjust_instruments_dialog(self):
        """แสดงไดอะล็อกปรับเครื่องดนตรี"""
        if not self.session:
            return
            
        dialog = AdjustInstrumentsDialog(self)
        if dialog.exec():
            # อัพเดตประวัติ
            self._update_history()
            
            # เล่นเพลงเวอร์ชันใหม่
            current = self.session.get_current_version()
            if current:
                self.music_player.play_file(Path(current['file_path']))
                
    def _show_adjust_mood_dialog(self):
        """แสดงไดอะล็อกปรับอารมณ์"""
        if not self.session:
            return
            
        dialog = AdjustMoodDialog(self)
        if dialog.exec():
            # อัพเดตประวัติ
            self._update_history()
            
            # เล่นเพลงเวอร์ชันใหม่
            current = self.session.get_current_version()
            if current:
                self.music_player.play_file(Path(current['file_path']))
                
    def _show_extend_duration_dialog(self):
        """แสดงไดอะล็อกต่อความยาว"""
        if not self.session:
            return
            
        dialog = ExtendDurationDialog(self)
        if dialog.exec():
            # อัพเดตประวัติ
            self._update_history()
            
            # เล่นเพลงเวอร์ชันใหม่
            current = self.session.get_current_version()
            if current:
                self.music_player.play_file(Path(current['file_path']))
                
    def _undo(self):
        """ย้อนกลับการแก้ไข"""
        if not self.session:
            return
            
        result = self.session.undo()
        if result:
            # อัพเดตประวัติ
            self._update_history()
            
            # เล่นเพลงเวอร์ชันก่อนหน้า
            self.music_player.play_file(Path(result['file_path']))
        else:
            QMessageBox.information(
                self, "ย้อนกลับ",
                "ไม่สามารถย้อนกลับได้อีก"
            )
            
    def _redo(self):
        """ทำซ้ำการแก้ไข"""
        if not self.session:
            return
            
        result = self.session.redo()
        if result:
            # อัพเดตประวัติ
            self._update_history()
            
            # เล่นเพลงเวอร์ชันถัดไป
            self.music_player.play_file(Path(result['file_path']))
        else:
            QMessageBox.information(
                self, "ทำซ้ำ",
                "ไม่สามารถทำซ้ำได้อีก"
            )
            
    def _update_history(self):
        """อัพเดตรายการประวัติ"""
        if not self.session:
            return
            
        self.history_list.clear()
        
        for entry in self.session.get_history():
            # สร้างข้อความแสดงการแก้ไข
            if entry['type'] == 'new':
                text = f"v{entry['version']}: สร้างเพลงใหม่"
            elif entry['type'] == 'adjust_instruments':
                text = f"v{entry['version']}: ปรับเครื่องดนตรี"
            elif entry['type'] == 'adjust_mood':
                text = f"v{entry['version']}: ปรับอารมณ์เป็น {entry['mood']}"
            elif entry['type'] == 'extend_duration':
                text = f"v{entry['version']}: ต่อความยาว +{entry['additional_seconds']} วินาที"
            else:
                text = f"v{entry['version']}: แก้ไข"
                
            # เพิ่มเวลาที่แก้ไข
            timestamp = datetime.fromisoformat(entry['timestamp'])
            text += f" ({timestamp.strftime('%H:%M:%S')})"
            
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            
            # ไฮไลท์เวอร์ชันปัจจุบัน
            if entry['version'] == self.session.current_version:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                
            self.history_list.addItem(item)
            
    def _on_history_selected(self, current, previous):
        """เรียกเมื่อเลือกรายการในประวัติ"""
        if not current:
            return
            
        entry = current.data(Qt.ItemDataRole.UserRole)
        if entry and 'file_path' in entry:
            self.music_player.play_file(Path(entry['file_path']))
            
    def closeEvent(self, event):
        """เรียกเมื่อปิดไดอะล็อก"""
        if self.session:
            reply = QMessageBox.question(
                self,
                "ยืนยันการปิด",
                f"คุณต้องการปิด session '{self.session.name}' หรือไม่?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                interactive_generator.close_session(self.session.name)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

class AdjustInstrumentsDialog(QDialog):
    """ไดอะล็อกสำหรับปรับเครื่องดนตรี"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("ปรับเครื่องดนตรี")
        self.session = parent.session
        self._init_ui()
        
    def _init_ui(self):
        """สร้างส่วนประกอบ UI"""
        layout = QVBoxLayout(self)
        
        # รายการเครื่องดนตรี
        self.instruments_list = QListWidget()
        self.instruments_list.setSelectionMode(
            QListWidget.SelectionMode.MultiSelection
        )
        for category, instruments in INSTRUMENT_CATEGORIES.items():
            for instrument in instruments:
                self.instruments_list.addItem(instrument)
        layout.addWidget(self.instruments_list)
        
        # ส่วนที่ต้องการคงไว้
        layout.addWidget(QLabel("ส่วนที่ต้องการคงไว้ (เลือกได้หลายอย่าง):"))
        
        self.keep_elements = QListWidget()
        self.keep_elements.setSelectionMode(
            QListWidget.SelectionMode.MultiSelection
        )
        self.keep_elements.addItems([
            "ทำนอง (Melody)",
            "จังหวะ (Rhythm)",
            "เสียงประสาน (Harmony)",
            "โครงสร้าง (Structure)"
        ])
        layout.addWidget(self.keep_elements)
        
        # ปุ่มตกลง/ยกเลิก
        button_box = QHBoxLayout()
        
        apply_btn = QPushButton("ปรับเครื่องดนตรี")
        apply_btn.clicked.connect(self._on_apply_clicked)
        button_box.addWidget(apply_btn)
        
        cancel_btn = QPushButton("ยกเลิก")
        cancel_btn.clicked.connect(self.reject)
        button_box.addWidget(cancel_btn)
        
        layout.addLayout(button_box)
        
    def _on_apply_clicked(self):
        """เรียกเมื่อกดปุ่มปรับเครื่องดนตรี"""
        instruments = [item.text() for item in self.instruments_list.selectedItems()]
        if not instruments:
            QMessageBox.warning(
                self, "ข้อผิดพลาด", 
                "กรุณาเลือกเครื่องดนตรีอย่างน้อย 1 ชิ้น"
            )
            return
            
        keep_elements = [item.text() for item in self.keep_elements.selectedItems()]
        
        try:
            self.session.adjust_instruments(
                instruments=instruments,
                keep_elements=keep_elements if keep_elements else None
            )
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "ข้อผิดพลาด", str(e))

class AdjustMoodDialog(QDialog):
    """ไดอะล็อกสำหรับปรับอารมณ์เพลง"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("ปรับอารมณ์เพลง")
        self.session = parent.session
        self._init_ui()
        
    def _init_ui(self):
        """สร้างส่วนประกอบ UI"""
        layout = QVBoxLayout(self)
        
        # เลือกอารมณ์
        layout.addWidget(QLabel("เลือกอารมณ์ใหม่:"))
        
        self.mood_input = QComboBox()
        self.mood_input.addItems(MOODS)
        layout.addWidget(self.mood_input)
        
        # ปุ่มตกลง/ยกเลิก
        button_box = QHBoxLayout()
        
        apply_btn = QPushButton("ปรับอารมณ์")
        apply_btn.clicked.connect(self._on_apply_clicked)
        button_box.addWidget(apply_btn)
        
        cancel_btn = QPushButton("ยกเลิก")
        cancel_btn.clicked.connect(self.reject)
        button_box.addWidget(cancel_btn)
        
        layout.addLayout(button_box)
        
    def _on_apply_clicked(self):
        """เรียกเมื่อกดปุ่มปรับอารมณ์"""
        try:
            self.session.adjust_mood(self.mood_input.currentText())
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "ข้อผิดพลาด", str(e))

class ExtendDurationDialog(QDialog):
    """ไดอะล็อกสำหรับต่อความยาวเพลง"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("ต่อความยาวเพลง")
        self.session = parent.session
        self._init_ui()
        
    def _init_ui(self):
        """สร้างส่วนประกอบ UI"""
        layout = QVBoxLayout(self)
        
        current = self.session.get_current_version()
        if current:
            current_duration = int(current['duration'])
            remaining = MAX_DURATION - current_duration
            
            layout.addWidget(QLabel(
                f"ความยาวปัจจุบัน: {current_duration} วินาที\n"
                f"สามารถต่อได้อีก: {remaining} วินาที"
            ))
            
            # เลือกความยาวที่จะต่อ
            layout.addWidget(QLabel("เลือกความยาวที่ต้องการต่อ (วินาที):"))
            
            self.duration_input = QSpinBox()
            self.duration_input.setRange(10, remaining)
            self.duration_input.setSingleStep(10)
            self.duration_input.setValue(min(30, remaining))
            layout.addWidget(self.duration_input)
            
            # ปุ่มตกลง/ยกเลิก
            button_box = QHBoxLayout()
            
            apply_btn = QPushButton("ต่อความยาว")
            apply_btn.clicked.connect(self._on_apply_clicked)
            button_box.addWidget(apply_btn)
            
            cancel_btn = QPushButton("ยกเลิก")
            cancel_btn.clicked.connect(self.reject)
            button_box.addWidget(cancel_btn)
            
            layout.addLayout(button_box)
            
    def _on_apply_clicked(self):
        """เรียกเมื่อกดปุ่มต่อความยาว"""
        try:
            self.session.extend_duration(self.duration_input.value())
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "ข้อผิดพลาด", str(e))
