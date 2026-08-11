import os, sys, shutil, json, logging, webbrowser, random, hashlib, csv
from collections import OrderedDict
from datetime import datetime, timedelta
from PySide6.QtCore import (QTime, Qt, QTimer, QPropertyAnimation, QEasingCurve,
                            QPoint, QThread, Signal, QFileSystemWatcher, QRect, QSize)
from PySide6.QtGui import QIcon, QAction, QPixmap, QColor, QShortcut, QKeySequence, QFont
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QFileDialog,
QListWidget, QPushButton, QVBoxLayout, QWidget, QSlider, QDialog, QLineEdit,
QMessageBox, QComboBox, QSystemTrayIcon, QMenu, QInputDialog, QGraphicsOpacityEffect,
QColorDialog, QProgressDialog, QScrollArea, QCheckBox, QListWidgetItem, QHeaderView,
QTableWidget, QTableWidgetItem, QTabWidget, QGroupBox, QGridLayout)
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, APIC, TYER
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
import requests

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

try:
    from pynput import keyboard as pynput_keyboard
    PYNPUT_AVAILABLE = True
except Exception:
    PYNPUT_AVAILABLE = False

# ---------------------------------------------------------------------------
# All files live NEXT TO the program
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

MUSIC_DIR = os.path.join(APP_DIR, "music")
PLAYLISTS_DIR = os.path.join(APP_DIR, "playlists")
STATS_FILE = os.path.join(APP_DIR, "lazy_stats.json")
FAVS_FILE = os.path.join(APP_DIR, "lazy_favs.json")
CUSTOM_COLORS_FILE = os.path.join(APP_DIR, "lazy_custom_colors.json")
LOG_FILE = os.path.join(APP_DIR, "lazy_pleer.log")

SETTINGS_FILE = os.path.join(APP_DIR, "lazy_settings.json")
EQ_CUSTOM_FILE = os.path.join(APP_DIR, "lazy_eq_custom.json")
META_CACHE_FILE = os.path.join(APP_DIR, "lazy_meta_cache.json")

logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("LazyPleer")

EQ_BAND_FREQS = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
EQ_PRESET_KEYS = ["eq_preset_flat", "eq_preset_bass", "eq_preset_vocal", "eq_preset_rock", "eq_preset_edm"]
EQ_PRESET_VALUES = {
    "eq_preset_flat": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "eq_preset_bass": [10, 8, 5, 2, 0, 0, 0, 0, 0, 0],
    "eq_preset_vocal": [-2, -2, 0, 3, 5, 5, 3, 1, 0, -1],
    "eq_preset_rock": [6, 4, 2, 0, -2, -1, 2, 4, 5, 5],
    "eq_preset_edm": [7, 6, 2, 0, -2, 0, 2, 4, 6, 7],
}
EQ_PRESET_CUSTOM_KEY = "eq_preset_custom"

# ---------------------------------------------------------------------------
# English-only strings
# ---------------------------------------------------------------------------
STRINGS = {
    "app_title": "LazyPleer",
    "tooltip_mini": "Compact mini-player on top of windows",
    "tooltip_share": "Share the track on social media",
    "tooltip_donate": "Support the author via DonationAlerts",
    "tooltip_diag": "Library diagnostics (find corrupted files and duplicates)",
    "tooltip_update": "Check for updates",
    "tooltip_settings": "Theme and sleep timer settings",
    "tooltip_shazam": "Identify current song",
    "screen_default": "Not playing\nDrop tracks into the /music folder",
    "playlist_library": "📚 Whole Library",
    "playlist_new": "➕ Create playlist...",
    "tooltip_pl_add": "Add the selected track to the current playlist",
    "tooltip_pl_remove": "Remove the selected track from the current playlist",
    "tooltip_pl_delete": "Delete the current playlist",
    "search_placeholder": "🔍 Live search by track or artist...",
    "filter_all": "All tracks",
    "filter_added": "By date added",
    "filter_year": "By year",
    "filter_favorites": "⭐ Favorites",
    "sort_added": "By date added",
    "sort_title": "By title",
    "sort_artist": "By artist",
    "sort_length": "By length",
    "counter_template": "Total files in your library: {n}",
    "bass_off": "🔥 BassBoost: Off",
    "bass_on": "🔥 BassBoost: On",
    "tooltip_bass": "Quick bass-boost preset",
    "btn_eq": "🎚 Equalizer",
    "tooltip_eq": "Full 10-band equalizer with presets",
    "speed_label": "🏎 Speed:",
    "speed_normal": "Current: 1.0x (Normal)",
    "speed_current": "Current: {x}x",
    "btn_edit_tags": "📝 Tag editor",
    "btn_delete": "❌ Delete",
    "btn_favorite": "❤️ Add to Favorites",
    "mode_normal": "🔁 In order",
    "mode_shuffle": "🔀 Shuffle",
    "mode_repeat": "🔂 Repeat",
    "settings_title": "Player settings",
    "settings_theme_label": "<b>🎨 Choose a theme:</b>",
    "settings_sleep_label": "<b>⏱️ Auto-off (Sleep timer):</b>",
    "settings_sleep_action_label": "<b>⏱️ Sleep timer action:</b>",
    "sleep_action_pause": "Pause playback",
    "sleep_action_quit": "Exit the app",
    "sleep_off": "⏱️ Timer off",
    "sleep_15": "15 min",
    "sleep_30": "30 min",
    "sleep_60": "60 min",
    "btn_apply_settings": "Apply settings",
    "msg_sleep_title": "Sleep timer",
    "msg_sleep_text": "Timer set: {m} minutes.",
    "about_title": "Statistics",
    "about_listen_time": "📊 Total listening time: {m} min.",
    "btn_close": "Close",
    "eq_title": "Equalizer",
    "eq_preset_label": "Preset:",
    "eq_preset_flat": "Flat (off)",
    "eq_preset_bass": "Bass boost",
    "eq_preset_vocal": "Vocal",
    "eq_preset_rock": "Rock",
    "eq_preset_edm": "Electronic",
    "eq_preset_custom": "Custom",
    "eq_save_btn": "💾 Save as 'Custom'",
    "eq_saved_title": "Saved",
    "eq_saved_text": "Current settings saved as the 'Custom' preset (saved to file).",
    "eq_unavailable_title": "Equalizer unavailable",
    "eq_unavailable_text": "No working VLC equalizer found (neither AudioEqualizer nor Equalizer).\n\nCheck version: pip show python-vlc, and your VLC Player version.",
    "vlc_missing_title": "VLC not found",
    "vlc_missing_text": "The python-vlc library or VLC Player itself was not found.\n\n1) Install VLC Player: https://www.videolan.org/vlc/\n2) pip install python-vlc\n\nWithout this, the player won't be able to play music.",
    "playlist_new_title": "New playlist",
    "playlist_new_prompt": "Playlist name:",
    "playlist_exists_title": "Already exists",
    "playlist_exists_text": "A playlist with this name already exists.",
    "playlist_none_title": "No playlists",
    "playlist_none_text": "Create a playlist first using the dropdown.",
    "playlist_choose_title": "Add to playlist",
    "playlist_choose_prompt": "Choose a playlist:",
    "playlist_added_title": "Done",
    "playlist_added_text": "Track added to \"{p}\"",
    "library_title": "Library",
    "library_no_remove": "This is the whole library — you can't \"remove\" a track, only delete the file.",
    "library_no_delete": "The library can't be deleted — it's just all files from the music folder.",
    "playlist_delete_confirm_title": "Delete playlist",
    "playlist_delete_confirm_text": "Delete playlist \"{p}\"?",
    "playlist_save_error_text": "Failed to save the playlist: {e}",
    "twitter_title": "X / Twitter",
    "twitter_copied": "Ready-made post copied to clipboard!",
    "twitter_share_text": "Listening to '{t}' on LazyPleer! Join the chill! 🎧🔥",
    "donate_title": "Support the author",
    "donate_text": "Open the DonationAlerts page?",
    "update_title": "Updates",
    "update_text": "Automatic update checking isn't set up yet — there's nowhere to check (no server/releases). Current version: LazyPleer v8.0.",
    "diag_title": "Library diagnostics",
    "diag_empty_text": "The music folder is completely empty!",
    "diag_report_header": "📊 Library diagnostics summary:",
    "diag_corrupted": "• Corrupted/broken files: {n}",
    "diag_duplicates": "• Duplicates found: {n}",
    "diag_recommend": "Recommended to clean up: {list}",
    "delete_confirm_title": "Delete",
    "delete_confirm_text": "Delete file {t}?",
    "delete_success_title": "Success",
    "delete_success_text": "File deleted!",
    "delete_error_title": "Error",
    "drop_error_text": "Failed to add file:\n{e}",
    "edit_tags_title": "Tag & Cover Editor",
    "edit_tags_track_label": "Track title:",
    "edit_tags_artist_label": "Artist:",
    "edit_tags_year_label": "Release year:",
    "edit_tags_cover_label": "<b>🖼️ Current album cover:</b>",
    "edit_tags_no_cover": "No cover",
    "edit_tags_load_error": "Load error",
    "edit_tags_load_btn": "📂 Load new cover (.jpg/.png)",
    "edit_tags_save_btn": "Save changes",
    "edit_tags_only_mp3": "MP3 only!",
    "edit_tags_format_title": "Format",
    "edit_tags_success": "Tags and cover saved!",
    "status_playing": "Playing",
    "status_paused": "Paused",
    "tray_play": "▶ Play",
    "tray_pause": "⏸ Pause",
    "tray_next": "⏭ Next",
    "tray_exit": "❌ Exit",
    "play_error_title": "Playback error",
    "play_error_text": "Failed to open the file:\n{e}",
    "choose_cover_dialog_title": "Choose cover",
    "settings_custom_label": "<b>🎨 Interface customization:</b>",
    "settings_accent_color_btn": "🎨 Accent color...",
    "settings_button_color_btn": "🔘 Button color...",
    "settings_reset_colors_btn": "↺ Reset colors",
    "settings_audio_output_label": "<b>🔊 Audio output:</b>",
    "audio_output_default": "System default device",
    "audio_output_unavailable": "Device list unavailable in this VLC/system version",
    "ctx_play": "▶ Play",
    "ctx_play_next": "⤵ Play next",
    "ctx_fav": "❤️ Favorite",
    "queue_title": "Queue",
    "queue_added": "Track will play next: {t}",
    "library_new": "🆕 New in library: {list}",
    "settings_discord_label": "Discord Rich Presence",
    "settings_discord_id_label": "Discord Application ID:",
    "settings_hotkeys": "Global media keys (requires pynput)",
    "settings_restore_pos": "Remember playback position",
    "settings_replaygain": "ReplayGain / volume normalization (recreates VLC)",
    "settings_crossfade": "Fade-out before track end (sec):",
    "settings_eq_disabled": "❌ Disable Equalizer / Bass Boost (for users without VLC)",
    "settings_font_size": "<b>📝 Font size:</b>",
    "settings_font_small": "Small",
    "settings_font_medium": "Medium",
    "settings_font_large": "Large",
    "settings_window_opacity": "<b>🔮 Window opacity:</b>",
    "settings_opacity_label": "{p}%",
    "settings_opacity_enable": "Enable transparency",
    "settings_toolbar_label": "<b>🎛️ Customize Toolbar:</b>",
    "settings_vinyl_mode": "🎵 Vinyl Mode (adds noise & distortion)",
    "settings_share_vk": "VK",
    "settings_share_tg": "Telegram",
    "settings_share_tw": "X / Twitter",
    "stats_title": "📊 Statistics",
    "stats_total_time": "⏱️ Total listening time: {h}h {m}m",
    "stats_total_tracks": "🎵 Total tracks played: {n}",
    "stats_top_artists": "🎤 Top Artists (this week):",
    "stats_most_skipped": "⏭️ Most skipped tracks:",
    "stats_week_chart": "📅 Listening by day of week:",
    "stats_hour_chart": "🕐 Listening by hour:",
    "stats_export_csv": "📥 Export CSV",
    "stats_no_data": "No data yet. Listen to some music!",
    "share_title": "📤 Share track",
    "share_vk_text": "🎧 Слушаю '{t}' в LazyPleer! Присоединяйся! 🎵",
    "share_tg_text": "🎧 Listening to '{t}' on LazyPleer! Join the vibe! 🎵",
    "share_tw_text": "Listening to '{t}' on LazyPleer! 🎧🔥",
    "shazam_title": "🎵 Identify Song",
    "shazam_loading": "🔍 Analyzing audio...",
    "shazam_error": "Could not identify the song.\nMake sure audio is playing.",
    "shazam_result": "🎵 Found: {title}\n👤 Artist: {artist}",
    "shazam_add": "Add to library?",
    "playlist_rename_title": "Rename playlist",
    "playlist_rename_prompt": "New name:",
    "playlist_count": " ({n} tracks)",
    "export_spotify_title": "Export to Spotify",
    "export_spotify_copied": "Playlist copied to clipboard in Spotify format!\nPaste into Spotify → Create playlist → Paste tracks",
    "track_skipped": "Track skipped",
}


def resource_free_name(base_name):
    bad = '<>:"/\\|?*'
    return "".join(c for c in base_name if c not in bad).strip() or "untitled"


