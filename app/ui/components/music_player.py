import os
import time
from pathlib import Path
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QSlider, QListWidget, QListWidgetItem,
    QProgressBar, QFrame, QFileDialog, QMessageBox, QMenu
)
from PyQt6.QtGui import QIcon, QFont, QAction
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from app.core.audio_utils import get_all_audio_files, delete_audio_file
from app.core.utilities import seconds_to_time_format

class MusicPlayer(QFrame):
    """คอมโพเนนต์สำหรับเล่นเพลงและจัดการไฟล์เพลง"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        
        self.current_file = None
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        # ตั้งค่า UI
        self._init_ui()
        
        # เชื่อมต่อสัญญาณ
        self._connect_signals()
        
        # โหลดรายการเพลง
        self._load_playlist()
        
        # ตั้ง timer สำหรับอัพเดต progress bar
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(100)  # 100 ms
        self.update_timer.timeout.connect(self._update_progress)
        
    def _init_ui(self):
        """สร้างส่วนประกอบ UI"""
        main_layout = QVBoxLayout(self)
        
        # หัวข้อ
        title_label = QLabel("เครื่องเล่นเพลง")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        main_layout.addWidget(title_label)
        
        # แสดงไฟล์ที่กำลังเล่น
        now_playing_group = QGroupBox("กำลังเล่น")
        now_playing_layout = QVBoxLayout(now_playing_group)
        
        self.now_playing_label = QLabel("ไม่มีเพลงที่กำลังเล่น")
        self.now_playing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.now_playing_label.setStyleSheet("font-weight: bold;")
        now_playing_layout.addWidget(self.now_playing_label)
        
        # Progress bar
        time_layout = QHBoxLayout()
        self.current_time_label = QLabel("00:00")
        self.total_time_label = QLabel("00:00")
        
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.setValue(0)
        self.progress_slider.setEnabled(False)
        
        time_layout.addWidget(self.current_time_label)
        time_layout.addWidget(self.progress_slider)
        time_layout.addWidget(self.total_time_label)
        now_playing_layout.addLayout(time_layout)
        
        # ปุ่มควบคุมการเล่น
        control_layout = QHBoxLayout()
        
        self.play_button = QPushButton("▶ เล่น")
        self.stop_button = QPushButton("■ หยุด")
        self.pause_button = QPushButton("❚❚ พัก")
        
        # ปรับขนาดปุ่ม
        for button in [self.play_button, self.stop_button, self.pause_button]:
            button.setMinimumWidth(80)
            
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.stop_button)
        
        # ปุ่มเพิ่มเติม
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)  # 70% volume
        self.volume_label = QLabel("🔊")
        
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(self.volume_label)
        volume_layout.addWidget(self.volume_slider)
        
        now_playing_layout.addLayout(control_layout)
        now_playing_layout.addLayout(volume_layout)
        
        main_layout.addWidget(now_playing_group)
        
        # รายการเพลง
        playlist_group = QGroupBox("รายการเพลง")
        playlist_layout = QVBoxLayout(playlist_group)
        
        self.playlist = QListWidget()
        self.playlist.setAlternatingRowColors(True)
        playlist_layout.addWidget(self.playlist)
        
        # ปุ่มจัดการรายการเพลง
        playlist_buttons_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("🔄 รีเฟรช")
        self.export_button = QPushButton("💾 ส่งออก")
        self.delete_button = QPushButton("🗑️ ลบ")
        
        playlist_buttons_layout.addWidget(self.refresh_button)
        playlist_buttons_layout.addWidget(self.export_button)
        playlist_buttons_layout.addWidget(self.delete_button)
        
        playlist_layout.addLayout(playlist_buttons_layout)
        
        main_layout.addWidget(playlist_group)
        
    def _connect_signals(self):
        """เชื่อมต่อสัญญาณ"""
        # สัญญาณเล่นเพลง
        self.play_button.clicked.connect(self._on_play_clicked)
        self.pause_button.clicked.connect(self._on_pause_clicked)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        
        # สัญญาณรายการเพลง
        self.playlist.itemDoubleClicked.connect(self._on_playlist_item_double_clicked)
        self.refresh_button.clicked.connect(self._load_playlist)
        self.export_button.clicked.connect(self._on_export_clicked)
        self.delete_button.clicked.connect(self._on_delete_clicked)
        
        # สัญญาณ media player
        self.media_player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.media_player.errorOccurred.connect(self._on_error)
        
        # สัญญาณ volume slider
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        self._on_volume_changed(self.volume_slider.value())  # ตั้งค่าเริ่มต้น
        
        # สัญญาณ progress slider
        self.progress_slider.sliderPressed.connect(self._on_progress_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_progress_slider_released)
        
        # ตั้งค่า context menu สำหรับรายการเพลง
        self.playlist.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.playlist.customContextMenuRequested.connect(self._show_playlist_context_menu)
        
    def _load_playlist(self):
        """โหลดรายการเพลงจากโฟลเดอร์"""
        self.playlist.clear()
        
        # ดึงไฟล์ทั้งหมด
        files = get_all_audio_files(sort_by='date', reverse=True)
        
        for file_path in files:
            # สร้าง item สำหรับแต่ละไฟล์
            item = QListWidgetItem(file_path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(file_path))
            self.playlist.addItem(item)
            
        if files:
            self.playlist.setCurrentRow(0)
            
    def _on_play_clicked(self):
        """เรียกเมื่อกดปุ่มเล่น"""
        # ถ้าไม่มีไฟล์ที่กำลังเล่น ให้เล่นไฟล์ที่เลือกในรายการ
        if not self.current_file or self.media_player.playbackState() == QMediaPlayer.PlaybackState.StoppedState:
            current_item = self.playlist.currentItem()
            if current_item:
                file_path = Path(current_item.data(Qt.ItemDataRole.UserRole))
                self._play_file(file_path)
        else:
            # ถ้ามีไฟล์ที่กำลังเล่นแล้ว ให้เล่นต่อ
            self.media_player.play()
            
    def _on_pause_clicked(self):
        """เรียกเมื่อกดปุ่มพัก"""
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            
    def _on_stop_clicked(self):
        """เรียกเมื่อกดปุ่มหยุด"""
        self.media_player.stop()
        self.update_timer.stop()
        self.progress_slider.setValue(0)
        self.current_time_label.setText("00:00")
        
    def _play_file(self, file_path):
        """เล่นไฟล์เพลง"""
        if not file_path.exists():
            QMessageBox.warning(self, "ไม่พบไฟล์", f"ไม่พบไฟล์ {file_path}")
            # อัพเดตรายการเพลงเพื่อลบไฟล์ที่ไม่มีอยู่จริง
            self._load_playlist()
            return
            
        # ตั้งค่าไฟล์ที่กำลังเล่น
        self.current_file = file_path
        self.now_playing_label.setText(file_path.name)
        
        # ตั้งค่า media player
        self.media_player.setSource(QUrl.fromLocalFile(str(file_path)))
        self.media_player.play()
        
        # เริ่ม timer สำหรับอัพเดต progress bar
        self.update_timer.start()
        
    def _on_playlist_item_double_clicked(self, item):
        """เรียกเมื่อดับเบิลคลิกไอเท็มในรายการเพลง"""
        file_path = Path(item.data(Qt.ItemDataRole.UserRole))
        self._play_file(file_path)
        
    def _on_playback_state_changed(self, state):
        """เรียกเมื่อสถานะการเล่นเปลี่ยน"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setEnabled(False)
            self.pause_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            self.progress_slider.setEnabled(True)
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.play_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.progress_slider.setEnabled(True)
        else:  # StoppedState
            self.play_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.progress_slider.setEnabled(False)
            self.update_timer.stop()
            
    def _on_duration_changed(self, duration):
        """เรียกเมื่อความยาวของเพลงเปลี่ยน"""
        if duration > 0:
            # อัพเดตความยาวทั้งหมด
            total_time = seconds_to_time_format(duration // 1000)  # หน่วยเป็น ms ต้องหารด้วย 1000
            self.total_time_label.setText(total_time)
            
            # อัพเดตพิสัยของ progress slider
            self.progress_slider.setRange(0, duration)
            
    def _on_volume_changed(self, value):
        """เรียกเมื่อระดับเสียงเปลี่ยน"""
        # ตั้งค่าระดับเสียง (0.0 - 1.0)
        volume = value / 100.0
        self.audio_output.setVolume(volume)
        
        # อัพเดตไอคอนระดับเสียง
        if value == 0:
            self.volume_label.setText("🔇")
        elif value < 30:
            self.volume_label.setText("🔈")
        elif value < 70:
            self.volume_label.setText("🔉")
        else:
            self.volume_label.setText("🔊")
            
    def _update_progress(self):
        """อัพเดต progress bar"""
        if not self._is_seeking:
            position = self.media_player.position()
            self.progress_slider.setValue(position)
            
            # อัพเดตเวลาปัจจุบัน
            current_time = seconds_to_time_format(position // 1000)  # หน่วยเป็น ms ต้องหารด้วย 1000
            self.current_time_label.setText(current_time)
            
    def _on_progress_slider_pressed(self):
        """เรียกเมื่อกดค้างที่ progress slider"""
        self._is_seeking = True
        
    def _on_progress_slider_released(self):
        """เรียกเมื่อปล่อย progress slider"""
        self._is_seeking = False
        self.media_player.setPosition(self.progress_slider.value())
        
    def _on_export_clicked(self):
        """เรียกเมื่อกดปุ่มส่งออก"""
        current_item = self.playlist.currentItem()
        if not current_item:
            QMessageBox.warning(self, "ไม่ได้เลือกไฟล์", "กรุณาเลือกไฟล์ที่ต้องการส่งออก")
            return
            
        file_path = Path(current_item.data(Qt.ItemDataRole.UserRole))
        if not file_path.exists():
            QMessageBox.warning(self, "ไม่พบไฟล์", f"ไม่พบไฟล์ {file_path}")
            self._load_playlist()
            return
            
        # เลือกที่บันทึกไฟล์
        save_path, _ = QFileDialog.getSaveFileName(
            self, 
            "บันทึกไฟล์เพลง", 
            str(Path.home() / file_path.name), 
            f"{file_path.suffix[1:]} Files (*{file_path.suffix});;All Files (*)"
        )
        
        if not save_path:
            return
            
        try:
            # คัดลอกไฟล์
            import shutil
            shutil.copy2(file_path, save_path)
            QMessageBox.information(self, "ส่งออกสำเร็จ", f"บันทึกไฟล์ไปที่ {save_path} เรียบร้อยแล้ว")
        except Exception as e:
            QMessageBox.critical(self, "เกิดข้อผิดพลาด", f"ไม่สามารถบันทึกไฟล์ได้: {e}")
            
    def _on_delete_clicked(self):
        """เรียกเมื่อกดปุ่มลบ"""
        current_item = self.playlist.currentItem()
        if not current_item:
            QMessageBox.warning(self, "ไม่ได้เลือกไฟล์", "กรุณาเลือกไฟล์ที่ต้องการลบ")
            return
            
        file_path = Path(current_item.data(Qt.ItemDataRole.UserRole))
        
        # ถามก่อนลบ
        reply = QMessageBox.question(
            self, 
            "ยืนยันการลบ", 
            f"คุณต้องการลบไฟล์ {file_path.name} หรือไม่?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # หยุดเล่นถ้ากำลังเล่นไฟล์นี้อยู่
            if self.current_file == file_path:
                self.media_player.stop()
                self.current_file = None
                self.now_playing_label.setText("ไม่มีเพลงที่กำลังเล่น")
                
            # ลบไฟล์
            if delete_audio_file(file_path):
                # ลบออกจากรายการ
                row = self.playlist.row(current_item)
                self.playlist.takeItem(row)
                
                QMessageBox.information(self, "ลบสำเร็จ", f"ลบไฟล์ {file_path.name} เรียบร้อยแล้ว")
            else:
                QMessageBox.warning(self, "เกิดข้อผิดพลาด", f"ไม่สามารถลบไฟล์ {file_path.name} ได้")
                
    def _on_error(self, error, error_string):
        """เรียกเมื่อเกิดข้อผิดพลาดในการเล่นเพลง"""
        QMessageBox.warning(self, "เกิดข้อผิดพลาด", f"เกิดข้อผิดพลาดในการเล่นเพลง: {error_string}")
        
    def _show_playlist_context_menu(self, position):
        """แสดงเมนูคลิกขวาสำหรับรายการเพลง"""
        item = self.playlist.itemAt(position)
        if not item:
            return
            
        menu = QMenu(self)
        
        play_action = QAction("▶ เล่น", self)
        play_action.triggered.connect(lambda: self._on_playlist_item_double_clicked(item))
        
        export_action = QAction("💾 ส่งออก", self)
        export_action.triggered.connect(self._on_export_clicked)
        
        delete_action = QAction("🗑️ ลบ", self)
        delete_action.triggered.connect(self._on_delete_clicked)
        
        menu.addAction(play_action)
        menu.addAction(export_action)
        menu.addAction(delete_action)
        
        menu.exec(self.playlist.mapToGlobal(position))
        
    def play_file(self, file_path):
        """เล่นไฟล์เพลง (เรียกจากภายนอก)"""
        self._play_file(file_path)
        
        # เลือกไฟล์ในรายการ
        for i in range(self.playlist.count()):
            item = self.playlist.item(i)
            if Path(item.data(Qt.ItemDataRole.UserRole)) == file_path:
                self.playlist.setCurrentItem(item)
                break 