from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QLineEdit, QMessageBox,
    QFormLayout, QComboBox, QSpinBox, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, Any

from app.core.preset_manager import preset_manager
from app.config.settings import INSTRUMENT_CATEGORIES, MOODS

class PresetManagerDialog(QDialog):
    """ไดอะล็อกสำหรับจัดการ presets"""
    
    preset_selected = pyqtSignal(dict)  # ส่งสัญญาณเมื่อเลือก preset
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("จัดการ Presets")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        self._init_ui()
        self._load_presets()
        
    def _init_ui(self):
        """สร้างส่วนประกอบ UI"""
        layout = QHBoxLayout(self)
        
        # ด้านซ้าย: รายการ presets
        left_layout = QVBoxLayout()
        
        # ปุ่มสร้าง preset ใหม่
        new_preset_btn = QPushButton("สร้าง Preset ใหม่")
        new_preset_btn.clicked.connect(self._show_new_preset_dialog)
        left_layout.addWidget(new_preset_btn)
        
        # รายการ presets
        self.preset_list = QListWidget()
        self.preset_list.currentItemChanged.connect(self._on_preset_selected)
        left_layout.addWidget(self.preset_list)
        
        # ด้านขวา: รายละเอียด preset
        right_layout = QVBoxLayout()
        
        # ฟอร์มแสดงรายละเอียด
        form_layout = QFormLayout()
        
        self.name_label = QLabel()
        form_layout.addRow("ชื่อ:", self.name_label)
        
        self.prompt_label = QLabel()
        self.prompt_label.setWordWrap(True)
        form_layout.addRow("Prompt:", self.prompt_label)
        
        self.instruments_label = QLabel()
        self.instruments_label.setWordWrap(True)
        form_layout.addRow("เครื่องดนตรี:", self.instruments_label)
        
        self.mood_label = QLabel()
        form_layout.addRow("อารมณ์:", self.mood_label)
        
        self.duration_label = QLabel()
        form_layout.addRow("ความยาว:", self.duration_label)
        
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        form_layout.addRow("รายละเอียด:", self.description_label)
        
        right_layout.addLayout(form_layout)
        
        # ปุ่มดำเนินการ
        button_layout = QHBoxLayout()
        
        self.use_btn = QPushButton("ใช้งาน")
        self.use_btn.clicked.connect(self._on_use_clicked)
        self.use_btn.setEnabled(False)
        button_layout.addWidget(self.use_btn)
        
        self.edit_btn = QPushButton("แก้ไข")
        self.edit_btn.clicked.connect(self._show_edit_preset_dialog)
        self.edit_btn.setEnabled(False)
        button_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("ลบ")
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        self.delete_btn.setEnabled(False)
        button_layout.addWidget(self.delete_btn)
        
        self.favorite_btn = QPushButton("เพิ่มในรายการโปรด")
        self.favorite_btn.clicked.connect(self._on_favorite_clicked)
        self.favorite_btn.setEnabled(False)
        button_layout.addWidget(self.favorite_btn)
        
        right_layout.addLayout(button_layout)
        
        # เพิ่ม layout ทั้งสองฝั่ง
        layout.addLayout(left_layout, 1)
        layout.addLayout(right_layout, 2)
        
    def _load_presets(self):
        """โหลดรายการ presets"""
        self.preset_list.clear()
        
        # เพิ่ม presets ทั้งหมด
        for preset in preset_manager.get_all_presets():
            self.preset_list.addItem(preset['name'])
            
    def _show_preset_details(self, preset: Dict[str, Any]):
        """แสดงรายละเอียดของ preset"""
        self.name_label.setText(preset['name'])
        self.prompt_label.setText(preset['prompt'])
        self.instruments_label.setText(", ".join(preset['instruments']))
        self.mood_label.setText(preset['mood'])
        self.duration_label.setText(f"{preset['duration']} วินาที")
        self.description_label.setText(preset.get('description', '-'))
        
        # เปิดใช้งานปุ่มต่างๆ
        self.use_btn.setEnabled(True)
        self.edit_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.favorite_btn.setEnabled(True)
        
        # อัพเดตปุ่ม favorite
        is_favorite = any(p['name'] == preset['name'] for p in preset_manager.get_favorites())
        self.favorite_btn.setText("ลบจากรายการโปรด" if is_favorite else "เพิ่มในรายการโปรด")
        
    def _on_preset_selected(self, current, previous):
        """เรียกเมื่อเลือก preset"""
        if current is None:
            return
            
        preset = preset_manager.get_preset(current.text())
        if preset:
            self._show_preset_details(preset)
            
    def _show_new_preset_dialog(self):
        """แสดงไดอะล็อกสร้าง preset ใหม่"""
        dialog = PresetDialog(self)
        if dialog.exec():
            self._load_presets()
            
    def _show_edit_preset_dialog(self):
        """แสดงไดอะล็อกแก้ไข preset"""
        current_item = self.preset_list.currentItem()
        if not current_item:
            return
            
        preset = preset_manager.get_preset(current_item.text())
        if not preset:
            return
            
        dialog = PresetDialog(self, preset)
        if dialog.exec():
            self._load_presets()
            self._show_preset_details(preset_manager.get_preset(preset['name']))
            
    def _on_use_clicked(self):
        """เรียกเมื่อกดปุ่มใช้งาน"""
        current_item = self.preset_list.currentItem()
        if not current_item:
            return
            
        preset = preset_manager.get_preset(current_item.text())
        if preset:
            # เพิ่มเข้า recent
            preset_manager.add_to_recent(preset['name'])
            
            # ส่งสัญญาณไปยังหน้าหลัก
            self.preset_selected.emit(preset)
            self.accept()
            
    def _on_delete_clicked(self):
        """เรียกเมื่อกดปุ่มลบ"""
        current_item = self.preset_list.currentItem()
        if not current_item:
            return
            
        reply = QMessageBox.question(
            self,
            "ยืนยันการลบ",
            f"คุณต้องการลบ preset '{current_item.text()}' หรือไม่?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            preset_manager.delete_preset(current_item.text())
            self._load_presets()
            
            # รีเซ็ตรายละเอียด
            self.name_label.clear()
            self.prompt_label.clear()
            self.instruments_label.clear()
            self.mood_label.clear()
            self.duration_label.clear()
            self.description_label.clear()
            
            # ปิดปุ่มต่างๆ
            self.use_btn.setEnabled(False)
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.favorite_btn.setEnabled(False)
            
    def _on_favorite_clicked(self):
        """เรียกเมื่อกดปุ่มเพิ่ม/ลบรายการโปรด"""
        current_item = self.preset_list.currentItem()
        if not current_item:
            return
            
        preset_name = current_item.text()
        is_favorite = any(p['name'] == preset_name for p in preset_manager.get_favorites())
        
        if is_favorite:
            preset_manager.remove_from_favorites(preset_name)
            self.favorite_btn.setText("เพิ่มในรายการโปรด")
        else:
            preset_manager.add_to_favorites(preset_name)
            self.favorite_btn.setText("ลบจากรายการโปรด")

class PresetDialog(QDialog):
    """ไดอะล็อกสำหรับสร้าง/แก้ไข preset"""
    
    def __init__(self, parent=None, preset: Dict[str, Any] = None):
        super().__init__(parent)
        self.setWindowTitle("สร้าง Preset" if preset is None else "แก้ไข Preset")
        self.preset = preset
        self._init_ui()
        
        # ถ้าเป็นการแก้ไข ให้ใส่ข้อมูลเดิม
        if preset:
            self.name_input.setText(preset['name'])
            self.name_input.setEnabled(False)  # ไม่ให้แก้ไขชื่อ
            self.prompt_input.setText(preset['prompt'])
            
            # เลือกเครื่องดนตรี
            for i in range(self.instruments_list.count()):
                item = self.instruments_list.item(i)
                if item.text() in preset['instruments']:
                    item.setSelected(True)
                    
            # เลือกอารมณ์
            index = self.mood_input.findText(preset['mood'])
            if index >= 0:
                self.mood_input.setCurrentIndex(index)
                
            self.duration_input.setValue(preset['duration'])
            if preset.get('description'):
                self.description_input.setText(preset['description'])
        
    def _init_ui(self):
        """สร้างส่วนประกอบ UI"""
        layout = QVBoxLayout(self)
        
        # ฟอร์มข้อมูล
        form_layout = QFormLayout()
        
        # ชื่อ
        self.name_input = QLineEdit()
        form_layout.addRow("ชื่อ:", self.name_input)
        
        # Prompt
        self.prompt_input = QTextEdit()
        self.prompt_input.setAcceptRichText(False)
        form_layout.addRow("Prompt:", self.prompt_input)
        
        # เครื่องดนตรี
        self.instruments_list = QListWidget()
        self.instruments_list.setSelectionMode(
            QListWidget.SelectionMode.MultiSelection
        )
        
        # เพิ่มรายการเครื่องดนตรี
        for category, instruments in INSTRUMENT_CATEGORIES.items():
            for instrument in instruments:
                self.instruments_list.addItem(instrument)
                
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
        
        # รายละเอียด
        self.description_input = QTextEdit()
        self.description_input.setAcceptRichText(False)
        form_layout.addRow("รายละเอียด:", self.description_input)
        
        layout.addLayout(form_layout)
        
        # ปุ่มตกลง/ยกเลิก
        button_box = QHBoxLayout()
        
        save_btn = QPushButton("บันทึก")
        save_btn.clicked.connect(self._on_save_clicked)
        button_box.addWidget(save_btn)
        
        cancel_btn = QPushButton("ยกเลิก")
        cancel_btn.clicked.connect(self.reject)
        button_box.addWidget(cancel_btn)
        
        layout.addLayout(button_box)
        
    def _on_save_clicked(self):
        """เรียกเมื่อกดปุ่มบันทึก"""
        # ตรวจสอบข้อมูล
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "ข้อผิดพลาด", "กรุณาระบุชื่อ preset")
            return
            
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "ข้อผิดพลาด", "กรุณาระบุ prompt")
            return
            
        instruments = [item.text() for item in self.instruments_list.selectedItems()]
        if not instruments:
            QMessageBox.warning(self, "ข้อผิดพลาด", "กรุณาเลือกเครื่องดนตรีอย่างน้อย 1 ชิ้น")
            return
            
        # รวบรวมข้อมูล
        data = {
            'name': name,
            'prompt': prompt,
            'instruments': instruments,
            'mood': self.mood_input.currentText(),
            'duration': self.duration_input.value(),
            'description': self.description_input.toPlainText().strip()
        }
        
        try:
            if self.preset:
                # แก้ไข preset
                preset_manager.update_preset(**data)
            else:
                # สร้าง preset ใหม่
                preset_manager.add_preset(**data)
                
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "ข้อผิดพลาด", str(e))
