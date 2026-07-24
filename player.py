import os, sys, shutil, json, logging, webbrowser, random
from PySide6.QtCore import (QUrl, QTime, Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint)
from PySide6.QtGui import QIcon, QAction, QPixmap
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QFileDialog,
    QListWidget, QPushButton, QVBoxLayout, QWidget, QSlider, QDialog, QLineEdit,
    QMessageBox, QComboBox, QSystemTrayIcon, QMenu, QInputDialog, QGraphicsOpacityEffect)
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, APIC, TYER

try:
    import vlc
    VLC_AVAILABLE = True
except Exception:
    VLC_AVAILABLE = False

try:
    from pypresence import Presence
    DISCORD_AVAILABLE = True
except Exception:
    DISCORD_AVAILABLE = False

# ---------------------------------------------------------------------------
# Все файлы (музыка, плейлисты, статистика, избранное, логи) лежат РЯДОМ
# С ПРОГРАММОЙ, а не в "текущей папке запуска" — иначе .exe создаёт файлы
# не там, где надо.
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

MUSIC_DIR = os.path.join(APP_DIR, "music")
PLAYLISTS_DIR = os.path.join(APP_DIR, "playlists")
STATS_FILE = os.path.join(APP_DIR, "lazy_stats.json")
FAVS_FILE = os.path.join(APP_DIR, "lazy_favs.json")
LOG_FILE = os.path.join(APP_DIR, "lazy_pleer.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("LazyPleer")

LIBRARY_LABEL = "📚 Вся библиотека"
NEW_PLAYLIST_LABEL = "➕ Создать плейлист..."

# 10-полосный эквалайзер libvlc: индекс -> примерная центральная частота
EQ_BAND_FREQS = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]

EQ_PRESETS = {
    "Плоский (выкл)":  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "Бас-буст":        [10, 8, 5, 2, 0, 0, 0, 0, 0, 0],
    "Вокал":           [-2, -2, 0, 3, 5, 5, 3, 1, 0, -1],
    "Рок":             [6, 4, 2, 0, -2, -1, 2, 4, 5, 5],
    "Электроника":     [7, 6, 2, 0, -2, 0, 2, 4, 6, 7],
}


def resource_free_name(base_name: str) -> str:
    """Убирает символы, которые нельзя использовать в имени файла."""
    bad = '<>:"/\\|?*'
    return "".join(c for c in base_name if c not in bad).strip() or "Без имени"