def enable_windows_blur(widget):
    """Real acrylic blur via undocumented DWM API. Windows 10/11 only."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        class ACCENT_POLICY(ctypes.Structure):
            _fields_ = [("AccentState", ctypes.c_int), ("AccentFlags", ctypes.c_int),
                        ("GradientColor", ctypes.c_int), ("AnimationId", ctypes.c_int)]

        class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
            _fields_ = [("Attribute", ctypes.c_int),
                        ("Data", ctypes.POINTER(ACCENT_POLICY)),
                        ("SizeOfData", ctypes.c_size_t)]

        accent = ACCENT_POLICY()
        accent.AccentState = 4
        accent.AccentFlags = 2
        accent.GradientColor = 0x66222222
        accent.AnimationId = 0
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19
        data.Data = ctypes.pointer(accent)
        data.SizeOfData = ctypes.sizeof(accent)
        ctypes.windll.user32.SetWindowCompositionAttribute(int(widget.winId()), ctypes.pointer(data))
        return True
    except Exception as e:
        log.info(f"Window blur unavailable: {e}")
        return False


def hash_file(path):
    h = hashlib.sha1()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
    except Exception as e:
        log.warning(f"Failed to hash {path}: {e}")
        return ""
    return h.hexdigest()


class MetadataCache:
    """Reads tags once, not on every search keystroke."""
    def __init__(self):
        self.cache = {}
        self.dirty = False
        self.load()

    def load(self):
        try:
            if os.path.exists(META_CACHE_FILE):
                with open(META_CACHE_FILE, "r", encoding="utf-8") as fp:
                    self.cache = json.load(fp)
        except Exception as e:
            log.warning(f"Failed to load metadata cache: {e}")

    def save(self):
        if not self.dirty:
            return
        try:
            with open(META_CACHE_FILE, "w", encoding="utf-8") as fp:
                json.dump(self.cache, fp, ensure_ascii=False)
            self.dirty = False
        except Exception as e:
            log.warning(f"Failed to save metadata cache: {e}")

    def invalidate(self, filename):
        self.cache.pop(filename, None)
        self.dirty = True

    def prune(self, files):
        existing = set(files)
        for key in list(self.cache.keys()):
            if key not in existing:
                self.cache.pop(key, None)
                self.dirty = True

    def get(self, filename):
        if filename in self.cache:
            return self.cache[filename]
        info = {"title": filename, "artist": "", "year": "", "duration": 0, "has_cover": False}
        path = os.path.join(MUSIC_DIR, filename)
        try:
            if filename.lower().endswith(".mp3"):
                audio = MP3(path, ID3=ID3)
                if audio.get("TIT2"): info["title"] = str(audio["TIT2"]).strip()
                if audio.get("TPE1"): info["artist"] = str(audio["TPE1"]).strip()
                if audio.get("TYER"): info["year"] = str(audio["TYER"]).strip()
                info["duration"] = int(getattr(audio.info, "length", 0) * 1000)
                info["has_cover"] = any(str(k).startswith("APIC") for k in audio.keys())
            elif filename.lower().endswith(".flac"):
                audio = FLAC(path)
                if audio.get("title"): info["title"] = str(audio["title"][0])
                if audio.get("artist"): info["artist"] = str(audio["artist"][0])
                if audio.get("date"): info["year"] = str(audio["date"][0])[:4]
                info["duration"] = int(getattr(audio.info, "length", 0) * 1000)
                info["has_cover"] = bool(audio.pictures)
            elif filename.lower().endswith(".ogg"):
                audio = OggVorbis(path)
                if audio.get("title"): info["title"] = str(audio["title"][0])
                if audio.get("artist"): info["artist"] = str(audio["artist"][0])
                if audio.get("date"): info["year"] = str(audio["date"][0])[:4]
                info["duration"] = int(getattr(audio.info, "length", 0) * 1000)
        except Exception as e:
            log.debug(f"Failed to read metadata {filename}: {e}")
        self.cache[filename] = info
        self.dirty = True
        return info


class DiagnosticWorker(QThread):
    """Background library diagnostics — UI never freezes."""
    done = Signal(dict)

    def __init__(self, files):
        super().__init__()
        self.files = list(files)

    def run(self):
        try:
            corrupted, duplicates, sizes = [], [], {}
            for f in self.files:
                path = os.path.join(MUSIC_DIR, f)
                try:
                    sizes.setdefault(os.path.getsize(path), []).append(f)
                    if f.lower().endswith(".mp3"):
                        MP3(path)
                    elif f.lower().endswith(".flac"):
                        FLAC(path)
                    elif f.lower().endswith(".ogg"):
                        OggVorbis(path)
                except Exception as e:
                    log.warning(f"Problem file {f}: {e}")
                    corrupted.append(f)
            for group in sizes.values():
                if len(group) < 2:
                    continue
                seen = {}
                for f in group:
                    d = hash_file(os.path.join(MUSIC_DIR, f))
                    if not d:
                        continue
                    if d in seen:
                        duplicates.append(f)
                    else:
                        seen[d] = f
            self.done.emit({"corrupted": corrupted, "duplicates": duplicates})
        except Exception as e:
            self.done.emit({"corrupted": [], "duplicates": [], "error": str(e)})


class HotkeyWorker(QThread):
    """Global media keys via pynput."""
    play_pause = Signal()
    next_track = Signal()
    prev_track = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._listener = None

    def run(self):
        if not PYNPUT_AVAILABLE:
            return

        def on_press(key):
            keys = getattr(pynput_keyboard, "Key", None)
            if key == getattr(keys, "media_play_pause", None):
                self.play_pause.emit()
            elif key == getattr(keys, "media_next", None):
                self.next_track.emit()
            elif key == getattr(keys, "media_previous", None):
                self.prev_track.emit()

        try:
            with pynput_keyboard.Listener(on_press=on_press) as listener:
                self._listener = listener
                listener.join()
        except Exception as e:
            log.info(f"Global hotkeys unavailable: {e}")

    def stop(self):
        try:
            if self._listener:
                self._listener.stop()
        except Exception:
            pass


class MiniPlayer(QWidget):
    """Compact always-on-top player. No polling timer — refresh() on demand."""
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
        self.title_lbl = QLabel(main_window.T("screen_default").split("\n")[0])
        self.title_lbl.setStyleSheet("color: white; font-size: 11px; font-weight: 600;")
        self.title_lbl.setWordWrap(True)
        mid.addWidget(self.title_lbl)

        controls = QHBoxLayout()
        self.btn_prev = QPushButton("⏮"); self.btn_prev.clicked.connect(lambda: self.main.prev_track())
        self.btn_play = QPushButton("⏯"); self.btn_play.clicked.connect(self.main.toggle_play_pause)
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
        self.setStyleSheet("background: rgba(20,20,20,0.82); border-radius: 16px; "
                           "border: 1px solid rgba(255,255,255,0.15);")
        self.refresh()

    def refresh(self):
        track = self.main.current_upg_track
        if not track:
            row = self.main.list_widget.currentRow()
            if 0 <= row < len(self.main.current_playlist):
                track = self.main.current_playlist[row]
        if not track:
            self.title_lbl.setText(self.main.T("screen_default").split("\n")[0])
            self.cover_lbl.setText("💿")
            return
        self.title_lbl.setText(self.main.display_name(track))
        pix = self.main.get_cover_pixmap(track, 44)
        if pix:
            self.cover_lbl.setText("")
            self.cover_lbl.setPixmap(pix)
        else:
            self.cover_lbl.setText("💿")

    def close_mini(self):
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
    """Full 10-band equalizer with presets."""
    def __init__(self, parent, current_gains, on_change, on_save_custom):
        super().__init__(parent)
        T = parent.T
        self.setWindowTitle(T("eq_title"))
        self.setFixedSize(420, 320)
        self.on_change = on_change
        self.sliders = []
        layout = QVBoxLayout(self)
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel(T("eq_preset_label")))
        self.preset_combo = QComboBox()
        for key in EQ_PRESET_KEYS:
            self.preset_combo.addItem(T(key), key)
        self.preset_combo.addItem(T(EQ_PRESET_CUSTOM_KEY), EQ_PRESET_CUSTOM_KEY)
        self.preset_combo.currentIndexChanged.connect(self.apply_preset)
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
            col.addWidget(QLabel(f"{freq}Hz" if freq < 1000 else f"{freq // 1000}k"), alignment=Qt.AlignCenter)
            bands_row.addLayout(col)
            self.sliders.append(slider)
        layout.addLayout(bands_row)
        btn_row = QHBoxLayout()
        btn_save = QPushButton(T("eq_save_btn"))
        btn_save.clicked.connect(lambda: on_save_custom(self.get_gains()))
        btn_row.addWidget(btn_save)
        btn_close = QPushButton(T("btn_close"))
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def apply_preset(self, index):
        gains = EQ_PRESET_VALUES.get(self.preset_combo.itemData(index))
        if gains is None:
            return
        for slider, val in zip(self.sliders, gains):
            slider.blockSignals(True)
            slider.setValue(val)
            slider.blockSignals(False)
        self.on_slider_changed()

    def on_slider_changed(self, *_):
        self.on_change(self.get_gains())

    def get_gains(self):
        return [s.value() for s in self.sliders]


DEFAULT_SETTINGS = {
    "volume": 70, "speed": 10, "last_track": "",
    "restore_position": True, "positions": {},
    "sleep_action": "pause",
    "discord_enabled": True, "discord_app_id": "",
    "hotkeys": True, "replaygain": False,
    "crossfade": 0, "sort": "added",
    "eq_disabled": False,
    "font_size": "medium",
    "window_opacity": 100,
    "opacity_enabled": False,
    "vinyl_mode": False,
    "window_geometry": None,
    "toolbar_buttons": {
        "mini": True, "share": True, "donate": True,
        "diag": True, "update": True, "info": True,
        "settings": True, "shazam": True
    }
}


class LazyPleerV4(QWidget):
    def __init__(self):
        super().__init__()

        self.settings = self.load_settings()
        self.metadata_cache = MetadataCache()
        self.play_queue = []
        self.shuffle_bag = []
        self._cover_cache = OrderedDict()
        self._tick_count = 0
        self._position_tick = 0
        self._last_notified_track = None
        self._fade_out_active = False
        self.current_upg_track = ""
        self.hotkey_worker = None
        self.diag_worker = None
        self.diag_progress = None
        self.vinyl_noise = None
        self.play_count = {}
        self.skip_count = {}
        self.listen_history = []
        self.weekly_stats = {}
        self.hourly_stats = {}
        self._stats_dirty = False

        self.setWindowTitle("LazyPleer v8.0")
        self.setMinimumSize(480, 720)
        self.resize(480, 720)
        self.setAcceptDrops(True)

        # Восстанавливаем геометрию окна
        if self.settings.get("window_geometry"):
            try:
                geo = self.settings["window_geometry"]
                self.setGeometry(geo[0], geo[1], geo[2], geo[3])
            except:
                pass

        if not VLC_AVAILABLE:
            QMessageBox.critical(self, self.T("vlc_missing_title"), self.T("vlc_missing_text"))

        self.vlc_instance = vlc.Instance("--no-video") if VLC_AVAILABLE else None
        self.player = self.vlc_instance.media_player_new() if self.vlc_instance else None
        self.equalizer = None
        self.eq_available = False
        self.eq_gains = list(EQ_PRESET_VALUES["eq_preset_flat"])
        
        if not self.settings.get("eq_disabled", False) and VLC_AVAILABLE:
            eq_class = getattr(vlc, "AudioEqualizer", None) or getattr(vlc, "Equalizer", None)
            if eq_class is not None:
                try:
                    self.equalizer = eq_class()
                    self.eq_available = True
                except Exception as e:
                    log.warning(f"VLC equalizer unavailable: {e}")
                    self.eq_available = False

        self.load_custom_eq()
        self.load_stats()

        self.is_bass_boost = False
        self.current_theme_name = "Light macOS"
        self.custom_accent_color = None
        self.custom_button_color = None
        self.load_custom_colors()

        self.playlist_files = []
        self.current_playlist = []
        self.is_slider_moving = False
        self.play_mode = "Normal"
        self.playlists = {}
        self.active_playlist = None
        self.total_listen_time = 0
        self.load_statistics()
        self.favorite_tracks = []
        self.load_favorites()
        self.mini_player = None
        self.header_buttons = []

        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self.tick)
        self.playback_timer.start(500)

        self.sleep_timer = QTimer(self)
        self.sleep_timer.timeout.connect(self.trigger_sleep)
        self.sleep_minutes_left = 0

        self.rpc = None
        self.init_discord_rpc()

        self.themes = {
            "Light macOS": {
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
            "Dark macOS": {
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
                "widget": ("background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, "
                           "stop:0 rgba(58,61,64,0.55), stop:1 rgba(20,22,23,0.55)); color: #FFFFFF;"),
                "screen": ("background-color: rgba(255, 255, 255, 0.08); "
                           "border: 1px solid rgba(255, 255, 255, 0.22); border-radius: 14px;"),
                "screen_lbl": "color: #E7FBFF; font-size: 13px; font-weight: 600;",
                "time_lbl": "color: #C9D6DA; font-size: 11px;",
                "list": ("QListWidget { background-color: rgba(15, 16, 18, 0.45); "
                         "border: 1px solid rgba(255, 255, 255, 0.16); border-radius: 14px; padding: 6px; "
                         "color: #F2FBFF; } QListWidget::item { border-radius: 8px; padding: 3px; } "
                         "QListWidget::item:hover { background-color: rgba(255, 255, 255, 0.10); } "
                         "QListWidget::item:selected { background-color: rgba(90, 200, 255, 0.35); "
                         "color: #EAFCFF; font-weight: bold; }"),
                "btn_sticker": ("QPushButton { background: transparent; border: none; font-size: 18px; "
                                "padding: 5px; color: #EAF6FF; } QPushButton:hover { color: #7FE0FF; }"),
                "btn_edit": ("QPushButton { background-color: rgba(255, 255, 255, 0.10); "
                             "border: 1px solid rgba(255, 255, 255, 0.22); border-radius: 8px; "
                             "padding: 6px 12px; font-size: 11px; color: #EAF6FF; } "
                             "QPushButton:hover { background-color: rgba(255, 255, 255, 0.22); border-color: #7FE0FF; }"),
                "input": ("QLineEdit { background-color: rgba(10, 10, 12, 0.45); "
                          "border: 1px solid rgba(255, 255, 255, 0.22); border-radius: 8px; "
                          "padding: 5px; color: #FFFFFF; }"),
                "slider": ("QSlider::groove:horizontal { height: 4px; background: rgba(255,255,255,0.18); "
                           "border-radius: 2px; } QSlider::sub-page:horizontal { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, "
                           "stop:0 #5AC8FA, stop:1 #7FE0FF); border-radius: 2px; } "
                           "QSlider::handle:horizontal { background: #FFFFFF; border: 1px solid #7FE0FF; "
                           "width: 13px; height: 13px; margin: -5px 0; border-radius: 7px; }"),
                "blur": True,
            },
            "New Year": {
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
            },
            "Neon Sunset": {
                "widget": ("background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, "
                           "stop:0 rgba(74,14,30,0.96), stop:0.5 rgba(122,22,80,0.96), stop:1 rgba(59,16,96,0.96)); color: #FFE3EC;"),
                "screen": ("background-color: rgba(255, 255, 255, 0.07); "
                           "border: 1px solid rgba(255, 46, 126, 0.45); border-radius: 14px;"),
                "screen_lbl": "color: #FFE3EC; font-size: 13px; font-weight: 600;",
                "time_lbl": "color: #E8A7C0; font-size: 11px;",
                "list": ("QListWidget { background-color: rgba(30, 5, 20, 0.55); "
                         "border: 1px solid rgba(255, 46, 126, 0.35); border-radius: 14px; padding: 6px; "
                         "color: #FFD9E8; } QListWidget::item { border-radius: 8px; padding: 3px; } "
                         "QListWidget::item:hover { background-color: rgba(255, 46, 126, 0.15); } "
                         "QListWidget::item:selected { background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0, "
                         "stop:0 rgba(255,59,59,0.75), stop:0.5 rgba(255,46,126,0.75), stop:1 rgba(166,77,255,0.75)); "
                         "color: #FFFFFF; font-weight: bold; }"),
                "btn_sticker": ("QPushButton { background: transparent; border: none; font-size: 18px; "
                                "padding: 5px; color: #FFD9E8; } QPushButton:hover { color: #FF2E7E; }"),
                "btn_edit": ("QPushButton { background-color: rgba(255, 46, 126, 0.15); "
                             "border: 1px solid rgba(255, 46, 126, 0.5); border-radius: 8px; "
                             "padding: 6px 12px; font-size: 11px; color: #FFE3EC; } "
                             "QPushButton:hover { background-color: rgba(255, 46, 126, 0.3); border-color: #A64DFF; }"),
                "input": ("QLineEdit { background-color: rgba(20, 4, 16, 0.6); "
                          "border: 1px solid rgba(255, 46, 126, 0.4); border-radius: 8px; "
                          "padding: 5px; color: #FFFFFF; }"),
                "slider": ("QSlider::groove:horizontal { height: 4px; background: rgba(255,255,255,0.18); "
                           "border-radius: 2px; } "
                           "QSlider::sub-page:horizontal { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, "
                           "stop:0 #FF3B3B, stop:0.5 #FF2E7E, stop:1 #A64DFF); border-radius: 2px; } "
                           "QSlider::handle:horizontal { background: #FFFFFF; border: 1px solid #FF2E7E; "
                           "width: 13px; height: 13px; margin: -5px 0; border-radius: 7px; }"),
                "blur": True,
            },
            "Aurora": {
                "widget": ("background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, "
                           "stop:0 rgba(4,12,28,0.96), stop:0.5 rgba(6,26,44,0.96), stop:1 rgba(4,32,34,0.96)); color: #DFFBF7;"),
                "screen": ("background-color: rgba(255, 255, 255, 0.06); "
                           "border: 1px solid rgba(64, 224, 208, 0.4); border-radius: 14px;"),
                "screen_lbl": "color: #DFFBF7; font-size: 13px; font-weight: 600;",
                "time_lbl": "color: #8FD8CC; font-size: 11px;",
                "list": ("QListWidget { background-color: rgba(3, 10, 22, 0.6); "
                         "border: 1px solid rgba(64, 224, 208, 0.3); border-radius: 14px; padding: 6px; "
                         "color: #CFF7EF; } QListWidget::item { border-radius: 8px; padding: 3px; } "
                         "QListWidget::item:hover { background-color: rgba(64, 224, 208, 0.12); } "
                         "QListWidget::item:selected { background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0, "
                         "stop:0 rgba(0,255,170,0.6), stop:1 rgba(0,180,255,0.6)); "
                         "color: #FFFFFF; font-weight: bold; }"),
                "btn_sticker": ("QPushButton { background: transparent; border: none; font-size: 18px; "
                                "padding: 5px; color: #CFF7EF; } QPushButton:hover { color: #40E0D0; }"),
                "btn_edit": ("QPushButton { background-color: rgba(64, 224, 208, 0.12); "
                             "border: 1px solid rgba(64, 224, 208, 0.45); border-radius: 8px; "
                             "padding: 6px 12px; font-size: 11px; color: #DFFBF7; } "
                             "QPushButton:hover { background-color: rgba(64, 224, 208, 0.25); border-color: #00FFAA; }"),
                "input": ("QLineEdit { background-color: rgba(2, 8, 18, 0.65); "
                          "border: 1px solid rgba(64, 224, 208, 0.35); border-radius: 8px; "
                          "padding: 5px; color: #FFFFFF; }"),
                "slider": ("QSlider::groove:horizontal { height: 4px; background: rgba(255,255,255,0.16); "
                           "border-radius: 2px; } "
                           "QSlider::sub-page:horizontal { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, "
                           "stop:0 #00FFAA, stop:1 #00B4FF); border-radius: 2px; } "
                           "QSlider::handle:horizontal { background: #FFFFFF; border: 1px solid #40E0D0; "
                           "width: 13px; height: 13px; margin: -5px 0; border-radius: 7px; }"),
                "blur": True,
            },
        }

        self.init_ui()
        self.init_tray()
        self.load_playlists()
        self.load_music()
        self.retranslate_ui()

        self.vol_slider.blockSignals(True)
        self.vol_slider.setValue(int(self.settings.get("volume", 70)))
        self.vol_slider.blockSignals(False)
        self.change_volume(self.vol_slider.value())

        self.speed_slider.blockSignals(True)
        self.speed_slider.setValue(int(self.settings.get("speed", 10)))
        self.speed_slider.blockSignals(False)
        self.change_playback_speed(self.speed_slider.value())

        if self.settings.get("replaygain"):
            self.recreate_vlc_engine()

        self.start_hotkeys()
        QTimer.singleShot(300, self.restore_last_session)

        self._watch_debounce = QTimer(self)
        self._watch_debounce.setSingleShot(True)
        self._watch_debounce.timeout.connect(self.on_music_dir_changed)
        self.fs_watcher = QFileSystemWatcher([MUSIC_DIR])
        self.fs_watcher.directoryChanged.connect(lambda _p: self._watch_debounce.start(400))

        # Горячие клавиши для 10-секундной перемотки (Shift+Left/Right)
        sc_seek_back = QShortcut(QKeySequence("Shift+Left"), self)
        sc_seek_back.activated.connect(lambda: self._hotkey_seek(-10000))
        sc_seek_forward = QShortcut(QKeySequence("Shift+Right"), self)
        sc_seek_forward.activated.connect(lambda: self._hotkey_seek(10000))

        # Обновляем состояние кнопок
        self.update_eq_buttons_state()
        self.update_toolbar_visibility()

    def T(self, key, **kwargs):
        text = STRINGS.get(key, key)
        if kwargs:
            try:
                text = text.format(**kwargs)
            except Exception:
                pass
        return text

    def load_settings(self):
        data = dict(DEFAULT_SETTINGS)
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as fp:
                    saved = json.load(fp)
                    data.update(saved)
        except Exception as e:
            log.warning(f"Failed to load settings: {e}")
        return data

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as fp:
                json.dump(self.settings, fp, ensure_ascii=False, indent=2)
        except Exception as e:
            log.warning(f"Failed to save settings: {e}")

    def load_stats(self):
        stats_file = os.path.join(APP_DIR, "lazy_play_stats.json")
        try:
            if os.path.exists(stats_file):
                with open(stats_file, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    self.play_count = data.get("play_count", {})
                    self.skip_count = data.get("skip_count", {})
                    self.listen_history = data.get("history", [])
                    self.weekly_stats = data.get("weekly", {})
                    self.hourly_stats = data.get("hourly", {})
        except Exception as e:
            log.warning(f"Failed to load stats: {e}")

    def save_stats(self):
        stats_file = os.path.join(APP_DIR, "lazy_play_stats.json")
        try:
            with open(stats_file, "w", encoding="utf-8") as fp:
                json.dump({
                    "play_count": self.play_count,
                    "skip_count": self.skip_count,
                    "history": self.listen_history[-1000:],
                    "weekly": self.weekly_stats,
                    "hourly": self.hourly_stats
                }, fp, ensure_ascii=False, indent=2)
        except Exception as e:
            log.warning(f"Failed to save stats: {e}")

    def track_played(self, track):
        if not track:
            return
        self.play_count[track] = self.play_count.get(track, 0) + 1
        self.listen_history.append({
            "track": track,
            "time": datetime.now().isoformat(),
            "action": "play"
        })
        day = datetime.now().strftime("%A")
        self.weekly_stats[day] = self.weekly_stats.get(day, 0) + 1
        hour = datetime.now().hour
        self.hourly_stats[str(hour)] = self.hourly_stats.get(str(hour), 0) + 1
        self.save_stats()

    def track_skipped(self, track):
        if not track:
            return
        self.skip_count[track] = self.skip_count.get(track, 0) + 1
        self.save_stats()
        if hasattr(self, "tray_icon") and self.tray_icon is not None:
            try:
                self.tray_icon.showMessage("⏭️ Skipped", f"{self.display_name(track)}",
                                          QSystemTrayIcon.MessageIcon.Information, 1000)
            except:
                pass

    # ------------------------------------------------------------------
    def load_custom_colors(self):
        try:
            if os.path.exists(CUSTOM_COLORS_FILE):
                with open(CUSTOM_COLORS_FILE, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                self.custom_accent_color = data.get("accent")
                self.custom_button_color = data.get("button")
        except Exception as e:
            log.warning(f"Failed to load custom colors: {e}")

    def save_custom_colors(self):
        try:
            with open(CUSTOM_COLORS_FILE, "w", encoding="utf-8") as fp:
                json.dump({"accent": self.custom_accent_color, "button": self.custom_button_color}, fp)
        except Exception as e:
            log.warning(f"Failed to save custom colors: {e}")

    def pick_accent_color(self):
        start = QColor(self.custom_accent_color) if self.custom_accent_color else QColor("#0071E3")
        color = QColorDialog.getColor(start, self, self.T("settings_accent_color_btn"))
        if color.isValid():
            self.custom_accent_color = color.name()
            self.save_custom_colors()
            self.apply_theme(self.current_theme_name)

    def pick_button_color(self):
        start = QColor(self.custom_button_color) if self.custom_button_color else QColor("#FFFFFF")
        color = QColorDialog.getColor(start, self, self.T("settings_button_color_btn"))
        if color.isValid():
            self.custom_button_color = color.name()
            self.save_custom_colors()
            self.apply_theme(self.current_theme_name)

    def reset_custom_colors(self):
        self.custom_accent_color = None
        self.custom_button_color = None
        self.save_custom_colors()
        self.apply_theme(self.current_theme_name)

    # ------------------------------------------------------------------
    def retranslate_ui(self):
        T = self.T
        self.btn_mini.setToolTip(T("tooltip_mini"))
        self.btn_share.setToolTip(T("tooltip_share"))
        self.btn_donate.setToolTip(T("tooltip_donate"))
        self.btn_diag.setToolTip(T("tooltip_diag"))
        self.btn_update.setToolTip(T("tooltip_update"))
        self.btn_settings.setToolTip(T("tooltip_settings"))
        self.btn_shazam.setToolTip(T("tooltip_shazam"))
        if self.list_widget.count() == 0 or self.list_widget.currentRow() < 0:
            self.screen_label.setText(T("screen_default"))
        current_data = self.playlist_selector.currentData()
        self.playlist_selector.blockSignals(True)
        self.playlist_selector.setItemText(0, T("playlist_library"))
        self.playlist_selector.setItemText(self.playlist_selector.count() - 1, T("playlist_new"))
        idx = self.playlist_selector.findData(current_data)
        if idx >= 0:
            self.playlist_selector.setCurrentIndex(idx)
        self.playlist_selector.blockSignals(False)
        self.btn_pl_add.setToolTip(T("tooltip_pl_add"))
        self.btn_pl_remove.setToolTip(T("tooltip_pl_remove"))
        self.btn_pl_delete.setToolTip(T("tooltip_pl_delete"))
        self.search_input.setPlaceholderText(T("search_placeholder"))
        current_filter = self.filter_selector.currentData()
        self.filter_selector.blockSignals(True)
        self.filter_selector.setItemText(0, T("filter_all"))
        self.filter_selector.setItemText(1, T("filter_added"))
        self.filter_selector.setItemText(2, T("filter_year"))
        self.filter_selector.setItemText(3, T("filter_favorites"))
        idx = self.filter_selector.findData(current_filter)
        if idx >= 0:
            self.filter_selector.setCurrentIndex(idx)
        self.filter_selector.blockSignals(False)
        self.counter_label.setText(T("counter_template", n=len(self.playlist_files)))
        self.btn_bass.setText(T("bass_on") if self.is_bass_boost else T("bass_off"))
        self.btn_bass.setToolTip(T("tooltip_bass"))
        self.btn_eq.setText(T("btn_eq"))
        self.btn_eq.setToolTip(T("tooltip_eq"))
        self.speed_label_widget.setText(T("speed_label"))
        speed = self.speed_slider.value() / 10.0
        self.speed_indicator_label.setText(T("speed_normal") if speed == 1.0 else T("speed_current", x=speed))
        self.btn_edit.setText(T("btn_edit_tags"))
        self.btn_delete.setText(T("btn_delete"))
        self.btn_fav.setText(T("btn_favorite"))
        mode_key = {"Normal": "mode_normal", "Shuffle": "mode_shuffle", "Repeat": "mode_repeat"}[self.play_mode]
        self.btn_mode.setText(T(mode_key))
        self.tray_play_action.setText(T("tray_play"))
        self.tray_pause_action.setText(T("tray_pause"))
        self.tray_next_action.setText(T("tray_next"))
        self.tray_exit_action.setText(T("tray_exit"))
        
        self.update_playlist_counter()
        self.filter_playlist()
        self.update_eq_buttons_state()

    def update_playlist_counter(self):
        if self.active_playlist and self.active_playlist in self.playlists:
            count = len(self.playlists[self.active_playlist]["tracks"])
            index = self.playlist_selector.findData(self.active_playlist)
            if index >= 0:
                current_text = self.playlist_selector.itemText(index)
                if "(" in current_text:
                    base_name = current_text.split(" (")[0]
                else:
                    base_name = current_text
                self.playlist_selector.setItemText(index, f"{base_name} ({count} tracks)")

    # ------------------------------------------------------------------
    def init_ui(self):
        T = self.T
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(12)

        # ----- HEADER WITH BUTTONS -----
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        # Кнопки управления окном
        for c, b in [("#FF5F56", "#E0443E"), ("#FFBD2E", "#DEA123"), ("#27C93F", "#1AAA2C")]:
            dot = QFrame()
            dot.setFixedSize(12, 12)
            dot.setStyleSheet(f"background-color: {c}; border-radius: 6px; border: 0.5px solid {b};")
            header_layout.addWidget(dot)
        
        self.title_label = QLabel("LazyPleer")
        self.title_label.setStyleSheet("font-weight: 700; font-size: 14px; margin-left: 5px;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        # Словарь для хранения всех кнопок
        self.header_buttons = []
        
        # Создаем кнопки с их идентификаторами
        button_configs = [
            ("🗗", "mini", self.toggle_mini_player),
            ("📤", "share", self.show_share_menu),
            ("💰", "donate", self.support_author),
            ("🛡️", "diag", self.run_library_diagnostic),
            ("🔄", "update", self.check_for_updates),
            ("ℹ️", "info", self.open_about_dialog),
            ("⚙️", "settings", self.open_settings_dialog),
            ("🎵", "shazam", self.identify_song),
        ]
        
        for text, btn_id, slot in button_configs:
            btn = QPushButton(text)
            btn.setFixedSize(26, 26)
            btn.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 13px; }")
            btn.clicked.connect(slot)
            btn.setProperty("btn_id", btn_id)
            header_layout.addWidget(btn)
            self.header_buttons.append(btn)
            
            if btn_id == "mini": self.btn_mini = btn
            elif btn_id == "share": self.btn_share = btn
            elif btn_id == "donate": self.btn_donate = btn
            elif btn_id == "diag": self.btn_diag = btn
            elif btn_id == "update": self.btn_update = btn
            elif btn_id == "info": self.btn_info = btn
            elif btn_id == "settings": self.btn_settings = btn
            elif btn_id == "shazam": self.btn_shazam = btn
        
        self.main_layout.addLayout(header_layout)

        # ----- SCREEN (cover + info) -----
        self.screen_frame = QFrame()
        self.screen_layout = QHBoxLayout(self.screen_frame)
        self.screen_layout.setContentsMargins(12, 12, 12, 12)
        self.cover_label = QLabel("💿")
        self.cover_label.setFixedSize(48, 48)
        self.cover_label.setStyleSheet("font-size: 32px; background: transparent; qproperty-alignment: 'AlignCenter';")
        self.screen_layout.addWidget(self.cover_label)
        text_screen_layout = QVBoxLayout()
        self.screen_label = QLabel(T("screen_default"))
        self.time_label = QLabel("00:00 / 00:00")
        text_screen_layout.addWidget(self.screen_label)
        text_screen_layout.addWidget(self.time_label)
        self.screen_layout.addLayout(text_screen_layout)
        self.main_layout.addWidget(self.screen_frame)

        self.screen_opacity = QGraphicsOpacityEffect(self.screen_frame)
        self.screen_frame.setGraphicsEffect(self.screen_opacity)
        self.screen_opacity.setOpacity(1.0)

        # ----- PROGRESS BAR -----
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.sliderPressed.connect(self.slider_pressed)
        self.progress_slider.sliderReleased.connect(self.slider_released)
        self.main_layout.addWidget(self.progress_slider)

        # ----- SEEK BUTTONS (10s) -----
        seek_layout = QHBoxLayout()
        self.btn_seek_back = QPushButton("⏪ 10s")
        self.btn_seek_back.setStyleSheet("font-size: 10px; padding: 2px 8px;")
        self.btn_seek_back.clicked.connect(lambda: self._hotkey_seek(-10000))
        self.btn_seek_forward = QPushButton("10s ⏩")
        self.btn_seek_forward.setStyleSheet("font-size: 10px; padding: 2px 8px;")
        self.btn_seek_forward.clicked.connect(lambda: self._hotkey_seek(10000))
        seek_layout.addWidget(self.btn_seek_back)
        seek_layout.addStretch()
        seek_layout.addWidget(self.btn_seek_forward)
        self.main_layout.addLayout(seek_layout)

        # ----- PLAYLIST SELECTOR -----
        playlist_row = QHBoxLayout()
        self.playlist_selector = QComboBox()
        self.playlist_selector.addItem(T("playlist_library"), None)
        self.playlist_selector.addItem(T("playlist_new"), "__new__")
        self.playlist_selector.currentIndexChanged.connect(self.on_playlist_changed)
        self.playlist_selector.installEventFilter(self)
        playlist_row.addWidget(self.playlist_selector, stretch=1)
        self.btn_pl_add = QPushButton("➕"); self.btn_pl_add.setFixedWidth(30)
        self.btn_pl_add.clicked.connect(self.add_track_to_active_playlist)
        self.btn_pl_remove = QPushButton("➖"); self.btn_pl_remove.setFixedWidth(30)
        self.btn_pl_remove.clicked.connect(self.remove_track_from_active_playlist)
        self.btn_pl_delete = QPushButton("🗑"); self.btn_pl_delete.setFixedWidth(30)
        self.btn_pl_delete.clicked.connect(self.delete_active_playlist)
        playlist_row.addWidget(self.btn_pl_add)
        playlist_row.addWidget(self.btn_pl_remove)
        playlist_row.addWidget(self.btn_pl_delete)
        self.main_layout.addLayout(playlist_row)

        # ----- SEARCH & FILTER -----
        filter_bar_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(T("search_placeholder"))
        self.search_input.textChanged.connect(self.filter_playlist)
        filter_bar_layout.addWidget(self.search_input)
        self.filter_selector = QComboBox()
        self.filter_selector.addItem(T("filter_all"), "all")
        self.filter_selector.addItem(T("filter_added"), "added")
        self.filter_selector.addItem(T("filter_year"), "year")
        self.filter_selector.addItem(T("filter_favorites"), "favorites")
        self.filter_selector.setStyleSheet("QComboBox { padding: 4px; font-size: 11px; }")
        self.filter_selector.currentIndexChanged.connect(self.filter_playlist)
        filter_bar_layout.addWidget(self.filter_selector)

        self.sort_selector = QComboBox()
        self.sort_selector.addItem(T("sort_added"), "added")
        self.sort_selector.addItem(T("sort_title"), "title")
        self.sort_selector.addItem(T("sort_artist"), "artist")
        self.sort_selector.addItem(T("sort_length"), "length")
        self.sort_selector.setStyleSheet("QComboBox { padding: 4px; font-size: 11px; }")
        idx = self.sort_selector.findData(self.settings.get("sort", "added"))
        self.sort_selector.setCurrentIndex(idx if idx >= 0 else 0)
        self.sort_selector.currentIndexChanged.connect(self.on_sort_changed)
        filter_bar_layout.addWidget(self.sort_selector)
        self.main_layout.addLayout(filter_bar_layout)

        self.counter_label = QLabel(T("counter_template", n=0))
        self.counter_label.setStyleSheet("font-size: 11px; font-weight: 500;")
        self.main_layout.addWidget(self.counter_label)

        # ----- PLAYLIST (with cover thumbnails) -----
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(32, 32))
        self.list_widget.itemDoubleClicked.connect(self.play_selected)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_track_context_menu)
        self.list_widget.setDragDropMode(QListWidget.InternalMove)
        self.list_widget.model().rowsMoved.connect(self.on_rows_moved)
        self.main_layout.addWidget(self.list_widget)

        self.list_opacity = QGraphicsOpacityEffect(self.list_widget)
        self.list_widget.setGraphicsEffect(self.list_opacity)
        self.list_opacity.setOpacity(1.0)

        # ----- FX CONTROLS -----
        fx_layout = QHBoxLayout()
        self.btn_bass = QPushButton(T("bass_off"))
        self.btn_bass.setStyleSheet("font-size: 10px; font-weight: bold; padding: 4px;")
        self.btn_bass.clicked.connect(self.toggle_bass_boost)
        fx_layout.addWidget(self.btn_bass)
        self.btn_eq = QPushButton(T("btn_eq"))
        self.btn_eq.setStyleSheet("font-size: 10px; font-weight: bold; padding: 4px;")
        self.btn_eq.clicked.connect(self.open_equalizer_dialog)
        fx_layout.addWidget(self.btn_eq)

        speed_vbox = QVBoxLayout()
        speed_hbox = QHBoxLayout()
        self.speed_label_widget = QLabel(T("speed_label"))
        speed_hbox.addWidget(self.speed_label_widget)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(5, 20)
        self.speed_slider.setValue(10)
        self.speed_slider.setFixedWidth(100)
        self.speed_slider.valueChanged.connect(self.change_playback_speed)
        speed_hbox.addWidget(self.speed_slider)
        speed_vbox.addLayout(speed_hbox)
        self.speed_indicator_label = QLabel(T("speed_normal"))
        self.speed_indicator_label.setStyleSheet("font-size: 9px; color: gray; qproperty-alignment: 'AlignCenter';")
        speed_vbox.addWidget(self.speed_indicator_label)
        fx_layout.addLayout(speed_vbox)
        self.main_layout.addLayout(fx_layout)

        # ----- META CONTROLS -----
        meta_layout = QHBoxLayout()
        self.btn_edit = QPushButton(T("btn_edit_tags")); self.btn_edit.clicked.connect(self.open_metadata_editor)
        self.btn_delete = QPushButton(T("btn_delete")); self.btn_delete.clicked.connect(self.delete_current_track)
        self.btn_fav = QPushButton(T("btn_favorite")); self.btn_fav.clicked.connect(self.toggle_favorite_track)
        meta_layout.addWidget(self.btn_edit)
        meta_layout.addWidget(self.btn_delete)
        meta_layout.addWidget(self.btn_fav)
        meta_layout.addStretch()
        self.btn_mode = QPushButton(T("mode_normal")); self.btn_mode.clicked.connect(self.toggle_play_mode)
        meta_layout.addWidget(self.btn_mode)
        self.main_layout.addLayout(meta_layout)

        # ----- VOLUME -----
        vol_layout = QHBoxLayout()
        self.vol_icon = QLabel("🔊")
        self.vol_icon.setStyleSheet("background: transparent; font-size: 11px;")
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 125)
        self.vol_slider.setValue(70)
        self.vol_slider.valueChanged.connect(self.change_volume)
        vol_layout.addWidget(self.vol_icon)
        vol_layout.addWidget(self.vol_slider)
        self.main_layout.addLayout(vol_layout)

        # ----- PLAYBACK CONTROLS -----
        self.controls_layout = QHBoxLayout()
        self.controls_layout.setSpacing(25)
        self.controls_layout.setAlignment(Qt.AlignCenter)
        self.btn_prev = QPushButton("⏮"); self.btn_prev.clicked.connect(self.prev_track)
        self.btn_play = QPushButton("▶"); self.btn_play.clicked.connect(self.play_track)
        self.btn_pause = QPushButton("⏸"); self.btn_pause.clicked.connect(self.pause_track)
        self.btn_next = QPushButton("⏭"); self.btn_next.clicked.connect(self.next_track)
        self.controls_layout.addWidget(self.btn_prev)
        self.controls_layout.addWidget(self.btn_play)
        self.controls_layout.addWidget(self.btn_pause)
        self.controls_layout.addWidget(self.btn_next)
        self.main_layout.addLayout(self.controls_layout)

        # ----- HIDE WIDGETS (уже не нужны, оставляем пустыми) -----
        self.focus_hide_widgets = []
        self.cinema_hide_widgets = []

        # Горячие клавиши
        sc_space = QShortcut(QKeySequence(Qt.Key_Space), self)
        sc_space.activated.connect(self._hotkey_play_pause)
        sc_right = QShortcut(QKeySequence(Qt.Key_Right), self)
        sc_right.activated.connect(lambda: self._hotkey_seek(5000))
        sc_left = QShortcut(QKeySequence(Qt.Key_Left), self)
        sc_left.activated.connect(lambda: self._hotkey_seek(-5000))

        self.apply_theme("Light macOS")
        self.apply_font_size()

    def toggle_mini_player(self):
        if self.mini_player is not None:
            self.mini_player.close_mini()
            return
        self.mini_player = MiniPlayer(self)
        self.mini_player.move(self.geometry().topRight() + QPoint(20, 0))
        self.mini_player.show()
        self.hide()

    def eventFilter(self, obj, event):
        if obj == self.playlist_selector and event.type() == event.Type.MouseButtonDblClick:
            current_data = self.playlist_selector.currentData()
            if current_data and current_data != "__new__" and current_data in self.playlists:
                self.rename_playlist(current_data)
                return True
        return super().eventFilter(obj, event)

    def rename_playlist(self, name):
        new_name, ok = QInputDialog.getText(self, self.T("playlist_rename_title"), 
                                           self.T("playlist_rename_prompt"), 
                                           QLineEdit.Normal, name)
        if ok and new_name.strip():
            new_name = new_name.strip()
            if new_name == name:
                return
            if new_name in self.playlists:
                QMessageBox.warning(self, self.T("playlist_exists_title"), self.T("playlist_exists_text"))
                return
            self.playlists[new_name] = self.playlists.pop(name)
            self.save_playlist(new_name)
            old_path = os.path.join(PLAYLISTS_DIR, f"{resource_free_name(name)}.json")
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except:
                    pass
            self.load_playlists()
            idx = self.playlist_selector.findData(new_name)
            if idx >= 0:
                self.playlist_selector.setCurrentIndex(idx)
            self.update_playlist_counter()

    def on_rows_moved(self, parent, start, end, destination, row):
        if not self.current_playlist:
            return
        items = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            text = item.text()
            for prefix in [" ❤️  ", "  🎵  "]:
                if text.startswith(prefix):
                    text = text[len(prefix):]
                    break
            items.append(text)
        
        if self.active_playlist and self.active_playlist in self.playlists:
            self.playlists[self.active_playlist]["tracks"] = items
            self.save_playlist(self.active_playlist)
        else:
            self.current_playlist = items
            self.settings["library_order"] = items
            self.save_settings()

    # ------------------------------------------------------------------
    def update_toolbar_visibility(self):
        toolbar_settings = self.settings.get("toolbar_buttons", {})
        for btn in self.header_buttons:
            btn_id = btn.property("btn_id")
            if btn_id and btn_id in toolbar_settings:
                btn.setVisible(toolbar_settings[btn_id])

    # ------------------------------------------------------------------
    def show_share_menu(self):
        track = self.current_upg_track or "?"
        menu = QMenu(self)
        menu.setStyleSheet(self.dialog_css())
        
        vk_action = menu.addAction(self.T("settings_share_vk"))
        tg_action = menu.addAction(self.T("settings_share_tg"))
        tw_action = menu.addAction(self.T("settings_share_tw"))
        
        action = menu.exec(self.btn_share.mapToGlobal(QPoint(0, self.btn_share.height())))
        
        track_name = self.display_name(track)
        if action == vk_action:
            text = self.T("share_vk_text", t=track_name)
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, self.T("share_title"), "✅ VK post copied to clipboard!")
        elif action == tg_action:
            text = self.T("share_tg_text", t=track_name)
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, self.T("share_title"), "✅ Telegram post copied to clipboard!")
        elif action == tw_action:
            text = self.T("share_tw_text", t=track_name)
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, self.T("twitter_title"), self.T("twitter_copied"))

    # ------------------------------------------------------------------
    def identify_song(self):
        if not self.current_upg_track or not self.player:
            QMessageBox.warning(self, self.T("shazam_title"), self.T("shazam_error"))
            return
        
        meta = self.metadata_cache.get(self.current_upg_track)
        if meta.get("artist") and meta.get("title") and meta.get("title") != self.current_upg_track:
            QMessageBox.information(self, self.T("shazam_title"), 
                                   self.T("shazam_result", title=meta["title"], artist=meta["artist"]))
            return
        
        import re
        filename = os.path.splitext(self.current_upg_track)[0]
        parts = re.split(r'[-–—]', filename)
        if len(parts) >= 2:
            artist = parts[0].strip()
            title = parts[1].strip()
            QMessageBox.information(self, self.T("shazam_title"), 
                                   self.T("shazam_result", title=title, artist=artist))
            if QMessageBox.question(self, self.T("shazam_title"), self.T("shazam_add"),
                                   QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                self.open_metadata_editor()
        else:
            QMessageBox.information(self, self.T("shazam_title"), 
                                   "Could not identify the song.\nTry editing tags manually.")

    # ------------------------------------------------------------------
    def export_to_spotify(self, playlist_name=None):
        if playlist_name is None:
            playlist_name = self.active_playlist
        if not playlist_name or playlist_name not in self.playlists:
            return
        
        tracks = self.playlists[playlist_name]["tracks"]
        if not tracks:
            QMessageBox.information(self, self.T("export_spotify_title"), "Playlist is empty!")
            return
        
        lines = []
        for track in tracks:
            meta = self.metadata_cache.get(track)
            artist = meta.get("artist", "Unknown")
            title = meta.get("title", track)
            lines.append(f"{artist} - {title}")
        
        text = "\n".join(lines)
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, self.T("export_spotify_title"), 
                               f"✅ {len(lines)} tracks copied!\nPaste into Spotify search to add to playlist.")

    # ------------------------------------------------------------------
    def apply_font_size(self):
        size = self.settings.get("font_size", "medium")
        font_map = {"small": 9, "medium": 11, "large": 14}
        font_size = font_map.get(size, 11)
        
        self.setStyleSheet(self.styleSheet() + f" * {{ font-size: {font_size}px; }}")
        icon_size = {9: 24, 11: 32, 14: 48}.get(font_size, 32)
        self.list_widget.setIconSize(QSize(icon_size, icon_size))

    def apply_window_opacity(self):
        if self.settings.get("opacity_enabled", False):
            opacity = self.settings.get("window_opacity", 100) / 100.0
            self.setWindowOpacity(opacity)
        else:
            self.setWindowOpacity(1.0)

    # ------------------------------------------------------------------
    def open_settings_dialog(self):
        T = self.T
        dialog = QDialog(self)
        dialog.setWindowTitle(T("settings_title"))
        dialog.resize(500, 750)
        dialog.setStyleSheet(self.dialog_css())

        outer = QVBoxLayout(dialog)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)

        # ----- Theme -----
        layout.addWidget(QLabel(T("settings_theme_label")))
        theme_combo = QComboBox()
        theme_combo.addItems(list(self.themes.keys()))
        theme_combo.setCurrentText(self.current_theme_name)
        layout.addWidget(theme_combo)

        # ----- Sleep Timer -----
        layout.addWidget(QLabel(T("settings_sleep_label")))
        sleep_combo = QComboBox()
        sleep_combo.addItem(T("sleep_off"), 0)
        sleep_combo.addItem(T("sleep_15"), 15)
        sleep_combo.addItem(T("sleep_30"), 30)
        sleep_combo.addItem(T("sleep_60"), 60)
        if self.sleep_minutes_left > 0:
            i2 = sleep_combo.findData(self.sleep_minutes_left)
            if i2 >= 0:
                sleep_combo.setCurrentIndex(i2)
        layout.addWidget(sleep_combo)

        layout.addWidget(QLabel(T("settings_sleep_action_label")))
        sleep_action_combo = QComboBox()
        sleep_action_combo.addItem(T("sleep_action_pause"), "pause")
        sleep_action_combo.addItem(T("sleep_action_quit"), "quit")
        idx = sleep_action_combo.findData(self.settings.get("sleep_action", "pause"))
        sleep_action_combo.setCurrentIndex(idx if idx >= 0 else 0)
        layout.addWidget(sleep_action_combo)

        # ----- Custom Colors -----
        layout.addWidget(QLabel(T("settings_custom_label")))
        color_row = QHBoxLayout()
        btn_accent = QPushButton(T("settings_accent_color_btn")); btn_accent.clicked.connect(self.pick_accent_color)
        btn_button_color = QPushButton(T("settings_button_color_btn")); btn_button_color.clicked.connect(self.pick_button_color)
        color_row.addWidget(btn_accent); color_row.addWidget(btn_button_color)
        layout.addLayout(color_row)
        btn_reset_colors = QPushButton(T("settings_reset_colors_btn")); btn_reset_colors.clicked.connect(self.reset_custom_colors)
        layout.addWidget(btn_reset_colors)

        # ----- Audio Output -----
        layout.addWidget(QLabel(T("settings_audio_output_label")))
        audio_combo = QComboBox()
        audio_combo.addItem(T("audio_output_default"), None)
        devices = self.enumerate_audio_devices()
        if not devices:
            audio_combo.addItem(T("audio_output_unavailable"), "__unavailable__")
        else:
            for device_id, description in devices:
                audio_combo.addItem(description, device_id)

        def on_audio_device_changed(i):
            data = audio_combo.itemData(i)
            if data not in (None, "__unavailable__"):
                self.set_audio_output_device(data)

        audio_combo.currentIndexChanged.connect(on_audio_device_changed)
        layout.addWidget(audio_combo)

        # ----- Font Size -----
        layout.addWidget(QLabel(T("settings_font_size")))
        font_combo = QComboBox()
        font_combo.addItem(T("settings_font_small"), "small")
        font_combo.addItem(T("settings_font_medium"), "medium")
        font_combo.addItem(T("settings_font_large"), "large")
        idx = font_combo.findData(self.settings.get("font_size", "medium"))
        font_combo.setCurrentIndex(idx if idx >= 0 else 1)
        layout.addWidget(font_combo)

        # ----- Window Opacity -----
        layout.addWidget(QLabel(T("settings_window_opacity")))
        opacity_row = QHBoxLayout()
        opacity_chk = QCheckBox(T("settings_opacity_enable"))
        opacity_chk.setChecked(bool(self.settings.get("opacity_enabled", False)))
        opacity_row.addWidget(opacity_chk)
        opacity_slider = QSlider(Qt.Horizontal)
        opacity_slider.setRange(20, 100)
        opacity_slider.setValue(int(self.settings.get("window_opacity", 100)))
        opacity_slider.setFixedWidth(150)
        opacity_label = QLabel(T("settings_opacity_label", p=opacity_slider.value()))
        opacity_slider.valueChanged.connect(lambda v: opacity_label.setText(T("settings_opacity_label", p=v)))
        opacity_row.addWidget(opacity_slider)
        opacity_row.addWidget(opacity_label)
        layout.addLayout(opacity_row)

        # ----- Toolbar Customization -----
        layout.addWidget(QLabel(T("settings_toolbar_label")))
        toolbar_group = QGroupBox("Toolbar Buttons")
        toolbar_layout = QGridLayout()
        toolbar_settings = self.settings.get("toolbar_buttons", {})
        
        button_names = {
            "mini": "🗗 Mini", "share": "📤 Share",
            "donate": "💰 Donate", "diag": "🛡️ Diag",
            "update": "🔄 Update", "info": "ℹ️ Info",
            "settings": "⚙️ Settings", "shazam": "🎵 Shazam"
        }
        
        toolbar_checkboxes = {}
        row, col = 0, 0
        for btn_id, name in button_names.items():
            chk = QCheckBox(name)
            chk.setChecked(toolbar_settings.get(btn_id, True))
            toolbar_layout.addWidget(chk, row, col)
            toolbar_checkboxes[btn_id] = chk
            col += 1
            if col > 2:
                col = 0
                row += 1
        
        toolbar_group.setLayout(toolbar_layout)
        layout.addWidget(toolbar_group)

        # ----- Vinyl Mode -----
        vinyl_chk = QCheckBox(T("settings_vinyl_mode"))
        vinyl_chk.setChecked(bool(self.settings.get("vinyl_mode", False)))
        layout.addWidget(vinyl_chk)

        # ----- EQ Disable -----
        eq_disabled_chk = QCheckBox(T("settings_eq_disabled"))
        eq_disabled_chk.setChecked(bool(self.settings.get("eq_disabled", False)))
        layout.addWidget(eq_disabled_chk)

        # ----- Advanced -----
        layout.addWidget(QLabel("<b>🧠 Advanced:</b>"))
        discord_enabled = QCheckBox(T("settings_discord_label"))
        discord_enabled.setChecked(bool(self.settings.get("discord_enabled", True)))
        layout.addWidget(discord_enabled)

        layout.addWidget(QLabel(T("settings_discord_id_label")))
        discord_id = QLineEdit(str(self.settings.get("discord_app_id", "")))
        discord_id.setPlaceholderText("Paste your ID from Discord Developer Portal")
        layout.addWidget(discord_id)

        hotkeys_chk = QCheckBox(T("settings_hotkeys"))
        hotkeys_chk.setChecked(bool(self.settings.get("hotkeys", True)))
        layout.addWidget(hotkeys_chk)

        restore_pos_chk = QCheckBox(T("settings_restore_pos"))
        restore_pos_chk.setChecked(bool(self.settings.get("restore_position", True)))
        layout.addWidget(restore_pos_chk)

        replaygain_chk = QCheckBox(T("settings_replaygain"))
        replaygain_chk.setChecked(bool(self.settings.get("replaygain", False)))
        layout.addWidget(replaygain_chk)

        cf_row = QHBoxLayout()
        cf_row.addWidget(QLabel(T("settings_crossfade")))
        cf_slider = QSlider(Qt.Horizontal)
        cf_slider.setRange(0, 5)
        cf_slider.setValue(int(self.settings.get("crossfade", 0)))
        cf_label = QLabel(f"{cf_slider.value()}s")
        cf_slider.valueChanged.connect(lambda v: cf_label.setText(f"{v}s"))
        cf_row.addWidget(cf_slider); cf_row.addWidget(cf_label)
        layout.addLayout(cf_row)

        layout.addSpacing(10)
        outer.addWidget(scroll)
        btn_save = QPushButton(T("btn_apply_settings"))
        btn_save.clicked.connect(lambda: self.save_settings_action(
            dialog, theme_combo.currentText(), sleep_combo.currentData(),
            sleep_action_combo.currentData(), discord_enabled.isChecked(),
            discord_id.text().strip(), hotkeys_chk.isChecked(), restore_pos_chk.isChecked(),
            replaygain_chk.isChecked(), cf_slider.value(), eq_disabled_chk.isChecked(),
            font_combo.currentData(), opacity_chk.isChecked(), opacity_slider.value(),
            vinyl_chk.isChecked(), {btn_id: chk.isChecked() for btn_id, chk in toolbar_checkboxes.items()}))
        outer.addWidget(btn_save)
        dialog.exec()

    def save_settings_action(self, dialog, theme, sleep_minutes, sleep_action,
                             discord_on, discord_id, hotkeys_on, restore_on, 
                             replaygain_on, crossfade, eq_disabled, font_size,
                             opacity_enabled, window_opacity, vinyl_mode, toolbar_buttons):
        old_replaygain = bool(self.settings.get("replaygain", False))
        old_eq_disabled = bool(self.settings.get("eq_disabled", False))
        old_opacity = self.settings.get("opacity_enabled", False)
        
        self.settings.update({
            "sleep_action": sleep_action or "pause",
            "discord_enabled": bool(discord_on),
            "discord_app_id": discord_id or "",
            "hotkeys": bool(hotkeys_on),
            "restore_position": bool(restore_on),
            "replaygain": bool(replaygain_on),
            "crossfade": int(crossfade or 0),
            "eq_disabled": bool(eq_disabled),
            "font_size": font_size or "medium",
            "opacity_enabled": bool(opacity_enabled),
            "window_opacity": int(window_opacity or 100),
            "vinyl_mode": bool(vinyl_mode),
            "toolbar_buttons": toolbar_buttons,
        })
        self.save_settings()
        self.apply_theme(theme)
        self.set_sleep_timer(sleep_minutes)
        self.init_discord_rpc()
        self.restart_hotkeys()
        self.apply_font_size()
        self.apply_window_opacity()
        self.update_toolbar_visibility()
        
        if vinyl_mode and not self.vinyl_noise:
            self.enable_vinyl_mode()
        elif not vinyl_mode and self.vinyl_noise:
            self.disable_vinyl_mode()
        
        if old_replaygain != bool(replaygain_on) or old_eq_disabled != bool(eq_disabled):
            self.recreate_vlc_engine()
            self.update_eq_buttons_state()
        
        dialog.accept()

    def enable_vinyl_mode(self):
        if not VLC_AVAILABLE or not self.player:
            return
        try:
            self.vinyl_noise = vlc.AudioFilter("vinyl", {})
            log.info("Vinyl mode enabled")
        except Exception as e:
            log.warning(f"Failed to enable vinyl mode: {e}")

    def disable_vinyl_mode(self):
        self.vinyl_noise = None
        log.info("Vinyl mode disabled")

    # ------------------------------------------------------------------
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
        for b in (self.btn_edit, self.btn_delete, self.btn_fav, self.btn_mode, self.btn_bass, self.btn_eq,
                  self.btn_seek_back, self.btn_seek_forward):
            b.setStyleSheet(style["btn_edit"])
        self.search_input.setStyleSheet(style["input"])
        for btn in [self.btn_prev, self.btn_play, self.btn_pause, self.btn_next]:
            btn.setStyleSheet(style["btn_sticker"])
        if self.custom_accent_color:
            accent_override = (f" QSlider::sub-page:horizontal {{ background: {self.custom_accent_color}; }} "
                               f"QSlider::handle:horizontal {{ border-color: {self.custom_accent_color}; }}")
            self.progress_slider.setStyleSheet(style["slider"] + accent_override)
            self.vol_slider.setStyleSheet(style["slider"] + accent_override)
        if self.custom_button_color:
            btn_override = f" QPushButton {{ background-color: {self.custom_button_color}; }}"
            for b in (self.btn_edit, self.btn_delete, self.btn_fav, self.btn_mode, self.btn_bass, self.btn_eq):
                b.setStyleSheet(style["btn_edit"] + btn_override)
        if style.get("blur"):
            if not enable_windows_blur(self):
                log.info("Real blur unavailable — theme stays translucent without blur.")
        self.load_music()
        self.update_eq_buttons_state()
        self.apply_font_size()
        self.apply_window_opacity()

    def _fade(self, opacity_effect, start=0.15, end=1.0, duration=260):
        anim = QPropertyAnimation(opacity_effect, b"opacity", self)
        anim.setDuration(duration)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        self._active_anim = anim

    # ------------------------------------------------------------------
    def change_playback_speed(self, value):
        speed = value / 10.0
        if self.player:
            self.player.set_rate(speed)
        self.speed_indicator_label.setText(
            self.T("speed_normal") if speed == 1.0 else self.T("speed_current", x=speed))
        self.settings["speed"] = int(value)
        self.save_settings()

    def apply_eq_gains(self, gains):
        if self.settings.get("eq_disabled", False):
            return
        self.eq_gains = gains
        if not (self.eq_available and self.player and self.equalizer):
            return
        for i, val in enumerate(gains):
            self.equalizer.set_amp_at_index(float(val), i)
        self.player.set_equalizer(self.equalizer)
        self.is_bass_boost = gains == EQ_PRESET_VALUES["eq_preset_bass"]
        self.btn_bass.setText(self.T("bass_on") if self.is_bass_boost else self.T("bass_off"))

    def open_equalizer_dialog(self):
        if self.settings.get("eq_disabled", False):
            QMessageBox.information(self, self.T("eq_unavailable_title"), 
                                   "Equalizer is disabled in settings.\nEnable it in Settings → 'Disable Equalizer'")
            return
        if not (self.eq_available and self.player and self.equalizer):
            QMessageBox.warning(self, self.T("eq_unavailable_title"), self.T("eq_unavailable_text"))
            return
        d = EqualizerDialog(self, self.eq_gains, self.apply_eq_gains, self.save_custom_eq_preset)
        d.setStyleSheet(self.dialog_css())
        d.exec()

    def save_custom_eq_preset(self, gains):
        EQ_PRESET_VALUES[EQ_PRESET_CUSTOM_KEY] = gains
        try:
            with open(EQ_CUSTOM_FILE, "w", encoding="utf-8") as fp:
                json.dump({"gains": gains}, fp)
        except Exception as e:
            log.warning(f"Failed to save custom EQ: {e}")
        QMessageBox.information(self, self.T("eq_saved_title"), self.T("eq_saved_text"))

    def load_custom_eq(self):
        try:
            if os.path.exists(EQ_CUSTOM_FILE):
                with open(EQ_CUSTOM_FILE, "r", encoding="utf-8") as fp:
                    gains = json.load(fp).get("gains")
                if gains and len(gains) == 10:
                    EQ_PRESET_VALUES[EQ_PRESET_CUSTOM_KEY] = gains
                    self.eq_gains = gains
        except Exception as e:
            log.warning(f"Failed to load custom EQ: {e}")

    def toggle_bass_boost(self):
        if self.settings.get("eq_disabled", False):
            QMessageBox.information(self, self.T("eq_unavailable_title"), 
                                   "Bass Boost is disabled in settings.\nEnable it in Settings → 'Disable Equalizer'")
            return
        if not (self.eq_available and self.player and self.equalizer):
            QMessageBox.warning(self, self.T("eq_unavailable_title"), self.T("eq_unavailable_text"))
            return
        if self.is_bass_boost:
            self.apply_eq_gains(list(EQ_PRESET_VALUES["eq_preset_flat"]))
        else:
            self.apply_eq_gains(list(EQ_PRESET_VALUES["eq_preset_bass"]))

    def change_volume(self, value):
        if self.player:
            self.player.audio_set_volume(value)
        self.vol_icon.setText("⚡" if value > 100 else "🔊")
        self.settings["volume"] = int(value)
        self.save_settings()

    def recreate_vlc_engine(self):
        if not VLC_AVAILABLE:
            return
        try:
            if self.player:
                self.player.stop()
            args = "--no-video"
            if self.settings.get("replaygain"):
                args += " --audio-replay-gain-mode=track"
            if self.settings.get("vinyl_mode"):
                args += " --audio-filter=vinyl"
            self.vlc_instance = vlc.Instance(args)
            self.player = self.vlc_instance.media_player_new()
            
            if not self.settings.get("eq_disabled", False):
                eq_class = getattr(vlc, "AudioEqualizer", None) or getattr(vlc, "Equalizer", None)
                if eq_class is not None:
                    try:
                        self.equalizer = eq_class()
                        self.eq_available = True
                        self.player.set_equalizer(self.equalizer)
                    except Exception as e:
                        log.warning(f"VLC equalizer unavailable: {e}")
                        self.eq_available = False
                else:
                    self.eq_available = False
            else:
                self.eq_available = False
                self.equalizer = None
            
            self.change_volume(self.vol_slider.value())
            self.change_playback_speed(self.speed_slider.value())
            self.update_eq_buttons_state()
        except Exception as e:
            log.warning(f"Failed to recreate VLC engine: {e}")

    def enumerate_audio_devices(self):
        devices = []
        if not (VLC_AVAILABLE and self.player and hasattr(self.player, "audio_output_device_enum")):
            return devices
        try:
            device_list = self.player.audio_output_device_enum()
            node = device_list
            while node:
                contents = node.contents
                device_id = contents.device.decode("utf-8", errors="ignore") if contents.device else ""
                description = contents.description.decode("utf-8", errors="ignore") if contents.description else device_id
                if device_id:
                    devices.append((device_id, description))
                node = contents.next
            if device_list and hasattr(vlc, "libvlc_audio_output_device_list_release"):
                vlc.libvlc_audio_output_device_list_release(device_list)
        except Exception as e:
            log.warning(f"Failed to enumerate audio devices: {e}")
            return []
        return devices

    def set_audio_output_device(self, device_id):
        if not (self.player and device_id):
            return
        try:
            try:
                self.player.audio_output_device_set(None, device_id)
            except TypeError:
                self.player.audio_output_device_set(device_id)
        except Exception as e:
            log.warning(f"Failed to switch audio output to {device_id}: {e}")

    # ------------------------------------------------------------------
    def init_discord_rpc(self):
        if self.rpc is not None:
            try:
                self.rpc.close()
            except Exception:
                pass
            self.rpc = None
        if not DISCORD_AVAILABLE or not self.settings.get("discord_enabled", True):
            return
        app_id = str(self.settings.get("discord_app_id", "")).strip()
        if not app_id:
            log.info("Discord RPC: Application ID not set — configure it in player settings.")
            return
        try:
            self.rpc = Presence(app_id)
            self.rpc.connect()
        except Exception as e:
            log.info(f"Discord RPC unavailable: {e}")
            self.rpc = None

    # ------------------------------------------------------------------
    def start_hotkeys(self):
        if not (PYNPUT_AVAILABLE and self.settings.get("hotkeys", True)):
            return
        self.hotkey_worker = HotkeyWorker()
        self.hotkey_worker.play_pause.connect(self.toggle_play_pause)
        self.hotkey_worker.next_track.connect(self.next_track)
        self.hotkey_worker.prev_track.connect(self.prev_track)
        self.hotkey_worker.start()

    def restart_hotkeys(self):
        if self.hotkey_worker is not None:
            self.hotkey_worker.stop()
            self.hotkey_worker.wait(800)
            self.hotkey_worker = None
        self.start_hotkeys()

    def toggle_play_pause(self):
        if not self.player:
            return
        if self.player.is_playing():
            self.pause_track()
        else:
            self.play_track()

    # ------------------------------------------------------------------
    def share_on_twitter(self):
        track = self.current_upg_track or "?"
        QApplication.clipboard().setText(self.T("twitter_share_text", t=self.display_name(track)))
        QMessageBox.information(self, self.T("twitter_title"), self.T("twitter_copied"))

    def support_author(self):
        if QMessageBox.question(self, self.T("donate_title"), self.T("donate_text"),
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            webbrowser.open("https://www.donationalerts.com/r/fleurdev")

    def check_for_updates(self):
        QMessageBox.information(self, self.T("update_title"), self.T("update_text"))

    def run_library_diagnostic(self):
        if not self.playlist_files:
            QMessageBox.warning(self, self.T("diag_title"), self.T("diag_empty_text"))
            return
        self.btn_diag.setEnabled(False)
        self.diag_progress = QProgressDialog(self.T("diag_title"), None, 0, 0, self)
        self.diag_progress.setWindowModality(Qt.WindowModal)
        try:
            self.diag_progress.setCancelButton(None)
        except Exception:
            pass
        self.diag_progress.show()
        self.diag_worker = DiagnosticWorker(self.playlist_files)
        self.diag_worker.done.connect(self.show_diagnostic_results)
        self.diag_worker.start()

    def show_diagnostic_results(self, result):
        if self.diag_progress:
            self.diag_progress.close()
            self.diag_progress = None
        self.btn_diag.setEnabled(True)
        if result.get("error"):
            QMessageBox.warning(self, self.T("diag_title"), f"Error: {result['error']}")
            return
        corrupted = result.get("corrupted", [])
        duplicates = result.get("duplicates", [])
        report = (self.T("diag_report_header") + "\n\n" +
                  self.T("diag_corrupted", n=len(corrupted)) + "\n" +
                  self.T("diag_duplicates", n=len(duplicates)))
        if corrupted:
            report += "\n\n" + "\n".join(corrupted[:5])
        if duplicates:
            report += "\n\n" + self.T("diag_recommend", list=", ".join(duplicates[:3]))
        QMessageBox.information(self, self.T("diag_title"), report)
        self.diag_worker = None

    def toggle_favorite_track(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.current_playlist):
            return
        track = self.current_playlist[row]
        if track in self.favorite_tracks:
            self.favorite_tracks.remove(track)
        else:
            self.favorite_tracks.append(track)
        self.save_favorites()
        self.load_music()

    def load_favorites(self):
        try:
            if os.path.exists(FAVS_FILE):
                with open(FAVS_FILE, "r", encoding="utf-8") as fp:
                    self.favorite_tracks = json.load(fp).get("tracks", [])
        except Exception as e:
            log.warning(f"Failed to load favorites: {e}")

    def save_favorites(self):
        try:
            with open(FAVS_FILE, "w", encoding="utf-8") as fp:
                json.dump({"tracks": self.favorite_tracks}, fp)
        except Exception as e:
            log.warning(f"Failed to save favorites: {e}")

    def load_statistics(self):
        try:
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                self.total_listen_time = data.get("time", 0)
                saved = data.get("theme", "Light macOS")
                saved = {"Светлая macOS": "Light macOS", "Тёмная macOS": "Dark macOS",
                         "Новогодняя": "New Year"}.get(saved, saved)
                QTimer.singleShot(150, lambda: self.apply_theme(saved))
        except Exception as e:
            log.warning(f"Failed to load statistics: {e}")

    def save_statistics(self):
        try:
            with open(STATS_FILE, "w", encoding="utf-8") as fp:
                json.dump({"time": self.total_listen_time, "theme": self.current_theme_name}, fp)
        except Exception as e:
            log.warning(f"Failed to save statistics: {e}")

    # ------------------------------------------------------------------
    def open_about_dialog(self):
        T = self.T
        dialog = QDialog(self)
        dialog.setWindowTitle(T("stats_title"))
        dialog.resize(500, 500)
        dialog.setStyleSheet(self.dialog_css())
        
        layout = QVBoxLayout(dialog)
        tabs = QTabWidget()
        
        # ----- TAB 1: Statistics -----
        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)
        
        total_minutes = int(self.total_listen_time) // 60
        hours = total_minutes // 60
        minutes = total_minutes % 60
        stats_layout.addWidget(QLabel(T("stats_total_time", h=hours, m=minutes)))
        stats_layout.addWidget(QLabel(T("stats_total_tracks", n=len(self.play_count))))
        
        stats_layout.addWidget(QLabel(T("stats_top_artists")))
        artist_counts = {}
        for track, count in self.play_count.items():
            meta = self.metadata_cache.get(track)
            artist = meta.get("artist", "Unknown")
            artist_counts[artist] = artist_counts.get(artist, 0) + count
        top_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        if top_artists:
            for artist, count in top_artists:
                stats_layout.addWidget(QLabel(f"  {artist}: {count} plays"))
        else:
            stats_layout.addWidget(QLabel(T("stats_no_data")))
        
        stats_layout.addWidget(QLabel(T("stats_most_skipped")))
        top_skipped = sorted(self.skip_count.items(), key=lambda x: x[1], reverse=True)[:10]
        if top_skipped:
            for track, count in top_skipped:
                stats_layout.addWidget(QLabel(f"  {self.display_name(track)}: {count} skips"))
        else:
            stats_layout.addWidget(QLabel(T("stats_no_data")))
        
        stats_layout.addStretch()
        tabs.addTab(stats_tab, "📊 Stats")
        
        # ----- TAB 2: Charts -----
        charts_tab = QWidget()
        charts_layout = QVBoxLayout(charts_tab)
        
        charts_layout.addWidget(QLabel(T("stats_week_chart")))
        if self.weekly_stats:
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            max_val = max(self.weekly_stats.values()) if self.weekly_stats else 1
            for day in days:
                count = self.weekly_stats.get(day, 0)
                bar = "█" * int(count / max_val * 30) if max_val > 0 else ""
                charts_layout.addWidget(QLabel(f"{day[:3]}: {bar} {count}"))
        else:
            charts_layout.addWidget(QLabel(T("stats_no_data")))
        
        charts_layout.addWidget(QLabel(T("stats_hour_chart")))
        if self.hourly_stats:
            max_val = max(self.hourly_stats.values()) if self.hourly_stats else 1
            for h in range(24):
                hour_str = str(h)
                count = self.hourly_stats.get(hour_str, 0)
                bar = "█" * int(count / max_val * 30) if max_val > 0 else ""
                charts_layout.addWidget(QLabel(f"{h:02d}:00 {bar} {count}"))
        else:
            charts_layout.addWidget(QLabel(T("stats_no_data")))
        
        charts_layout.addStretch()
        tabs.addTab(charts_tab, "📈 Charts")
        
        layout.addWidget(tabs)
        
        btn_export = QPushButton(T("stats_export_csv"))
        btn_export.clicked.connect(self.export_stats_csv)
        layout.addWidget(btn_export)
        
        btn_close = QPushButton(T("btn_close"))
        btn_close.clicked.connect(dialog.accept)
        layout.addWidget(btn_close)
        
        dialog.exec()

    def export_stats_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Statistics", "lazy_stats.csv", "CSV Files (*.csv)")
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Track", "Artist", "Plays", "Skips"])
                
                all_tracks = set(self.play_count.keys()) | set(self.skip_count.keys())
                for track in sorted(all_tracks):
                    meta = self.metadata_cache.get(track)
                    artist = meta.get("artist", "Unknown")
                    plays = self.play_count.get(track, 0)
                    skips = self.skip_count.get(track, 0)
                    writer.writerow([track, artist, plays, skips])
            
            QMessageBox.information(self, self.T("delete_success_title"), "✅ Statistics exported successfully!")
        except Exception as e:
            QMessageBox.critical(self, self.T("delete_error_title"), f"Failed to export: {e}")

    # ------------------------------------------------------------------
    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon.fromTheme("media-playback-start"))
        tray_menu = QMenu()
        self.tray_play_action = QAction(self.T("tray_play"), self); self.tray_play_action.triggered.connect(self.play_track)
        self.tray_pause_action = QAction(self.T("tray_pause"), self); self.tray_pause_action.triggered.connect(self.pause_track)
        self.tray_next_action = QAction(self.T("tray_next"), self); self.tray_next_action.triggered.connect(self.next_track)
        self.tray_exit_action = QAction(self.T("tray_exit"), self); self.tray_exit_action.triggered.connect(QApplication.instance().quit)
        for a in (self.tray_play_action, self.tray_pause_action, self.tray_next_action):
            tray_menu.addAction(a)
        tray_menu.addSeparator()
        tray_menu.addAction(self.tray_exit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip("LazyPleer v8.0")
        self.tray_icon.show()

    def set_sleep_timer(self, minutes):
        if not minutes:
            self.sleep_timer.stop()
            self.sleep_minutes_left = 0
            return
        self.sleep_minutes_left = int(minutes)
        self.sleep_timer.start(60000)
        QMessageBox.information(self, self.T("msg_sleep_title"), self.T("msg_sleep_text", m=minutes))

    def trigger_sleep(self):
        self.sleep_minutes_left -= 1
        if self.sleep_minutes_left <= 0:
            self.sleep_timer.stop()
            if self.settings.get("sleep_action", "pause") == "quit":
                QApplication.instance().quit()
            else:
                self.pause_track()
                self.sleep_minutes_left = 0

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        os.makedirs(MUSIC_DIR, exist_ok=True)
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith(('.mp3', '.wav', '.m4a', '.flac', '.ogg')):
                try:
                    shutil.copy(file_path, MUSIC_DIR)
                except Exception as e:
                    log.warning(f"Failed to copy {file_path}: {e}")
                    QMessageBox.warning(self, self.T("delete_error_title"), self.T("drop_error_text", e=e))
        self.load_music()

    # ------------------------------------------------------------------
    def load_playlists(self):
        os.makedirs(PLAYLISTS_DIR, exist_ok=True)
        self.playlists = {}
        try:
            for fname in os.listdir(PLAYLISTS_DIR):
                if not fname.endswith(".json"):
                    continue
                try:
                    with open(os.path.join(PLAYLISTS_DIR, fname), "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                    self.playlists[data.get("name") or fname[:-5]] = {"tracks": data.get("tracks", [])}
                except Exception as e:
                    log.warning(f"Failed to read playlist {fname}: {e}")
        except Exception as e:
            log.error(f"Failed to read playlists folder: {e}")
        current_data = self.playlist_selector.currentData() if hasattr(self, "playlist_selector") else None
        self.playlist_selector.blockSignals(True)
        self.playlist_selector.clear()
        self.playlist_selector.addItem(self.T("playlist_library"), None)
        for name in self.playlists:
            count = len(self.playlists[name]["tracks"])
            self.playlist_selector.addItem(f"{name} ({count} tracks)", name)
        self.playlist_selector.addItem(self.T("playlist_new"), "__new__")
        idx = self.playlist_selector.findData(current_data)
        self.playlist_selector.setCurrentIndex(idx if idx >= 0 else 0)
        self.playlist_selector.blockSignals(False)

    def save_playlist(self, name):
        try:
            os.makedirs(PLAYLISTS_DIR, exist_ok=True)
            path = os.path.join(PLAYLISTS_DIR, f"{resource_free_name(name)}.json")
            with open(path, "w", encoding="utf-8") as fp:
                json.dump({"name": name, "tracks": self.playlists[name]["tracks"]}, fp, ensure_ascii=False)
        except Exception as e:
            log.error(f"Failed to save playlist {name}: {e}")
            QMessageBox.warning(self, self.T("delete_error_title"), self.T("playlist_save_error_text", e=e))

    def on_playlist_changed(self, index):
        data = self.playlist_selector.itemData(index)
        if data == "__new__":
            name, ok = QInputDialog.getText(self, self.T("playlist_new_title"), self.T("playlist_new_prompt"))
            if ok and name.strip():
                name = name.strip()
                if name in self.playlists:
                    QMessageBox.warning(self, self.T("playlist_exists_title"), self.T("playlist_exists_text"))
                else:
                    self.playlists[name] = {"tracks": []}
                    self.save_playlist(name)
                    self.load_playlists()
                    idx = self.playlist_selector.findData(name)
                    self.playlist_selector.setCurrentIndex(idx if idx >= 0 else 0)
            else:
                self.playlist_selector.setCurrentIndex(0)
            return
        self.active_playlist = data
        self.load_music()

    def add_track_to_active_playlist(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.current_playlist):
            return
        track = self.current_playlist[row]
        target = self.active_playlist
        if target is None:
            names = list(self.playlists.keys())
            if not names:
                QMessageBox.information(self, self.T("playlist_none_title"), self.T("playlist_none_text"))
                return
            name, ok = QInputDialog.getItem(self, self.T("playlist_choose_title"), self.T("playlist_choose_prompt"), names, editable=False)
            if not ok:
                return
            target = name
        if track not in self.playlists[target]["tracks"]:
            self.playlists[target]["tracks"].append(track)
            self.save_playlist(target)
        QMessageBox.information(self, self.T("playlist_added_title"), self.T("playlist_added_text", p=target))
        self.load_playlists()
        self.update_playlist_counter()

    def remove_track_from_active_playlist(self):
        if self.active_playlist is None:
            QMessageBox.information(self, self.T("library_title"), self.T("library_no_remove"))
            return
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.current_playlist):
            return
        track = self.current_playlist[row]
        tracks = self.playlists[self.active_playlist]["tracks"]
        if track in tracks:
            tracks.remove(track)
            self.save_playlist(self.active_playlist)
            self.load_music()
            self.load_playlists()

    def delete_active_playlist(self):
        if self.active_playlist is None:
            QMessageBox.information(self, self.T("library_title"), self.T("library_no_delete"))
            return
        reply = QMessageBox.question(self, self.T("playlist_delete_confirm_title"),
                                     self.T("playlist_delete_confirm_text", p=self.active_playlist),
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        name = self.active_playlist
        try:
            path = os.path.join(PLAYLISTS_DIR, f"{resource_free_name(name)}.json")
            if os.path.exists(path):
                os.remove(path)
            self.playlists.pop(name, None)
        except Exception as e:
            log.error(f"Failed to delete playlist {name}: {e}")
        self.active_playlist = None
        self.load_playlists()
        self.load_music()

    # ------------------------------------------------------------------
    def load_music(self):
        os.makedirs(MUSIC_DIR, exist_ok=True)
        self.playlist_files = [f for f in os.listdir(MUSIC_DIR) if f.endswith(('.mp3', '.wav', '.m4a', '.flac', '.ogg'))]
        if hasattr(self, "counter_label"):
            self.counter_label.setText(self.T("counter_template", n=len(self.playlist_files)))
        self.metadata_cache.prune(self.playlist_files)
        self.filter_playlist()

    def on_music_dir_changed(self):
        if MUSIC_DIR not in self.fs_watcher.directories():
            self.fs_watcher.addPath(MUSIC_DIR)
        old = set(self.playlist_files)
        self.load_music()
        added = sorted(set(self.playlist_files) - old)
        if added and hasattr(self, "tray_icon") and self.tray_icon is not None:
            try:
                self.tray_icon.showMessage(
                    "LazyPleer",
                    self.T("library_new", list=", ".join(added[:3])),
                    QSystemTrayIcon.MessageIcon.Information, 2500)
            except Exception:
                pass

    def on_sort_changed(self, index):
        self.settings["sort"] = self.sort_selector.itemData(index) or "added"
        self.save_settings()
        self.filter_playlist()

    def toggle_play_mode(self):
        if self.play_mode == "Normal":
            self.play_mode = "Shuffle"; self.btn_mode.setText(self.T("mode_shuffle"))
        elif self.play_mode == "Shuffle":
            self.play_mode = "Repeat"; self.btn_mode.setText(self.T("mode_repeat"))
        else:
            self.play_mode = "Normal"; self.btn_mode.setText(self.T("mode_normal"))
        self.shuffle_bag = []

    def display_name(self, track):
        meta = self.metadata_cache.get(track)
        title, artist = meta.get("title", ""), meta.get("artist", "")
        if title and title != track and artist:
            return f"{artist} - {title}"
        if title and title != track:
            return title
        return os.path.splitext(track)[0]

    def filter_playlist(self):
        if not hasattr(self, "list_widget"):
            return
        search_text = self.search_input.text().lower().strip()
        filter_key = self.filter_selector.currentData() or "all"
        sort_mode = self.sort_selector.currentData() if hasattr(self, "sort_selector") else "added"

        if self.active_playlist is not None and self.active_playlist in self.playlists:
            base_files = [f for f in self.playlists[self.active_playlist]["tracks"] if f in self.playlist_files]
        else:
            base_files = self.playlist_files

        result = []
        for f in base_files:
            meta = self.metadata_cache.get(f)
            if search_text:
                hay = f"{f.lower()} {meta.get('title', '').lower()} {meta.get('artist', '').lower()}"
                if search_text not in hay:
                    continue
            if filter_key == "favorites" and f not in self.favorite_tracks:
                continue
            if filter_key == "year" and not meta.get("year"):
                continue
            result.append(f)

        if sort_mode == "title":
            result.sort(key=lambda f: self.display_name(f).lower())
        elif sort_mode == "artist":
            result.sort(key=lambda f: (self.metadata_cache.get(f).get("artist", "").lower(), self.display_name(f).lower()))
        elif sort_mode == "length":
            result.sort(key=lambda f: self.metadata_cache.get(f).get("duration", 0))

        current = self.current_upg_track
        self.current_playlist = result
        self.play_queue = []
        self.shuffle_bag = []
        
        self.list_widget.clear()
        for track in self.current_playlist:
            item = QListWidgetItem()
            prefix = "❤️ " if track in self.favorite_tracks else "🎵 "
            item.setText(f"{prefix}{self.display_name(track)}")
            pix = self.get_cover_pixmap(track, 32)
            if pix:
                item.setIcon(QIcon(pix))
            else:
                item.setIcon(QIcon())
                item.setText(f"💿 {item.text()}")
            self.list_widget.addItem(item)
            
        if current in self.current_playlist:
            self.list_widget.setCurrentRow(self.current_playlist.index(current))
        elif self.current_playlist:
            self.list_widget.setCurrentRow(0)
        self._fade(self.list_opacity)

    # ------------------------------------------------------------------
    def get_cover_pixmap(self, track, size):
        if not track:
            return None
        key = (track, int(size))
        if key in self._cover_cache:
            self._cover_cache.move_to_end(key)
            return self._cover_cache[key]
        pix = None
        try:
            path = os.path.join(MUSIC_DIR, track)
            if track.lower().endswith(".mp3"):
                audio = MP3(path, ID3=ID3)
                for k in audio.keys():
                    if str(k).startswith("APIC"):
                        p = QPixmap()
                        if p.loadFromData(audio[k].data):
                            pix = p.scaled(int(size), int(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            break
            elif track.lower().endswith(".flac"):
                audio = FLAC(path)
                if audio.pictures:
                    p = QPixmap()
                    if p.loadFromData(audio.pictures[0].data):
                        pix = p.scaled(int(size), int(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except Exception as e:
            log.debug(f"Failed to read cover {track}: {e}")
        if pix is not None:
            self._cover_cache[key] = pix
            self._cover_cache.move_to_end(key)
            while len(self._cover_cache) > 80:
                self._cover_cache.popitem(last=False)
        return pix

    def refresh_cover(self):
        track = self.current_upg_track
        if not track:
            self.cover_label.setText("💿")
            return
        pix = self.get_cover_pixmap(track, 48)
        if pix:
            self.cover_label.setText("")
            self.cover_label.setPixmap(pix)
        else:
            self.cover_label.setText("💿")

    # ------------------------------------------------------------------
    def show_track_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        row = self.list_widget.row(item)
        if row < 0 or row >= len(self.current_playlist):
            return
        track = self.current_playlist[row]
        menu = QMenu(self)
        menu.setStyleSheet(self.dialog_css())
        act_play = menu.addAction(self.T("ctx_play"))
        act_next = menu.addAction(self.T("ctx_play_next"))
        act_fav = menu.addAction(self.T("ctx_fav"))
        menu.addSeparator()
        act_export = menu.addAction("📤 Export to Spotify")
        chosen = menu.exec(self.list_widget.mapToGlobal(pos))
        if chosen == act_play:
            self.list_widget.setCurrentRow(row)
            self.play_track()
        elif chosen == act_next:
            self.play_queue.insert(0, track)
            QMessageBox.information(self, self.T("queue_title"), self.T("queue_added", t=self.display_name(track)))
        elif chosen == act_fav:
            self.list_widget.setCurrentRow(row)
            self.toggle_favorite_track()
        elif chosen == act_export:
            if self.active_playlist:
                self.export_to_spotify(self.active_playlist)
            else:
                QMessageBox.information(self, "Export", "Select a playlist first!")

    # ------------------------------------------------------------------
    def restore_last_session(self):
        last = self.settings.get("last_track", "")
        if not last:
            return
        if last in self.current_playlist:
            self.list_widget.setCurrentRow(self.current_playlist.index(last))
        self.current_upg_track = last
        self.update_screen(self.T("status_paused"))

    def restore_position(self, track):
        if not self.settings.get("restore_position", True) or not self.player:
            return
        pos = int(self.settings.get("positions", {}).get(track, 0))
        if pos <= 4000:
            return
        QTimer.singleShot(300, lambda: self.player.set_time(pos) if self.player else None)

    def play_track(self, track_name=None):
        if isinstance(track_name, bool):
            track_name = None
        if not self.player:
            return
        state = self.player.get_state()

        if track_name is None and state == vlc.State.Paused:
            self.player.play()
            self.update_screen(self.T("status_playing"))
            return
        if track_name is None and state == vlc.State.Playing:
            return

        if track_name is None:
            row = self.list_widget.currentRow()
            if row < 0 and self.current_playlist:
                row = 0
                self.list_widget.setCurrentRow(0)
            if row < 0 or row >= len(self.current_playlist):
                return
            track_name = self.current_playlist[row]
        else:
            if track_name in self.current_playlist:
                self.list_widget.setCurrentRow(self.current_playlist.index(track_name))

        track_path = os.path.abspath(os.path.join(MUSIC_DIR, track_name))
        if not os.path.exists(track_path):
            QMessageBox.critical(self, self.T("play_error_title"), self.T("play_error_text", e=track_path))
            return
        try:
            self._fade_out_active = False
            self.player.set_media(self.vlc_instance.media_new(track_path))
            self.player.play()
            if self.eq_available and not self.settings.get("eq_disabled", False):
                self.player.set_equalizer(self.equalizer)
            self.change_playback_speed(self.speed_slider.value())
            self.change_volume(self.vol_slider.value())
            self.current_upg_track = track_name
            self.settings["last_track"] = track_name
            self.update_screen(self.T("status_playing"))
            self.restore_position(track_name)
            self.track_played(track_name)
            if self.rpc:
                try:
                    self.rpc.update(details=self.display_name(track_name)[:120], state="LazyPleer v8.0")
                except Exception as e:
                    log.debug(f"Discord RPC update failed: {e}")
        except Exception as e:
            log.error(f"Failed to play {track_name}: {e}")
            QMessageBox.critical(self, self.T("play_error_title"), self.T("play_error_text", e=e))

    def play_selected(self, item):
        self.play_track()

    def pause_track(self):
        if self.player and self.player.is_playing():
            self.player.pause()
            self.update_screen(self.T("status_paused"))

    def refill_shuffle_bag(self):
        self.shuffle_bag = list(range(len(self.current_playlist)))
        row = self.list_widget.currentRow()
        if len(self.shuffle_bag) > 1 and row in self.shuffle_bag:
            self.shuffle_bag.remove(row)

    def next_track(self):
        if self.play_queue:
            self.play_track(self.play_queue.pop(0))
            return
        if not self.current_playlist:
            return
        current_track = self.current_upg_track
        if current_track and self.player and self.player.is_playing():
            self.track_skipped(current_track)
            
        if self.play_mode == "Shuffle":
            if not self.shuffle_bag:
                self.refill_shuffle_bag()
            next_row = self.shuffle_bag.pop(random.randrange(len(self.shuffle_bag))) if self.shuffle_bag else self.list_widget.currentRow()
        else:
            next_row = (self.list_widget.currentRow() + 1) % len(self.current_playlist)
        self.list_widget.setCurrentRow(next_row)
        self.play_track()

    def prev_track(self):
        if not self.current_playlist:
            return
        try:
            if self.player and self.player.get_time() > 3000:
                self.player.set_time(0)
                return
        except Exception:
            pass
        self.list_widget.setCurrentRow((self.list_widget.currentRow() - 1) % len(self.current_playlist))
        self.play_track()

    # ------------------------------------------------------------------
    def _hotkey_play_pause(self):
        if self.search_input.hasFocus():
            return
        self.toggle_play_pause()

    def _hotkey_seek(self, ms):
        if self.search_input.hasFocus():
            return
        self.seek_relative(ms)

    def seek_relative(self, ms):
        if not self.player:
            return
        try:
            new_time = max(0, self.player.get_time() + int(ms))
            self.player.set_time(new_time)
            if not self.is_slider_moving:
                pos = self.player.get_position()
                if pos >= 0:
                    self.progress_slider.setValue(int(pos * 1000))
        except Exception:
            pass

    def slider_pressed(self):
        self.is_slider_moving = True

    def slider_released(self):
        self.is_slider_moving = False
        if self.player:
            self.player.set_position(self.progress_slider.value() / 1000.0)

    def tick(self):
        if not self.player:
            return
        state = self.player.get_state()
        if state == vlc.State.Playing:
            self.total_listen_time += 0.5
            self._tick_count += 1
            self._position_tick += 1
            if self._tick_count % 20 == 0:
                self.save_statistics()
                self.save_settings()
            if self._position_tick % 10 == 0 and self.current_upg_track:
                try:
                    pos = self.player.get_time()
                    if pos > 0:
                        positions = self.settings.setdefault("positions", {})
                        positions[self.current_upg_track] = int(pos)
                        if len(positions) > 200:
                            for k in list(positions.keys())[:len(positions) - 200]:
                                positions.pop(k, None)
                except Exception:
                    pass
            if not self.is_slider_moving:
                pos = self.player.get_position()
                if pos >= 0:
                    self.progress_slider.setValue(int(pos * 1000))
            length_ms = self.player.get_length()
            pos_ms = self.player.get_time()
            pos_time = QTime(0, 0, 0).addMSecs(max(pos_ms, 0)).toString("mm:ss")
            dur_time = QTime(0, 0, 0).addMSecs(max(length_ms, 0)).toString("mm:ss")
            remaining = max(0, length_ms - pos_ms)
            remaining_time = QTime(0, 0, 0).addMSecs(remaining).toString("mm:ss")
            self.time_label.setText(f"{pos_time} / {dur_time} (-{remaining_time})")
            self.progress_slider.setToolTip(f"{pos_time} / {dur_time} (-{remaining_time})")

            crossfade = int(self.settings.get("crossfade", 0))
            if crossfade > 0 and length_ms > 0:
                remaining = length_ms - pos_ms
                if remaining <= crossfade * 1000:
                    base = int(self.settings.get("volume", self.vol_slider.value()))
                    try:
                        self.player.audio_set_volume(max(0, int(base * remaining / max(1, crossfade * 1000))))
                        self._fade_out_active = True
                    except Exception:
                        pass

        elif state == vlc.State.Ended:
            if self.play_mode == "Repeat":
                self.play_track(self.current_upg_track or None)
            else:
                self.next_track()
        else:
            if self.current_upg_track and not self.player.is_playing():
                length = self.player.get_length()
                pos = self.player.get_time()
                if length > 0 and pos > 0 and (length - pos) < 500:
                    self.player.stop()
                    self.next_track()

    def update_screen(self, status):
        track = self.current_upg_track
        if not track:
            row = self.list_widget.currentRow()
            if 0 <= row < len(self.current_playlist):
                track = self.current_playlist[row]
                self.current_upg_track = track
        if not track:
            self.screen_label.setText(self.T("screen_default"))
            self.cover_label.setText("💿")
            self.setWindowTitle("LazyPleer v8.0")
            return

        display = self.display_name(track)
        self.screen_label.setText(f"{display}\n({status})")
        icon = "▶" if status == self.T("status_playing") else "⏸"
        self.setWindowTitle(f"{icon} {display} — LazyPleer v8.0")

        self.refresh_cover()
        if hasattr(self, "tray_icon") and self.tray_icon is not None:
            self.tray_icon.setToolTip(f"LazyPleer v8.0: {display}")
            if status == self.T("status_playing") and track != self._last_notified_track:
                self._last_notified_track = track
                try:
                    self.tray_icon.showMessage("LazyPleer v8.0", display,
                                               QSystemTrayIcon.MessageIcon.Information, 2000)
                except Exception:
                    pass

        if self.mini_player:
            self.mini_player.refresh()
        self._fade(self.screen_opacity)

    # ------------------------------------------------------------------
    def delete_current_track(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.current_playlist):
            return
        track_name = self.current_playlist[row]
        track_path = os.path.abspath(os.path.join(MUSIC_DIR, track_name))
        if QMessageBox.question(self, self.T("delete_confirm_title"),
                                self.T("delete_confirm_text", t=track_name),
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        if self.player:
            self.player.stop()
        try:
            os.remove(track_path)
            for pl in self.playlists.values():
                if track_name in pl["tracks"]:
                    pl["tracks"].remove(track_name)
            for name in list(self.playlists.keys()):
                self.save_playlist(name)
            if track_name in self.favorite_tracks:
                self.favorite_tracks.remove(track_name)
                self.save_favorites()
            self.metadata_cache.invalidate(track_name)
            self.settings.get("positions", {}).pop(track_name, None)
            if self.settings.get("last_track") == track_name:
                self.settings["last_track"] = ""
                self.current_upg_track = ""
            self.save_settings()
            QMessageBox.information(self, self.T("delete_success_title"), self.T("delete_success_text"))
            self.load_music()
        except Exception as e:
            log.error(f"Failed to delete {track_name}: {e}")
            QMessageBox.critical(self, self.T("delete_error_title"), f"{e}")

    def open_metadata_editor(self):
        T = self.T
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.current_playlist):
            return
        track_name = self.current_playlist[row]
        track_path = os.path.abspath(os.path.join(MUSIC_DIR, track_name))
        if not track_name.lower().endswith(('.mp3', '.flac', '.ogg')):
            QMessageBox.warning(self, T("edit_tags_format_title"), "Only MP3, FLAC and OGG are supported!")
            return
        if self.player:
            self.player.stop()
        dialog = QDialog(self)
        dialog.setWindowTitle(T("edit_tags_title"))
        dialog.setFixedSize(360, 460)
        dialog.setStyleSheet(self.dialog_css())
        layout = QVBoxLayout(dialog)
        try:
            if track_name.lower().endswith(".mp3"):
                audio = MP3(track_path, ID3=ID3)
                t = str(audio.get('TIT2', '')); a = str(audio.get('TPE1', '')); y = str(audio.get('TYER', ''))
            elif track_name.lower().endswith(".flac"):
                audio = FLAC(track_path)
                t = str(audio.get('title', [''])[0]); a = str(audio.get('artist', [''])[0]); y = str(audio.get('date', [''])[0])[:4]
            elif track_name.lower().endswith(".ogg"):
                audio = OggVorbis(track_path)
                t = str(audio.get('title', [''])[0]); a = str(audio.get('artist', [''])[0]); y = str(audio.get('date', [''])[0])[:4]
            else:
                t, a, y = "", "", ""
        except Exception as e:
            log.warning(f"Failed to read tags {track_name}: {e}")
            t, a, y = "", "", ""
        layout.addWidget(QLabel(T("edit_tags_track_label"))); t_in = QLineEdit(t); layout.addWidget(t_in)
        layout.addWidget(QLabel(T("edit_tags_artist_label"))); a_in = QLineEdit(a); layout.addWidget(a_in)
        layout.addWidget(QLabel(T("edit_tags_year_label"))); y_in = QLineEdit(y); layout.addWidget(y_in)
        layout.addWidget(QLabel(T("edit_tags_cover_label")))
        preview_label = QLabel(); preview_label.setFixedSize(100, 100)
        preview_label.setStyleSheet("border: 1px dashed gray; background-color: rgba(0,0,0,0.05);")
        preview_label.setAlignment(Qt.AlignCenter)
        try:
            if hasattr(audio, 'pictures') and audio.pictures:
                pixmap = QPixmap(); pixmap.loadFromData(audio.pictures[0].data)
                preview_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            elif 'APIC:' in audio:
                pixmap = QPixmap(); pixmap.loadFromData(audio['APIC:'].data)
                preview_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                preview_label.setText(T("edit_tags_no_cover"))
        except Exception:
            preview_label.setText(T("edit_tags_load_error"))
        layout.addWidget(preview_label, alignment=Qt.AlignCenter)
        self.selected_cover_bin = None

        def choose_cover():
            file_path, _ = QFileDialog.getOpenFileName(dialog, T("choose_cover_dialog_title"), "", "Images (*.png *.jpg *.jpeg)")
            if file_path:
                with open(file_path, 'rb') as f:
                    self.selected_cover_bin = f.read()
                preview_label.setPixmap(QPixmap(file_path).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        btn_cover = QPushButton(T("edit_tags_load_btn")); btn_cover.clicked.connect(choose_cover); layout.addWidget(btn_cover)

        def save():
            try:
                if track_name.lower().endswith(".mp3"):
                    tags = ID3(track_path)
                    tags['TIT2'] = TIT2(encoding=3, text=t_in.text())
                    tags['TPE1'] = TPE1(encoding=3, text=a_in.text())
                    tags['TYER'] = TYER(encoding=3, text=y_in.text())
                    if self.selected_cover_bin:
                        tags['APIC'] = APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=self.selected_cover_bin)
                    tags.save(track_path)
                elif track_name.lower().endswith(".flac"):
                    audio = FLAC(track_path)
                    audio['title'] = t_in.text()
                    audio['artist'] = a_in.text()
                    audio['date'] = y_in.text()
                    if self.selected_cover_bin:
                        from mutagen.flac import Picture
                        pic = Picture()
                        pic.data = self.selected_cover_bin
                        pic.type = 3
                        pic.mime = 'image/jpeg'
                        audio.clear_pictures()
                        audio.add_picture(pic)
                    audio.save()
                elif track_name.lower().endswith(".ogg"):
                    audio = OggVorbis(track_path)
                    audio['title'] = t_in.text()
                    audio['artist'] = a_in.text()
                    audio['date'] = y_in.text()
                    audio.save()
                
                self.metadata_cache.invalidate(track_name)
                self.metadata_cache.prune(self.playlist_files)
                QMessageBox.information(dialog, T("delete_success_title"), T("edit_tags_success"))
            except Exception as e:
                log.error(f"Failed to save tags {track_name}: {e}")
                QMessageBox.critical(dialog, T("delete_error_title"), f"{e}")
            dialog.accept()

        btn = QPushButton(T("edit_tags_save_btn")); btn.clicked.connect(save); layout.addWidget(btn)
        dialog.exec()
        self.load_music()
        self.play_track(track_name)

    def update_eq_buttons_state(self):
        eq_disabled = self.settings.get("eq_disabled", False)
        disabled = eq_disabled or not self.eq_available
        self.btn_bass.setEnabled(not disabled)
        self.btn_eq.setEnabled(not disabled)
        if disabled:
            self.btn_bass.setToolTip("❌ Equalizer disabled in settings")
            self.btn_eq.setToolTip("❌ Equalizer disabled in settings")
        else:
            self.btn_bass.setToolTip(self.T("tooltip_bass"))
            self.btn_eq.setToolTip(self.T("tooltip_eq"))

    def dialog_css(self):
        dark = self.current_theme_name in ("Dark macOS", "Liquid Glass", "New Year", "Neon Sunset", "Aurora")
        bg = "#2D2D2D" if dark else "#F5F5F7"
        fg = "#FFFFFF" if dark else "#1D1D1F"
        input_bg = "#1E1E1E" if dark else "#FFFFFF"
        border = "#3A3A3C" if dark else "#D2D2D7"
        return (f"QDialog, QMessageBox, QMenu {{ background-color: {bg}; color: {fg}; }}"
                f"QLabel {{ color: {fg}; background: transparent; }}"
                f"QLineEdit {{ background-color: {input_bg}; color: {fg}; border: 1px solid {border}; border-radius: 6px; padding: 4px; }}"
                f"QComboBox {{ background-color: {input_bg}; color: {fg}; border: 1px solid {border}; border-radius: 6px; padding: 4px; }}"
                f"QComboBox QAbstractItemView {{ background-color: {bg}; color: {fg}; }}"
                f"QCheckBox {{ color: {fg}; }}"
                f"QPushButton {{ background-color: {input_bg}; color: {fg}; border: 1px solid {border}; border-radius: 6px; padding: 6px 12px; }}"
                f"QPushButton:hover {{ border-color: #7FE0FF; }}"
                f"QScrollArea {{ border: none; background: transparent; }}"
                f"QTabWidget::pane {{ border: 1px solid {border}; background: {bg}; }}"
                f"QTabBar::tab {{ background: {input_bg}; color: {fg}; padding: 6px 12px; }}"
                f"QTabBar::tab:selected {{ background: {bg}; border-bottom: 2px solid #7FE0FF; }}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon.fromTheme("media-playback-start"))
    player = LazyPleerV4()
    player.show()
    sys.exit(app.exec())