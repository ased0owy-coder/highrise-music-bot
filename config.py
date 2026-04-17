"""
ملف الإعدادات الرئيسي للبوت
محمول ومتوافق مع جميع البيئات (Replit, Katabump, إلخ)
"""
import os
from pathlib import Path
from dataclasses import dataclass

# تحديد المسار الأساسي للمشروع
BASE_DIR = Path(__file__).parent.absolute()

@dataclass
class SystemFiles:
    """مسارات ملفات النظام"""
    QUEUE = str(BASE_DIR / "queue.txt")
    DEFAULT_PLAYLIST = str(BASE_DIR / "default_playlist.txt")
    PLAYLIST_STATE = str(BASE_DIR / "playlist_state.json")
    HISTORY = str(BASE_DIR / "play_history.txt")
    FAILED_REQUESTS = str(BASE_DIR / "failed_requests.txt")
    SONG_NOTIFICATIONS = str(BASE_DIR / "song_notifications.json")

@dataclass
class StreamSettings:
    """إعدادات البث"""
    ZENO_STREAM_URL = "https://stream.zeno.fm/60rfrcy14kmvv"
    ZENO_SERVER = "link.zeno.fm"
    ZENO_PORT = 80
    ZENO_USERNAME = "source"
    ZENO_MOUNT_POINT = "60rfrcy14kmvv"
    ZENO_PASSWORD = os.environ.get("ZENO_PASSWORD", "lUZG9WeQ")
    ZENO_ENCODING = "MP3"
    MIN_SONG_DURATION = 30
    MAX_RETRY_ATTEMPTS = 3
    STREAM_BITRATE = "128k"
    CACHE_DIR = str(BASE_DIR / "song_cache")

@dataclass
class LogSettings:
    """إعدادات التسجيل (Logging)"""
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

@dataclass
class HighriseSettings:
    """إعدادات Highrise"""
    BOT_TOKEN = os.environ.get("HIGHRISE_BOT_TOKEN", "a491ead4b09decabf6baa7c174486025062bd2bdcd4baed384e87c12887c8dda")
    ROOM_ID = os.environ.get("HIGHRISE_ROOM_ID", "69e16f0953cad135111f0fab")
    # قائمة الملاك - يمكن إضافة أكثر من مالك
    OWNERS = ["SKP6", "_S7Q", "9O.S", "SKP.6", "7_e", "SA_D27"]
    
    @property
    def OWNER_USERNAME(self):
        # للتوافق مع الكود القديم، نرجع أول مالك
        return self.OWNERS[0] if self.OWNERS else ""
    
    # قائمة المشرفين اليدوية - يمكنك إضافة أسماء مستخدمين هنا مباشرة
    # مثال: MODERATORS = ["username1", "username2"]
    # ملاحظة: البوت يكتشف المشرفين/المصممين/المالك تلقائياً ويحفظهم في staff_cache.json
    MODERATORS = []
    
    VIP_PRICE = 500  # سعر VIP بالذهب
    
    # تفعيل الأغاني الافتراضية عند فراغ الطلبات
    ENABLE_DEFAULT_SONGS = False
    
    # إعدادات موقع البوت عند بدء التشغيل
    # غيّر القيم حسب الموقع المطلوب
    BOT_POSITION_X = 16.0
    BOT_POSITION_Y = 14.75
    BOT_POSITION_Z = 2.0
    BOT_POSITION_FACING = "FrontLeft"  # الاتجاهات المتاحة: FrontRight, FrontLeft, BackRight, BackLeft

# قائمة الأغاني الافتراضية - تم إفراغها بناءً على طلب المستخدم
DEFAULT_SONGS = []