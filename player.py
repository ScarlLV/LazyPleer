import os, sys
from PySide6.QtCore import QUrl, QTime, Qt
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QFileDialog,
    QListWidget, QPushButton, QVBoxLayout, QWidget, QSlider, QDialog, QLineEdit, QMessageBox)
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, APIC

class LazyPleer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LazyPleer")
        self.setFixedSize(440, 500)
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.7)
        self.music_dir = "./music"
        self.playlist_files = []
        self.is_slider_moving = False
        self.init_ui()
        self.load_music()
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)
        self.player.mediaStatusChanged.connect(self.status_changed)

    def init_ui(self):
        self.setStyleSheet("QWidget { background-color: #F5F5F7; font-family: 'SF Pro Display', 'Arial'; font-size: 13px; color: #1D1D1F; }")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        for c, b in [("#FF5F56", "#E0443E"), ("#FFBD2E", "#DEA123"), ("#27C93F", "#1AAA2C")]:
            dot = QFrame()
            dot.setFixedSize(12, 12)
            dot.setStyleSheet(f"background-color: {c}; border-radius: 6px; border: 0.5px solid {b};")
            header_layout.addWidget(dot)
        
        title_text = QLabel("LazyPleer")
        title_text.setStyleSheet("font-weight: 700; color: #1D1D1F; margin-left: 10px; font-size: 14px;")
        header_layout.addWidget(title_text)
        header_layout.addStretch()
        
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 14px; } QPushButton:hover { color: #0071E3; }")
        self.btn_refresh.clicked.connect(self.load_music)
        header_layout.addWidget(self.btn_refresh)
        main_layout.addLayout(header_layout)

        screen_frame = QFrame()
        screen_frame.setStyleSheet("background-color: #FFFFFF; border: 1px solid #D2D2D7; border-radius: 10px;")
        screen_layout = QVBoxLayout(screen_frame)
        screen_layout.setContentsMargins(16, 14, 16, 14)
        self.screen_label = QLabel("Не играет\nЗакиньте музыку в папку /music")
        self.screen_label.setStyleSheet("color: #1D1D1F; font-size: 14px; font-weight: 600; qproperty-alignment: 'AlignCenter'; background: transparent;")
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("color: #86868B; font-size: 11px; qproperty-alignment: 'AlignCenter'; background: transparent; margin-top: 4px;")
        screen_layout.addWidget(self.screen_label)
        screen_layout.addWidget(self.time_label)
        main_layout.addWidget(screen_frame)

        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.setStyleSheet("QSlider::groove:horizontal { height: 4px; background: #E5E5EA; border-radius: 2px; } QSlider::sub-page:horizontal { background: #0071E3; border-radius: 2px; } QSlider::handle:horizontal { background: #FFFFFF; border: 0.5px solid #D2D2D7; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }")
        self.progress_slider.sliderPressed.connect(self.slider_pressed)
        self.progress_slider.sliderReleased.connect(self.slider_released)
        main_layout.addWidget(self.progress_slider)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("QListWidget { background-color: #FFFFFF; border: 1px solid #D2D2D7; border-radius: 10px; padding: 5px; } QListWidget::item { padding: 8px 12px; border-radius: 6px; margin-bottom: 2px; color: #1D1D1F; } QListWidget::item:hover { background-color: #F5F5F7; } QListWidget::item:selected { background-color: #0071E3; color: #FFFFFF; }")
        self.list_widget.itemDoubleClicked.connect(self.play_selected)
        main_layout.addWidget(self.list_widget)

        meta_layout = QHBoxLayout()
        self.btn_edit = QPushButton("📝 Редактировать теги MP3")
        self.btn_edit.setStyleSheet("QPushButton { background-color: #FFFFFF; border: 1px solid #D2D2D7; border-radius: 6px; padding: 6px 12px; font-size: 11px; font-weight: 500; } QPushButton:hover { background-color: #E8E8ED; border-color: #86868B; }")
        self.btn_edit.clicked.connect(self.open_metadata_editor)
        meta_layout.addWidget(self.btn_edit)
        meta_layout.addStretch()
        main_layout.addLayout(meta_layout)

        vol_layout = QHBoxLayout()
        vol_icon = QLabel("🔊")
        vol_icon.setStyleSheet("color: #86868B; font-size: 12px; background: transparent;")
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(70)
        self.vol_slider.setStyleSheet("QSlider { background: transparent; } QSlider::groove:horizontal { height: 4px; background: #E5E5EA; border-radius: 2.5px; } QSlider::sub-page:horizontal { background: #1D1D1F; border-radius: 2.5px; } QSlider::handle:horizontal { background: #FFFFFF; border: 0.5px solid #D2D2D7; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }")
        self.vol_slider.valueChanged.connect(self.change_volume)
        vol_layout.addWidget(vol_icon)
        vol_layout.addWidget(self.vol_slider)
        main_layout.addLayout(vol_layout)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        controls_layout.setAlignment(Qt.AlignCenter)
        
        btn_style = """
            QPushButton {
                background-color: #FFFFFF; border: 1px solid #D2D2D7; border-radius: 8px;
                color: #1D1D1F; font-size: 14px; font-weight: bold; width: 50px; height: 34px;
            }
            QPushButton:hover { background-color: #F5F5F7; border-color: #0071E3; }
            QPushButton:pressed { background-color: #E8E8ED; }
        """
        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setStyleSheet(btn_style)
        self.btn_prev.clicked.connect(self.prev_track)

        self.btn_play = QPushButton("▶")
        self.btn_play.setStyleSheet(btn_style)
        self.btn_play.clicked.connect(self.play_track)

        self.btn_pause = QPushButton("⏸")
        self.btn_pause.setStyleSheet(btn_style)
        self.btn_pause.clicked.connect(self.pause_track)

        self.btn_next = QPushButton("⏭")
        self.btn_next.setStyleSheet(btn_style)
        self.btn_next.clicked.connect(self.next_track)

        controls_layout.addWidget(self.btn_prev)
        controls_layout.addWidget(self.btn_play)
        controls_layout.addWidget(self.btn_pause)
        controls_layout.addWidget(self.btn_next)
        main_layout.addLayout(controls_layout)
    def load_music(self):
        if not os.path.exists(self.music_dir): os.makedirs(self.music_dir)
        current_row = self.list_widget.currentRow()
        self.playlist_files = [f for f in os.listdir(self.music_dir) if f.endswith(('.mp3', '.wav', '.m4a'))]
        self.list_widget.clear()
        for track in self.playlist_files:
            track_path = os.path.join(self.music_dir, track)
            display_name = track
            try:
                if track.endswith('.mp3'):
                    audio = MP3(track_path, ID3=ID3)
                    title = audio.get('TIT2')
                    artist = audio.get('TPE1')
                    if title and artist: display_name = f"{artist} - {title}"
            except: pass
            self.list_widget.addItem(f"  🎵  {display_name}")
        if self.playlist_files:
            if 0 <= current_row < len(self.playlist_files): self.list_widget.setCurrentRow(current_row)
            else: self.list_widget.setCurrentRow(0)
        else: self.screen_label.setText("Медиатека пуста\nДобавьте аудио в /music")

    def play_track(self):
        if not self.playlist_files: return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self.player.play()
            self.update_screen("Воспроизведение")
            return
        current_row = self.list_widget.currentRow()
        if current_row < 0: current_row = 0
        track_name = self.playlist_files[current_row]
        track_path = os.path.abspath(os.path.join(self.music_dir, track_name))
        self.player.setSource(QUrl.fromLocalFile(track_path))
        self.player.play()
        self.update_screen("Воспроизведение")

    def play_selected(self, item): self.play_track()
    def pause_track(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.update_screen("Пауза")

    def next_track(self):
        if not self.playlist_files: return
        next_row = (self.list_widget.currentRow() + 1) % len(self.playlist_files)
        self.list_widget.setCurrentRow(next_row)
        self.play_track()

    def prev_track(self):
        if not self.playlist_files: return
        prev_row = (self.list_widget.currentRow() - 1) % len(self.playlist_files)
        if prev_row < 0: prev_row = len(self.playlist_files) - 1
        self.list_widget.setCurrentRow(prev_row)
        self.play_track()

    def change_volume(self, value): self.audio_output.setVolume(value / 100.0)
    def slider_pressed(self): self.is_slider_moving = True
    def slider_released(self):
        self.is_slider_moving = False
        self.player.setPosition(self.progress_slider.value())

    def update_position(self, position):
        if not self.is_slider_moving: self.progress_slider.setValue(position)
        pos_time = QTime(0, 0, 0).addMSecs(position).toString("mm:ss")
        dur_time = QTime(0, 0, 0).addMSecs(self.player.duration()).toString("mm:ss")
        self.time_label.setText(f"{pos_time} / {dur_time}")

    def update_duration(self, duration): self.progress_slider.setRange(0, duration)
    def status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia: self.next_track()

    def update_screen(self, status):
        current_row = self.list_widget.currentRow()
        if current_row < 0: return
        track_name = self.playlist_files[current_row]
        self.screen_label.setText(f"{track_name}\n({status})")

    def open_metadata_editor(self):
        current_row = self.list_widget.currentRow()
        if current_row < 0: return
        track_name = self.playlist_files[current_row]
        track_path = os.path.abspath(os.path.join(self.music_dir, track_name))
        if not track_name.endswith('.mp3'):
            QMessageBox.warning(self, "Формат файла", "Только для MP3!")
            return
        self.player.setSource(QUrl())
        dialog = QDialog(self)
        dialog.setWindowTitle("Свойства MP3")
        dialog.setFixedSize(340, 260)
        dialog.setStyleSheet("background-color: #F5F5F7;")
        layout = QVBoxLayout(dialog)
        try:
            audio = MP3(track_path, ID3=ID3)
            current_title = str(audio.get('TIT2', ''))
            current_artist = str(audio.get('TPE1', ''))
        except: current_title, current_artist = "", ""

        layout.addWidget(QLabel("Название трека:"))
        title_input = QLineEdit(current_title)
        title_input.setStyleSheet("background: white; border: 1px solid #D2D2D7; border-radius: 6px; padding: 5px;")
        layout.addWidget(title_input)
        layout.addWidget(QLabel("Исполнитель:"))
        artist_input = QLineEdit(current_artist)
        artist_input.setStyleSheet("background: white; border: 1px solid #D2D2D7; border-radius: 6px; padding: 5px;")
        layout.addWidget(artist_input)
        file_path_label = QLabel("Обложка не изменена")
        file_path_label.setStyleSheet("font-size: 11px; color: #86868B;")
        
        self.selected_cover_bin = None
        def choose_cover():
            file_path, _ = QFileDialog.getOpenFileName(dialog, "Выбрать обложку", "", "Images (*.png *.jpg *.jpeg)")
            if file_path:
                file_path_label.setText(os.path.basename(file_path))
                with open(file_path, 'rb') as f: self.selected_cover_bin = f.read()

        btn_cover = QPushButton("🖼 Изменить обложку альбома")
        btn_cover.setStyleSheet("background-color: #FFFFFF; border: 1px solid #D2D2D7; border-radius: 6px; padding: 6px;")
        btn_cover.clicked.connect(choose_cover)
        layout.addWidget(btn_cover)
        layout.addWidget(file_path_label)

        def save_tags():
            try:
                try: audio_tags = ID3(track_path)
                except: audio_tags = ID3(); audio_tags.save(track_path)
                audio_tags['TIT2'] = TIT2(encoding=3, text=title_input.text())
                audio_tags['TPE1'] = TPE1(encoding=3, text=artist_input.text())
                if self.selected_cover_bin:
                    audio_tags['APIC'] = APIC(encoding=3, mime='image/jpeg', type=3, desc=u'Cover', data=self.selected_cover_bin)
                audio_tags.save(track_path)
                QMessageBox.information(dialog, "Успех", "Теги успешно сохранены!")
            except Exception as e: QMessageBox.critical(dialog, "Ошибка", f"Ошибка: {e}")
            dialog.accept()

        btn_save = QPushButton("Сохранить в файл")
        btn_save.setStyleSheet("background-color: #0071E3; color: white; border: none; border-radius: 8px; padding: 8px; font-weight: bold;")
        btn_save.clicked.connect(save_tags)
        layout.addWidget(btn_save)
        dialog.exec()
        self.load_music()
        self.play_track()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = LazyPleer()
    player.show()
    sys.exit(app.exec())
