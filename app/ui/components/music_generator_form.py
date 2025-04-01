from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QTextEdit, QComboBox, QCheckBox,
    QPushButton, QSlider, QSpinBox, QFrame, QListWidget,
    QMessageBox
)
from PyQt6.QtGui import QFont

from app.config.settings import (
    INSTRUMENT_CATEGORIES, MOODS, 
    DURATION_PRESETS, MAX_DURATION
)
from app.core.utilities import estimate_generation_time, seconds_to_time_format

class MusicGeneratorForm(QFrame):
    """ฟอร์มสำหรับกรอกข้อมูลการสร้างเพลง"""
    
    # สัญญาณที่จะส่งเมื่อผู้ใช้กดปุ่มสร้างเพลง
    generation_requested = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        
        # ตั้งค่า UI
        self._init_ui()
        
        # เชื่อมต่อสัญญาณ
        self._connect_signals()
        
    def _init_ui(self):
        """สร้างส่วนประกอบ UI"""
        main_layout = QVBoxLayout(self)
        
        # หัวข้อ
        title_label = QLabel("สร้างเพลงใหม่")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        main_layout.addWidget(title_label)
        
        # ส่วน Prompt
        prompt_group = QGroupBox("คำอธิบายเพลง (Prompt)")
        prompt_layout = QVBoxLayout(prompt_group)
        
        prompt_desc = QLabel("อธิบายเพลงที่ต้องการสร้าง:")
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("อธิบายเพลงที่ต้องการ เช่น 'เพลงเปียโนเศร้า ช้า ผ่อนคลาย'")
        self.prompt_input.setMaximumHeight(80)
        
        prompt_layout.addWidget(prompt_desc)
        prompt_layout.addWidget(self.prompt_input)
        
        main_layout.addWidget(prompt_group)
        
        # ส่วนเครื่องดนตรี
        instrument_group = QGroupBox("เครื่องดนตรี")
        instrument_layout = QVBoxLayout(instrument_group)
        
        self.instrument_combos = []
        for i in range(3):  # สร้าง combo box สำหรับเลือกเครื่องดนตรี 3 ชิ้น
            combo = QComboBox()
            if i == 0:
                # จำเป็นต้องเลือกเครื่องดนตรีอย่างน้อย 1 ชิ้น
                combo.addItem("-- เลือกเครื่องดนตรี --")
            else:
                # เครื่องดนตรีเพิ่มเติมสามารถเว้นว่างได้
                combo.addItem("-- ไม่เลือก --")
                
            # เพิ่มเครื่องดนตรีเข้า combo box แยกตามประเภท
            for category, instruments in INSTRUMENT_CATEGORIES.items():
                combo.addItem(f"=== {category} ===")
                for instrument in instruments:
                    combo.addItem(instrument)
            
            self.instrument_combos.append(combo)
            instrument_layout.addWidget(combo)
        
        main_layout.addWidget(instrument_group)
        
        # ส่วนอารมณ์เพลง
        mood_group = QGroupBox("อารมณ์เพลง")
        mood_layout = QVBoxLayout(mood_group)
        
        self.mood_combo = QComboBox()
        self.mood_combo.addItem("-- เลือกอารมณ์ --")
        self.mood_combo.addItems(MOODS)
        mood_layout.addWidget(self.mood_combo)
        
        main_layout.addWidget(mood_group)
        
        # ส่วนความยาวเพลง
        duration_group = QGroupBox("ความยาวเพลง")
        duration_layout = QVBoxLayout(duration_group)
        
        # สร้าง slider และ spin box
        duration_inner_layout = QHBoxLayout()
        self.duration_slider = QSlider(Qt.Orientation.Horizontal)
        self.duration_slider.setRange(30, MAX_DURATION)  # 30 วินาที ถึง MAX_DURATION
        self.duration_slider.setValue(60)  # 1 นาที
        self.duration_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.duration_slider.setTickInterval(60)  # ทุก 1 นาที
        
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(30, MAX_DURATION)
        self.duration_spin.setValue(60)
        self.duration_spin.setSuffix(" วินาที")
        
        duration_inner_layout.addWidget(self.duration_slider)
        duration_inner_layout.addWidget(self.duration_spin)
        
        # เพิ่มปุ่ม preset
        preset_layout = QHBoxLayout()
        preset_label = QLabel("Preset: ")
        preset_layout.addWidget(preset_label)
        
        for duration in DURATION_PRESETS:
            seconds = duration
            preset_button = QPushButton(seconds_to_time_format(seconds))
            preset_button.setProperty("duration", seconds)
            preset_button.clicked.connect(self._on_preset_clicked)
            preset_layout.addWidget(preset_button)
        
        duration_layout.addLayout(duration_inner_layout)
        duration_layout.addLayout(preset_layout)
        
        # แสดงเวลาประมาณในการสร้าง
        self.estimated_time_label = QLabel("เวลาประมาณในการสร้าง: 10 วินาที")
        duration_layout.addWidget(self.estimated_time_label)
        
        main_layout.addWidget(duration_group)
        
        # ปุ่มสร้างเพลง
        button_layout = QHBoxLayout()
        
        self.preview_button = QPushButton("ตัวอย่าง (10 วินาที)")
        self.preview_button.setProperty("duration", 10)  # สร้างแค่ 10 วินาที
        
        self.generate_button = QPushButton("สร้างเพลง")
        self.generate_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        button_layout.addWidget(self.preview_button)
        button_layout.addWidget(self.generate_button)
        
        main_layout.addLayout(button_layout)
        
        # เพิ่มช่องว่างด้านล่าง
        main_layout.addStretch(1)
        
    def _connect_signals(self):
        """เชื่อมต่อสัญญาณ"""
        # เชื่อมต่อ slider และ spin box
        self.duration_slider.valueChanged.connect(self.duration_spin.setValue)
        self.duration_spin.valueChanged.connect(self.duration_slider.setValue)
        
        # อัพเดตเวลาประมาณเมื่อเปลี่ยนความยาว
        self.duration_spin.valueChanged.connect(self._update_estimated_time)
        
        # อัพเดตเวลาประมาณเมื่อเปลี่ยนเครื่องดนตรี
        for combo in self.instrument_combos:
            combo.currentIndexChanged.connect(self._update_estimated_time)
        
        # เชื่อมต่อปุ่มสร้างเพลง
        self.generate_button.clicked.connect(self._on_generate_clicked)
        self.preview_button.clicked.connect(self._on_preview_clicked)
        
        # เรียกครั้งแรกเพื่ออัพเดตเวลาประมาณ
        self._update_estimated_time()
        
    def _on_preset_clicked(self):
        """เรียกเมื่อกดปุ่ม preset"""
        sender = self.sender()
        duration = sender.property("duration")
        self.duration_spin.setValue(duration)
        
    def _update_estimated_time(self):
        """อัพเดตเวลาประมาณในการสร้างเพลง"""
        duration = self.duration_spin.value()
        
        # นับเครื่องดนตรีที่เลือก
        instrument_count = 0
        for combo in self.instrument_combos:
            if combo.currentIndex() > 1:  # ข้ามตัวเลือกแรกและหัวข้อประเภท
                instrument_count += 1
                
        # คำนวณเวลาประมาณ
        estimated_seconds = estimate_generation_time(duration, instrument_count)
        
        # อัพเดต label
        time_format = seconds_to_time_format(estimated_seconds)
        self.estimated_time_label.setText(f"เวลาประมาณในการสร้าง: {time_format}")
        
    def _on_generate_clicked(self):
        """เรียกเมื่อกดปุ่มสร้างเพลง"""
        # ตรวจสอบข้อมูล
        if not self._validate_form():
            return
            
        # รวบรวมข้อมูล
        generation_params = self._collect_parameters()
        
        # ส่งสัญญาณ
        self.generation_requested.emit(generation_params)
        
        # ล็อคฟอร์ม (ถูกปลดล็อคโดยส่วนของ MainWindow)
        self._lock_form()
        
    def _on_preview_clicked(self):
        """เรียกเมื่อกดปุ่มตัวอย่าง"""
        # ตรวจสอบข้อมูล
        if not self._validate_form():
            return
            
        # รวบรวมข้อมูล
        generation_params = self._collect_parameters()
        
        # ตั้งค่าความยาวเป็น 10 วินาที
        generation_params['duration'] = 10
        generation_params['is_preview'] = True
        
        # ส่งสัญญาณ
        self.generation_requested.emit(generation_params)
        
        # ล็อคฟอร์ม (ถูกปลดล็อคโดยส่วนของ MainWindow)
        self._lock_form()
        
    def _validate_form(self):
        """ตรวจสอบความถูกต้องของข้อมูล"""
        # ตรวจสอบ prompt
        if not self.prompt_input.toPlainText().strip():
            QMessageBox.warning(self, "กรุณากรอกข้อมูล", "กรุณาอธิบายเพลงที่ต้องการสร้าง")
            self.prompt_input.setFocus()
            return False
            
        # ตรวจสอบว่าเลือกเครื่องดนตรีอย่างน้อย 1 ชิ้น
        if self.instrument_combos[0].currentIndex() == 0:
            QMessageBox.warning(self, "กรุณาเลือกเครื่องดนตรี", "กรุณาเลือกเครื่องดนตรีอย่างน้อย 1 ชิ้น")
            self.instrument_combos[0].setFocus()
            return False
            
        # ตรวจสอบว่าเลือกอารมณ์เพลง
        if self.mood_combo.currentIndex() == 0:
            QMessageBox.warning(self, "กรุณาเลือกอารมณ์เพลง", "กรุณาเลือกอารมณ์เพลง")
            self.mood_combo.setFocus()
            return False
            
        return True
        
    def _collect_parameters(self):
        """รวบรวมข้อมูลจากฟอร์ม"""
        # รวบรวมเครื่องดนตรีที่เลือก
        instruments = []
        for combo in self.instrument_combos:
            if combo.currentIndex() > 1:  # ข้ามตัวเลือกแรกและหัวข้อประเภท
                instruments.append(combo.currentText())
                
        return {
            'prompt': self.prompt_input.toPlainText().strip(),
            'instruments': instruments,
            'mood': self.mood_combo.currentText(),
            'duration': self.duration_spin.value(),
            'is_preview': False
        }
        
    def _lock_form(self):
        """ล็อคฟอร์มระหว่างรอการสร้างเพลง"""
        self.setEnabled(False)
        
    def unlock_form(self):
        """ปลดล็อคฟอร์มหลังจากสร้างเพลงเสร็จ"""
        self.setEnabled(True) 