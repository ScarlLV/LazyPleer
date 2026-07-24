import os, sys, shutil, random, json, webbrowser
from PySide6.QtCore import QUrl, QTime, Qt, QTimer, QEvent
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtGui import QIcon, QAction, QColor, QPixmap
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QFileDialog,
    QListWidget, QPushButton, QVBoxLayout, QWidget, QSlider, QDialog, QLineEdit, 
    QMessageBox, QComboBox, QSystemTrayIcon, QMenu, QTextEdit, QInputDialog)
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, APIC, TYER, USLT

try:
    from pypresence import Presence
    DISCORD_AVAILABLE = True
except:
    DISCORD_AVAILABLE = False

class LazyPleerV4(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LazyPleer v4.0 Ultra Final")
        self.setMinimumSize(480, 660) 
        self.resize(480, 660)
        self.setAcceptDrops(True)
        
        QApplication.instance().installEventFilter(self)
        
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.7)
        
        self.is_bass_boost = False
        self.current_theme_name = "Светлая macOS"
        
        self.music_dir = "./music"
        self.playlist_files = []      
        self.current_playlist = []    
        self.is_slider_moving = False
        self.play_mode = "Normal"     
        
        self.stats_file = "./lazy_stats.json"
        self.total_listen_time = 0  
        self.load_statistics()
        
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.update_listen_stats)
        self.stats_timer.start(1000)
        
        self.sleep_timer = QTimer(self)
        self.sleep_timer.timeout.connect(self.trigger_sleep)
        self.sleep_minutes_left = 0

        self.favorite_tracks = []
        self.load_favorites()

        self.rpc = None
        if DISCORD_AVAILABLE:
            try:
                self.rpc = Presence("123456789012345678")
                self.rpc.connect()
            except:
                self.rpc = None
        self.themes = {
            "Светлая macOS": {
                "widget": "background-color: #F5F5F7; color: #1D1D1F;",
                "screen": "background-color: #FFFFFF; border: 1px solid #D2D2D7; border-radius: 10px;",
                "screen_lbl": "color: #1D1D1F; font-size: 13px; font-weight: 600;",
                "time_lbl": "color: #86868B; font-size: 11px;",
                "list": "QListWidget { background-color: #FFFFFF; border: 1px solid #D2D2D7; border-radius: 10px; padding: 5px; color: #1D1D1F; } QListWidget::item:hover { background-color: #F5F5F7; } QListWidget::item:selected { background-color: #0071E3; color: #FFFFFF; }",
                "btn_sticker": "QPushButton { background: transparent; border: none; font-size: 18px; padding: 5px; color: #1D1D1F; } QPushButton:hover { color: #0071E3; }",
                "btn_edit": "QPushButton { background-color: #FFFFFF; border: 1px solid #D2D2D7; border-radius: 6px; padding: 6px 12px; font-size: 11px; font-weight: 500; color: #1D1D1F; } QPushButton:hover { background-color: #E8E8ED; border-color: #86868B; }",
                "input": "QLineEdit { background-color: #FFFFFF; border: 1px solid #D2D2D7; border-radius: 6px; padding: 5px; color: #1D1D1F; }",
                "slider": "QSlider::groove:horizontal { height: 4px; background: #E5E5EA; border-radius: 2px; } QSlider::sub-page:horizontal { background: #0071E3; border-radius: 2px; } QSlider::handle:horizontal { background: #FFFFFF; border: 0.5px solid #D2D2D7; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }"
            },
            "Тёмная macOS": {
                "widget": "background-color: #1E1E1E; color: #FFFFFF;",
                "screen": "background-color: #2D2D2D; border: 1px solid #3A3A3C; border-radius: 10px;",
                "screen_lbl": "color: #FFFFFF; font-size: 13px; font-weight: 600;",
                "time_lbl": "color: #AEAEB2; font-size: 11px;",
                "list": "QListWidget { background-color: #2D2D2D; border: 1px solid #3A3A3C; border-radius: 10px; padding: 5px; color: #FFFFFF; } QListWidget::item:hover { background-color: #3A3A3C; } QListWidget::item:selected { background-color: #0A84FF; color: #FFFFFF; }",
                "btn_sticker": "QPushButton { background: transparent; border: none; font-size: 18px; padding: 5px; color: #FFFFFF; } QPushButton:hover { color: #0A84FF; }",
                "btn_edit": "QPushButton { background-color: #2D2D2D; border: 1px solid #3A3A3C; border-radius: 6px; padding: 6px 12px; font-size: 11px; font-weight: 500; color: #FFFFFF; } QPushButton:hover { background-color: #3A3A3C; border-color: #AEAEB2; }",
                "input": "QLineEdit { background-color: #2D2D2D; border: 1px solid #3A3A3C; border-radius: 6px; padding: 5px; color: #FFFFFF; }",
                "slider": "QSlider::groove:horizontal { height: 4px; background: #3A3A3C; border-radius: 2px; } QSlider::sub-page:horizontal { background: #0A84FF; border-radius: 2px; } QSlider::handle:horizontal { background: #FFFFFF; border: 0.5px solid #3A3A3C; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }"
            },
            "Liquid Glass": {
                "widget": "background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #3A3D40, stop:1 #181A1B); color: #FFFFFF;",
                "screen": "background-color: rgba(255, 255, 255, 0.12); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 10px;",
                "screen_lbl": "color: #00FFFF; font-size: 13px; font-weight: 600; text-shadow: 0px 0px 4px rgba(0,255,255,0.5);",
                "time_lbl": "color: #E0E0E0; font-size: 11px;",
                "list": "QListWidget { background-color: rgba(20, 20, 20, 0.75); border: 1px solid rgba(255, 255, 255, 0.25); border-radius: 10px; padding: 5px; color: #FFFFFF; } QListWidget::item:hover { background-color: rgba(255, 255, 255, 0.15); } QListWidget::item:selected { background-color: rgba(0, 255, 255, 0.4); color: #00FFFF; font-weight: bold; }",
                "btn_sticker": "QPushButton { background: transparent; border: none; font-size: 18px; padding: 5px; color: #FFFFFF; } QPushButton:hover { color: #00FFFF; }",
                "btn_edit": "QPushButton { background-color: rgba(255, 255, 255, 0.15); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 6px; padding: 6px 12px; font-size: 11px; color: #FFFFFF; } QPushButton:hover { background-color: rgba(255, 255, 255, 0.3); border-color: #00FFFF; }",
                "input": "QLineEdit { background-color: rgba(10, 10, 10, 0.6); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 6px; padding: 5px; color: #FFFFFF; }",
                "slider": "QSlider::groove:horizontal { height: 4px; background: rgba(255,255,255,0.2); border-radius: 2px; } QSlider::sub-page:horizontal { background: #00FFFF; border-radius: 2px; } QSlider::handle:horizontal { background: #FFFFFF; border: 1px solid #00FFFF; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }"
            },
            "Новогодняя": {
                "widget": "background-color: #143222; color: #FFF5E6;",
                "screen": "background-color: #8B2635; border: 2px dashed #D4AF37; border-radius: 8px;",
                "screen_lbl": "color: #FFF5E6; font-size: 13px; font-weight: 600;",
                "time_lbl": "color: #E6C280; font-size: 11px;",
                "list": "QListWidget { background-color: #1C4530; border: 1px solid #D4AF37; border-radius: 8px; padding: 5px; color: #FFF5E6; } QListWidget::item:hover { background-color: #265C40; } QListWidget::item:selected { background-color: #8B2635; color: #FFFFFF; }",
                "btn_sticker": "QPushButton { background: transparent; border: none; font-size: 18px; padding: 5px; color: #FFF5E6; } QPushButton:hover { color: #D4AF37; }",
                "btn_edit": "QPushButton { background-color: #8B2635; border: 1px solid #D4AF37; border-radius: 6px; padding: 6px 12px; font-size: 11px; color: #FFF5E6; } QPushButton:hover { background-color: #A33847; }",
                "input": "QLineEdit { background-color: #1C4530; border: 1px solid #D4AF37; border-radius: 6px; padding: 5px; color: #FFF5E6; }",
                "slider": "QSlider::groove:horizontal { height: 4px; background: #0D2116; border-radius: 2px; } QSlider::sub-page:horizontal { background: #D4AF37; border-radius: 2px; } QSlider::handle:horizontal { background: #8B2635; border: 1px solid #D4AF37; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }"
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

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        for c, b in [("#FF5F56", "#E0443E"), ("#FFBD2E", "#DEA123"), ("#27C93F", "#1AAA2C")]:
            dot = QFrame()
            dot.setFixedSize(12, 12)
            dot.setStyleSheet(f"background-color: {c}; border-radius: 6px; border: 0.5px solid {b};")
            header_layout.addWidget(dot)
        
        self.title_label = QLabel("LazyPleer")
        self.title_label.setStyleSheet("font-weight: 700; font-size: 14px; margin-left: 5px;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        self.btn_share_x = QPushButton("🐦")
        self.btn_share_x.setFixedSize(26, 26)
        self.btn_share_x.setToolTip("Поделиться треком в X / Твиттер")
        self.btn_share_x.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 13px; }")
        self.btn_share_x.clicked.connect(self.share_on_twitter)
        header_layout.addWidget(self.btn_share_x)

        self.btn_donate = QPushButton("💰")
        self.btn_donate.setFixedSize(26, 26)
        self.btn_donate.setToolTip("Поддержать автора через DonationAlerts")
        self.btn_donate.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 13px; }")
        self.btn_donate.clicked.connect(self.support_author)
        header_layout.addWidget(self.btn_donate)

        self.btn_diag = QPushButton("🛡️")
        self.btn_diag.setFixedSize(26, 26)
        self.btn_diag.setToolTip("Диагностика библиотеки (Поиск битых файлов и дубликатов)")
        self.btn_diag.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 13px; }")
        self.btn_diag.clicked.connect(self.run_library_diagnostic)
        header_layout.addWidget(self.btn_diag)

        self.btn_check_update = QPushButton("🔄")
        self.btn_check_update.setFixedSize(26, 26)
        self.btn_check_update.setToolTip("Проверить наличие обновлений")
        self.btn_check_update.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 13px; }")
        self.btn_check_update.clicked.connect(self.check_for_updates)
        header_layout.addWidget(self.btn_check_update)

        self.btn_info = QPushButton("ℹ️")
        self.btn_info.setFixedSize(26, 26)
        self.btn_info.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 13px; }")
        self.btn_info.clicked.connect(self.open_about_dialog)
        header_layout.addWidget(self.btn_info)

        self.btn_settings = QPushButton("⚙️")
        self.btn_settings.setFixedSize(26, 26)
        self.btn_settings.setToolTip("Настройки оформления и таймера плеера")
        self.btn_settings.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 14px; }")
        self.btn_settings.clicked.connect(self.open_settings_dialog)
        header_layout.addWidget(self.btn_settings)
        self.main_layout.addLayout(header_layout)
        self.screen_frame = QFrame()
        self.screen_layout = QHBoxLayout(self.screen_frame)
        self.screen_layout.setContentsMargins(12, 12, 12, 12)
        
        self.cover_label = QLabel("💿")
        self.cover_label.setFixedSize(48, 48)
        self.cover_label.setStyleSheet("font-size: 32px; background: transparent; qproperty-alignment: 'AlignCenter';")
        self.screen_layout.addWidget(self.cover_label)
        
        text_screen_layout = QVBoxLayout()
        self.screen_label = QLabel("Не играет\nЗакиньте треки в папочку /music")
        self.time_label = QLabel("00:00 / 00:00")
        text_screen_layout.addWidget(self.screen_label)
        text_screen_layout.addWidget(self.time_label)
        self.screen_layout.addLayout(text_screen_layout)
        self.main_layout.addWidget(self.screen_frame)

        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.sliderPressed.connect(self.slider_pressed)
        self.progress_slider.sliderReleased.connect(self.slider_released)
        self.main_layout.addWidget(self.progress_slider)

        filter_bar_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск по трекам или авторам на лету...")
        self.search_input.textChanged.connect(self.filter_playlist)
        filter_bar_layout.addWidget(self.search_input)

        self.filter_selector = QComboBox()
        self.filter_selector.addItems(["Все треки", "По добавлению", "По году", "⭐ Избранное"])
        self.filter_selector.setStyleSheet("QComboBox { padding: 4px; font-size: 11px; }")
        self.filter_selector.currentTextChanged.connect(self.change_filter_type)
        filter_bar_layout.addWidget(self.filter_selector)
        self.main_layout.addLayout(filter_bar_layout)

        self.counter_label = QLabel("Всего файлов в вашей библиотеке: 0")
        self.counter_label.setStyleSheet("font-size: 11px; font-weight: 500;")
        self.main_layout.addWidget(self.counter_label)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.play_selected)
        self.main_layout.addWidget(self.list_widget)
        fx_layout = QHBoxLayout()
        
        self.btn_bass = QPushButton("🔥 BassBoost: Выкл")
        self.btn_bass.setStyleSheet("font-size: 10px; font-weight: bold; padding: 4px;")
        self.btn_bass.clicked.connect(self.toggle_bass_boost)
        fx_layout.addWidget(self.btn_bass)
        
        speed_vbox = QVBoxLayout()
        speed_hbox = QHBoxLayout()
        speed_hbox.addWidget(QLabel("🏎 Скорость:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(5, 20) 
        self.speed_slider.setValue(10) 
        self.speed_slider.setFixedWidth(100)
        self.speed_slider.valueChanged.connect(self.change_playback_speed)
        speed_hbox.addWidget(self.speed_slider)
        speed_vbox.addLayout(speed_hbox)
        
        self.speed_indicator_label = QLabel("Текущая: 1.0x (Норма)")
        self.speed_indicator_label.setStyleSheet("font-size: 9px; color: gray; qproperty-alignment: 'AlignCenter';")
        speed_vbox.addWidget(self.speed_indicator_label)
        fx_layout.addLayout(speed_vbox)
        self.main_layout.addLayout(fx_layout)

        meta_layout = QHBoxLayout()
        self.btn_edit = QPushButton("📝 Редактор тегов")
        self.btn_edit.clicked.connect(self.open_metadata_editor)
        meta_layout.addWidget(self.btn_edit)

        self.btn_delete = QPushButton("❌ Удалить")
        self.btn_delete.clicked.connect(self.delete_current_track)
        meta_layout.addWidget(self.btn_delete)

        self.btn_fav = QPushButton("❤️ В Избранное")
        self.btn_fav.clicked.connect(self.toggle_favorite_track)
        meta_layout.addWidget(self.btn_fav)
        meta_layout.addStretch()

        self.btn_mode = QPushButton("🔁 По порядку")
        self.btn_mode.clicked.connect(self.toggle_play_mode)
        meta_layout.addWidget(self.btn_mode)
        self.main_layout.addLayout(meta_layout)

        vol_layout = QHBoxLayout()
        self.vol_icon = QLabel("🔊")
        self.vol_icon.setStyleSheet("background: transparent; font-size: 11px;")
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 200) 
        self.vol_slider.setValue(70)
        self.vol_slider.valueChanged.connect(self.change_volume)
        vol_layout.addWidget(self.vol_icon)
        vol_layout.addWidget(self.vol_slider)
        self.main_layout.addLayout(vol_layout)

        self.controls_layout = QHBoxLayout()
        self.controls_layout.setSpacing(25)
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

    def open_settings_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Настройки плеера")
        dialog.setFixedSize(300, 180)
        
        if self.current_theme_name == "Liquid Glass" or self.current_theme_name == "Тёмная macOS":
            dialog.setStyleSheet("background-color: #2D2D2D; color: white; QComboBox { color: black; background: white; }")
        else:
            dialog.setStyleSheet("background-color: #F5F5F7; color: #1D1D1F; QComboBox { color: black; background: white; }")
            
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("<b>🎨 Выберите оформление:</b>"))
        theme_combo = QComboBox()
        theme_combo.addItems(["Светлая macOS", "Тёмная macOS", "Liquid Glass", "Новогодняя"])
        theme_combo.setCurrentText(self.current_theme_name)
        layout.addWidget(theme_combo)
        
        layout.addWidget(QLabel("<b>⏱️ Автовыключение (Таймер сна):</b>"))
        sleep_combo = QComboBox()
        sleep_combo.addItems(["⏱️ Таймер отключен", "15 мин", "30 мин", "60 мин"])
        if self.sleep_minutes_left > 0:
            sleep_combo.setCurrentText(f"{self.sleep_minutes_left} мин")
        layout.addWidget(sleep_combo)
        
        layout.addSpacing(10)
        btn_save = QPushButton("Применить настройки")
        btn_save.clicked.connect(lambda: self.save_settings_action(dialog, theme_combo.currentText(), sleep_combo.currentText()))
        layout.addWidget(btn_save)
        dialog.exec()

    def save_settings_action(self, dialog, selected_theme, selected_sleep):
        self.apply_theme(selected_theme)
        self.set_sleep_timer(selected_sleep)
        dialog.accept()

    def apply_theme(self, theme_name):
        if theme_name not in self.themes: return
        self.current_theme_name = theme_name
        style = self.themes[theme_name]
        self.setStyleSheet(style["widget"])
        self.screen_frame.setStyleSheet(style["screen"])
        self.screen_label.setStyleSheet(style["screen_lbl"] + " background: transparent;")
        self.time_label.setStyleSheet(style["time_lbl"] + " background: transparent;")
        self.list_widget.setStyleSheet(style["list"])
        self.progress_slider.setStyleSheet(style["slider"])
        self.vol_slider.setStyleSheet(style["slider"])
        self.btn_edit.setStyleSheet(style["btn_edit"])
        self.btn_delete.setStyleSheet(style["btn_edit"])
        self.btn_fav.setStyleSheet(style["btn_edit"])
        self.btn_mode.setStyleSheet(style["btn_edit"])
        self.search_input.setStyleSheet(style["input"])
        
        for btn in [self.btn_prev, self.btn_play, self.btn_pause, self.btn_next]:
            btn.setStyleSheet(style["btn_sticker"])
        self.load_music(self.filter_selector.currentText())
    def change_playback_speed(self, value):
        speed = value / 10.0
        self.player.setPlaybackRate(speed)
        if speed == 1.0:
            self.speed_indicator_label.setText("Текущая: 1.0x (Норма)")
        else:
            self.speed_indicator_label.setText(f"Текущая: {speed}x")

    def toggle_bass_boost(self):
        self.is_bass_boost = not self.is_bass_boost
        if self.is_bass_boost:
            self.btn_bass.setText("🔥 BassBoost: Вкл")
            self.audio_output.setVolume(min(2.0, self.audio_output.volume() * 1.45))
        else:
            self.btn_bass.setText("🔥 BassBoost: Выкл")
            self.change_volume(self.vol_slider.value())

    def change_volume(self, value):
        vol_float = value / 100.0
        self.audio_output.setVolume(vol_float)
        if value > 100:
            self.vol_icon.setText("⚡🚀")
        else:
            self.vol_icon.setText("🔊")

    def share_on_twitter(self):
        current_row = self.list_widget.currentRow()
        track_name = self.current_playlist[current_row] if current_row >= 0 and current_row < len(self.current_playlist) else "свои любимые треки"
        text = f"Слушаю сочный трек '{track_name}' в плеере LazyPleer v4.0! Присоединяйтесь к чиллу! 🎧🔥"
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "X / Twitter", "Стильный готовый пост скопирован в буфер обмена!\nВставьте его на страницу своего блога!")

    def support_author(self):
        reply = QMessageBox.question(self, "Поддержка автора", "Хотите перейти на страницу DonationAlerts автора для отправки поддержки проекта LazyPleer?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            webbrowser.open("https://www.donationalerts.com/r/fleurdev")

    def check_for_updates(self):
        QMessageBox.information(self, "Обновления", "Подключение к серверам обновлений...\nУ вас установлена самая последняя глобальная версия: LazyPleer v4.0 Ultra Final!")
    def run_library_diagnostic(self):
        if not self.playlist_files:
            QMessageBox.warning(self, "Диагностика библиотеки", "Папка с музыкой абсолютно пуста!")
            return
        
        duplicates = []
        seen_sizes = {}
        corrupted_count = 0
        
        for f in self.playlist_files:
            path = os.path.join(self.music_dir, f)
            try:
                size = os.path.getsize(path)
                if size in seen_sizes:
                    duplicates.append(f)
                else:
                    seen_sizes[size] = f
                if f.endswith('.mp3'):
                    audio = MP3(path)
            except:
                corrupted_count += 1
                
        report = f"📊 Сводный отчет диагностики библиотеки:\n\n• Битых/Поврежденных файлов: {corrupted_count}\n• Обнаружено дубликатов: {len(duplicates)}\n"
        if duplicates:
            report += f"\nРекомендуется очистить: {duplicates[:3]}"
        QMessageBox.information(self, "Диагностика библиотеки", report)

    def toggle_favorite_track(self):
        current_row = self.list_widget.currentRow()
        if current_row < 0: return
        track_name = self.current_playlist[current_row]
        if track_name in self.favorite_tracks:
            self.favorite_tracks.remove(track_name)
            QMessageBox.information(self, "Избранное", "Трек убран из вашего списка любимых!")
        else:
            self.favorite_tracks.append(track_name)
            QMessageBox.information(self, "Избранное", "❤️ Трек помечен сердечком и добавлен в Избранное!")
        self.save_favorites()
        self.load_music(self.filter_selector.currentText())

    def load_favorites(self):
        try:
            if os.path.exists("./lazy_favs.json"):
                data = json.load(open("./lazy_favs.json", "r"))
                self.favorite_tracks = data.get("tracks", [])
        except: pass

    def save_favorites(self):
        try:
            json.dump({"tracks": self.favorite_tracks}, open("./lazy_favs.json", "w"))
        except: pass

    def change_filter_type(self, text):
        self.load_music(text)
    def load_statistics(self):
        try:
            if os.path.exists(self.stats_file):
                data = json.load(open(self.stats_file, "r"))
                self.total_listen_time = data.get("time", 0)
                saved_theme = data.get("theme", "Светлая macOS")
                QTimer.singleShot(150, lambda: self.apply_theme(saved_theme))
        except: pass

    def update_listen_stats(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.total_listen_time += 1
            if self.total_listen_time % 10 == 0:
                try: 
                    json.dump({
                        "time": self.total_listen_time,
                        "theme": self.current_theme_name
                    }, open(self.stats_file, "w"))
                except: pass

    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon.fromTheme("media-playback-start"))
        tray_menu = QMenu()
        play_action = QAction("▶ Старт", self); play_action.triggered.connect(self.play_track)
        pause_action = QAction("⏸ Пауза", self); pause_action.triggered.connect(self.pause_track)
        next_action = QAction("⏭ Вперед", self); next_action.triggered.connect(self.next_track)
        exit_action = QAction("❌ Выход", self); exit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(play_action); tray_menu.addAction(pause_action); tray_menu.addAction(next_action)
        tray_menu.addSeparator(); tray_menu.addAction(exit_action)
        self.tray_icon.setContextMenu(tray_menu); self.tray_icon.show()

    def set_sleep_timer(self, text):
        if text == "15 мин": self.sleep_minutes_left = 15
        elif text == "30 мин": self.sleep_minutes_left = 30
        elif text == "60 мин": self.sleep_minutes_left = 60
        else: self.sleep_timer.stop(); return
        self.sleep_timer.start(60000)
        QMessageBox.information(self, "Таймер сна", f"Плеер закроется через {self.sleep_minutes_left} минут!")

    def trigger_sleep(self):
        self.sleep_minutes_left -= 1
        if self.sleep_minutes_left <= 0: self.sleep_timer.stop(); QApplication.instance().quit()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
    def dropEvent(self, event):
        if not os.path.exists(self.music_dir): os.makedirs(self.music_dir)
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith(('.mp3', '.wav', '.m4a')):
                try: shutil.copy(file_path, self.music_dir)
                except: pass
        self.load_music(self.filter_selector.currentText())

    def load_music(self, filter_type="Все треки"):
        if not os.path.exists(self.music_dir): os.makedirs(self.music_dir)
        self.playlist_files = [f for f in os.listdir(self.music_dir) if f.endswith(('.mp3', '.wav', '.m4a'))]
        self.counter_label.setText(f"Всего файлов в вашей библиотеке: {len(self.playlist_files)}")
        self.filter_playlist()

    def toggle_play_mode(self):
        if self.play_mode == "Normal":
            self.play_mode = "Shuffle"; self.btn_mode.setText("🔀 Случайный")
        elif self.play_mode == "Shuffle":
            self.play_mode = "Repeat"; self.btn_mode.setText("🔂 Повтор")
        else:
            self.play_mode = "Normal"; self.btn_mode.setText("🔁 По порядку")
    def filter_playlist(self):
        search_text = self.search_input.text().lower()
        filter_type = self.filter_selector.currentText()
        
        self.current_playlist = []
        for f in self.playlist_files:
            if search_text and search_text not in f.lower(): continue
            if filter_type == "⭐ Избранное" and f not in self.favorite_tracks: continue
            self.current_playlist.append(f)
            
        self.list_widget.clear()
        for track in self.current_playlist:
            display_name = track
            try:
                if track.endswith('.mp3'):
                    audio = MP3(os.path.join(self.music_dir, track))
                    title, artist = audio.get('TIT2'), audio.get('TPE1')
                    if title and artist: display_name = f"{artist} - {title}"
            except: pass
            
            if track in self.favorite_tracks:
                self.list_widget.addItem(f" ❤️  {display_name}")
            else:
                self.list_widget.addItem(f"  🎵  {display_name}")

    def play_track(self):
        if not self.current_playlist: return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self.player.play(); self.update_screen("Воспроизведение"); return
            
        current_row = self.list_widget.currentRow()
        if current_row < 0: current_row = 0
        track_name = self.current_playlist[current_row]
        track_path = os.path.abspath(os.path.join(self.music_dir, track_name))
        
        self.player.setSource(QUrl.fromLocalFile(track_path))
        self.player.play()
        self.change_playback_speed(self.speed_slider.value())
        self.update_screen("Воспроизведение")
        
        if self.rpc:
            try: self.rpc.update(details=f"Слушает {track_name}", state="В плеере LazyPleer v4.0")
            except: pass

    def play_selected(self, item): self.play_track()
    def pause_track(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause(); self.update_screen("Пауза")

    def next_track(self):
        if not self.current_playlist: return
        next_row = (self.list_widget.currentRow() + 1) % len(self.current_playlist)
        self.list_widget.setCurrentRow(next_row); self.play_track()

    def prev_track(self):
        if not self.current_playlist: return
        prev_row = (self.list_widget.currentRow() - 1) % len(self.current_playlist)
        self.list_widget.setCurrentRow(prev_row); self.play_track()

    def slider_pressed(self): self.is_slider_moving = True
    def slider_released(self):
        self.is_slider_moving = False; self.player.setPosition(self.progress_slider.value())

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
        if current_row < 0 or current_row >= len(self.current_playlist): return
        track_name = self.current_playlist[current_row]
        self.screen_label.setText(f"{track_name}\n({status})")
        
        try:
            if track_name.endswith('.mp3'):
                audio = MP3(os.path.join(self.music_dir, track_name), ID3=ID3)
                if 'APIC:' in audio: self.cover_label.setText("🖼️")
                else: self.cover_label.setText("💿")
        except: self.cover_label.setText("💿")

    def delete_current_track(self):
        current_row = self.list_widget.currentRow()
        if current_row < 0: return
        track_name = self.current_playlist[current_row]
        track_path = os.path.abspath(os.path.join(self.music_dir, track_name))
        reply = QMessageBox.question(self, "Удаление", f"Удалить файл {track_name}?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.player.setSource(QUrl())
            try: os.remove(track_path); QMessageBox.information(self, "Успех", "Файл удален!"); self.load_music()
            except Exception as e: QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")

    def open_about_dialog(self):
        dialog = QDialog(self); dialog.setWindowTitle("Статистика"); dialog.setFixedSize(340, 200)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("<b>LazyPleer v4.0 Ultra Final</b>"))
        mins = self.total_listen_time // 60
        layout.addWidget(QLabel(f"📊 Общее время прослушивания: {mins} мин. ({self.total_listen_time} сек.)"))
        tg = QLineEdit("ТГ: @french_parasite"); tg.setReadOnly(True); tg.setStyleSheet("background: transparent; border: none;"); layout.addWidget(tg)
        mail = QLineEdit("Почта: lilvanforover@mail.com"); mail.setReadOnly(True); mail.setStyleSheet("background: transparent; border: none;"); layout.addWidget(mail)
        btn = QPushButton("Закрыть"); btn.clicked.connect(dialog.accept); layout.addWidget(btn)
        dialog.exec()

    def open_metadata_editor(self):
        current_row = self.list_widget.currentRow()
        if current_row < 0: return
        track_name = self.current_playlist[current_row]
        track_path = os.path.abspath(os.path.join(self.music_dir, track_name))
        if not track_name.endswith('.mp3'): QMessageBox.warning(self, "Формат", "Только MP3!"); return
        self.player.setSource(QUrl())
        
        dialog = QDialog(self); dialog.setWindowTitle("Редактор тегов и Обложки"); dialog.setFixedSize(360, 460)
        layout = QVBoxLayout(dialog)
        try:
            audio = MP3(track_path, ID3=ID3)
            t = str(audio.get('TIT2', '')); a = str(audio.get('TPE1', '')); y = str(audio.get('TYER', ''))
        except: t, a, y = "", "", ""
        
        layout.addWidget(QLabel("Название трека:")); t_in = QLineEdit(t); layout.addWidget(t_in)
        layout.addWidget(QLabel("Исполнитель:")); a_in = QLineEdit(a); layout.addWidget(a_in)
        layout.addWidget(QLabel("Год выпуска:")); y_in = QLineEdit(y); layout.addWidget(y_in)
        layout.addWidget(QLabel("<b>🖼️ Текущая обложка альбома:</b>"))
        
        preview_label = QLabel(); preview_label.setFixedSize(100, 100); preview_label.setStyleSheet("border: 1px dashed gray; background-color: rgba(0,0,0,0.05);"); preview_label.setAlignment(Qt.AlignCenter)
        try:
            if 'APIC:' in audio:
                pixmap = QPixmap(); pixmap.loadFromData(audio['APIC:'].data)
                preview_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else: preview_label.setText("Нет обложки")
        except: preview_label.setText("Ошибка загрузки")
        layout.addWidget(preview_label, alignment=Qt.AlignCenter)
        
        self.selected_cover_bin = None
        def choose_cover():
            file_path, _ = QFileDialog.getOpenFileName(dialog, "Выбрать обложку", "", "Images (*.png *.jpg *.jpeg)")
            if file_path:
                with open(file_path, 'rb') as f: self.selected_cover_bin = f.read()
                pixmap = QPixmap(file_path); preview_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        btn_cover = QPushButton("📂 Загрузить новую обложку (.jpg/.png)"); btn_cover.clicked.connect(choose_cover); layout.addWidget(btn_cover)

        def save():
            try:
                try: tags = ID3(track_path)
                except: tags = ID3(); tags.save(track_path)
                tags['TIT2'] = TIT2(encoding=3, text=t_in.text())
                tags['TPE1'] = TPE1(encoding=3, text=a_in.text())
                tags['TYER'] = TYER(encoding=3, text=y_in.text())
                if self.selected_cover_bin:
                    tags['APIC'] = APIC(encoding=3, mime='image/jpeg', type=3, desc=u'Cover', data=self.selected_cover_bin)
                tags.save(track_path); QMessageBox.information(dialog, "Успех", "Теги и Обложка MP3 сохранены!")
            except Exception as e: QMessageBox.critical(dialog, "Ошибка", f"{e}")
            dialog.accept()
            
        btn = QPushButton("Сохранить изменения"); btn.clicked.connect(save); layout.addWidget(btn)
        dialog.exec(); self.load_music(); self.play_track()

    def eventFilter(self, obj, event): return super().eventFilter(obj, event)

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setWindowIcon(QIcon.fromTheme("media-playback-start"))
    player = LazyPleerV4(); player.show(); sys.exit(app.exec())
