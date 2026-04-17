#!/usr/bin/env python3
"""
نظام إدارة قائمة التشغيل المستمرة
يحافظ على استمرارية البث بدون انقطاع ويشغل الطلبات فوراً
"""

import os
import time
import json
import logging
import threading
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

# استيراد الإعدادات من config.py
from config import SystemFiles, StreamSettings, DEFAULT_SONGS, LogSettings, HighriseSettings

logging.basicConfig(
    level=getattr(logging, LogSettings.LOG_LEVEL, logging.WARNING),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('continuous_playlist')

class ContinuousPlaylistManager:
    """مدير قائمة التشغيل المستمرة"""

    def __init__(self):
        # ملفات النظام من config
        self.QUEUE_FILE = SystemFiles.QUEUE
        self.DEFAULT_PLAYLIST_FILE = SystemFiles.DEFAULT_PLAYLIST
        self.CURRENT_STATE_FILE = SystemFiles.PLAYLIST_STATE
        self.HISTORY_FILE = SystemFiles.HISTORY
        self.FAILED_REQUESTS_FILE = SystemFiles.FAILED_REQUESTS
        self.LIKES_FILE = "likes.txt"

        # حالة النظام
        self.current_song = None
        self.is_playing_user_request = False
        self.is_playing_liked_song = False
        self.default_playlist = []
        self.liked_songs = []
        self.current_default_index = 0
        self.current_liked_index = 0
        self.current_cache_index = 0
        self.cache_playlist = []
        self.last_played_time = None

        # إعدادات من config
        self.min_song_duration = StreamSettings.MIN_SONG_DURATION
        self.shuffle_default_playlist = True
        self.max_retry_attempts = StreamSettings.MAX_RETRY_ATTEMPTS

        # تتبع المحاولات الفاشلة
        self.failed_requests = {}  # {song: attempts_count}

        # تحميل أغاني الـ cache
        self.load_cache_playlist()
        self.load_liked_songs()
        self.load_state()

        logger.info("🎵 تم تشغيل مدير قائمة التشغيل المستمرة")

    def load_cache_playlist(self):
        """تحميل جميع الأغاني من مجلد song_cache"""
        try:
            cache_path = Path(StreamSettings.CACHE_DIR)
            
            if not cache_path.exists():
                cache_path.mkdir(parents=True, exist_ok=True)
                logger.info("📁 تم إنشاء مجلد song_cache")
                self.cache_playlist = []
                return
            
            # البحث عن جميع ملفات MP3 في المجلد
            mp3_files = list(cache_path.glob("*.mp3"))
            
            if not mp3_files:
                logger.warning("⚠️ مجلد song_cache لا يحتوي على أي أغاني MP3")
                self.cache_playlist = []
                return
            
            # استخراج أسماء الأغاني من أسماء الملفات
            self.cache_playlist = []
            for mp3_file in mp3_files:
                # استخراج الاسم من اسم الملف (بدون الهاش)
                filename = mp3_file.stem  # اسم الملف بدون .mp3
                
                # إذا كان الاسم يحتوي على هاش (مثل: أغنية_5f3a2c.mp3)
                # نأخذ الجزء قبل آخر _
                if '_' in filename:
                    # مثل: "أغنية_5f3a2c" → "أغنية"
                    name_parts = filename.rsplit('_', 1)
                    if len(name_parts) > 1:
                        song_name = name_parts[0]
                    else:
                        song_name = filename
                else:
                    song_name = filename
                
                # تنظيف المسافات الزائدة
                song_name = song_name.strip()
                
                if song_name and song_name not in self.cache_playlist:
                    self.cache_playlist.append(song_name)
            
            logger.info(f"📁 تم تحميل {len(self.cache_playlist)} أغنية من song_cache")
            
            # حفظ القائمة في ملف للفحص
            cache_list_file = Path(StreamSettings.CACHE_DIR) / "cache_playlist.txt"
            with open(cache_list_file, 'w', encoding='utf-8') as f:
                for song in self.cache_playlist:
                    f.write(f"{song}\n")
            
        except Exception as e:
            logger.error(f"❌ خطأ في تحميل أغاني الـ cache: {e}")
            self.cache_playlist = []

    def load_liked_songs(self):
        """تحميل قائمة الأغاني المفضلة"""
        try:
            if Path(self.LIKES_FILE).exists():
                with open(self.LIKES_FILE, 'r', encoding='utf-8') as f:
                    self.liked_songs = [line.strip() for line in f.readlines() if line.strip()]
                logger.info(f"❤️ تم تحميل {len(self.liked_songs)} أغنية مفضلة")
            else:
                self.liked_songs = []
        except Exception as e:
            logger.error(f"❌ خطأ في تحميل المفضلات: {e}")
            self.liked_songs = []

    def save_liked_songs(self):
        """حفظ قائمة الأغاني المفضلة"""
        try:
            with open(self.LIKES_FILE, 'w', encoding='utf-8') as f:
                for song in self.liked_songs:
                    f.write(f"{song}\n")
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ المفضلات: {e}")

    def add_like(self, song: str) -> bool:
        if not song or song in self.liked_songs:
            return False
        self.liked_songs.append(song)
        self.save_liked_songs()
        return True

    def clear_likes(self):
        self.liked_songs = []
        if Path(self.LIKES_FILE).exists():
            try:
                os.remove(self.LIKES_FILE)
            except:
                pass

    def load_default_playlist(self):
        """تحميل قائمة الأغاني الافتراضية"""
        try:
            if Path(self.DEFAULT_PLAYLIST_FILE).exists():
                with open(self.DEFAULT_PLAYLIST_FILE, 'r', encoding='utf-8') as f:
                    self.default_playlist = [line.strip() for line in f.readlines() if line.strip()]
                logger.info(f"✅ تم تحميل {len(self.default_playlist)} أغنية افتراضية")
            else:
                self.create_default_playlist()
        except Exception as e:
            logger.error(f"❌ خطأ في تحميل القائمة الافتراضية: {e}")
            self.create_default_playlist()

    def create_default_playlist(self):
        """إنشاء قائمة أغاني افتراضية"""
        default_songs = DEFAULT_SONGS
        try:
            with open(self.DEFAULT_PLAYLIST_FILE, 'w', encoding='utf-8') as f:
                for song in default_songs:
                    f.write(f"{song}\n")
            self.default_playlist = default_songs
            logger.info(f"✅ تم إنشاء قائمة افتراضية بـ {len(default_songs)} أغنية")
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء القائمة الافتراضية: {e}")

    def load_state(self):
        """تحميل حالة التشغيل المحفوظة"""
        try:
            if Path(self.CURRENT_STATE_FILE).exists():
                with open(self.CURRENT_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.current_default_index = state.get('current_default_index', 0)
                    self.current_liked_index = state.get('current_liked_index', 0)
                    self.current_cache_index = state.get('current_cache_index', 0)
                    self.current_song = state.get('current_song')
                    self.is_playing_user_request = state.get('is_playing_user_request', False)
                    self.is_playing_liked_song = state.get('is_playing_liked_song', False)

                if self.current_default_index >= len(self.default_playlist):
                    self.current_default_index = 0
                if self.liked_songs and self.current_liked_index >= len(self.liked_songs):
                    self.current_liked_index = 0
                if self.cache_playlist and self.current_cache_index >= len(self.cache_playlist):
                    self.current_cache_index = 0

                logger.info("✅ تم تحميل حالة التشغيل المحفوظة")
        except Exception as e:
            logger.error(f"❌ خطأ في تحميل الحالة: {e}")

    def save_state(self):
        """حفظ حالة التشغيل الحالية"""
        try:
            state = {
                'current_default_index': self.current_default_index,
                'current_liked_index': self.current_liked_index,
                'current_cache_index': self.current_cache_index,
                'current_song': self.current_song,
                'is_playing_user_request': self.is_playing_user_request,
                'is_playing_liked_song': self.is_playing_liked_song,
                'last_saved': datetime.now().isoformat()
            }
            with open(self.CURRENT_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ الحالة: {e}")

    def get_next_song(self) -> Optional[str]:
        """الحصول على الأغنية التالية للتشغيل"""
        # أولاً: التحقق من طلبات المستخدمين (لها الأولوية القصوى)
        user_request = self.peek_user_request()
        if user_request:
            self.current_song = user_request
            self.is_playing_user_request = True
            self.is_playing_liked_song = False
            self.save_state()
            logger.info(f"🎵 طلب مستخدم (أولوية فورية): {user_request}")
            return user_request

        # ثانياً: التحقق من الأغاني المفضلة
        if hasattr(self, 'liked_songs') and self.liked_songs:
            if self.current_liked_index >= len(self.liked_songs):
                self.current_liked_index = 0
            song = self.liked_songs[self.current_liked_index]
            self.current_song = song
            self.is_playing_user_request = False
            self.is_playing_liked_song = True
            self.save_state()
            logger.info(f"❤️ أغنية مفضلة: {song}")
            return song

        # ثالثاً: تشغيل من الـ cache بدلاً من القائمة الافتراضية
        if hasattr(self, 'cache_playlist') and self.cache_playlist:
            if self.current_cache_index >= len(self.cache_playlist):
                self.current_cache_index = 0
            
            song = self.cache_playlist[self.current_cache_index]
            self.current_song = song
            self.is_playing_user_request = False
            self.is_playing_liked_song = False
            self.save_state()
            logger.info(f"📁 أغنية من cache: {song}")
            return song

        # رابعاً: إذا كان الـ cache فارغاً، استخدم القائمة الافتراضية (للاحتياط فقط)
        if hasattr(self, 'default_playlist') and self.default_playlist:
            if self.current_default_index >= len(self.default_playlist):
                self.current_default_index = 0
            song = self.default_playlist[self.current_default_index]
            self.current_song = song
            self.is_playing_user_request = False
            self.is_playing_liked_song = False
            self.save_state()
            logger.info(f"🎶 أغنية افتراضية (الاحتياطي): {song}")
            return song

        self.current_song = None
        self.is_playing_user_request = False
        self.is_playing_liked_song = False
        self.save_state()
        return None

    def mark_song_started_successfully(self, song: str):
        """تسجيل بدء تشغيل الأغنية بنجاح"""
        if self.is_playing_user_request and song == self.current_song:
            # إزالة الطلب من قائمة الفشل إذا نجح
            if song in self.failed_requests:
                del self.failed_requests[song]
                logger.info(f"🔄 تم إزالة {song} من قائمة الطلبات الفاشلة")

            # حذف الطلب من القائمة بعد النجاح في تشغيله
            if self.consume_user_request():
                logger.info(f"✅ تم بدء تشغيل طلب المستخدم بنجاح: {song}")
            else:
                logger.warning(f"⚠️ تعذر حذف الطلب من القائمة: {song}")
        
        elif self.is_playing_liked_song:
            logger.info(f"✅ تم بدء تشغيل الأغنية المفضلة: {song}")
            self.advance_liked_index()
        
        else:
            # إذا كانت من الـ cache، ننتقل للأغنية التالية في الـ cache
            logger.info(f"✅ تم بدء تشغيل الأغنية من cache: {song}")
            self.advance_cache_index()

    def peek_user_request(self) -> Optional[str]:
        """معاينة طلب المستخدم بدون حذفه من queue.txt"""
        try:
            if not Path(self.QUEUE_FILE).exists():
                return None

            with open(self.QUEUE_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if not lines:
                return None

            # معاينة أول طلب بدون حذف
            next_request = lines[0].strip()
            return next_request if next_request else None

        except Exception as e:
            logger.error(f"❌ خطأ في معاينة طلبات المستخدمين: {e}")
            return None

    def consume_user_request(self) -> bool:
        """حذف أول طلب من queue.txt بعد النجاح في تشغيله"""
        try:
            if not Path(self.QUEUE_FILE).exists():
                return False

            with open(self.QUEUE_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if not lines:
                return False

            # حذف أول طلب فقط
            remaining_lines = lines[1:]

            with open(self.QUEUE_FILE, 'w', encoding='utf-8') as f:
                f.writelines(remaining_lines)

            logger.info("✅ تم حذف الطلب بعد النجاح في تشغيله")
            return True

        except Exception as e:
            logger.error(f"❌ خطأ في حذف الطلب: {e}")
            return False

    def get_user_request(self) -> Optional[str]:
        """قراءة طلب المستخدم من queue.txt - استخدم peek بدلاً منها"""
        return self.peek_user_request()

    def add_to_history(self, song: str):
        """إضافة الأغنية لتاريخ التشغيل"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.HISTORY_FILE, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} - {song}\n")
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة التاريخ: {e}")

    def mark_song_finished(self, song: str):
        """تسجيل انتهاء الأغنية بنجاح"""
        logger.info(f"✅ انتهت الأغنية: {song}")

        # التحقق من قائمة الانتظار وتنظيفها إذا كانت فارغة
        try:
            if Path(self.QUEUE_FILE).exists():
                with open(self.QUEUE_FILE, 'r', encoding='utf-8') as f:
                    queue = [line.strip() for line in f.readlines() if line.strip()]

                # إذا كانت القائمة فارغة، امسحها
                if not queue:
                    with open(self.QUEUE_FILE, 'w', encoding='utf-8') as f:
                        f.write("")
                    logger.info("🧹 تم مسح قائمة الانتظار (فارغة)")
        except Exception as e:
            logger.error(f"❌ خطأ في تنظيف القائمة: {e}")

        self.save_state()

    def get_queue_status(self) -> Dict[str, any]:
        """الحصول على حالة القائمة"""
        try:
            # عد طلبات المستخدمين
            user_requests_count = 0
            if Path(self.QUEUE_FILE).exists():
                with open(self.QUEUE_FILE, 'r', encoding='utf-8') as f:
                    user_requests_count = len([line for line in f.readlines() if line.strip()])

            return {
                'current_song': self.current_song,
                'is_user_request': self.is_playing_user_request,
                'user_requests_pending': user_requests_count,
                'cache_playlist_size': len(self.cache_playlist),
                'current_cache_position': self.current_cache_index,
                'next_cache_song': self.cache_playlist[self.current_cache_index] if self.cache_playlist else None
            }

        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على حالة القائمة: {e}")
            return {}

    def mark_request_failed(self, song: str):
        """تسجيل فشل طلب وزيادة عداد المحاولات"""
        if song in self.failed_requests:
            self.failed_requests[song] += 1
        else:
            self.failed_requests[song] = 1

        attempts = self.failed_requests[song]
        logger.info(f"❌ فشل طلب {song} - المحاولة {attempts}/{self.max_retry_attempts}")

        if attempts >= self.max_retry_attempts:
            logger.warning(f"⚠️ تم تجاوز الحد الأقصى من المحاولات لـ: {song}")

    def move_failed_request_to_end(self):
        """نقل الطلب الفاشل إلى نهاية القائمة"""
        try:
            failed_request = self.peek_user_request()
            if failed_request and self.consume_user_request():
                # إضافة الطلب لنهاية القائمة
                with open(self.QUEUE_FILE, 'a', encoding='utf-8') as f:
                    f.write(f"{failed_request}\n")
                logger.info(f"🔄 تم نقل الطلب الفاشل لنهاية القائمة: {failed_request}")

                # إزالة من قائمة الفشل لإعطائه فرصة أخرى لاحقاً
                if failed_request in self.failed_requests:
                    del self.failed_requests[failed_request]

        except Exception as e:
            logger.error(f"❌ خطأ في نقل الطلب الفاشل: {e}")

    def advance_default_index(self):
        """الانتقال للأغنية الافتراضية التالية"""
        if hasattr(self, 'default_playlist') and self.default_playlist:
            self.current_default_index = (self.current_default_index + 1) % len(self.default_playlist)

    def advance_liked_index(self):
        """الانتقال للأغنية المفضلة التالية"""
        if hasattr(self, 'liked_songs') and self.liked_songs:
            self.current_liked_index = (self.current_liked_index + 1) % len(self.liked_songs)

    def advance_cache_index(self):
        """الانتقال للأغنية التالية في الـ cache"""
        if hasattr(self, 'cache_playlist') and self.cache_playlist:
            self.current_cache_index = (self.current_cache_index + 1) % len(self.cache_playlist)
            logger.debug(f"➡️ مؤشر cache الجديد: {self.current_cache_index}/{len(self.cache_playlist)}")

    def add_song_to_default_playlist(self, song: str):
        """إضافة أغنية للقائمة الافتراضية"""
        try:
            if song not in self.default_playlist:
                self.default_playlist.append(song)

                # حفظ في الملف
                with open(self.DEFAULT_PLAYLIST_FILE, 'a', encoding='utf-8') as f:
                    f.write(f"{song}\n")

                logger.info(f"✅ تم إضافة أغنية للقائمة الافتراضية: {song}")
                return True
            else:
                logger.info(f"⚠️ الأغنية موجودة مسبقاً: {song}")
                return False

        except Exception as e:
            logger.error(f"❌ خطأ في إضافة الأغنية: {e}")
            return False

    def is_liked(self, song: str) -> bool:
        return song in self.liked_songs

    def ensure_queue_file(self):
        """التأكد من وجود ملف الطلبات"""
        if not Path(self.QUEUE_FILE).exists():
            Path(self.QUEUE_FILE).touch()

    def refresh_cache_playlist(self):
        """تحديث قائمة الـ cache من المجلد"""
        old_count = len(self.cache_playlist)
        self.load_cache_playlist()
        new_count = len(self.cache_playlist)
        
        if new_count > old_count:
            logger.info(f"🔄 تمت إضافة {new_count - old_count} أغنية جديدة للكاش")
        elif new_count < old_count:
            logger.info(f"📉 تم إزالة {old_count - new_count} أغنية من الكاش")
        
        # ضبط المؤشر إذا كان خارج النطاق
        if self.cache_playlist and self.current_cache_index >= len(self.cache_playlist):
            self.current_cache_index = 0


def test_playlist_manager():
    """اختبار مدير قائمة التشغيل"""
    manager = ContinuousPlaylistManager()

    print("🧪 اختبار مدير قائمة التشغيل")
    print("="*50)
    
    # عرض محتويات الـ cache
    print(f"📁 عدد الأغاني في الـ cache: {len(manager.cache_playlist)}")
    if manager.cache_playlist:
        print("🎵 قائمة أغاني الـ cache:")
        for i, song in enumerate(manager.cache_playlist[:10], 1):
            print(f"  {i}. {song}")
        if len(manager.cache_playlist) > 10:
            print(f"  ... و {len(manager.cache_playlist) - 10} أغنية أخرى")
    
    # إضافة طلب تجريبي
    with open("queue.txt", "w", encoding="utf-8") as f:
        f.write("فيروز - حبيتك بالصيف\n")

    # اختبار الحصول على الأغنية التالية
    for i in range(5):
        song = manager.get_next_song()
        print(f"🎵 الأغنية {i+1}: {song}")
        if song:
            manager.mark_song_finished(song)
        print(f"📊 الحالة: {manager.get_queue_status()}")
        print("-" * 30)


if __name__ == "__main__":
    test_playlist_manager()