def enable_windows_blur(widget: QWidget):
    """
    Пытается включить настоящий блюр фона окна (эффект в духе macOS/Win11 Acrylic)
    через недокументированный DWM API. Работает только на Windows 10/11.
    На других ОС и в случае любой ошибки — тихо ничего не делает,
    тема просто останется полупрозрачной без блюра.
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        class ACCENT_POLICY(ctypes.Structure):
            _fields_ = [
                ("AccentState", ctypes.c_int),
                ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_int),
                ("AnimationId", ctypes.c_int),
            ]

        class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
            _fields_ = [
                ("Attribute", ctypes.c_int),
                ("Data", ctypes.POINTER(ACCENT_POLICY)),
                ("SizeOfData", ctypes.c_size_t),
            ]

        ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
        WCA_ACCENT_POLICY = 19

        accent = ACCENT_POLICY()
        accent.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
        accent.AccentFlags = 2
        accent.GradientColor = 0x66222222  # ARGB: полупрозрачный тёмный подложка
        accent.AnimationId = 0

        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = WCA_ACCENT_POLICY
        data.Data = ctypes.pointer(accent)
        data.SizeOfData = ctypes.sizeof(accent)

        hwnd = int(widget.winId())
        set_attr = ctypes.windll.user32.SetWindowCompositionAttribute
        set_attr(hwnd, ctypes.pointer(data))
        return True
    except Exception as e:
        log.info(f"Блюр окна недоступен (не Windows 10/11 или нет прав): {e}")
        return False


class MiniPlayer(QWidget):
    """Компактный плеер поверх окон: обложка/название + play/pause/next."""

    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(280, 84)
        self._drag_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.cover_lbl = QLabel("💿")
        self.cover_lbl.setFixedSize(44, 44)
        self.cover_lbl.setStyleSheet("font-size: 26px; qproperty-alignment: 'AlignCenter';")
        layout.addWidget(self.cover_lbl)

        mid = QVBoxLayout()
        self.title_lbl = QLabel("Ничего не играет")
        self.title_lbl.setStyleSheet("color: white; font-size: 11px; font-weight: 600;")
        self.title_lbl.setWordWrap(True)
        mid.addWidget(self.title_lbl)

        controls = QHBoxLayout()
        self.btn_prev = QPushButton("⏮"); self.btn_prev.clicked.connect(lambda: self.main.prev_track())
        self.btn_play = QPushButton("⏯"); self.btn_play.clicked.connect(self.toggle_play)
        self.btn_next = QPushButton("⏭"); self.btn_next.clicked.connect(lambda: self.main.next_track())
        self.btn_close = QPushButton("✕"); self.btn_close.clicked.connect(self.close_mini)
        for b in (self.btn_prev, self.btn_play, self.btn_next, self.btn_close):
            b.setFixedSize(24, 24)
            b.setStyleSheet("QPushButton { background: rgba(255,255,255,0.12); border: none; "
                             "border-radius: 12px; color: white; font-size: 11px; } "
                             "QPushButton:hover { background: rgba(255,255,255,0.25); }")
            controls.addWidget(b)
        mid.addLayout(controls)
        layout.addLayout(mid)

        self.setStyleSheet(
            "background: rgba(20,20,20,0.82); border-radius: 16px; "
            "border: 1px solid rgba(255,255,255,0.15);"
        )

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(700)

    def toggle_play(self):
        if self.main.player and self.main.player.is_playing():
            self.main.pause_track()
        else:
            self.main.play_track()

    def refresh(self):
        row = self.main.list_widget.currentRow()
        if 0 <= row < len(self.main.current_playlist):
            self.title_lbl.setText(self.main.current_playlist[row])
            self.cover_lbl.setText(self.main.cover_label.text())

    def close_mini(self):
        self.refresh_timer.stop()
        self.main.mini_player = None
        self.main.show()
        self.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)


class EqualizerDialog(QDialog):
    """Полноценный 10-полосный эквалайзер с пресетами."""

    def __init__(self, parent, current_gains, on_change, on_save_custom):
        super().__init__(parent)
        self.setWindowTitle("Эквалайзер")
        self.setFixedSize(420, 320)
        self.on_change = on_change
        self.sliders = []

        layout = QVBoxLayout(self)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Пресет:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(EQ_PRESETS.keys()) + ["Свой"])
        self.preset_combo.currentTextChanged.connect(self.apply_preset)
        preset_row.addWidget(self.preset_combo)
        layout.addLayout(preset_row)

        bands_row = QHBoxLayout()
        for i, freq in enumerate(EQ_BAND_FREQS):
            col = QVBoxLayout()
            lbl_val = QLabel("0")
            lbl_val.setAlignment(Qt.AlignCenter)
            lbl_val.setStyleSheet("font-size: 9px;")
            slider = QSlider(Qt.Vertical)
            slider.setRange(-20, 20)
            slider.setValue(current_gains[i] if i < len(current_gains) else 0)
            lbl_val.setText(str(slider.value()))
            slider.valueChanged.connect(lambda v, l=lbl_val: l.setText(str(v)))
            slider.valueChanged.connect(self.on_slider_changed)
            slider.setFixedHeight(140)
            col.addWidget(slider, alignment=Qt.AlignCenter)
            col.addWidget(lbl_val)
            freq_label = f"{freq}Гц" if freq < 1000 else f"{freq // 1000}к"
            col.addWidget(QLabel(freq_label), alignment=Qt.AlignCenter)
            bands_row.addLayout(col)
            self.sliders.append(slider)
        layout.addLayout(bands_row)

        btn_row = QHBoxLayout()
        btn_save = QPushButton("💾 Сохранить как 'Свой'")
        btn_save.clicked.connect(lambda: on_save_custom(self.get_gains()))
        btn_row.addWidget(btn_save)
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def apply_preset(self, name):
        if name not in EQ_PRESETS:
            return
        gains = EQ_PRESETS[name]
        for slider, val in zip(self.sliders, gains):
            slider.blockSignals(True)
            slider.setValue(val)
            slider.blockSignals(False)
        self.on_slider_changed()

    def on_slider_changed(self, *_):
        self.on_change(self.get_gains())

    def get_gains(self):
        return [s.value() for s in self.sliders]


class LazyPleerV4(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LazyPleer v5.0")
        self.setMinimumSize(480, 720)
        self.resize(480, 720)
        self.setAcceptDrops(True)

        if not VLC_AVAILABLE:
            QMessageBox.critical(
                self, "VLC не найден",
                "Не найдена библиотека python-vlc или сам VLC Player.\n\n"
                "1) Установи VLC Player: https://www.videolan.org/vlc/\n"
                "2) pip install python-vlc\n\n"
                "Без этого плеер не сможет проигрывать музыку."
            )

        self.vlc_instance = vlc.Instance("--no-video") if VLC_AVAILABLE else None
        self.player = self.vlc_instance.media_player_new() if self.vlc_instance else None

        self.equalizer = None
        self.eq_available = False
        self.eq_gains = list(EQ_PRESETS["Плоский (выкл)"])
        if VLC_AVAILABLE:
            # В разных версиях python-vlc класс называется по-разному:
            # старые -> vlc.Equalizer, новые -> vlc.AudioEqualizer
            eq_class = getattr(vlc, "AudioEqualizer", None) or getattr(vlc, "Equalizer", None)
            if eq_class is not None:
                try:
                    self.equalizer = eq_class()
                    self.eq_available = True
                except Exception as e:
                    log.warning(f"Эквалайзер VLC недоступен: {e}")
            else:
                log.warning(
                    "У установленной библиотеки vlc нет ни AudioEqualizer, ни Equalizer. "
                    "Скорее всего стоит не тот пакет (нужен 'python-vlc') "
                    "или очень нестандартная версия VLC Player."
                )

        self.is_bass_boost = False
        self.current_theme_name = "Светлая macOS"

        self.playlist_files = []
        self.current_playlist = []
        self.is_slider_moving = False
        self.play_mode = "Normal"

        self.playlists = {}          # name -> {"tracks": [...]}
        self.active_playlist = None  # None = вся библиотека

        self.total_listen_time = 0
        self.load_statistics()

        self.favorite_tracks = []
        self.load_favorites()

        self.mini_player = None

        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self.tick)
        self.playback_timer.start(500)

        self.sleep_timer = QTimer(self)
        self.sleep_timer.timeout.connect(self.trigger_sleep)
        self.sleep_minutes_left = 0

        self.rpc = None
        if DISCORD_AVAILABLE:
            try:
                self.rpc = Presence("123456789012345678")
                self.rpc.connect()
            except Exception as e:
                log.info(f"Discord RPC недоступен: {e}")
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
                "slider": "QSlider::groove:horizontal { height: 4px; background: #E5E5EA; border-radius: 2px; } QSlider::sub-page:horizontal { background: #0071E3; border-radius: 2px; } QSlider::handle:horizontal { background: #FFFFFF; border: 0.5px solid #D2D2D7; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }",
                "blur": False,
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
                "slider": "QSlider::groove:horizontal { height: 4px; background: #3A3A3C; border-radius: 2px; } QSlider::sub-page:horizontal { background: #0A84FF; border-radius: 2px; } QSlider::handle:horizontal { background: #FFFFFF; border: 0.5px solid #3A3A3C; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }",
                "blur": False,
            },
            "Liquid Glass": {
                # v2: более "стеклянный" градиент, мягкое свечение акцента,
                # тонкие полупрозрачные бордеры + попытка настоящего блюра окна.
                "widget": ("background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, "
                           "stop:0 rgba(58,61,64,0.55), stop:1 rgba(20,22,23,0.55)); color: #FFFFFF;"),
                "screen": ("background-color: rgba(255, 255, 255, 0.08); "
                           "border: 1px solid rgba(255, 255, 255, 0.22); border-radius: 14px;"),
                "screen_lbl": "color: #E7FBFF; font-size: 13px; font-weight: 600;",
                "time_lbl": "color: #C9D6DA; font-size: 11px;",
                "list": ("QListWidget { background-color: rgba(15, 16, 18, 0.45); "
                          "border: 1px solid rgba(255, 255, 255, 0.16); border-radius: 14px; padding: 6px; "
                          "color: #F2FBFF; } "
                          "QListWidget::item { border-radius: 8px; padding: 3px; } "
                          "QListWidget::item:hover { background-color: rgba(255, 255, 255, 0.10); } "
                          "QListWidget::item:selected { background-color: rgba(90, 200, 255, 0.35); "
                          "color: #EAFCFF; font-weight: bold; }"),
                "btn_sticker": ("QPushButton { background: transparent; border: none; font-size: 18px; "
                                "padding: 5px; color: #EAF6FF; } "
                                "QPushButton:hover { color: #7FE0FF; }"),
                "btn_edit": ("QPushButton { background-color: rgba(255, 255, 255, 0.10); "
                             "border: 1px solid rgba(255, 255, 255, 0.22); border-radius: 8px; "
                             "padding: 6px 12px; font-size: 11px; color: #EAF6FF; } "
                             "QPushButton:hover { background-color: rgba(255, 255, 255, 0.22); "
                             "border-color: #7FE0FF; }"),
                "input": ("QLineEdit { background-color: rgba(10, 10, 12, 0.45); "
                           "border: 1px solid rgba(255, 255, 255, 0.22); border-radius: 8px; "
                           "padding: 5px; color: #FFFFFF; }"),
                "slider": ("QSlider::groove:horizontal { height: 4px; background: rgba(255,255,255,0.18); "
                           "border-radius: 2px; } "
                           "QSlider::sub-page:horizontal { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, "
                           "stop:0 #5AC8FA, stop:1 #7FE0FF); border-radius: 2px; } "
                           "QSlider::handle:horizontal { background: #FFFFFF; border: 1px solid #7FE0FF; "
                           "width: 13px; height: 13px; margin: -5px 0; border-radius: 7px; }"),
                "blur": True,
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
                "slider": "QSlider::groove:horizontal { height: 4px; background: #0D2116; border-radius: 2px; } QSlider::sub-page:horizontal { background: #D4AF37; border-radius: 2px; } QSlider::handle:horizontal { background: #8B2635; border: 1px solid #D4AF37; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }",
                "blur": False,
            }
        }
        self.init_ui()
        self.init_tray()
        self.load_playlists()
        self.load_music()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
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

        self.btn_mini = QPushButton("🗗")
        self.btn_mini.setFixedSize(26, 26)
        self.btn_mini.setToolTip("Компактный мини-плеер поверх окон")
        self.btn_mini.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 13px; }")
        self.btn_mini.clicked.connect(self.open_mini_player)
        header_layout.addWidget(self.btn_mini)

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

        # эффект прозрачности для плавного fade обложки/названия при смене трека
        self.screen_opacity = QGraphicsOpacityEffect(self.screen_frame)
        self.screen_frame.setGraphicsEffect(self.screen_opacity)
        self.screen_opacity.setOpacity(1.0)

        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)  # промилле позиции VLC (0.0-1.0)
        self.progress_slider.sliderPressed.connect(self.slider_pressed)
        self.progress_slider.sliderReleased.connect(self.slider_released)
        self.main_layout.addWidget(self.progress_slider)

        # --- строка плейлистов ---
        playlist_row = QHBoxLayout()
        self.playlist_selector = QComboBox()
        self.playlist_selector.addItem(LIBRARY_LABEL)
        self.playlist_selector.addItem(NEW_PLAYLIST_LABEL)
        self.playlist_selector.currentTextChanged.connect(self.on_playlist_changed)
        playlist_row.addWidget(self.playlist_selector, stretch=1)

        self.btn_pl_add = QPushButton("➕")
        self.btn_pl_add.setToolTip("Добавить выбранный трек в текущий плейлист")
        self.btn_pl_add.setFixedWidth(30)
        self.btn_pl_add.clicked.connect(self.add_track_to_active_playlist)
        playlist_row.addWidget(self.btn_pl_add)

        self.btn_pl_remove = QPushButton("➖")
        self.btn_pl_remove.setToolTip("Убрать выбранный трек из текущего плейлиста")
        self.btn_pl_remove.setFixedWidth(30)
        self.btn_pl_remove.clicked.connect(self.remove_track_from_active_playlist)
        playlist_row.addWidget(self.btn_pl_remove)

        self.btn_pl_delete = QPushButton("🗑")
        self.btn_pl_delete.setToolTip("Удалить текущий плейлист")
        self.btn_pl_delete.setFixedWidth(30)
        self.btn_pl_delete.clicked.connect(self.delete_active_playlist)
        playlist_row.addWidget(self.btn_pl_delete)
        self.main_layout.addLayout(playlist_row)

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

        self.list_opacity = QGraphicsOpacityEffect(self.list_widget)
        self.list_widget.setGraphicsEffect(self.list_opacity)
        self.list_opacity.setOpacity(1.0)

        fx_layout = QHBoxLayout()

        self.btn_bass = QPushButton("🔥 BassBoost: Выкл")
        self.btn_bass.setStyleSheet("font-size: 10px; font-weight: bold; padding: 4px;")
        self.btn_bass.setToolTip("Быстрый пресет усиления баса")
        self.btn_bass.clicked.connect(self.toggle_bass_boost)
        fx_layout.addWidget(self.btn_bass)

        self.btn_eq = QPushButton("🎚 Эквалайзер")
        self.btn_eq.setStyleSheet("font-size: 10px; font-weight: bold; padding: 4px;")
        self.btn_eq.setToolTip("Полный 10-полосный эквалайзер с пресетами")
        self.btn_eq.clicked.connect(self.open_equalizer_dialog)
        fx_layout.addWidget(self.btn_eq)

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
        self.vol_slider.setRange(0, 125)  # 125 — реальный потолок громкости VLC без клиппинга
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
        self.change_volume(70)

    # ------------------------------------------------------------------
    # Мини-плеер
    # ------------------------------------------------------------------
    def open_mini_player(self):
        if self.mini_player is not None:
            self.mini_player.close_mini()
            return
        self.mini_player = MiniPlayer(self)
        self.mini_player.move(self.geometry().topRight() + QPoint(20, 0))
        self.mini_player.show()
        self.hide()

    def closeEvent(self, event):
        self.save_statistics()
        if self.player:
            self.player.stop()
        if self.mini_player:
            self.mini_player.close()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Плейлисты
    # ------------------------------------------------------------------
    def load_playlists(self):
        os.makedirs(PLAYLISTS_DIR, exist_ok=True)
        self.playlists = {}
        try:
            for fname in os.listdir(PLAYLISTS_DIR):
                if not fname.endswith(".json"):
                    continue
                path = os.path.join(PLAYLISTS_DIR, fname)
                try:
                    with open(path, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                    name = data.get("name") or fname[:-5]
                    self.playlists[name] = {"tracks": data.get("tracks", [])}
                except Exception as e:
                    log.warning(f"Не удалось прочитать плейлист {fname}: {e}")
        except Exception as e:
            log.error(f"Не удалось прочитать папку плейлистов: {e}")

        current = self.playlist_selector.currentText() if hasattr(self, "playlist_selector") else LIBRARY_LABEL
        self.playlist_selector.blockSignals(True)
        self.playlist_selector.clear()
        self.playlist_selector.addItem(LIBRARY_LABEL)
        for name in self.playlists:
            self.playlist_selector.addItem(name)
        self.playlist_selector.addItem(NEW_PLAYLIST_LABEL)
        idx = self.playlist_selector.findText(current)
        self.playlist_selector.setCurrentIndex(idx if idx >= 0 else 0)
        self.playlist_selector.blockSignals(False)

    def save_playlist(self, name):
        try:
            os.makedirs(PLAYLISTS_DIR, exist_ok=True)
            safe_name = resource_free_name(name)
            path = os.path.join(PLAYLISTS_DIR, f"{safe_name}.json")
            with open(path, "w", encoding="utf-8") as fp:
                json.dump({"name": name, "tracks": self.playlists[name]["tracks"]}, fp, ensure_ascii=False)
        except Exception as e:
            log.error(f"Не удалось сохранить плейлист {name}: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить плейлист: {e}")

    def on_playlist_changed(self, text):
        if text == NEW_PLAYLIST_LABEL:
            name, ok = QInputDialog.getText(self, "Новый плейлист", "Название плейлиста:")
            if ok and name.strip():
                name = name.strip()
                if name in self.playlists:
                    QMessageBox.warning(self, "Уже есть", "Плейлист с таким именем уже существует.")
                else:
                    self.playlists[name] = {"tracks": []}
                    self.save_playlist(name)
                    self.load_playlists()
                    idx = self.playlist_selector.findText(name)
                    self.playlist_selector.setCurrentIndex(idx if idx >= 0 else 0)
                return
            else:
                self.playlist_selector.setCurrentIndex(0)
                return

        self.active_playlist = None if text == LIBRARY_LABEL else text
        self.load_music(self.filter_selector.currentText())

    def add_track_to_active_playlist(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.current_playlist):
            return
        track = self.current_playlist[row]
        target = self.active_playlist
        if target is None:
            names = list(self.playlists.keys())
            if not names:
                QMessageBox.information(self, "Нет плейлистов", "Сначала создай плейлист через выпадающий список.")
                return
            name, ok = QInputDialog.getItem(self, "Добавить в плейлист", "Выбери плейлист:", names, editable=False)
            if not ok:
                return
            target = name
        if track not in self.playlists[target]["tracks"]:
            self.playlists[target]["tracks"].append(track)
            self.save_playlist(target)
        QMessageBox.information(self, "Готово", f"Трек добавлен в «{target}»")

    def remove_track_from_active_playlist(self):
        if self.active_playlist is None:
            QMessageBox.information(self, "Библиотека", "Это вся библиотека, из неё нельзя «убрать» трек — только удалить файл.")
            return
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.current_playlist):
            return
        track = self.current_playlist[row]
        tracks = self.playlists[self.active_playlist]["tracks"]
        if track in tracks:
            tracks.remove(track)
            self.save_playlist(self.active_playlist)
            self.load_music(self.filter_selector.currentText())

    def delete_active_playlist(self):
        if self.active_playlist is None:
            QMessageBox.information(self, "Библиотека", "Библиотеку удалить нельзя — это все файлы из папки music.")
            return
        reply = QMessageBox.question(self, "Удалить плейлист", f"Удалить плейлист «{self.active_playlist}»?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        name = self.active_playlist
        try:
            safe_name = resource_free_name(name)
            path = os.path.join(PLAYLISTS_DIR, f"{safe_name}.json")
            if os.path.exists(path):
                os.remove(path)
            self.playlists.pop(name, None)
        except Exception as e:
            log.error(f"Не удалось удалить плейлист {name}: {e}")
        self.active_playlist = None
        self.load_playlists()
        self.load_music(self.filter_selector.currentText())

    # ------------------------------------------------------------------
    # Настройки / темы
    # ------------------------------------------------------------------
    def open_settings_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Настройки плеера")
        dialog.setFixedSize(300, 180)

        if self.current_theme_name in ("Liquid Glass", "Тёмная macOS"):
            dialog.setStyleSheet("background-color: #2D2D2D; color: white; QComboBox { color: black; background: white; }")
        else:
            dialog.setStyleSheet("background-color: #F5F5F7; color: #1D1D1F; QComboBox { color: black; background: white; }")

        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("<b>🎨 Выберите оформление:</b>"))
        theme_combo = QComboBox()
        theme_combo.addItems(list(self.themes.keys()))
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
        if theme_name not in self.themes:
            return
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
        self.btn_bass.setStyleSheet(style["btn_edit"])
        self.btn_eq.setStyleSheet(style["btn_edit"])
        self.search_input.setStyleSheet(style["input"])

        for btn in [self.btn_prev, self.btn_play, self.btn_pause, self.btn_next]:
            btn.setStyleSheet(style["btn_sticker"])

        if style.get("blur"):
            ok = enable_windows_blur(self)
            if not ok:
                log.info("Настоящий блюр не включился — тема останется полупрозрачной без размытия.")

        self.load_music(self.filter_selector.currentText())

    # ------------------------------------------------------------------
    # Анимации
    # ------------------------------------------------------------------
    def _fade(self, opacity_effect, start=0.15, end=1.0, duration=260):
        anim = QPropertyAnimation(opacity_effect, b"opacity", self)
        anim.setDuration(duration)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        # держим ссылку, чтобы GC не убил анимацию на середине
        self._active_anim = anim

    # ------------------------------------------------------------------
    # Аудио-эффекты (реальные, через libvlc equalizer)
    # ------------------------------------------------------------------
    def change_playback_speed(self, value):
        speed = value / 10.0
        if self.player:
            self.player.set_rate(speed)
        self.speed_indicator_label.setText(
            "Текущая: 1.0x (Норма)" if speed == 1.0 else f"Текущая: {speed}x"
        )

    def apply_eq_gains(self, gains):
        self.eq_gains = gains
        if not (self.eq_available and self.player and self.equalizer):
            return
        for i, val in enumerate(gains):
            self.equalizer.set_amp_at_index(float(val), i)
        self.player.set_equalizer(self.equalizer)
        self.is_bass_boost = gains == EQ_PRESETS["Бас-буст"]
        self.btn_bass.setText("🔥 BassBoost: Вкл" if self.is_bass_boost else "🔥 BassBoost: Выкл")

    def open_equalizer_dialog(self):
        if not (self.eq_available and self.player and self.equalizer):
            QMessageBox.warning(
                self, "Эквалайзер недоступен",
                "Не найден рабочий эквалайзер VLC (ни AudioEqualizer, ни Equalizer).\n\n"
                "Проверь версию: pip show python-vlc, и версию VLC Player."
            )
            return
        dialog = EqualizerDialog(self, self.eq_gains, self.apply_eq_gains, self.save_custom_eq_preset)
        dialog.exec()

    def save_custom_eq_preset(self, gains):
        EQ_PRESETS["Свой"] = gains
        QMessageBox.information(self, "Сохранено", "Текущие настройки сохранены как пресет «Свой» (до перезапуска).")

    def toggle_bass_boost(self):
        if not (self.eq_available and self.player and self.equalizer):
            QMessageBox.warning(
                self, "Эквалайзер недоступен",
                "Не найден рабочий эквалайзер VLC (ни AudioEqualizer, ни Equalizer)."
            )
            return
        if self.is_bass_boost:
            self.apply_eq_gains(list(EQ_PRESETS["Плоский (выкл)"]))
        else:
            self.apply_eq_gains(list(EQ_PRESETS["Бас-буст"]))

    def change_volume(self, value):
        if self.player:
            self.player.audio_set_volume(value)
        self.vol_icon.setText("⚡🚀" if value > 100 else "🔊")

    # ------------------------------------------------------------------
    # Прочее (шэринг, донат, диагностика)
    # ------------------------------------------------------------------
    def share_on_twitter(self):
        current_row = self.list_widget.currentRow()
        track_name = self.current_playlist[current_row] if 0 <= current_row < len(self.current_playlist) else "свои любимые треки"
        text = f"Слушаю сочный трек '{track_name}' в плеере LazyPleer! Присоединяйтесь к чиллу! 🎧🔥"
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "X / Twitter", "Готовый пост скопирован в буфер обмена!")

    def support_author(self):
        reply = QMessageBox.question(self, "Поддержка автора", "Перейти на страницу DonationAlerts?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            webbrowser.open("https://www.donationalerts.com/r/fleurdev")

    def check_for_updates(self):
        # Честно: без сервера/GitHub-релиза автопроверка невозможна.
        QMessageBox.information(
            self, "Обновления",
            "Автопроверка обновлений пока не подключена — негде проверять "
            "(нет сервера/релизов). Текущая версия: LazyPleer v5.0."
        )

    def run_library_diagnostic(self):
        if not self.playlist_files:
            QMessageBox.warning(self, "Диагностика библиотеки", "Папка с музыкой абсолютно пуста!")
            return

        duplicates = []
        seen_sizes = {}
        corrupted_count = 0

        for f in self.playlist_files:
            path = os.path.join(MUSIC_DIR, f)
            try:
                size = os.path.getsize(path)
                if size in seen_sizes:
                    duplicates.append(f)
                else:
                    seen_sizes[size] = f
                if f.endswith('.mp3'):
                    MP3(path)
            except Exception as e:
                log.warning(f"Проблемный файл {f}: {e}")
                corrupted_count += 1

        report = (f"📊 Сводный отчет диагностики библиотеки:\n\n"
                  f"• Битых/Поврежденных файлов: {corrupted_count}\n"
                  f"• Обнаружено дубликатов: {len(duplicates)}\n")
        if duplicates:
            report += f"\nРекомендуется очистить: {duplicates[:3]}"
        QMessageBox.information(self, "Диагностика библиотеки", report)

    def toggle_favorite_track(self):
        current_row = self.list_widget.currentRow()
        if current_row < 0:
            return
        track_name = self.current_playlist[current_row]
        if track_name in self.favorite_tracks:
            self.favorite_tracks.remove(track_name)
        else:
            self.favorite_tracks.append(track_name)
        self.save_favorites()
        self.load_music(self.filter_selector.currentText())

    def load_favorites(self):
        try:
            if os.path.exists(FAVS_FILE):
                with open(FAVS_FILE, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                self.favorite_tracks = data.get("tracks", [])
        except Exception as e:
            log.warning(f"Не удалось загрузить избранное: {e}")

    def save_favorites(self):
        try:
            with open(FAVS_FILE, "w", encoding="utf-8") as fp:
                json.dump({"tracks": self.favorite_tracks}, fp)
        except Exception as e:
            log.warning(f"Не удалось сохранить избранное: {e}")

    def change_filter_type(self, text):
        self.load_music(text)

    def load_statistics(self):
        try:
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                self.total_listen_time = data.get("time", 0)
                saved_theme = data.get("theme", "Светлая macOS")
                QTimer.singleShot(150, lambda: self.apply_theme(saved_theme))
        except Exception as e:
            log.warning(f"Не удалось загрузить статистику: {e}")

    def save_statistics(self):
        try:
            with open(STATS_FILE, "w", encoding="utf-8") as fp:
                json.dump({"time": self.total_listen_time, "theme": self.current_theme_name}, fp)
        except Exception as e:
            log.warning(f"Не удалось сохранить статистику: {e}")

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
        minutes = {"15 мин": 15, "30 мин": 30, "60 мин": 60}.get(text)
        if minutes is None:
            self.sleep_timer.stop()
            self.sleep_minutes_left = 0
            return
        self.sleep_minutes_left = minutes
        self.sleep_timer.start(60000)
        QMessageBox.information(self, "Таймер сна", f"Плеер закроется через {minutes} минут!")

    def trigger_sleep(self):
        self.sleep_minutes_left -= 1
        if self.sleep_minutes_left <= 0:
            self.sleep_timer.stop()
            QApplication.instance().quit()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        os.makedirs(MUSIC_DIR, exist_ok=True)
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith(('.mp3', '.wav', '.m4a')):
                try:
                    shutil.copy(file_path, MUSIC_DIR)
                except Exception as e:
                    log.warning(f"Не удалось скопировать {file_path}: {e}")
                    QMessageBox.warning(self, "Ошибка", f"Не удалось добавить файл:\n{e}")
        self.load_music(self.filter_selector.currentText())

    # ------------------------------------------------------------------
    # Библиотека / плейлист
    # ------------------------------------------------------------------
    def load_music(self, filter_type="Все треки"):
        os.makedirs(MUSIC_DIR, exist_ok=True)
        self.playlist_files = [f for f in os.listdir(MUSIC_DIR) if f.endswith(('.mp3', '.wav', '.m4a'))]
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

        # базовый набор: либо вся библиотека, либо активный плейлист (только реально существующие файлы)
        if self.active_playlist is not None and self.active_playlist in self.playlists:
            base_files = [f for f in self.playlists[self.active_playlist]["tracks"] if f in self.playlist_files]
        else:
            base_files = self.playlist_files

        self.current_playlist = []
        for f in base_files:
            if search_text and search_text not in f.lower():
                continue
            if filter_type == "⭐ Избранное" and f not in self.favorite_tracks:
                continue
            self.current_playlist.append(f)

        self.list_widget.clear()
        for track in self.current_playlist:
            display_name = track
            try:
                if track.endswith('.mp3'):
                    audio = MP3(os.path.join(MUSIC_DIR, track))
                    title, artist = audio.get('TIT2'), audio.get('TPE1')
                    if title and artist:
                        display_name = f"{artist} - {title}"
            except Exception as e:
                log.debug(f"Не удалось прочитать теги {track}: {e}")

            prefix = " ❤️  " if track in self.favorite_tracks else "  🎵  "
            self.list_widget.addItem(f"{prefix}{display_name}")

        self._fade(self.list_opacity)

    # ------------------------------------------------------------------
    # Воспроизведение (через VLC)
    # ------------------------------------------------------------------
    def play_track(self):
        if not self.current_playlist or not self.player:
            return

        state = self.player.get_state()
        if state == vlc.State.Paused:
            self.player.play()
            self.update_screen("Воспроизведение")
            return

        current_row = self.list_widget.currentRow()
        if current_row < 0:
            current_row = 0
            self.list_widget.setCurrentRow(0)
        track_name = self.current_playlist[current_row]
        track_path = os.path.abspath(os.path.join(MUSIC_DIR, track_name))

        try:
            media = self.vlc_instance.media_new(track_path)
            self.player.set_media(media)
            self.player.play()
            if self.eq_available:
                self.player.set_equalizer(self.equalizer)
            self.change_playback_speed(self.speed_slider.value())
            self.change_volume(self.vol_slider.value())
            self.update_screen("Воспроизведение")
        except Exception as e:
            log.error(f"Не удалось воспроизвести {track_name}: {e}")
            QMessageBox.critical(self, "Ошибка воспроизведения", f"Не удалось открыть файл:\n{e}")
            return

        if self.rpc:
            try:
                self.rpc.update(details=f"Слушает {track_name}", state="В плеере LazyPleer")
            except Exception as e:
                log.debug(f"Discord RPC update failed: {e}")

    def play_selected(self, item):
        self.play_track()

    def pause_track(self):
        if self.player and self.player.is_playing():
            self.player.pause()
            self.update_screen("Пауза")

    def next_track(self):
        if not self.current_playlist:
            return
        if self.play_mode == "Shuffle":
            next_row = random.randrange(len(self.current_playlist))
        else:
            next_row = (self.list_widget.currentRow() + 1) % len(self.current_playlist)
        self.list_widget.setCurrentRow(next_row)
        self.play_track()

    def prev_track(self):
        if not self.current_playlist:
            return
        prev_row = (self.list_widget.currentRow() - 1) % len(self.current_playlist)
        self.list_widget.setCurrentRow(prev_row)
        self.play_track()

    def slider_pressed(self):
        self.is_slider_moving = True

    def slider_released(self):
        self.is_slider_moving = False
        if self.player:
            self.player.set_position(self.progress_slider.value() / 1000.0)

    def tick(self):
        """Общий таймер: обновляет позицию, копит статистику, ловит конец трека."""
        if not self.player:
            return
        state = self.player.get_state()

        if state == vlc.State.Playing:
            self.total_listen_time += 0.5
            if int(self.total_listen_time) % 10 == 0:
                self.save_statistics()

            if not self.is_slider_moving:
                pos = self.player.get_position()  # 0.0 - 1.0, либо -1 если неизвестно
                if pos >= 0:
                    self.progress_slider.setValue(int(pos * 1000))
            length_ms = self.player.get_length()
            pos_ms = self.player.get_time()
            pos_time = QTime(0, 0, 0).addMSecs(max(pos_ms, 0)).toString("mm:ss")
            dur_time = QTime(0, 0, 0).addMSecs(max(length_ms, 0)).toString("mm:ss")
            self.time_label.setText(f"{pos_time} / {dur_time}")

        elif state == vlc.State.Ended:
            if self.play_mode != "Repeat":
                self.next_track()
            else:
                self.play_track()

    def update_screen(self, status):
        current_row = self.list_widget.currentRow()
        if current_row < 0 or current_row >= len(self.current_playlist):
            return
        track_name = self.current_playlist[current_row]
        self.screen_label.setText(f"{track_name}\n({status})")

        try:
            if track_name.endswith('.mp3'):
                audio = MP3(os.path.join(MUSIC_DIR, track_name), ID3=ID3)
                self.cover_label.setText("🖼️" if 'APIC:' in audio else "💿")
            else:
                self.cover_label.setText("💿")
        except Exception as e:
            log.debug(f"Не удалось прочитать обложку {track_name}: {e}")
            self.cover_label.setText("💿")

        self._fade(self.screen_opacity)

    def delete_current_track(self):
        current_row = self.list_widget.currentRow()
        if current_row < 0:
            return
        track_name = self.current_playlist[current_row]
        track_path = os.path.abspath(os.path.join(MUSIC_DIR, track_name))
        reply = QMessageBox.question(self, "Удаление", f"Удалить файл {track_name}?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.player:
                self.player.stop()
            try:
                os.remove(track_path)
                # убираем упоминания файла из всех плейлистов и избранного
                for pl in self.playlists.values():
                    if track_name in pl["tracks"]:
                        pl["tracks"].remove(track_name)
                for name in list(self.playlists.keys()):
                    self.save_playlist(name)
                if track_name in self.favorite_tracks:
                    self.favorite_tracks.remove(track_name)
                    self.save_favorites()
                QMessageBox.information(self, "Успех", "Файл удален!")
                self.load_music()
            except Exception as e:
                log.error(f"Не удалось удалить {track_name}: {e}")
                QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")

    def open_about_dialog(self):
        dialog = QDialog(self); dialog.setWindowTitle("Статистика"); dialog.setFixedSize(340, 200)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("<b>LazyPleer v5.0</b>"))
        mins = int(self.total_listen_time) // 60
        layout.addWidget(QLabel(f"📊 Общее время прослушивания: {mins} мин."))
        tg = QLineEdit("ТГ: @french_parasite"); tg.setReadOnly(True); tg.setStyleSheet("background: transparent; border: none;"); layout.addWidget(tg)
        mail = QLineEdit("Почта: lilvanforover@mail.com"); mail.setReadOnly(True); mail.setStyleSheet("background: transparent; border: none;"); layout.addWidget(mail)
        btn = QPushButton("Закрыть"); btn.clicked.connect(dialog.accept); layout.addWidget(btn)
        dialog.exec()

    def open_metadata_editor(self):
        current_row = self.list_widget.currentRow()
        if current_row < 0:
            return
        track_name = self.current_playlist[current_row]
        track_path = os.path.abspath(os.path.join(MUSIC_DIR, track_name))
        if not track_name.endswith('.mp3'):
            QMessageBox.warning(self, "Формат", "Только MP3!")
            return
        if self.player:
            self.player.stop()

        dialog = QDialog(self); dialog.setWindowTitle("Редактор тегов и Обложки"); dialog.setFixedSize(360, 460)
        layout = QVBoxLayout(dialog)
        try:
            audio = MP3(track_path, ID3=ID3)
            t = str(audio.get('TIT2', '')); a = str(audio.get('TPE1', '')); y = str(audio.get('TYER', ''))
        except Exception as e:
            log.warning(f"Не удалось прочитать теги {track_name}: {e}")
            t, a, y = "", "", ""

        layout.addWidget(QLabel("Название трека:")); t_in = QLineEdit(t); layout.addWidget(t_in)
        layout.addWidget(QLabel("Исполнитель:")); a_in = QLineEdit(a); layout.addWidget(a_in)
        layout.addWidget(QLabel("Год выпуска:")); y_in = QLineEdit(y); layout.addWidget(y_in)
        layout.addWidget(QLabel("<b>🖼️ Текущая обложка альбома:</b>"))

        preview_label = QLabel(); preview_label.setFixedSize(100, 100)
        preview_label.setStyleSheet("border: 1px dashed gray; background-color: rgba(0,0,0,0.05);")
        preview_label.setAlignment(Qt.AlignCenter)
        try:
            if 'APIC:' in audio:
                pixmap = QPixmap(); pixmap.loadFromData(audio['APIC:'].data)
                preview_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                preview_label.setText("Нет обложки")
        except Exception as e:
            log.debug(f"Не удалось показать обложку: {e}")
            preview_label.setText("Ошибка загрузки")
        layout.addWidget(preview_label, alignment=Qt.AlignCenter)

        self.selected_cover_bin = None
        def choose_cover():
            file_path, _ = QFileDialog.getOpenFileName(dialog, "Выбрать обложку", "", "Images (*.png *.jpg *.jpeg)")
            if file_path:
                with open(file_path, 'rb') as f:
                    self.selected_cover_bin = f.read()
                pixmap = QPixmap(file_path)
                preview_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        btn_cover = QPushButton("📂 Загрузить новую обложку (.jpg/.png)"); btn_cover.clicked.connect(choose_cover); layout.addWidget(btn_cover)

        def save():
            try:
                try:
                    tags = ID3(track_path)
                except Exception:
                    tags = ID3(); tags.save(track_path)
                tags['TIT2'] = TIT2(encoding=3, text=t_in.text())
                tags['TPE1'] = TPE1(encoding=3, text=a_in.text())
                tags['TYER'] = TYER(encoding=3, text=y_in.text())
                if self.selected_cover_bin:
                    tags['APIC'] = APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=self.selected_cover_bin)
                tags.save(track_path)
                QMessageBox.information(dialog, "Успех", "Теги и обложка сохранены!")
            except Exception as e:
                log.error(f"Не удалось сохранить теги {track_name}: {e}")
                QMessageBox.critical(dialog, "Ошибка", f"{e}")
            dialog.accept()

        btn = QPushButton("Сохранить изменения"); btn.clicked.connect(save); layout.addWidget(btn)
        dialog.exec()
        self.load_music()
        self.play_track()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon.fromTheme("media-playback-start"))
    player = LazyPleerV4()
    player.show()
    sys.exit(app.exec())