import os, sys, shutil, random
from PySide6.QtCore import QUrl, QTime, Qt, QTimer
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtGui import QKeyEvent, QIcon, QAction
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QFileDialog,
    QListWidget, QPushButton, QVBoxLayout, QWidget, QSlider, QDialog, QLineEdit, 
    QMessageBox, QComboBox, QSystemTrayIcon, QMenu)
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, APIC

class LazyPleerV2(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LazyPleer v2.0")
        self.setMinimumSize(460, 580) 
        self.resize(460, 620)
        
        # Включаем Drag-and-Drop (Перетаскивание файлов мышкой)
        self.setAcceptDrops(True)
        
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.7)
        
        self.music_dir = "./music"
        self.playlist_files = []      # Оригинальный список файлов
        self.current_playlist = []    # Список файлов с учетом поиска/перемешивания
        self.is_slider_moving = False
        
        # Переменные для новых фишек
        self.play_mode = "Normal"     # Режимы: Normal, Shuffle, Repeat
        self.sleep_timer = QTimer(self)
        self.sleep_timer.timeout.connect(self.trigger_sleep)
        self.sleep_minutes_left = 0

        # Стили наших сочных и строгих тем
        self.themes = {
            "Светлая macOS": {
                "widget": "background-color: #F5F5F7; color: #1D1D1F;",
                "screen": "background-color: #FFFFFF; border: 1px solid #D2D2D7; border-radius: 10px;",
                "screen_lbl": "color: #1D1D1F; font-size: 14px; font-weight: 600;",
                "time_lbl": "color: #86868B; font-size: 11px;",
                "list": "QListWidget { background-color: #FFFFFF; border: 1px solid #D2D2D7; border-radius: 10px; padding: 5px; color: #1D1D1F; } QListWidget::item:hover { background-color: #F5F5F7; } QListWidget::item:selected { background-color: #0071E3; color: #FFFFFF; }",
                "btn_ctrl": "QPushButton { background-color: #FFFFFF; border: 1px solid #D2D2D7; border-radius: 8px; color: #1D1D1F; font-size: 14px; font-weight: bold; min-width: 50px; height: 34px; } QPushButton:hover { background-color: #F5F5F7; border-color: #0071E3; } QPushButton:pressed { background-color: #E8E8ED; }",
                "btn_edit": "QPushButton { background-color: #FFFFFF; border: 1px solid #D2D2D7; border-radius: 6px; padding: 6px 12px; font-size: 11px; font-weight: 500; color: #1D1D1F; } QPushButton:hover { background-color: #E8E8ED; border-color: #86868B; }",
                "input": "QLineEdit { background-color: #FFFFFF; border: 1px solid #D2D2D7; border-radius: 6px; padding: 5px; color: #1D1D1F; }",
                "slider": "QSlider::groove:horizontal { height: 4px; background: #E5E5EA; border-radius: 2px; } QSlider::sub-page:horizontal { background: #0071E3; border-radius: 2px; } QSlider::handle:horizontal { background: #FFFFFF; border: 0.5px solid #D2D2D7; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }"
            },
            "Тёмная macOS": {
                "widget": "background-color: #1E1E1E; color: #FFFFFF;",
                "screen": "background-color: #2D2D2D; border: 1px solid #3A3A3C; border-radius: 10px;",
                "screen_lbl": "color: #FFFFFF; font-size: 14px; font-weight: 600;",
                "time_lbl": "color: #AEAEB2; font-size: 11px;",
                "list": "QListWidget { background-color: #2D2D2D; border: 1px solid #3A3A3C; border-radius: 10px; padding: 5px; color: #FFFFFF; } QListWidget::item:hover { background-color: #3A3A3C; } QListWidget::item:selected { background-color: #0A84FF; color: #FFFFFF; }",
                "btn_ctrl": "QPushButton { background-color: #2D2D2D; border: 1px solid #3A3A3C; border-radius: 8px; color: #FFFFFF; font-size: 14px; font-weight: bold; min-width: 50px; height: 34px; } QPushButton:hover { background-color: #3A3A3C; border-color: #0A84FF; } QPushButton:pressed { background-color: #48484A; }",
                "btn_edit": "QPushButton { background-color: #2D2D2D; border: 1px solid #3A3A3C; border-radius: 6px; padding: 6px 12px; font-size: 11px; font-weight: 500; color: #FFFFFF; } QPushButton:hover { background-color: #3A3A3C; border-color: #AEAEB2; }",
                "input": "QLineEdit { background-color: #2D2D2D; border: 1px solid #3A3A3C; border-radius: 6px; padding: 5px; color: #FFFFFF; }",
                "slider": "QSlider::groove:horizontal { height: 4px; background: #3A3A3C; border-radius: 2px; } QSlider::sub-page:horizontal { background: #0A84FF; border-radius: 2px; } QSlider::handle:horizontal { background: #FFFFFF; border: 0.5px solid #3A3A3C; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }"
            }
        }
        self.init_ui()
        self.init_tray()
        self.load_music()
        
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)
        self.player.mediaStatusChanged.connect(self.status_changed)
    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(12)

        # --- ВЕРХНЯЯ ПАНЕЛЬ (СВЕТОФОРЫ + ТЕМЫ + ТАЙМЕР) ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        for c, b in [("#FF5F56", "#E0443E"), ("#FFBD2E", "#DEA123"), ("#27C93F", "#1AAA2C")]:
            dot = QFrame()
            dot.setFixedSize(12, 12)
            dot.setStyleSheet(f"background-color: {c}; border-radius: 6px; border: 0.5px solid {b};")
            header_layout.addWidget(dot)
        
        self.title_label = QLabel("LazyPleer v2.0")
        self.title_label.setStyleSheet("font-weight: 700; font-size: 14px; margin-left: 5px;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        # Фишка 6: Выбор таймера сна
        self.sleep_selector = QComboBox()
        self.sleep_selector.addItems(["⏱ Таймер", "15 мин", "30 мин", "60 min"])
        self.sleep_selector.setStyleSheet("QComboBox { padding: 4px 6px; border: 1px solid #D2D2D7; border-radius: 6px; background: white; color: black; font-size: 11px; }")
        self.sleep_selector.currentTextChanged.connect(self.set_sleep_timer)
        header_layout.addWidget(self.sleep_selector)

        # Селектор тем
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(["Светлая macOS", "Тёмная macOS"])
        self.theme_selector.setStyleSheet("QComboBox { padding: 4px 6px; border: 1px solid #D2D2D7; border-radius: 6px; background: white; color: black; font-size: 11px; }")
        self.theme_selector.currentTextChanged.connect(self.apply_theme)
        header_layout.addWidget(self.theme_selector)
        
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 14px; } QPushButton:hover { color: #0071E3; }")
        self.btn_refresh.clicked.connect(self.load_music)
        header_layout.addWidget(self.btn_refresh)
        self.main_layout.addLayout(header_layout)

        # --- СТИЛЬНЫЙ ДИСПЛЕЙ ---
        self.screen_frame = QFrame()
        self.screen_layout = QVBoxLayout(self.screen_frame)
        self.screen_layout.setContentsMargins(16, 14, 16, 14)
        self.screen_label = QLabel("Не играет\nПеретащите треки сюда или закиньте в /music")
        self.time_label = QLabel("00:00 / 00:00")
        self.screen_layout.addWidget(self.screen_label)
        self.screen_layout.addWidget(self.time_label)
        self.main_layout.addWidget(self.screen_frame)

        # --- СЛАЙДЕР ПЕРЕМОТКИ ---
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.sliderPressed.connect(self.slider_pressed)
        self.progress_slider.sliderReleased.connect(self.slider_released)
        self.main_layout.addWidget(self.progress_slider)

        # Фишка 5: Умная строка поиска (Spotlight style)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Быстрый поиск трека на лету...")
        self.search_input.textChanged.connect(self.filter_playlist)
        self.main_layout.addWidget(self.search_input)

        # --- ПЛЕЙЛИСТ ---
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.play_selected)
        self.main_layout.addWidget(self.list_widget)

        # --- ПАНЕЛЬ ФУНКЦИЙ (РЕДАКТОР + SHUFFLE/REPEAT) ---
        meta_layout = QHBoxLayout()
        self.btn_edit = QPushButton("📝 Редактировать теги")
        self.btn_edit.clicked.connect(self.open_metadata_editor)
        meta_layout.addWidget(self.btn_edit)
        meta_layout.addStretch()

        # Фишка 2: Кнопка переключения режимов Shuffle / Repeat
        self.btn_mode = QPushButton("🔁 По порядку")
        self.btn_mode.setStyleSheet("QPushButton { background-color: #FFFFFF; border: 1px solid #D2D2D7; border-radius: 6px; padding: 5px 10px; font-size: 11px; color: #1D1D1F; }")
        self.btn_mode.clicked.connect(self.toggle_play_mode)
        meta_layout.addWidget(self.btn_mode)
        self.main_layout.addLayout(meta_layout)

        # --- ГРОМКОСТЬ ---
        vol_layout = QHBoxLayout()
        self.vol_icon = QLabel("🔊")
        self.vol_icon.setStyleSheet("background: transparent; font-size: 12px;")
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(70)
        self.vol_slider.valueChanged.connect(self.change_volume)
        vol_layout.addWidget(self.vol_icon)
        vol_layout.addWidget(self.vol_slider)
        self.main_layout.addLayout(vol_layout)

        # --- КНОПКИ УПРАВЛЕНИЯ ---
        self.controls_layout = QHBoxLayout()
        self.controls_layout.setSpacing(10)
        self.controls_layout.setAlignment(Qt.AlignCenter)
        
        self.btn_prev = QPushButton("⏮")
        self.btn_prev.clicked.connect(self.prev_track)
        self.btn_play = QPushButton("▶")
        self.btn_play.clicked.connect(self.play_track)
        self.btn_pause = QPushButton("⏸")
        self.btn_pause.clicked.connect(self.pause_track)
        self.btn_next = QPushButton("⏭")
        self.btn_next.clicked.connect(self.next_track)

        self.controls_layout.addWidget(self.btn_prev)
        self.controls_layout.addWidget(self.btn_play)
        self.controls_layout.addWidget(self.btn_pause)
        self.controls_layout.addWidget(self.btn_next)
        self.main_layout.addLayout(self.controls_layout)

        self.apply_theme("Светлая macOS")
    def apply_theme(self, theme_name):
        style = self.themes[theme_name]
        self.setStyleSheet(style["widget"])
        self.screen_frame.setStyleSheet(style["screen"])
        self.screen_label.setStyleSheet(style["screen_lbl"] + " background: transparent; qproperty-alignment: 'AlignCenter';")
        self.time_label.setStyleSheet(style["time_lbl"] + " background: transparent; qproperty-alignment: 'AlignCenter';")
        self.list_widget.setStyleSheet(style["list"])
        self.progress_slider.setStyleSheet(style["slider"])
        self.vol_slider.setStyleSheet(style["slider"])
        self.btn_edit.setStyleSheet(style["btn_edit"])
        self.search_input.setStyleSheet(style["input"])
        if theme_name == "Тёмная macOS":
            self.btn_mode.setStyleSheet("QPushButton { background-color: #2D2D2D; border: 1px solid #3A3A3C; border-radius: 6px; padding: 5px 10px; font-size: 11px; color: #FFFFFF; }")
        else:
            self.btn_mode.setStyleSheet("QPushButton { background-color: #FFFFFF; border: 1px solid #D2D2D7; border-radius: 6px; padding: 5px 10px; font-size: 11px; color: #1D1D1F; }")
        for btn in [self.btn_prev, self.btn_play, self.btn_pause, self.btn_next]:
            btn.setStyleSheet(style["btn_ctrl"])

    # Фишка 4: Работа с системным треем Windows
    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        # Ставим стандартную иконку, если нет своей .png
        self.tray_icon.setIcon(QIcon.fromTheme("media-playback-start"))
        
        tray_menu = QMenu()
        play_action = QAction("▶ Старт", self)
        play_action.triggered.connect(self.play_track)
        pause_action = QAction("⏸ Пауза", self)
        pause_action.triggered.connect(self.pause_track)
        next_action = QAction("⏭ Вперед", self)
        next_action.triggered.connect(self.next_track)
        exit_action = QAction("❌ Выход", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        
        tray_menu.addAction(play_action)
        tray_menu.addAction(pause_action)
        tray_menu.addAction(next_action)
        tray_menu.addSeparator()
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        # Разворачивание по двойному клику по иконке в трее
        self.tray_icon.activated.connect(self.tray_icon_activated)

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.showNormal()
            self.activateWindow()

    # Сворачивание приложения в трей при нажатии "минус"
    def changeEvent(self, event):
        if event.type() == event.type().WindowStateChange:
            if self.isMinimized():
                QTimer.singleShot(0, self.hide)
                self.tray_icon.showMessage("LazyPleer", "Плеер свернут в системный трей!", QSystemTrayIcon.Information, 2000)
        super().changeEvent(event)

    # Фишка 2: Логика Shuffle / Repeat режимов
    def toggle_play_mode(self):
        if self.play_mode == "Normal":
            self.play_mode = "Shuffle"
            self.btn_mode.setText("🔀 Случайный")
        elif self.play_mode == "Shuffle":
            self.play_mode = "Repeat"
            self.btn_mode.setText("🔂 Повтор")
        else:
            self.play_mode = "Normal"
            self.btn_mode.setText("🔁 По порядку")

    # Фишка 6: Установка таймера сна
    def set_sleep_timer(self, text):
        if text == "15 мин": self.sleep_minutes_left = 15
        elif text == "30 мин": self.sleep_minutes_left = 30
        elif text == "60 min": self.sleep_minutes_left = 60
        else:
            self.sleep_timer.stop()
            return
        self.sleep_timer.start(60000) # Проверка каждую минуту
        QMessageBox.information(self, "Таймер сна", f"Плеер закроется через {self.sleep_minutes_left} минут!")

    def trigger_sleep(self):
        self.sleep_minutes_left -= 1
        if self.sleep_minutes_left <= 0:
            self.sleep_timer.stop()
            QApplication.instance().quit()
    # Фишка 3: Перетаскивание музыки мышкой (Drag-and-Drop)
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
    def dropEvent(self, event):
        if not os.path.exists(self.music_dir): os.makedirs(self.music_dir)
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith(('.mp3', '.wav', '.m4a')):
                try:
                    shutil.copy(file_path, self.music_dir)
                except: pass
        self.load_music()

    # Фишка 1: Горячие клавиши и Медиа-кнопки
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Space: self.play_track() if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState else self.pause_track()
        elif event.key() == Qt.Key_Left: self.player.setPosition(max(0, self.player.position() - 5000))
        elif event.key() == Qt.Key_Right: self.player.setPosition(min(self.player.duration(), self.player.position() + 5000))
        else: super().keyPressEvent(event)

    def load_music(self):
        if not os.path.exists(self.music_dir): os.makedirs(self.music_dir)
        self.playlist_files = [f for f in os.listdir(self.music_dir) if f.endswith(('.mp3', '.wav', '.m4a'))]
        self.filter_playlist()

    # Фишка 5: Фильтрация списка при поиске
    def filter_playlist(self):
        search_text = self.search_input.text().lower()
        self.current_playlist = [f for f in self.playlist_files if search_text in f.lower()]
        
        current_row = self.list_widget.currentRow()
        self.list_widget.clear()
        
        for track in self.current_playlist:
            track_path = os.path.join(self.music_dir, track)
            display_name = track
            try:
                if track.endswith('.mp3'):
                    audio = MP3(track_path, ID3=ID3)
                    title, artist = audio.get('TIT2'), audio.get('TPE1')
                    if title and artist: display_name = f"{artist} - {title}"
            except: pass
            self.list_widget.addItem(f"  🎵  {display_name}")
            
        if self.current_playlist:
            if 0 <= current_row < len(self.current_playlist): self.list_widget.setCurrentRow(current_row)
            else: self.list_widget.setCurrentRow(0)

    def play_track(self):
        if not self.current_playlist: return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self.player.play()
            self.update_screen("Воспроизведение")
            return
        current_row = self.list_widget.currentRow()
        if current_row < 0: current_row = 0
        track_name = self.current_playlist[current_row]
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
        if not self.current_playlist: return
        if self.play_mode == "Shuffle":
            next_row = random.randint(0, len(self.current_playlist) - 1)
        else:
            next_row = (self.list_widget.currentRow() + 1) % len(self.current_playlist)
        self.list_widget.setCurrentRow(next_row)
        self.play_track()

    def prev_track(self):
        if not self.current_playlist: return
        prev_row = (self.list_widget.currentRow() - 1) % len(self.current_playlist)
        if prev_row < 0: prev_row = len(self.current_playlist) - 1
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
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.play_mode == "Repeat": self.play_track() # Повтор текущего трека
            else: self.next_track()

    def update_screen(self, status):
        current_row = self.list_widget.currentRow()
        if current_row < 0 or current_row >= len(self.current_playlist): return
        track_name = self.current_playlist[current_row]
        self.screen_label.setText(f"{track_name}\n({status})")

    def open_metadata_editor(self):
        current_row = self.list_widget.currentRow()
        if current_row < 0: return
        track_name = self.current_playlist[current_row]
        track_path = os.path.abspath(os.path.join(self.music_dir, track_name))
        if not track_name.endswith('.mp3'):
            QMessageBox.warning(self, "Формат файла", "Только для MP3!")
            return
        self.player.setSource(QUrl())
        dialog = QDialog(self)
        dialog.setWindowTitle("Свойства MP3")
        dialog.setFixedSize(340, 260)
        current_theme = self.theme_selector.currentText()
        dialog.setStyleSheet(self.themes[current_theme]["widget"])
        layout = QVBoxLayout(dialog)
        try:
            audio = MP3(track_path, ID3=ID3)
            current_title = str(audio.get('TIT2', ''))
            current_artist = str(audio.get('TPE1', ''))
        except: current_title, current_artist = "", ""

        layout.addWidget(QLabel("Название трека:"))
        title_input = QLineEdit(current_title)
        title_input.setStyleSheet("background: white; border: 1px solid #D2D2D7; border-radius: 6px; padding: 5px; color: black;")
        layout.addWidget(title_input)
        layout.addWidget(QLabel("Исполнитель:"))
        artist_input = QLineEdit(current_artist)
        artist_input.setStyleSheet("background: white; border: 1px solid #D2D2D7; border-radius: 6px; padding: 5px; color: black;")
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
        btn_cover.setStyleSheet(self.themes[current_theme]["btn_edit"])
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
    player = LazyPleerV2()
    player.show()
    sys.exit(app.exec())
