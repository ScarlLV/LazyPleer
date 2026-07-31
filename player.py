import os, sys, shutil, json, logging, webbrowser, random
from PySide6.QtCore import (QUrl, QTime, Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QLocale)
from PySide6.QtGui import QIcon, QAction, QPixmap, QColor
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QFileDialog,
    QListWidget, QPushButton, QVBoxLayout, QWidget, QSlider, QDialog, QLineEdit,
    QMessageBox, QComboBox, QSystemTrayIcon, QMenu, QInputDialog, QGraphicsOpacityEffect,
    QColorDialog)
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
# Все файлы (музыка, плейлисты, статистика, избранное, логи, язык) лежат
# РЯДОМ С ПРОГРАММОЙ, а не в "текущей папке запуска".
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

MUSIC_DIR = os.path.join(APP_DIR, "music")
PLAYLISTS_DIR = os.path.join(APP_DIR, "playlists")
STATS_FILE = os.path.join(APP_DIR, "lazy_stats.json")
FAVS_FILE = os.path.join(APP_DIR, "lazy_favs.json")
LANG_FILE = os.path.join(APP_DIR, "lazy_lang.json")
CUSTOM_COLORS_FILE = os.path.join(APP_DIR, "lazy_custom_colors.json")
LOG_FILE = os.path.join(APP_DIR, "lazy_pleer.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("LazyPleer")

# 10-полосный эквалайзер libvlc: индекс -> примерная центральная частота
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
# Локализация: 9 языков. Порядок в кортежах ниже строго соответствует LANGS.
# ---------------------------------------------------------------------------
LANGS = ["ru", "en", "uk", "be", "zh", "ja", "es", "de", "ar"]
RTL_LANGS = {"ar"}
LANG_NAMES = {
    "ru": "Русский", "en": "English", "uk": "Українська", "be": "Беларуская",
    "zh": "中文", "ja": "日本語", "es": "Español", "de": "Deutsch", "ar": "العربية",
}

STRINGS = {
    "app_title": ("LazyPleer",) * 9,
    "tooltip_mini": ("Компактный мини-плеер поверх окон", "Compact mini-player on top of windows", "Компактний міні-плеєр поверх вікон", "Кампактны міні-плэер паверх вокнаў", "紧凑型迷你播放器（置顶）", "コンパクトなミニプレーヤー（最前面表示）", "Reproductor compacto siempre visible", "Kompakter Mini-Player im Vordergrund", "مشغل مصغّر مضغوط فوق النوافذ"),
    "tooltip_share": ("Поделиться треком в X / Твиттер", "Share the track on X / Twitter", "Поділитися треком у X / Twitter", "Падзяліцца трэкам у X / Twitter", "在 X / 推特上分享曲目", "X（Twitter）でトラックをシェア", "Compartir la pista en X / Twitter", "Track auf X / Twitter teilen", "مشاركة المقطوعة على X / تويتر"),
    "tooltip_donate": ("Поддержать автора через DonationAlerts", "Support the author via DonationAlerts", "Підтримати автора через DonationAlerts", "Падтрымаць аўтара праз DonationAlerts", "通过 DonationAlerts 支持作者", "DonationAlerts で作者をサポート", "Apoyar al autor mediante DonationAlerts", "Autor über DonationAlerts unterstützen", "دعم المطوّر عبر DonationAlerts"),
    "tooltip_diag": ("Диагностика библиотеки (Поиск битых файлов и дубликатов)", "Library diagnostics (find corrupted files and duplicates)", "Діагностика бібліотеки (пошук пошкоджених файлів і дублікатів)", "Дыягностыка бібліятэкі (пошук пашкоджаных файлаў і дублікатаў)", "音乐库诊断（查找损坏文件和重复项）", "ライブラリ診断（破損ファイルと重複の検出）", "Diagnóstico de biblioteca (archivos dañados y duplicados)", "Bibliotheksdiagnose (beschädigte Dateien und Duplikate suchen)", "تشخيص المكتبة (البحث عن ملفات تالفة ومكررة)"),
    "tooltip_update": ("Проверить наличие обновлений", "Check for updates", "Перевірити наявність оновлень", "Праверыць наяўнасць абнаўленняў", "检查更新", "アップデートを確認", "Buscar actualizaciones", "Nach Updates suchen", "التحقق من وجود تحديثات"),
    "tooltip_settings": ("Настройки оформления и таймера плеера", "Theme and sleep timer settings", "Налаштування оформлення й таймера сну", "Налады афармлення і таймера сну", "外观与定时关闭设置", "テーマとスリープタイマーの設定", "Ajustes de tema y temporizador", "Design- und Timer-Einstellungen", "إعدادات المظهر ومؤقت السكون"),
    "screen_default": ("Не играет\nЗакиньте треки в папочку /music", "Not playing\nDrop tracks into the /music folder", "Не грає\nКиньте треки в папку /music", "Не грае\nКіньце трэкі ў папку /music", "未在播放\n将音乐文件放入 /music 文件夹", "再生していません\n/music フォルダに曲を追加してください", "Sin reproducir\nArrastra pistas a la carpeta /music", "Nichts spielt\nTracks in den Ordner /music legen", "لا يوجد تشغيل\nضع المقطوعات في مجلد /music"),
    "playlist_library": ("📚 Вся библиотека", "📚 Whole Library", "📚 Уся бібліотека", "📚 Уся бібліятэка", "📚 全部音乐库", "📚 ライブラリ全体", "📚 Toda la biblioteca", "📚 Gesamte Bibliothek", "📚 كل المكتبة"),
    "playlist_new": ("➕ Создать плейлист...", "➕ Create playlist...", "➕ Створити плейлист...", "➕ Стварыць плэйліст...", "➕ 新建播放列表...", "➕ プレイリストを作成...", "➕ Crear lista...", "➕ Playlist erstellen...", "➕ إنشاء قائمة تشغيل..."),
    "tooltip_pl_add": ("Добавить выбранный трек в текущий плейлист", "Add the selected track to the current playlist", "Додати обраний трек до поточного плейлиста", "Дадаць абраны трэк у бягучы плэйліст", "将所选曲目添加到当前播放列表", "選択した曲を現在のプレイリストに追加", "Añadir la pista seleccionada a la lista actual", "Ausgewählten Track zur aktuellen Playlist hinzufügen", "إضافة المقطوعة المحددة إلى قائمة التشغيل الحالية"),
    "tooltip_pl_remove": ("Убрать выбранный трек из текущего плейлиста", "Remove the selected track from the current playlist", "Прибрати обраний трек із поточного плейлиста", "Прыбраць абраны трэк з бягучага плэйліста", "从当前播放列表中移除所选曲目", "選択した曲を現在のプレイリストから削除", "Quitar la pista seleccionada de la lista actual", "Ausgewählten Track aus der aktuellen Playlist entfernen", "إزالة المقطوعة المحددة من قائمة التشغيل الحالية"),
    "tooltip_pl_delete": ("Удалить текущий плейлист", "Delete the current playlist", "Видалити поточний плейлист", "Выдаліць бягучы плэйліст", "删除当前播放列表", "現在のプレイリストを削除", "Eliminar la lista actual", "Aktuelle Playlist löschen", "حذف قائمة التشغيل الحالية"),
    "search_placeholder": ("🔍 Поиск по трекам или авторам на лету...", "🔍 Live search by track or artist...", "🔍 Пошук за треками чи виконавцями...", "🔍 Пошук па трэках ці выканаўцах...", "🔍 按曲目或歌手实时搜索...", "🔍 曲名やアーティストをリアルタイム検索...", "🔍 Buscar por pista o artista...", "🔍 Live-Suche nach Titel oder Interpret...", "🔍 بحث فوري حسب المقطوعة أو الفنان..."),
    "filter_all": ("Все треки", "All tracks", "Усі треки", "Усе трэкі", "全部曲目", "すべての曲", "Todas las pistas", "Alle Titel", "كل المقطوعات"),
    "filter_added": ("По добавлению", "By date added", "За додаванням", "Па даданні", "按添加顺序", "追加順", "Por fecha de añadido", "Nach Hinzufügedatum", "حسب تاريخ الإضافة"),
    "filter_year": ("По году", "By year", "За роком", "Па годзе", "按年份", "年別", "Por año", "Nach Jahr", "حسب السنة"),
    "filter_favorites": ("⭐ Избранное", "⭐ Favorites", "⭐ Обране", "⭐ Абранае", "⭐ 收藏", "⭐ お気に入り", "⭐ Favoritos", "⭐ Favoriten", "⭐ المفضلة"),
    "counter_template": ("Всего файлов в вашей библиотеке: {n}", "Total files in your library: {n}", "Усього файлів у бібліотеці: {n}", "Усяго файлаў у бібліятэцы: {n}", "音乐库中共有 {n} 个文件", "ライブラリ内の合計ファイル数: {n}", "Archivos totales en tu biblioteca: {n}", "Dateien insgesamt in deiner Bibliothek: {n}", "إجمالي الملفات في مكتبتك: {n}"),
    "bass_off": ("🔥 BassBoost: Выкл", "🔥 BassBoost: Off", "🔥 BassBoost: Викл", "🔥 BassBoost: Выкл", "🔥 低音增强: 关", "🔥 バスブースト: オフ", "🔥 Realce de graves: Apagado", "🔥 Bassverstärkung: Aus", "🔥 تعزيز الجهير: إيقاف"),
    "bass_on": ("🔥 BassBoost: Вкл", "🔥 BassBoost: On", "🔥 BassBoost: Увімк", "🔥 BassBoost: Укл", "🔥 低音增强: 开", "🔥 バスブースト: オン", "🔥 Realce de graves: Activado", "🔥 Bassverstärkung: An", "🔥 تعزيز الجهير: تشغيل"),
    "tooltip_bass": ("Быстрый пресет усиления баса", "Quick bass-boost preset", "Швидкий пресет підсилення басів", "Хуткі прэсет узмацнення басу", "快速低音增强预设", "素早いバスブーストプリセット", "Preajuste rápido de realce de graves", "Schnelle Bassverstärkung-Voreinstellung", "إعداد سريع لتعزيز الجهير"),
    "btn_eq": ("🎚 Эквалайзер", "🎚 Equalizer", "🎚 Еквалайзер", "🎚 Эквалайзер", "🎚 均衡器", "🎚 イコライザー", "🎚 Ecualizador", "🎚 Equalizer", "🎚 موازن الصوت"),
    "tooltip_eq": ("Полный 10-полосный эквалайзер с пресетами", "Full 10-band equalizer with presets", "Повний 10-смуговий еквалайзер із пресетами", "Поўны 10-паласны эквалайзер з прэсетамі", "完整的10段均衡器，带预设", "プリセット付きフル10バンドイコライザー", "Ecualizador completo de 10 bandas con preajustes", "Voller 10-Band-Equalizer mit Voreinstellungen", "موازن صوت كامل بعشرة نطاقات مع إعدادات مسبقة"),
    "speed_label": ("🏎 Скорость:", "🏎 Speed:", "🏎 Швидкість:", "🏎 Хуткасць:", "🏎 速度：", "🏎 速度：", "🏎 Velocidad:", "🏎 Geschwindigkeit:", "🏎 السرعة:"),
    "speed_normal": ("Текущая: 1.0x (Норма)", "Current: 1.0x (Normal)", "Поточна: 1.0x (Норма)", "Бягучая: 1.0x (Норма)", "当前：1.0x（正常）", "現在: 1.0x（標準）", "Actual: 1.0x (Normal)", "Aktuell: 1.0x (Normal)", "الحالية: 1.0x (عادي)"),
    "speed_current": ("Текущая: {x}x", "Current: {x}x", "Поточна: {x}x", "Бягучая: {x}x", "当前：{x}x", "現在: {x}x", "Actual: {x}x", "Aktuell: {x}x", "الحالية: {x}x"),
    "btn_edit_tags": ("📝 Редактор тегов", "📝 Tag editor", "📝 Редактор тегів", "📝 Рэдактар тэгаў", "📝 标签编辑器", "📝 タグエディター", "📝 Editor de etiquetas", "📝 Tag-Editor", "📝 محرر الوسوم"),
    "btn_delete": ("❌ Удалить", "❌ Delete", "❌ Видалити", "❌ Выдаліць", "❌ 删除", "❌ 削除", "❌ Eliminar", "❌ Löschen", "❌ حذف"),
    "btn_favorite": ("❤️ В Избранное", "❤️ Add to Favorites", "❤️ До обраного", "❤️ У Абранае", "❤️ 加入收藏", "❤️ お気に入りに追加", "❤️ Añadir a Favoritos", "❤️ Zu Favoriten", "❤️ إلى المفضلة"),
    "mode_normal": ("🔁 По порядку", "🔁 In order", "🔁 По порядку", "🔁 Па парадку", "🔁 顺序播放", "🔁 順番に再生", "🔁 En orden", "🔁 Der Reihe nach", "🔁 بالترتيب"),
    "mode_shuffle": ("🔀 Случайный", "🔀 Shuffle", "🔀 Випадковий", "🔀 Выпадковы", "🔀 随机播放", "🔀 シャッフル", "🔀 Aleatorio", "🔀 Zufällig", "🔀 عشوائي"),
    "mode_repeat": ("🔂 Повтор", "🔂 Repeat", "🔂 Повтор", "🔂 Паўтор", "🔂 单曲循环", "🔂 リピート", "🔂 Repetir", "🔂 Wiederholen", "🔂 تكرار"),
    "settings_title": ("Настройки плеера", "Player settings", "Налаштування плеєра", "Налады плэера", "播放器设置", "プレーヤー設定", "Ajustes del reproductor", "Player-Einstellungen", "إعدادات المشغل"),
    "settings_theme_label": ("<b>🎨 Выберите оформление:</b>", "<b>🎨 Choose a theme:</b>", "<b>🎨 Виберіть оформлення:</b>", "<b>🎨 Абярыце афармленне:</b>", "<b>🎨 选择主题：</b>", "<b>🎨 テーマを選択：</b>", "<b>🎨 Elige un tema:</b>", "<b>🎨 Design wählen:</b>", "<b>🎨 اختر المظهر:</b>"),
    "settings_sleep_label": ("<b>⏱️ Автовыключение (Таймер сна):</b>", "<b>⏱️ Auto-off (Sleep timer):</b>", "<b>⏱️ Автовимкнення (Таймер сну):</b>", "<b>⏱️ Аўтавыключэнне (Таймер сну):</b>", "<b>⏱️ 自动关闭（睡眠定时器）：</b>", "<b>⏱️ 自動オフ（スリープタイマー）：</b>", "<b>⏱️ Apagado automático (temporizador):</b>", "<b>⏱️ Auto-Aus (Sleep-Timer):</b>", "<b>⏱️ إيقاف تلقائي (مؤقت السكون):</b>"),
    "sleep_off": ("⏱️ Таймер отключен", "⏱️ Timer off", "⏱️ Таймер вимкнено", "⏱️ Таймер выключаны", "⏱️ 定时器已关闭", "⏱️ タイマーオフ", "⏱️ Temporizador apagado", "⏱️ Timer aus", "⏱️ المؤقت متوقف"),
    "sleep_15": ("15 мин", "15 min", "15 хв", "15 хв", "15 分钟", "15 分", "15 min", "15 Min", "15 دقيقة"),
    "sleep_30": ("30 мин", "30 min", "30 хв", "30 хв", "30 分钟", "30 分", "30 min", "30 Min", "30 دقيقة"),
    "sleep_60": ("60 мин", "60 min", "60 хв", "60 хв", "60 分钟", "60 分", "60 min", "60 Min", "60 دقيقة"),
    "settings_lang_label": ("<b>🌐 Язык приложения:</b>", "<b>🌐 App language:</b>", "<b>🌐 Мова застосунку:</b>", "<b>🌐 Мова праграмы:</b>", "<b>🌐 应用语言：</b>", "<b>🌐 アプリの言語：</b>", "<b>🌐 Idioma de la app:</b>", "<b>🌐 App-Sprache:</b>", "<b>🌐 لغة التطبيق:</b>"),
    "btn_apply_settings": ("Применить настройки", "Apply settings", "Застосувати налаштування", "Прымяніць налады", "应用设置", "設定を適用", "Aplicar ajustes", "Einstellungen anwenden", "تطبيق الإعدادات"),
    "msg_sleep_title": ("Таймер сна", "Sleep timer", "Таймер сну", "Таймер сну", "睡眠定时器", "スリープタイマー", "Temporizador", "Sleep-Timer", "مؤقت السكون"),
    "msg_sleep_text": ("Плеер закроется через {m} минут!", "The player will close in {m} minutes!", "Плеєр закриється через {m} хвилин!", "Плэер зачыніцца праз {m} хвілін!", "播放器将在 {m} 分钟后关闭！", "プレーヤーは{m}分後に終了します！", "¡El reproductor se cerrará en {m} minutos!", "Der Player schließt in {m} Minuten!", "سيُغلق المشغل خلال {m} دقيقة!"),
    "about_title": ("Статистика", "Statistics", "Статистика", "Статыстыка", "统计", "統計", "Estadísticas", "Statistik", "إحصائيات"),
    "about_listen_time": ("📊 Общее время прослушивания: {m} мин.", "📊 Total listening time: {m} min.", "📊 Загальний час прослуховування: {m} хв.", "📊 Агульны час праслухоўвання: {m} хв.", "📊 总收听时长：{m} 分钟", "📊 総再生時間: {m} 分", "📊 Tiempo total de escucha: {m} min.", "📊 Gesamte Hörzeit: {m} Min.", "📊 إجمالي وقت الاستماع: {m} دقيقة"),
    "btn_close": ("Закрыть", "Close", "Закрити", "Зачыніць", "关闭", "閉じる", "Cerrar", "Schließen", "إغلاق"),
    "eq_title": ("Эквалайзер", "Equalizer", "Еквалайзер", "Эквалайзер", "均衡器", "イコライザー", "Ecualizador", "Equalizer", "موازن الصوت"),
    "eq_preset_label": ("Пресет:", "Preset:", "Пресет:", "Прэсет:", "预设：", "プリセット：", "Preajuste:", "Voreinstellung:", "إعداد مسبق:"),
    "eq_preset_flat": ("Плоский (выкл)", "Flat (off)", "Плоский (викл)", "Плоскі (выкл)", "平坦（关闭）", "フラット（オフ）", "Plano (apagado)", "Flach (aus)", "مسطّح (إيقاف)"),
    "eq_preset_bass": ("Бас-буст", "Bass boost", "Бас-буст", "Бас-буст", "低音增强", "バスブースト", "Realce de graves", "Bassverstärkung", "تعزيز الجهير"),
    "eq_preset_vocal": ("Вокал", "Vocal", "Вокал", "Вакал", "人声", "ボーカル", "Voz", "Gesang", "الصوت الغنائي"),
    "eq_preset_rock": ("Рок", "Rock", "Рок", "Рок", "摇滚", "ロック", "Rock", "Rock", "روك"),
    "eq_preset_edm": ("Электроника", "Electronic", "Електроніка", "Электроніка", "电子", "エレクトロニック", "Electrónica", "Elektronisch", "إلكترونية"),
    "eq_preset_custom": ("Свой", "Custom", "Власний", "Свой", "自定义", "カスタム", "Personalizado", "Eigene", "مخصص"),
    "eq_save_btn": ("💾 Сохранить как 'Свой'", "💾 Save as 'Custom'", "💾 Зберегти як 'Власний'", "💾 Захаваць як 'Свой'", "💾 保存为“自定义”", "💾「カスタム」として保存", "💾 Guardar como 'Personalizado'", "💾 Als 'Eigene' speichern", "💾 حفظ كـ 'مخصص'"),
    "eq_saved_title": ("Сохранено", "Saved", "Збережено", "Захавана", "已保存", "保存しました", "Guardado", "Gespeichert", "تم الحفظ"),
    "eq_saved_text": ("Текущие настройки сохранены как пресет «Свой» (до перезапуска).", "Current settings saved as the 'Custom' preset (until restart).", "Поточні налаштування збережено як пресет «Власний» (до перезапуску).", "Бягучыя налады захаваны як прэсет «Свой» (да перазапуску).", "当前设置已保存为“自定义”预设（重启前有效）。", "現在の設定を「カスタム」プリセットとして保存しました（再起動まで有効）。", "Ajustes actuales guardados como preajuste 'Personalizado' (hasta reiniciar).", "Aktuelle Einstellungen als Voreinstellung 'Eigene' gespeichert (bis zum Neustart).", "تم حفظ الإعدادات الحالية كإعداد 'مخصص' (حتى إعادة التشغيل)."),
    "eq_unavailable_title": ("Эквалайзер недоступен", "Equalizer unavailable", "Еквалайзер недоступний", "Эквалайзер недаступны", "均衡器不可用", "イコライザーが利用できません", "Ecualizador no disponible", "Equalizer nicht verfügbar", "موازن الصوت غير متاح"),
    "eq_unavailable_text": ("Не найден рабочий эквалайзер VLC (ни AudioEqualizer, ни Equalizer).\n\nПроверь версию: pip show python-vlc, и версию VLC Player.", "No working VLC equalizer found (neither AudioEqualizer nor Equalizer).\n\nCheck version: pip show python-vlc, and your VLC Player version.", "Не знайдено робочого еквалайзера VLC (ні AudioEqualizer, ні Equalizer).\n\nПеревір версію: pip show python-vlc, і версію VLC Player.", "Не знойдзены працоўны эквалайзер VLC (ні AudioEqualizer, ні Equalizer).\n\nПраверце версію: pip show python-vlc, і версію VLC Player.", "未找到可用的 VLC 均衡器（AudioEqualizer 和 Equalizer 均不可用）。\n\n请检查版本：pip show python-vlc，以及 VLC Player 的版本。", "動作する VLC イコライザーが見つかりません（AudioEqualizer も Equalizer も不可）。\n\nバージョンを確認してください: pip show python-vlc、および VLC Player のバージョン。", "No se encontró un ecualizador VLC funcional (ni AudioEqualizer ni Equalizer).\n\nComprueba la versión: pip show python-vlc, y la versión de VLC Player.", "Kein funktionierender VLC-Equalizer gefunden (weder AudioEqualizer noch Equalizer).\n\nVersion prüfen: pip show python-vlc, und die VLC-Player-Version.", "لم يتم العثور على موازن صوت VLC يعمل (لا AudioEqualizer ولا Equalizer).\n\nتحقق من الإصدار: pip show python-vlc، وإصدار VLC Player."),
    "vlc_missing_title": ("VLC не найден", "VLC not found", "VLC не знайдено", "VLC не знойдзены", "未找到 VLC", "VLC が見つかりません", "VLC no encontrado", "VLC nicht gefunden", "لم يتم العثور على VLC"),
    "vlc_missing_text": ("Не найдена библиотека python-vlc или сам VLC Player.\n\n1) Установи VLC Player: https://www.videolan.org/vlc/\n2) pip install python-vlc\n\nБез этого плеер не сможет проигрывать музыку.", "The python-vlc library or VLC Player itself was not found.\n\n1) Install VLC Player: https://www.videolan.org/vlc/\n2) pip install python-vlc\n\nWithout this, the player won't be able to play music.", "Не знайдено бібліотеку python-vlc або сам VLC Player.\n\n1) Встанови VLC Player: https://www.videolan.org/vlc/\n2) pip install python-vlc\n\nБез цього плеєр не зможе відтворювати музику.", "Не знойдзена бібліятэка python-vlc або сам VLC Player.\n\n1) Устанаві VLC Player: https://www.videolan.org/vlc/\n2) pip install python-vlc\n\nБез гэтага плэер не зможа прайграваць музыку.", "未找到 python-vlc 库或 VLC Player 本身。\n\n1) 安装 VLC Player：https://www.videolan.org/vlc/\n2) pip install python-vlc\n\n没有它播放器将无法播放音乐。", "python-vlc ライブラリまたは VLC Player 自体が見つかりません。\n\n1) VLC Player をインストール: https://www.videolan.org/vlc/\n2) pip install python-vlc\n\nこれがないと音楽を再生できません。", "No se encontró la biblioteca python-vlc ni VLC Player.\n\n1) Instala VLC Player: https://www.videolan.org/vlc/\n2) pip install python-vlc\n\nSin esto, el reproductor no podrá reproducir música.", "Die Bibliothek python-vlc oder der VLC Player selbst wurde nicht gefunden.\n\n1) VLC Player installieren: https://www.videolan.org/vlc/\n2) pip install python-vlc\n\nOhne das kann der Player keine Musik abspielen.", "لم يتم العثور على مكتبة python-vlc أو مشغل VLC نفسه.\n\n1) ثبّت VLC Player: https://www.videolan.org/vlc/\n2) pip install python-vlc\n\nبدون ذلك لن يتمكن المشغل من تشغيل الموسيقى."),
    "playlist_new_title": ("Новый плейлист", "New playlist", "Новий плейлист", "Новы плэйліст", "新建播放列表", "新しいプレイリスト", "Nueva lista", "Neue Playlist", "قائمة تشغيل جديدة"),
    "playlist_new_prompt": ("Название плейлиста:", "Playlist name:", "Назва плейлиста:", "Назва плэйліста:", "播放列表名称：", "プレイリスト名：", "Nombre de la lista:", "Playlist-Name:", "اسم قائمة التشغيل:"),
    "playlist_exists_title": ("Уже есть", "Already exists", "Вже є", "Ужо ёсць", "已存在", "既に存在します", "Ya existe", "Bereits vorhanden", "موجودة بالفعل"),
    "playlist_exists_text": ("Плейлист с таким именем уже существует.", "A playlist with this name already exists.", "Плейлист із такою назвою вже існує.", "Плэйліст з такой назвай ужо існуе.", "已存在同名播放列表。", "同じ名前のプレイリストが既に存在します。", "Ya existe una lista con ese nombre.", "Eine Playlist mit diesem Namen existiert bereits.", "توجد قائمة تشغيل بهذا الاسم بالفعل."),
    "playlist_none_title": ("Нет плейлистов", "No playlists", "Немає плейлистів", "Няма плэйлістаў", "没有播放列表", "プレイリストがありません", "Sin listas", "Keine Playlists", "لا توجد قوائم تشغيل"),
    "playlist_none_text": ("Сначала создай плейлист через выпадающий список.", "Create a playlist first using the dropdown.", "Спочатку створи плейлист через випадний список.", "Спачатку стварыце плэйліст праз выпадальны спіс.", "请先通过下拉菜单创建播放列表。", "まずドロップダウンからプレイリストを作成してください。", "Primero crea una lista con el menú desplegable.", "Erstelle zuerst eine Playlist über das Dropdown-Menü.", "أنشئ قائمة تشغيل أولاً من القائمة المنسدلة."),
    "playlist_choose_title": ("Добавить в плейлист", "Add to playlist", "Додати до плейлиста", "Дадаць у плэйліст", "添加到播放列表", "プレイリストに追加", "Añadir a la lista", "Zur Playlist hinzufügen", "إضافة إلى قائمة التشغيل"),
    "playlist_choose_prompt": ("Выбери плейлист:", "Choose a playlist:", "Обери плейлист:", "Абярыце плэйліст:", "选择播放列表：", "プレイリストを選択：", "Elige una lista:", "Playlist auswählen:", "اختر قائمة تشغيل:"),
    "playlist_added_title": ("Готово", "Done", "Готово", "Гатова", "完成", "完了", "Hecho", "Fertig", "تم"),
    "playlist_added_text": ("Трек добавлен в «{p}»", 'Track added to "{p}"', "Трек додано до «{p}»", "Трэк дададзены ў «{p}»", "曲目已添加到「{p}」", "「{p}」に曲を追加しました", "Pista añadida a «{p}»", 'Track zu „{p}" hinzugefügt', "تمت إضافة المقطوعة إلى «{p}»"),
    "library_title": ("Библиотека", "Library", "Бібліотека", "Бібліятэка", "音乐库", "ライブラリ", "Biblioteca", "Bibliothek", "المكتبة"),
    "library_no_remove": ("Это вся библиотека, из неё нельзя «убрать» трек — только удалить файл.", 'This is the whole library — you can\'t "remove" a track, only delete the file.', "Це вся бібліотека, з неї не можна «прибрати» трек — тільки видалити файл.", "Гэта ўся бібліятэка, з яе нельга «прыбраць» трэк — толькі выдаліць файл.", "这是全部音乐库，无法从中“移除”曲目——只能删除文件。", "これはライブラリ全体です。曲を「削除」することはできず、ファイル自体を削除するしかありません。", 'Esta es toda la biblioteca — no puedes "quitar" una pista, solo eliminar el archivo.', 'Das ist die gesamte Bibliothek — ein Track kann nicht „entfernt" werden, nur die Datei gelöscht.', "هذه كل المكتبة، لا يمكن «إزالة» مقطوعة منها، بل حذف الملف فقط."),
    "library_no_delete": ("Библиотеку удалить нельзя — это все файлы из папки music.", "The library can't be deleted — it's just all files from the music folder.", "Бібліотеку не можна видалити — це всі файли з папки music.", "Бібліятэку нельга выдаліць — гэта ўсе файлы з папкі music.", "无法删除音乐库——它只是 music 文件夹中的全部文件。", "ライブラリは削除できません。music フォルダ内の全ファイルを指すだけです。", "No se puede eliminar la biblioteca — son todos los archivos de la carpeta music.", "Die Bibliothek kann nicht gelöscht werden — das sind alle Dateien im music-Ordner.", "لا يمكن حذف المكتبة، فهي كل الملفات الموجودة في مجلد music."),
    "playlist_delete_confirm_title": ("Удалить плейлист", "Delete playlist", "Видалити плейлист", "Выдаліць плэйліст", "删除播放列表", "プレイリストを削除", "Eliminar lista", "Playlist löschen", "حذف قائمة التشغيل"),
    "playlist_delete_confirm_text": ("Удалить плейлист «{p}»?", 'Delete playlist "{p}"?', "Видалити плейлист «{p}»?", "Выдаліць плэйліст «{p}»?", "删除播放列表「{p}」？", "プレイリスト「{p}」を削除しますか？", "¿Eliminar la lista «{p}»?", 'Playlist „{p}" löschen?', "هل تريد حذف قائمة التشغيل «{p}»؟"),
    "twitter_title": ("X / Twitter",) * 9,
    "twitter_copied": ("Готовый пост скопирован в буфер обмена!", "Ready-made post copied to clipboard!", "Готовий пост скопійовано в буфер обміну!", "Гатовы пост скапіраваны ў буфер абмену!", "帖子已复制到剪贴板！", "投稿をクリップボードにコピーしました！", "¡Publicación copiada al portapapeles!", "Fertiger Beitrag in die Zwischenablage kopiert!", "تم نسخ المنشور الجاهز إلى الحافظة!"),
    "twitter_share_text": ("Слушаю сочный трек '{t}' в плеере LazyPleer! Присоединяйтесь к чиллу! 🎧🔥", "Listening to the juicy track '{t}' on LazyPleer! Join the chill! 🎧🔥", "Слухаю соковитий трек '{t}' у плеєрі LazyPleer! Приєднуйтесь до чілу! 🎧🔥", "Слухаю сакавіты трэк '{t}' у плэеры LazyPleer! Далучайцеся да чылу! 🎧🔥", "正在 LazyPleer 中收听劲爆曲目 '{t}'！一起来放松吧！🎧🔥", "LazyPleer で '{t}' を再生中！一緒にチルしよう！🎧🔥", "¡Escuchando la pista '{t}' en LazyPleer! ¡Únete al chill! 🎧🔥", "Höre gerade den Track '{t}' in LazyPleer! Mach mit beim Chillen! 🎧🔥", "أستمع إلى المقطوعة الرائعة '{t}' على LazyPleer! انضم للاسترخاء! 🎧🔥"),
    "donate_title": ("Поддержка автора", "Support the author", "Підтримка автора", "Падтрымка аўтара", "支持作者", "作者を応援", "Apoyar al autor", "Autor unterstützen", "دعم المطوّر"),
    "donate_text": ("Перейти на страницу DonationAlerts?", "Open the DonationAlerts page?", "Перейти на сторінку DonationAlerts?", "Перайсці на старонку DonationAlerts?", "前往 DonationAlerts 页面？", "DonationAlerts のページを開きますか？", "¿Abrir la página de DonationAlerts?", "DonationAlerts-Seite öffnen?", "الانتقال إلى صفحة DonationAlerts؟"),
    "update_title": ("Обновления", "Updates", "Оновлення", "Абнаўленні", "更新", "アップデート", "Actualizaciones", "Updates", "التحديثات"),
    "update_text": ("Автопроверка обновлений пока не подключена — негде проверять (нет сервера/релизов). Текущая версия: LazyPleer v7.0.", "Automatic update checking isn't set up yet — there's nowhere to check (no server/releases). Current version: LazyPleer v7.0.", "Автоперевірка оновлень поки не підключена — нема де перевіряти (немає сервера/релізів). Поточна версія: LazyPleer v7.0.", "Аўтаправерка абнаўленняў пакуль не падключана — няма дзе правяраць (няма сервера/рэлізаў). Бягучая версія: LazyPleer v7.0.", "自动更新检查尚未启用——没有可检查的地方（无服务器/发布版本）。当前版本：LazyPleer v7.0。", "自動アップデート確認はまだ設定されていません（サーバー・リリースがありません）。現在のバージョン: LazyPleer v7.0。", "La comprobación automática de actualizaciones aún no está configurada. Versión actual: LazyPleer v7.0.", "Die automatische Update-Prüfung ist noch nicht eingerichtet. Aktuelle Version: LazyPleer v7.0.", "لم يتم تفعيل التحقق التلقائي من التحديثات بعد. الإصدار الحالي: LazyPleer v7.0."),
    "diag_title": ("Диагностика библиотеки", "Library diagnostics", "Діагностика бібліотеки", "Дыягностыка бібліятэкі", "音乐库诊断", "ライブラリ診断", "Diagnóstico de biblioteca", "Bibliotheksdiagnose", "تشخيص المكتبة"),
    "diag_empty_text": ("Папка с музыкой абсолютно пуста!", "The music folder is completely empty!", "Папка з музикою абсолютно порожня!", "Папка з музыкай абсалютна пустая!", "音乐文件夹完全为空！", "音楽フォルダは空です！", "¡La carpeta de música está completamente vacía!", "Der Musikordner ist völlig leer!", "مجلد الموسيقى فارغ تمامًا!"),
    "diag_report_header": ("📊 Сводный отчет диагностики библиотеки:", "📊 Library diagnostics summary:", "📊 Зведений звіт діагностики бібліотеки:", "📊 Зводная справаздача дыягностыкі бібліятэкі:", "📊 音乐库诊断汇总：", "📊 ライブラリ診断サマリー：", "📊 Resumen del diagnóstico de biblioteca:", "📊 Zusammenfassung der Bibliotheksdiagnose:", "📊 ملخص تشخيص المكتبة:"),
    "diag_corrupted": ("• Битых/Поврежденных файлов: {n}", "• Corrupted/broken files: {n}", "• Пошкоджених файлів: {n}", "• Пашкоджаных файлаў: {n}", "• 损坏文件数：{n}", "• 破損ファイル数: {n}", "• Archivos dañados: {n}", "• Beschädigte Dateien: {n}", "• الملفات التالفة: {n}"),
    "diag_duplicates": ("• Обнаружено дубликатов: {n}", "• Duplicates found: {n}", "• Знайдено дублікатів: {n}", "• Знойдзена дублікатаў: {n}", "• 发现重复项：{n}", "• 重複ファイル数: {n}", "• Duplicados encontrados: {n}", "• Gefundene Duplikate: {n}", "• الملفات المكررة: {n}"),
    "diag_recommend": ("Рекомендуется очистить: {list}", "Recommended to clean up: {list}", "Рекомендується очистити: {list}", "Рэкамендуецца ачысціць: {list}", "建议清理：{list}", "クリーンアップ推奨: {list}", "Se recomienda limpiar: {list}", "Empfohlen zum Aufräumen: {list}", "يُنصح بتنظيف: {list}"),
    "delete_confirm_title": ("Удаление", "Delete", "Видалення", "Выдаленне", "删除", "削除", "Eliminar", "Löschen", "حذف"),
    "delete_confirm_text": ("Удалить файл {t}?", "Delete file {t}?", "Видалити файл {t}?", "Выдаліць файл {t}?", "删除文件 {t}？", "ファイル {t} を削除しますか？", "¿Eliminar el archivo {t}?", "Datei {t} löschen?", "هل تريد حذف الملف {t}؟"),
    "delete_success_title": ("Успех", "Success", "Успіх", "Поспех", "成功", "成功", "Éxito", "Erfolg", "تم بنجاح"),
    "delete_success_text": ("Файл удален!", "File deleted!", "Файл видалено!", "Файл выдалены!", "文件已删除！", "ファイルを削除しました！", "¡Archivo eliminado!", "Datei gelöscht!", "تم حذف الملف!"),
    "delete_error_title": ("Ошибка", "Error", "Помилка", "Памылка", "错误", "エラー", "Error", "Fehler", "خطأ"),
    "edit_tags_title": ("Редактор тегов и Обложки", "Tag & Cover Editor", "Редактор тегів та обкладинки", "Рэдактар тэгаў і вокладкі", "标签与封面编辑器", "タグ・カバー編集", "Editor de etiquetas y portada", "Tag- & Cover-Editor", "محرر الوسوم والغلاف"),
    "edit_tags_track_label": ("Название трека:", "Track title:", "Назва треку:", "Назва трэка:", "曲目名称：", "曲名：", "Título de la pista:", "Titel:", "عنوان المقطوعة:"),
    "edit_tags_artist_label": ("Исполнитель:", "Artist:", "Виконавець:", "Выканаўца:", "艺术家：", "アーティスト：", "Artista:", "Interpret:", "الفنان:"),
    "edit_tags_year_label": ("Год выпуска:", "Release year:", "Рік випуску:", "Год выпуску:", "发行年份：", "リリース年：", "Año de lanzamiento:", "Erscheinungsjahr:", "سنة الإصدار:"),
    "edit_tags_cover_label": ("<b>🖼️ Текущая обложка альбома:</b>", "<b>🖼️ Current album cover:</b>", "<b>🖼️ Поточна обкладинка альбому:</b>", "<b>🖼️ Бягучая вокладка альбома:</b>", "<b>🖼️ 当前专辑封面：</b>", "<b>🖼️ 現在のアルバムカバー：</b>", "<b>🖼️ Portada actual:</b>", "<b>🖼️ Aktuelles Albumcover:</b>", "<b>🖼️ غلاف الألبوم الحالي:</b>"),
    "edit_tags_no_cover": ("Нет обложки", "No cover", "Немає обкладинки", "Няма вокладкі", "无封面", "カバーなし", "Sin portada", "Kein Cover", "لا يوجد غلاف"),
    "edit_tags_load_error": ("Ошибка загрузки", "Load error", "Помилка завантаження", "Памылка загрузкі", "加载错误", "読み込みエラー", "Error de carga", "Ladefehler", "خطأ في التحميل"),
    "edit_tags_load_btn": ("📂 Загрузить новую обложку (.jpg/.png)", "📂 Load new cover (.jpg/.png)", "📂 Завантажити нову обкладинку (.jpg/.png)", "📂 Загрузіць новую вокладку (.jpg/.png)", "📂 加载新封面 (.jpg/.png)", "📂 新しいカバーを読み込む (.jpg/.png)", "📂 Cargar nueva portada (.jpg/.png)", "📂 Neues Cover laden (.jpg/.png)", "📂 تحميل غلاف جديد (.jpg/.png)"),
    "edit_tags_save_btn": ("Сохранить изменения", "Save changes", "Зберегти зміни", "Захаваць змены", "保存更改", "変更を保存", "Guardar cambios", "Änderungen speichern", "حفظ التغييرات"),
    "edit_tags_only_mp3": ("Только MP3!", "MP3 only!", "Тільки MP3!", "Толькі MP3!", "仅支持 MP3！", "MP3 のみ対応！", "¡Solo MP3!", "Nur MP3!", "MP3 فقط!"),
    "edit_tags_format_title": ("Формат", "Format", "Формат", "Фармат", "格式", "フォーマット", "Formato", "Format", "الصيغة"),
    "edit_tags_success": ("Теги и обложка сохранены!", "Tags and cover saved!", "Теги та обкладинку збережено!", "Тэгі і вокладку захаваны!", "标签与封面已保存！", "タグとカバーを保存しました！", "¡Etiquetas y portada guardadas!", "Tags und Cover gespeichert!", "تم حفظ الوسوم والغلاف!"),
    "status_playing": ("Воспроизведение", "Playing", "Відтворення", "Прайграванне", "正在播放", "再生中", "Reproduciendo", "Wiedergabe", "قيد التشغيل"),
    "status_paused": ("Пауза", "Paused", "Пауза", "Паўза", "已暂停", "一時停止", "Pausado", "Pausiert", "إيقاف مؤقت"),
    "tray_play": ("▶ Старт", "▶ Play", "▶ Старт", "▶ Старт", "▶ 播放", "▶ 再生", "▶ Reproducir", "▶ Start", "▶ تشغيل"),
    "tray_pause": ("⏸ Пауза", "⏸ Pause", "⏸ Пауза", "⏸ Паўза", "⏸ 暂停", "⏸ 一時停止", "⏸ Pausa", "⏸ Pause", "⏸ إيقاف مؤقت"),
    "tray_next": ("⏭ Вперед", "⏭ Next", "⏭ Вперед", "⏭ Наперад", "⏭ 下一首", "⏭ 次へ", "⏭ Siguiente", "⏭ Weiter", "⏭ التالي"),
    "tray_exit": ("❌ Выход", "❌ Exit", "❌ Вихід", "❌ Выхад", "❌ 退出", "❌ 終了", "❌ Salir", "❌ Beenden", "❌ خروج"),
    "play_error_title": ("Ошибка воспроизведения", "Playback error", "Помилка відтворення", "Памылка прайгравання", "播放错误", "再生エラー", "Error de reproducción", "Wiedergabefehler", "خطأ في التشغيل"),
    "play_error_text": ("Не удалось открыть файл:\n{e}", "Failed to open the file:\n{e}", "Не вдалося відкрити файл:\n{e}", "Не ўдалося адкрыць файл:\n{e}", "无法打开文件：\n{e}", "ファイルを開けませんでした:\n{e}", "No se pudo abrir el archivo:\n{e}", "Datei konnte nicht geöffnet werden:\n{e}", "تعذر فتح الملف:\n{e}"),
    "playlist_save_error_text": ("Не удалось сохранить плейлист: {e}", "Failed to save the playlist: {e}", "Не вдалося зберегти плейлист: {e}", "Не ўдалося захаваць плэйліст: {e}", "保存播放列表失败：{e}", "プレイリストの保存に失敗しました: {e}", "No se pudo guardar la lista: {e}", "Playlist konnte nicht gespeichert werden: {e}", "تعذر حفظ قائمة التشغيل: {e}"),
    "drop_error_text": ("Не удалось добавить файл:\n{e}", "Failed to add file:\n{e}", "Не вдалося додати файл:\n{e}", "Не ўдалося дадаць файл:\n{e}", "添加文件失败：\n{e}", "ファイルの追加に失敗しました:\n{e}", "No se pudo añadir el archivo:\n{e}", "Datei konnte nicht hinzugefügt werden:\n{e}", "تعذرت إضافة الملف:\n{e}"),
    "choose_cover_dialog_title": ("Выбрать обложку", "Choose cover", "Обрати обкладинку", "Абраць вокладку", "选择封面", "カバーを選択", "Elegir portada", "Cover auswählen", "اختر الغلاف"),
    "tooltip_cinema": ("Режим кинотеатра (полноэкранный, только обложка и управление)", "Cinema mode (fullscreen, cover art and controls only)", "Режим кінотеатру (повноекранний, лише обкладинка й керування)", "Рэжым кінатэатра (поўнаэкранны, толькі вокладка і кіраванне)", "影院模式（全屏，仅显示封面与控制按钮）", "シアターモード（全画面、カバーと操作のみ）", "Modo cine (pantalla completa, solo portada y controles)", "Kinomodus (Vollbild, nur Cover und Steuerung)", "وضع السينما (ملء الشاشة، الغلاف وعناصر التحكم فقط)"),
    "tooltip_focus": ("Режим фокусировки (скрыть второстепенные элементы интерфейса)", "Focus mode (hide secondary interface elements)", "Режим фокусування (сховати другорядні елементи інтерфейсу)", "Рэжым фокусіроўкі (схаваць другарадныя элементы інтэрфейсу)", "专注模式（隐藏次要界面元素）", "フォーカスモード（副次的なUI要素を非表示）", "Modo enfoque (ocultar elementos secundarios)", "Fokusmodus (sekundäre Elemente ausblenden)", "وضع التركيز (إخفاء عناصر الواجهة الثانوية)"),
    "settings_custom_label": ("<b>🎨 Кастомизация интерфейса:</b>", "<b>🎨 Interface customization:</b>", "<b>🎨 Кастомізація інтерфейсу:</b>", "<b>🎨 Кастамізацыя інтэрфейсу:</b>", "<b>🎨 界面自定义：</b>", "<b>🎨 インターフェースのカスタマイズ：</b>", "<b>🎨 Personalización de interfaz:</b>", "<b>🎨 Oberflächenanpassung:</b>", "<b>🎨 تخصيص الواجهة:</b>"),
    "settings_accent_color_btn": ("🎨 Цвет акцента...", "🎨 Accent color...", "🎨 Колір акценту...", "🎨 Колер акцэнту...", "🎨 强调色...", "🎨 アクセントカラー...", "🎨 Color de acento...", "🎨 Akzentfarbe...", "🎨 لون التمييز..."),
    "settings_button_color_btn": ("🔘 Цвет кнопок...", "🔘 Button color...", "🔘 Колір кнопок...", "🔘 Колер кнопак...", "🔘 按钮颜色...", "🔘 ボタンの色...", "🔘 Color de botones...", "🔘 Schaltflächenfarbe...", "🔘 لون الأزرار..."),
    "settings_reset_colors_btn": ("↺ Сбросить цвета", "↺ Reset colors", "↺ Скинути кольори", "↺ Скінуць колеры", "↺ 重置颜色", "↺ 色をリセット", "↺ Restablecer colores", "↺ Farben zurücksetzen", "↺ إعادة تعيين الألوان"),
    "settings_audio_output_label": ("<b>🔊 Аудиовыход:</b>", "<b>🔊 Audio output:</b>", "<b>🔊 Аудіовихід:</b>", "<b>🔊 Аудыявыхад:</b>", "<b>🔊 音频输出：</b>", "<b>🔊 オーディオ出力：</b>", "<b>🔊 Salida de audio:</b>", "<b>🔊 Audioausgabe:</b>", "<b>🔊 مخرج الصوت:</b>"),
    "audio_output_default": ("Системное устройство по умолчанию", "System default device", "Системний пристрій за замовчуванням", "Сістэмная прылада па змаўчанні", "系统默认设备", "システムのデフォルトデバイス", "Dispositivo predeterminado del sistema", "Standard-Systemgerät", "جهاز النظام الافتراضي"),
    "audio_output_unavailable": ("Список устройств недоступен в этой версии VLC/системы", "Device list unavailable in this VLC/system version", "Список пристроїв недоступний у цій версії VLC/системи", "Спіс прылад недаступны ў гэтай версіі VLC/сістэмы", "此 VLC/系统版本无法获取设备列表", "このVLC/システムのバージョンではデバイス一覧を取得できません", "Lista de dispositivos no disponible en esta versión de VLC/sistema", "Geräteliste in dieser VLC-/Systemversion nicht verfügbar", "قائمة الأجهزة غير متاحة في هذا الإصدار من VLC/النظام"),
}

TRANSLATIONS = {lang: {key: vals[i] for key, vals in STRINGS.items()} for i, lang in enumerate(LANGS)}


def detect_default_language() -> str:
    """Пытается подхватить системный язык; если он не из списка поддерживаемых — английский."""
    try:
        sys_lang = QLocale.system().name()[:2].lower()
        if sys_lang in LANGS:
            return sys_lang
    except Exception as e:
        log.debug(f"Не удалось определить системный язык: {e}")
    return "en"


def resource_free_name(base_name: str) -> str:
    """Убирает символы, которые нельзя использовать в имени файла."""
    bad = '<>:"/\\|?*'
    return "".join(c for c in base_name if c not in bad).strip() or "untitled"


def enable_windows_blur(widget: QWidget):
    """
    Пытается включить настоящий блюр фона окна (эффект в духе macOS/Win11 Acrylic)
    через недокументированный DWM API. Работает только на Windows 10/11.
    На других ОС и в случае любой ошибки — тихо ничего не делает.
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes

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
        accent.GradientColor = 0x66222222
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
        self.title_lbl = QLabel(main_window.T("screen_default").split("\n")[0])
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
            freq_label = f"{freq}Hz" if freq < 1000 else f"{freq // 1000}k"
            col.addWidget(QLabel(freq_label), alignment=Qt.AlignCenter)
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
        key = self.preset_combo.itemData(index)
        gains = EQ_PRESET_VALUES.get(key)
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


class LazyPleerV4(QWidget):
    def __init__(self):
        super().__init__()
        self.current_language = self.load_language()

        self.setWindowTitle("LazyPleer v7.0")
        self.setMinimumSize(480, 720)
        self.resize(480, 720)
        self.setAcceptDrops(True)

        if not VLC_AVAILABLE:
            QMessageBox.critical(self, self.T("vlc_missing_title"), self.T("vlc_missing_text"))

        self.vlc_instance = vlc.Instance("--no-video") if VLC_AVAILABLE else None
        self.player = self.vlc_instance.media_player_new() if self.vlc_instance else None

        self.equalizer = None
        self.eq_available = False
        self.eq_gains = list(EQ_PRESET_VALUES["eq_preset_flat"])
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
        self.custom_accent_color = None
        self.custom_button_color = None
        self.load_custom_colors()
        self.cinema_mode = False
        self.focus_mode = False

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
                # ЗАМЕНИ на свой Application ID с https://discord.com/developers/applications
                # (создай там своё приложение — без этого Rich Presence не подключится)
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
        self.apply_layout_direction()
        self.retranslate_ui()

    # ------------------------------------------------------------------
    # Локализация
    # ------------------------------------------------------------------
    def T(self, key, **kwargs):
        """Возвращает переведённую строку по ключу для текущего языка."""
        text = TRANSLATIONS.get(self.current_language, {}).get(key)
        if text is None:
            text = TRANSLATIONS["en"].get(key, key)
        if kwargs:
            try:
                text = text.format(**kwargs)
            except Exception:
                pass
        return text

    def load_language(self):
        try:
            if os.path.exists(LANG_FILE):
                with open(LANG_FILE, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                lang = data.get("lang")
                if lang in LANGS:
                    return lang
        except Exception as e:
            log.warning(f"Не удалось загрузить язык: {e}")
        return detect_default_language()

    def save_language(self):
        try:
            with open(LANG_FILE, "w", encoding="utf-8") as fp:
                json.dump({"lang": self.current_language}, fp)
        except Exception as e:
            log.warning(f"Не удалось сохранить язык: {e}")

    # ------------------------------------------------------------------
    # Кастомизация цветов интерфейса (поверх выбранной темы)
    # ------------------------------------------------------------------
    def load_custom_colors(self):
        try:
            if os.path.exists(CUSTOM_COLORS_FILE):
                with open(CUSTOM_COLORS_FILE, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                self.custom_accent_color = data.get("accent")
                self.custom_button_color = data.get("button")
        except Exception as e:
            log.warning(f"Не удалось загрузить кастомные цвета: {e}")

    def save_custom_colors(self):
        try:
            with open(CUSTOM_COLORS_FILE, "w", encoding="utf-8") as fp:
                json.dump({"accent": self.custom_accent_color, "button": self.custom_button_color}, fp)
        except Exception as e:
            log.warning(f"Не удалось сохранить кастомные цвета: {e}")

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

    def apply_layout_direction(self):
        rtl = self.current_language in RTL_LANGS
        self.setLayoutDirection(Qt.RightToLeft if rtl else Qt.LeftToRight)

    def change_language(self, lang_code):
        if lang_code not in LANGS or lang_code == self.current_language:
            return
        self.current_language = lang_code
        self.save_language()
        self.apply_layout_direction()
        self.retranslate_ui()

    def retranslate_ui(self):
        """Обновляет текст всех постоянных виджетов главного окна под текущий язык."""
        T = self.T
        self.btn_mini.setToolTip(T("tooltip_mini"))
        self.btn_cinema.setToolTip(T("tooltip_cinema"))
        self.btn_focus.setToolTip(T("tooltip_focus"))
        self.btn_share_x.setToolTip(T("tooltip_share"))
        self.btn_donate.setToolTip(T("tooltip_donate"))
        self.btn_diag.setToolTip(T("tooltip_diag"))
        self.btn_check_update.setToolTip(T("tooltip_update"))
        self.btn_settings.setToolTip(T("tooltip_settings"))

        if self.list_widget.count() == 0 or self.list_widget.currentRow() < 0:
            self.screen_label.setText(T("screen_default"))

        # плейлисты: переводим фиксированные пункты, сохраняя выбор
        current_data = self.playlist_selector.currentData()
        self.playlist_selector.blockSignals(True)
        self.playlist_selector.setItemText(0, T("playlist_library"))
        last_index = self.playlist_selector.count() - 1
        self.playlist_selector.setItemText(last_index, T("playlist_new"))
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

        # трей
        self.tray_play_action.setText(T("tray_play"))
        self.tray_pause_action.setText(T("tray_pause"))
        self.tray_next_action.setText(T("tray_next"))
        self.tray_exit_action.setText(T("tray_exit"))

        self.filter_playlist()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def init_ui(self):
        T = self.T
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
        self.btn_mini.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 13px; }")
        self.btn_mini.clicked.connect(self.open_mini_player)
        header_layout.addWidget(self.btn_mini)

        self.btn_cinema = QPushButton("🎬")
        self.btn_cinema.setFixedSize(26, 26)
        self.btn_cinema.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 13px; }")
        self.btn_cinema.clicked.connect(self.toggle_cinema_mode)
        header_layout.addWidget(self.btn_cinema)

        self.btn_focus = QPushButton("🎯")
        self.btn_focus.setFixedSize(26, 26)
        self.btn_focus.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 13px; }")
        self.btn_focus.clicked.connect(self.toggle_focus_mode)
        header_layout.addWidget(self.btn_focus)

        self.btn_share_x = QPushButton("🐦")
        self.btn_share_x.setFixedSize(26, 26)
        self.btn_share_x.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 13px; }")
        self.btn_share_x.clicked.connect(self.share_on_twitter)
        header_layout.addWidget(self.btn_share_x)

        self.btn_donate = QPushButton("💰")
        self.btn_donate.setFixedSize(26, 26)
        self.btn_donate.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 13px; }")
        self.btn_donate.clicked.connect(self.support_author)
        header_layout.addWidget(self.btn_donate)

        self.btn_diag = QPushButton("🛡️")
        self.btn_diag.setFixedSize(26, 26)
        self.btn_diag.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 13px; }")
        self.btn_diag.clicked.connect(self.run_library_diagnostic)
        header_layout.addWidget(self.btn_diag)

        self.btn_check_update = QPushButton("🔄")
        self.btn_check_update.setFixedSize(26, 26)
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
        self.screen_label = QLabel(T("screen_default"))
        self.time_label = QLabel("00:00 / 00:00")
        text_screen_layout.addWidget(self.screen_label)
        text_screen_layout.addWidget(self.time_label)
        self.screen_layout.addLayout(text_screen_layout)
        self.main_layout.addWidget(self.screen_frame)

        self.screen_opacity = QGraphicsOpacityEffect(self.screen_frame)
        self.screen_frame.setGraphicsEffect(self.screen_opacity)
        self.screen_opacity.setOpacity(1.0)

        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.sliderPressed.connect(self.slider_pressed)
        self.progress_slider.sliderReleased.connect(self.slider_released)
        self.main_layout.addWidget(self.progress_slider)

        # --- строка плейлистов (используем currentData, не текст — независимо от языка) ---
        playlist_row = QHBoxLayout()
        self.playlist_selector = QComboBox()
        self.playlist_selector.addItem(T("playlist_library"), None)
        self.playlist_selector.addItem(T("playlist_new"), "__new__")
        self.playlist_selector.currentIndexChanged.connect(self.on_playlist_changed)
        playlist_row.addWidget(self.playlist_selector, stretch=1)

        self.btn_pl_add = QPushButton("➕")
        self.btn_pl_add.setFixedWidth(30)
        self.btn_pl_add.clicked.connect(self.add_track_to_active_playlist)
        playlist_row.addWidget(self.btn_pl_add)

        self.btn_pl_remove = QPushButton("➖")
        self.btn_pl_remove.setFixedWidth(30)
        self.btn_pl_remove.clicked.connect(self.remove_track_from_active_playlist)
        playlist_row.addWidget(self.btn_pl_remove)

        self.btn_pl_delete = QPushButton("🗑")
        self.btn_pl_delete.setFixedWidth(30)
        self.btn_pl_delete.clicked.connect(self.delete_active_playlist)
        playlist_row.addWidget(self.btn_pl_delete)
        self.main_layout.addLayout(playlist_row)

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
        self.main_layout.addLayout(filter_bar_layout)

        self.counter_label = QLabel(T("counter_template", n=0))
        self.counter_label.setStyleSheet("font-size: 11px; font-weight: 500;")
        self.main_layout.addWidget(self.counter_label)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.play_selected)
        self.main_layout.addWidget(self.list_widget)

        self.list_opacity = QGraphicsOpacityEffect(self.list_widget)
        self.list_widget.setGraphicsEffect(self.list_opacity)
        self.list_opacity.setOpacity(1.0)

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

        meta_layout = QHBoxLayout()
        self.btn_edit = QPushButton(T("btn_edit_tags"))
        self.btn_edit.clicked.connect(self.open_metadata_editor)
        meta_layout.addWidget(self.btn_edit)

        self.btn_delete = QPushButton(T("btn_delete"))
        self.btn_delete.clicked.connect(self.delete_current_track)
        meta_layout.addWidget(self.btn_delete)

        self.btn_fav = QPushButton(T("btn_favorite"))
        self.btn_fav.clicked.connect(self.toggle_favorite_track)
        meta_layout.addWidget(self.btn_fav)
        meta_layout.addStretch()

        self.btn_mode = QPushButton(T("mode_normal"))
        self.btn_mode.clicked.connect(self.toggle_play_mode)
        meta_layout.addWidget(self.btn_mode)
        self.main_layout.addLayout(meta_layout)

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

        # Виджеты, скрываемые в режиме фокусировки (второстепенные элементы)
        self.focus_hide_widgets = [
            self.btn_share_x, self.btn_donate, self.btn_diag, self.btn_check_update,
            self.search_input, self.filter_selector, self.playlist_selector,
            self.btn_pl_add, self.btn_pl_remove, self.btn_pl_delete, self.counter_label,
        ]
        # Режим кинотеатра скрывает всё, кроме обложки/названия/прогресса/громкости/управления
        self.cinema_hide_widgets = self.focus_hide_widgets + [
            self.list_widget, self.btn_bass, self.btn_eq, self.speed_label_widget,
            self.speed_slider, self.speed_indicator_label, self.btn_edit, self.btn_delete,
            self.btn_fav, self.btn_mode, self.btn_mini, self.btn_info, self.btn_settings,
        ]

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

        current_data = self.playlist_selector.currentData() if hasattr(self, "playlist_selector") else None
        self.playlist_selector.blockSignals(True)
        self.playlist_selector.clear()
        self.playlist_selector.addItem(self.T("playlist_library"), None)
        for name in self.playlists:
            self.playlist_selector.addItem(name, name)
        self.playlist_selector.addItem(self.T("playlist_new"), "__new__")
        idx = self.playlist_selector.findData(current_data)
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
                return
            else:
                self.playlist_selector.setCurrentIndex(0)
                return

        self.active_playlist = data  # None = библиотека, иначе имя плейлиста
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
            safe_name = resource_free_name(name)
            path = os.path.join(PLAYLISTS_DIR, f"{safe_name}.json")
            if os.path.exists(path):
                os.remove(path)
            self.playlists.pop(name, None)
        except Exception as e:
            log.error(f"Не удалось удалить плейлист {name}: {e}")
        self.active_playlist = None
        self.load_playlists()
        self.load_music()

    # ------------------------------------------------------------------
    # Настройки / темы
    # ------------------------------------------------------------------
    def open_settings_dialog(self):
        T = self.T
        dialog = QDialog(self)
        dialog.setWindowTitle(T("settings_title"))
        dialog.setFixedSize(340, 520)

        if self.current_theme_name in ("Liquid Glass", "Тёмная macOS"):
            dialog.setStyleSheet("background-color: #2D2D2D; color: white; QComboBox { color: black; background: white; }")
        else:
            dialog.setStyleSheet("background-color: #F5F5F7; color: #1D1D1F; QComboBox { color: black; background: white; }")

        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel(T("settings_theme_label")))
        theme_combo = QComboBox()
        theme_combo.addItems(list(self.themes.keys()))
        theme_combo.setCurrentText(self.current_theme_name)
        layout.addWidget(theme_combo)

        layout.addWidget(QLabel(T("settings_lang_label")))
        lang_combo = QComboBox()
        for code in LANGS:
            lang_combo.addItem(LANG_NAMES[code], code)
        idx = lang_combo.findData(self.current_language)
        lang_combo.setCurrentIndex(idx if idx >= 0 else 0)
        layout.addWidget(lang_combo)

        layout.addWidget(QLabel(T("settings_sleep_label")))
        sleep_combo = QComboBox()
        sleep_combo.addItem(T("sleep_off"), 0)
        sleep_combo.addItem(T("sleep_15"), 15)
        sleep_combo.addItem(T("sleep_30"), 30)
        sleep_combo.addItem(T("sleep_60"), 60)
        if self.sleep_minutes_left > 0:
            idx2 = sleep_combo.findData(self.sleep_minutes_left)
            if idx2 >= 0:
                sleep_combo.setCurrentIndex(idx2)
        layout.addWidget(sleep_combo)

        # --- Кастомизация интерфейса (применяется сразу, отдельно от темы) ---
        layout.addWidget(QLabel(T("settings_custom_label")))
        color_row = QHBoxLayout()
        btn_accent = QPushButton(T("settings_accent_color_btn"))
        btn_accent.clicked.connect(self.pick_accent_color)
        color_row.addWidget(btn_accent)
        btn_button_color = QPushButton(T("settings_button_color_btn"))
        btn_button_color.clicked.connect(self.pick_button_color)
        color_row.addWidget(btn_button_color)
        layout.addLayout(color_row)
        btn_reset_colors = QPushButton(T("settings_reset_colors_btn"))
        btn_reset_colors.clicked.connect(self.reset_custom_colors)
        layout.addWidget(btn_reset_colors)

        # --- Аудиовыход (применяется сразу при выборе) ---
        layout.addWidget(QLabel(T("settings_audio_output_label")))
        audio_combo = QComboBox()
        audio_combo.addItem(T("audio_output_default"), None)
        devices = self.enumerate_audio_devices()
        if not devices:
            audio_combo.addItem(T("audio_output_unavailable"), "__unavailable__")
        else:
            for device_id, description in devices:
                audio_combo.addItem(description, device_id)

        def on_audio_device_changed(idx):
            data = audio_combo.itemData(idx)
            if data not in (None, "__unavailable__"):
                self.set_audio_output_device(data)
        audio_combo.currentIndexChanged.connect(on_audio_device_changed)
        layout.addWidget(audio_combo)

        layout.addSpacing(10)
        btn_save = QPushButton(T("btn_apply_settings"))
        btn_save.clicked.connect(lambda: self.save_settings_action(
            dialog, theme_combo.currentText(), lang_combo.currentData(), sleep_combo.currentData()))
        layout.addWidget(btn_save)
        dialog.exec()

    def save_settings_action(self, dialog, selected_theme, selected_lang, selected_sleep_minutes):
        self.change_language(selected_lang)
        self.apply_theme(selected_theme)
        self.set_sleep_timer(selected_sleep_minutes)
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

        # Кастомные цвета поверх темы (если заданы в настройках)
        if self.custom_accent_color:
            accent_override = (
                f" QSlider::sub-page:horizontal {{ background: {self.custom_accent_color}; }} "
                f"QSlider::handle:horizontal {{ border-color: {self.custom_accent_color}; }}"
            )
            self.progress_slider.setStyleSheet(style["slider"] + accent_override)
            self.vol_slider.setStyleSheet(style["slider"] + accent_override)

        if self.custom_button_color:
            btn_override = f" QPushButton {{ background-color: {self.custom_button_color}; }}"
            for b in (self.btn_edit, self.btn_delete, self.btn_fav, self.btn_mode, self.btn_bass, self.btn_eq):
                b.setStyleSheet(style["btn_edit"] + btn_override)

        if style.get("blur"):
            ok = enable_windows_blur(self)
            if not ok:
                log.info("Настоящий блюр не включился — тема останется полупрозрачной без размытия.")

        self.load_music()

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
        self._active_anim = anim

    # ------------------------------------------------------------------
    # Аудио-эффекты (реальные, через libvlc equalizer)
    # ------------------------------------------------------------------
    def change_playback_speed(self, value):
        speed = value / 10.0
        if self.player:
            self.player.set_rate(speed)
        self.speed_indicator_label.setText(
            self.T("speed_normal") if speed == 1.0 else self.T("speed_current", x=speed)
        )

    def apply_eq_gains(self, gains):
        self.eq_gains = gains
        if not (self.eq_available and self.player and self.equalizer):
            return
        for i, val in enumerate(gains):
            self.equalizer.set_amp_at_index(float(val), i)
        self.player.set_equalizer(self.equalizer)
        self.is_bass_boost = gains == EQ_PRESET_VALUES["eq_preset_bass"]
        self.btn_bass.setText(self.T("bass_on") if self.is_bass_boost else self.T("bass_off"))

    def open_equalizer_dialog(self):
        if not (self.eq_available and self.player and self.equalizer):
            QMessageBox.warning(self, self.T("eq_unavailable_title"), self.T("eq_unavailable_text"))
            return
        dialog = EqualizerDialog(self, self.eq_gains, self.apply_eq_gains, self.save_custom_eq_preset)
        dialog.exec()

    def save_custom_eq_preset(self, gains):
        EQ_PRESET_VALUES[EQ_PRESET_CUSTOM_KEY] = gains
        QMessageBox.information(self, self.T("eq_saved_title"), self.T("eq_saved_text"))

    def toggle_bass_boost(self):
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
        self.vol_icon.setText("⚡🚀" if value > 100 else "🔊")

    # ------------------------------------------------------------------
    # Аудиовыход (наушники / колонки / другие устройства)
    # ------------------------------------------------------------------
    def enumerate_audio_devices(self):
        """Возвращает список (device_id, description). Пустой список — если недоступно."""
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
            log.warning(f"Не удалось получить список аудио-устройств: {e}")
            return []
        return devices

    def set_audio_output_device(self, device_id):
        if not (self.player and device_id):
            return
        try:
            # Сигнатура отличается между версиями python-vlc: пробуем оба варианта.
            try:
                self.player.audio_output_device_set(None, device_id)
            except TypeError:
                self.player.audio_output_device_set(device_id)
        except Exception as e:
            log.warning(f"Не удалось переключить аудиовыход на {device_id}: {e}")

    # ------------------------------------------------------------------
    # Режим кинотеатра / режим фокусировки
    # ------------------------------------------------------------------
    def toggle_cinema_mode(self):
        self.cinema_mode = not self.cinema_mode
        for w in self.cinema_hide_widgets:
            w.setVisible(not self.cinema_mode)
        if self.cinema_mode:
            self.cover_label.setFixedSize(160, 160)
            self.cover_label.setStyleSheet("font-size: 96px; background: transparent; qproperty-alignment: 'AlignCenter';")
            self.btn_cinema.setText("✕")
        else:
            self.cover_label.setFixedSize(48, 48)
            self.cover_label.setStyleSheet("font-size: 32px; background: transparent; qproperty-alignment: 'AlignCenter';")
            self.btn_cinema.setText("🎬")

    def toggle_focus_mode(self):
        self.focus_mode = not self.focus_mode
        for w in self.focus_hide_widgets:
            w.setVisible(not self.focus_mode)
        self.btn_focus.setText("✕" if self.focus_mode else "🎯")

    # ------------------------------------------------------------------
    # Прочее (шэринг, донат, диагностика)
    # ------------------------------------------------------------------
    def share_on_twitter(self):
        current_row = self.list_widget.currentRow()
        track_name = self.current_playlist[current_row] if 0 <= current_row < len(self.current_playlist) else "?"
        text = self.T("twitter_share_text", t=track_name)
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, self.T("twitter_title"), self.T("twitter_copied"))

    def support_author(self):
        reply = QMessageBox.question(self, self.T("donate_title"), self.T("donate_text"), QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            webbrowser.open("https://www.donationalerts.com/r/fleurdev")

    def check_for_updates(self):
        QMessageBox.information(self, self.T("update_title"), self.T("update_text"))

    def run_library_diagnostic(self):
        if not self.playlist_files:
            QMessageBox.warning(self, self.T("diag_title"), self.T("diag_empty_text"))
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

        report = (self.T("diag_report_header") + "\n\n" +
                  self.T("diag_corrupted", n=corrupted_count) + "\n" +
                  self.T("diag_duplicates", n=len(duplicates)))
        if duplicates:
            report += "\n\n" + self.T("diag_recommend", list=duplicates[:3])
        QMessageBox.information(self, self.T("diag_title"), report)

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
        self.load_music()

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
        self.tray_play_action = QAction(self.T("tray_play"), self); self.tray_play_action.triggered.connect(self.play_track)
        self.tray_pause_action = QAction(self.T("tray_pause"), self); self.tray_pause_action.triggered.connect(self.pause_track)
        self.tray_next_action = QAction(self.T("tray_next"), self); self.tray_next_action.triggered.connect(self.next_track)
        self.tray_exit_action = QAction(self.T("tray_exit"), self); self.tray_exit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(self.tray_play_action); tray_menu.addAction(self.tray_pause_action); tray_menu.addAction(self.tray_next_action)
        tray_menu.addSeparator(); tray_menu.addAction(self.tray_exit_action)
        self.tray_icon.setContextMenu(tray_menu); self.tray_icon.show()

    def set_sleep_timer(self, minutes):
        if not minutes:
            self.sleep_timer.stop()
            self.sleep_minutes_left = 0
            return
        self.sleep_minutes_left = minutes
        self.sleep_timer.start(60000)
        QMessageBox.information(self, self.T("msg_sleep_title"), self.T("msg_sleep_text", m=minutes))

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
                    QMessageBox.warning(self, self.T("delete_error_title"), self.T("drop_error_text", e=e))
        self.load_music()

    # ------------------------------------------------------------------
    # Библиотека / плейлист
    # ------------------------------------------------------------------
    def load_music(self):
        os.makedirs(MUSIC_DIR, exist_ok=True)
        self.playlist_files = [f for f in os.listdir(MUSIC_DIR) if f.endswith(('.mp3', '.wav', '.m4a'))]
        self.counter_label.setText(self.T("counter_template", n=len(self.playlist_files)))
        self.filter_playlist()

    def toggle_play_mode(self):
        if self.play_mode == "Normal":
            self.play_mode = "Shuffle"; self.btn_mode.setText(self.T("mode_shuffle"))
        elif self.play_mode == "Shuffle":
            self.play_mode = "Repeat"; self.btn_mode.setText(self.T("mode_repeat"))
        else:
            self.play_mode = "Normal"; self.btn_mode.setText(self.T("mode_normal"))

    def filter_playlist(self):
        search_text = self.search_input.text().lower()
        filter_key = self.filter_selector.currentData() or "all"

        if self.active_playlist is not None and self.active_playlist in self.playlists:
            base_files = [f for f in self.playlists[self.active_playlist]["tracks"] if f in self.playlist_files]
        else:
            base_files = self.playlist_files

        self.current_playlist = []
        for f in base_files:
            if search_text and search_text not in f.lower():
                continue
            if filter_key == "favorites" and f not in self.favorite_tracks:
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
            self.update_screen(self.T("status_playing"))
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
            self.update_screen(self.T("status_playing"))
        except Exception as e:
            log.error(f"Не удалось воспроизвести {track_name}: {e}")
            QMessageBox.critical(self, self.T("play_error_title"), self.T("play_error_text", e=e))
            return

        if self.rpc:
            try:
                self.rpc.update(details=f"{track_name}", state="LazyPleer")
            except Exception as e:
                log.debug(f"Discord RPC update failed: {e}")

    def play_selected(self, item):
        self.play_track()

    def pause_track(self):
        if self.player and self.player.is_playing():
            self.player.pause()
            self.update_screen(self.T("status_paused"))

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
        if not self.player:
            return
        state = self.player.get_state()

        if state == vlc.State.Playing:
            self.total_listen_time += 0.5
            if int(self.total_listen_time) % 10 == 0:
                self.save_statistics()

            if not self.is_slider_moving:
                pos = self.player.get_position()
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
        reply = QMessageBox.question(self, self.T("delete_confirm_title"), self.T("delete_confirm_text", t=track_name), QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
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
                QMessageBox.information(self, self.T("delete_success_title"), self.T("delete_success_text"))
                self.load_music()
            except Exception as e:
                log.error(f"Не удалось удалить {track_name}: {e}")
                QMessageBox.critical(self, self.T("delete_error_title"), f"{e}")

    def open_about_dialog(self):
        T = self.T
        dialog = QDialog(self); dialog.setWindowTitle(T("about_title")); dialog.setFixedSize(340, 200)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("<b>LazyPleer v7.0</b>"))
        mins = int(self.total_listen_time) // 60
        layout.addWidget(QLabel(T("about_listen_time", m=mins)))
        tg = QLineEdit("Telegram: @french_parasite"); tg.setReadOnly(True); tg.setStyleSheet("background: transparent; border: none;"); layout.addWidget(tg)
        mail = QLineEdit("Email: lilvanforover@mail.com"); mail.setReadOnly(True); mail.setStyleSheet("background: transparent; border: none;"); layout.addWidget(mail)
        btn = QPushButton(T("btn_close")); btn.clicked.connect(dialog.accept); layout.addWidget(btn)
        dialog.exec()

    def open_metadata_editor(self):
        T = self.T
        current_row = self.list_widget.currentRow()
        if current_row < 0:
            return
        track_name = self.current_playlist[current_row]
        track_path = os.path.abspath(os.path.join(MUSIC_DIR, track_name))
        if not track_name.endswith('.mp3'):
            QMessageBox.warning(self, T("edit_tags_format_title"), T("edit_tags_only_mp3"))
            return
        if self.player:
            self.player.stop()

        dialog = QDialog(self); dialog.setWindowTitle(T("edit_tags_title")); dialog.setFixedSize(360, 460)
        layout = QVBoxLayout(dialog)
        try:
            audio = MP3(track_path, ID3=ID3)
            t = str(audio.get('TIT2', '')); a = str(audio.get('TPE1', '')); y = str(audio.get('TYER', ''))
        except Exception as e:
            log.warning(f"Не удалось прочитать теги {track_name}: {e}")
            t, a, y = "", "", ""

        layout.addWidget(QLabel(T("edit_tags_track_label"))); t_in = QLineEdit(t); layout.addWidget(t_in)
        layout.addWidget(QLabel(T("edit_tags_artist_label"))); a_in = QLineEdit(a); layout.addWidget(a_in)
        layout.addWidget(QLabel(T("edit_tags_year_label"))); y_in = QLineEdit(y); layout.addWidget(y_in)
        layout.addWidget(QLabel(T("edit_tags_cover_label")))

        preview_label = QLabel(); preview_label.setFixedSize(100, 100)
        preview_label.setStyleSheet("border: 1px dashed gray; background-color: rgba(0,0,0,0.05);")
        preview_label.setAlignment(Qt.AlignCenter)
        try:
            if 'APIC:' in audio:
                pixmap = QPixmap(); pixmap.loadFromData(audio['APIC:'].data)
                preview_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                preview_label.setText(T("edit_tags_no_cover"))
        except Exception as e:
            log.debug(f"Не удалось показать обложку: {e}")
            preview_label.setText(T("edit_tags_load_error"))
        layout.addWidget(preview_label, alignment=Qt.AlignCenter)

        self.selected_cover_bin = None
        def choose_cover():
            file_path, _ = QFileDialog.getOpenFileName(dialog, T("choose_cover_dialog_title"), "", "Images (*.png *.jpg *.jpeg)")
            if file_path:
                with open(file_path, 'rb') as f:
                    self.selected_cover_bin = f.read()
                pixmap = QPixmap(file_path)
                preview_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        btn_cover = QPushButton(T("edit_tags_load_btn")); btn_cover.clicked.connect(choose_cover); layout.addWidget(btn_cover)

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
                QMessageBox.information(dialog, T("delete_success_title"), T("edit_tags_success"))
            except Exception as e:
                log.error(f"Не удалось сохранить теги {track_name}: {e}")
                QMessageBox.critical(dialog, T("delete_error_title"), f"{e}")
            dialog.accept()

        btn = QPushButton(T("edit_tags_save_btn")); btn.clicked.connect(save); layout.addWidget(btn)
        dialog.exec()
        self.load_music()
        self.play_track()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon.fromTheme("media-playback-start"))
    player = LazyPleerV4()
    player.show()
    sys.exit(app.exec())