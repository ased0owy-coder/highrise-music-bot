#!/usr/bin/env python3
"""
Live streaming service to Zeno.fm
نظام البث الذكي مع المؤقت الزمني الدقيق
"""

import os
import subprocess
import time
import json
import sys
import logging
import asyncio
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from continuous_playlist_manager import ContinuousPlaylistManager
from config import SystemFiles, StreamSettings, LogSettings
from responses import BotResponses
import hashlib
import re


logging.basicConfig(
    level=getattr(LogSettings.LOG_LEVEL, LogSettings.LOG_LEVEL, logging.WARNING),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('streamer')

class SmartSongTimer:
    """مؤقت ذكي يعتمد على المدة الزمنية الحقيقية للأغاني"""
    
    def __init__(self, playlist_manager):
        self.playlist_manager = playlist_manager
        self.current_timer = None
        self.is_running = False
        self.song_duration_cache = {}  # كاش لمدة الأغاني
        
    def get_song_duration(self, query: str) -> int:
        """الحصول على مدة الأغنية من YouTube"""
        try:
            # 🔴 تنظيف الاستعلام أولاً
            clean_query = self._clean_search_query(query)
            
            # التحقق من الكاش أولاً
            if clean_query in self.song_duration_cache:
                return self.song_duration_cache[clean_query]
            
            # استخدام yt-dlp لاستخراج المدة فقط
            cmd = [
                sys.executable,
                "-m", "yt_dlp",
                "--get-duration",
                "--no-warnings",
                "--quiet",
                "--skip-download",
                f"ytsearch1:{clean_query}"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                duration_str = result.stdout.strip()
                
                # تحويل "MM:SS" أو "HH:MM:SS" إلى ثواني
                parts = duration_str.split(':')
                seconds = 0
                
                if len(parts) == 2:  # MM:SS
                    seconds = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:  # HH:MM:SS
                    seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                else:
                    seconds = 180  # افتراضي 3 دقائق
                
                # تخزين في الكاش
                self.song_duration_cache[clean_query] = seconds
                logger.info(f"⏱️ مدة الأغنية: {clean_query} = {seconds} ثانية ({duration_str})")
                return seconds
                
        except subprocess.TimeoutExpired:
            logger.warning(f"⏱️ تجاوز الوقت للحصول على مدة: {query}")
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على المدة: {e}")
        
        # مدة افتراضية إذا فشلنا
        return 180  # 3 دقائق افتراضية
    
    def _clean_search_query(self, query: str) -> str:
        """تنظيف استعلام البحث"""
        if not query:
            return ""
        
        # إذا كان يحتوي على | نفصل الجزء الأول فقط (اسم الأغنية)
        if '|' in query:
            query = query.split('|')[0].strip()
        
        # إزالة الرموز الخاصة التي قد تسبب مشاكل
        query = re.sub(r'[\\/*?:"<>|\[\](){}]', '', query)
        query = query.strip()
        
        return query[:200]  # تحديد الطول
    
    async def start_timer_for_song(self, song_title: str):
        """بدء مؤقت للأغنية الجديدة"""
        # إلغاء المؤقت السابق
        await self.cancel_timer()
        
        # 🔴 تنظيف اسم الأغنية أولاً
        clean_title = self._clean_search_query(song_title)
        
        # الحصول على مدة الأغنية
        duration = self.get_song_duration(clean_title)
        
        self.is_running = True
        logger.info(f"⏰ بدء مؤقت لـ {clean_title}: {duration} ثانية")
        
        # بدء المؤقت
        self.current_timer = asyncio.create_task(
            self.timer_callback(clean_title, duration)
        )
    
    async def timer_callback(self, song_title: str, wait_seconds: int):
        """نداء المؤقت عند انتهاء الوقت"""
        try:
            logger.info(f"⏳ انتظار {wait_seconds} ثانية لـ {song_title}...")
            await asyncio.sleep(wait_seconds)
            
            if self.is_running:
                logger.info(f"⏰ انتهى وقت {song_title}")
                
                # إرسال إشارة التخطي التلقائي
                Path("timer_skip_signal.txt").touch()
                logger.info("🚀 تم إنشاء إشارة التخطي التلقائي")
                
        except asyncio.CancelledError:
            logger.info("⏹️ تم إلغاء المؤقت")
        except Exception as e:
            logger.error(f"❌ خطأ في المؤقت: {e}")
    
    async def cancel_timer(self):
        """إلغاء المؤقت الحالي"""
        if self.current_timer and not self.current_timer.done():
            self.current_timer.cancel()
            self.is_running = False
            try:
                await self.current_timer
            except asyncio.CancelledError:
                pass
    
    def update_progress_continuously(self):
        """تحديث التقدم بشكل مستمر - تعمل في خيط منفصل"""
        while True:
            try:
                if Path("song_notifications.json").exists():
                    with open("song_notifications.json", 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    song_title = data.get('song_title')
                    duration = data.get('duration_seconds', 0)
                    start_time_str = data.get('start_time')
                    
                    if song_title and duration and start_time_str:
                        try:
                            start_time = datetime.fromisoformat(start_time_str)
                            elapsed = (datetime.now() - start_time).total_seconds()
                            
                            # التأكد أن التقدم لا يتجاوز 100%
                            if elapsed > duration:
                                elapsed = duration
                            
                            # حساب التقدم
                            if duration > 0:
                                progress = (elapsed / duration) * 100
                            else:
                                progress = 0
                            
                            # تحديث البيانات
                            data['current_progress'] = min(100.0, round(progress, 1))
                            data['elapsed_seconds'] = int(elapsed)
                            
                            # حساب الدقائق والثواني
                            elapsed_min = int(elapsed) // 60
                            elapsed_sec = int(elapsed) % 60
                            remaining = max(0, duration - elapsed)
                            remaining_min = int(remaining) // 60
                            remaining_sec = int(remaining) % 60
                            
                            data['elapsed_formatted'] = f"{elapsed_min}:{elapsed_sec:02d}"
                            data['remaining_formatted'] = f"{remaining_min}:{remaining_sec:02d}"
                            
                            # حفظ التحديث
                            with open("song_notifications.json", 'w', encoding='utf-8') as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                                
                        except Exception as time_error:
                            logger.debug(f"تخطي خطأ الوقت: {time_error}")
                
                time.sleep(1)  # تحديث كل ثانية
                
            except Exception as e:
                logger.error(f"❌ خطأ في تحديث التقدم: {e}")
                time.sleep(5)

class ZenoStreamer:
    """خدمة البث مع النظام الذكي"""

    def __init__(self):
        self.playlist_manager = ContinuousPlaylistManager()
        self.zeno_password = StreamSettings.ZENO_PASSWORD
        # Construct the stream URL with correct information
        self.stream_url = f"icecast://{StreamSettings.ZENO_USERNAME}:{self.zeno_password}@{StreamSettings.ZENO_SERVER}:{StreamSettings.ZENO_PORT}/{StreamSettings.ZENO_MOUNT_POINT}"
        self.notifications_file = SystemFiles.SONG_NOTIFICATIONS
        self.skip_signal_file = "skip_signal.txt"
        self.current_process = None
        
        # النظام الذكي
        self.timer_system = SmartSongTimer(self.playlist_manager)
        
        # إنشاء مجلد التخزين المؤقت
        Path(StreamSettings.CACHE_DIR).mkdir(exist_ok=True)
        logger.info(f"📁 Cache directory ready: {StreamSettings.CACHE_DIR}")
        
        # بدء تحديث التقدم في خيط منفصل
        progress_thread = threading.Thread(
            target=self.timer_system.update_progress_continuously,
            daemon=True
        )
        progress_thread.start()
        logger.info("📊 بدء نظام تحديث التقدم المستمر")

    def get_cache_filename(self, query: str) -> str:
        """توليد اسم ملف فريد للأغنية بناءً على الاستعلام"""
        # تنظيف الاستعلام أولاً
        clean_query = self._clean_search_query(query)
        
        # استخدام hash للحصول على اسم ملف آمن وفريد
        query_hash = hashlib.md5(clean_query.encode()).hexdigest()[:12]
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in clean_query)
        safe_name = safe_name[:50].strip()  # تحديد طول الاسم
        return f"{StreamSettings.CACHE_DIR}/{safe_name}_{query_hash}.mp3"
    
    def _clean_search_query(self, query: str) -> str:
        """تنظيف استعلام البحث"""
        if not query:
            return ""
        
        # إذا كان يحتوي على | نفصل الجزء الأول فقط (اسم الأغنية)
        if '|' in query:
            query = query.split('|')[0].strip()
        
        # إزالة الرموز الخاصة التي قد تسبب مشاكل
        query = re.sub(r'[\\/*?:"<>|\[\](){}]', '', query)
        query = query.strip()
        
        return query[:200]  # تحديد الطول

    def cleanup_song_cache(self, max_songs: int = 10):
        """حذف أقدم الأغاني تلقائياً إذا تجاوز الكاش الحد المسموح"""
        try:
            cache_dir = Path(StreamSettings.CACHE_DIR)
            mp3_files = sorted(cache_dir.glob("*.mp3"), key=lambda f: f.stat().st_mtime)
            if len(mp3_files) > max_songs:
                to_delete = mp3_files[:len(mp3_files) - max_songs]
                for f in to_delete:
                    f.unlink()
                    logger.info(f"🗑️ تم حذف الأغنية القديمة من الكاش: {f.name}")
        except Exception as e:
            logger.error(f"❌ خطأ في تنظيف الكاش: {e}")

    def download_song(self, query: str) -> Optional[str]:
        """Download song from YouTube or use cached version"""
        # تنظيف الكاش تلقائياً قبل كل تحميل
        self.cleanup_song_cache(max_songs=10)
        try:
            # 🔴 أولاً: تنظيف الاستعلام واستخراج اسم الأغنية فقط
            clean_query = self._clean_search_query(query)
            
            # 🔴 استخراج معلومات المستخدم والمدة إذا كانت موجودة
            requested_by = "افتراضي"
            original_duration = "0"
            
            if '|' in query:
                parts = query.split('|')
                if len(parts) >= 2:
                    requested_by = parts[1].strip()
                if len(parts) >= 3:
                    original_duration = parts[2].strip()
            
            logger.info(f"🎵 بحث: '{clean_query}' | 👤: {requested_by} | ⏱️: {original_duration}")

            msg, _ = BotResponses.STREAM_SEARCHING
            logger.info(msg.format(query=clean_query))

            # التحقق من وجود الأغنية في الـ cache
            cache_file = self.get_cache_filename(clean_query)

            if Path(cache_file).exists():
                file_size = Path(cache_file).stat().st_size
                if file_size > 10000:  # أكبر من 10KB
                    logger.info(f"✅ استخدام نسخة محفوظة: {cache_file}")
                    msg, _ = BotResponses.STREAM_DOWNLOADING
                    logger.info(msg.format(title=cache_file))
                    return cache_file
                else:
                    # ملف تالف، احذفه
                    logger.warning(f"⚠️ ملف تالف، سيتم حذفه: {cache_file}")
                    Path(cache_file).unlink()

            # الأغنية غير موجودة، قم بتحميلها
            output_file = cache_file

            # Download using yt-dlp - optimized for speed
            cmd = [
                sys.executable,
                "-m", "yt_dlp",
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "5",          # جودة متوسطة = تحميل أسرع
                "--no-check-certificates",
                "--no-playlist",                  # تجنب تحميل قوائم تشغيل كاملة
                "--no-write-thumbnail",           # لا نحتاج صورة الغلاف
                "--no-write-info-json",           # لا نحتاج ملف المعلومات
                "--no-embed-metadata",            # تخطي حفظ البيانات الوصفية
                "--concurrent-fragments", "4",    # تحميل 4 أجزاء بالتوازي
                "--buffer-size", "32K",           # زيادة حجم البافر
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "--extractor-retries", "2",
                "--retries", "2",
                "--quiet",
                "-o", output_file,
                f"ytsearch1:{clean_query}"
            ]

            logger.info(f"⬇️ تحميل: {clean_query}")
            
            # Start download process with waiting for completion
            download_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Monitor skip signal during download
            while download_process.poll() is None:
                # Only allow skip during download for default songs, not user requests
                if Path(self.skip_signal_file).exists():
                    if not self.playlist_manager.is_playing_user_request:
                        logger.info("⏭️ Skip signal received during download (default song)")
                        download_process.terminate()
                        download_process.wait()
                        # Delete partial file if it exists
                        if Path(output_file).exists():
                            Path(output_file).unlink()
                        return "SKIPPED"
                    else:
                        # حماية طلبات المستخدمين - حذف إشارة التخطي
                        Path(self.skip_signal_file).unlink()
                        logger.info("🔒 تجاهل إشارة التخطي - جاري تحميل طلب المستخدم")
                time.sleep(0.1)   # فحص أسرع كل 0.1 ثانية بدل 0.3

            # Check if download was successful
            if download_process.returncode == 0 and Path(output_file).exists():
                # Wait a moment to ensure file is fully written
                time.sleep(0.2)  # تقليل وقت الانتظار

                # Verify file size is valid
                file_size = Path(output_file).stat().st_size
                if file_size < 1000:  # Less than 1KB means incomplete/corrupted
                    logger.error(f"❌ Incomplete download: {file_size} bytes")
                    Path(output_file).unlink()
                    return None

                msg, _ = BotResponses.STREAM_DOWNLOADING
                logger.info(msg.format(title=output_file))
                return output_file
            else:
                _, stderr = download_process.communicate()
                error_msg = stderr.decode('utf-8', errors='ignore') if stderr else 'Unknown error'
                msg, _ = BotResponses.STREAM_DOWNLOAD_ERROR
                logger.error(msg.format(error=error_msg[:200]))
                
                # 🔴 محاولة بديلة: استخدام جزء من الاسم فقط
                if '|' in query:
                    song_parts = query.split('|')[0].strip().split()
                    if len(song_parts) > 3:
                        simple_query = " ".join(song_parts[:3])  # أول 3 كلمات فقط
                        logger.info(f"🔄 محاولة بحث أبسط: '{simple_query}'")
                        return self.download_song(simple_query)
                
                return None

        except Exception as e:
            logger.error(f"❌ Download error: {e}")
            return None

    def save_song_notification(self, song_title: str, duration_seconds: int, requested_by: str = "افتراضي"):
        """Save current song information with progress tracking"""
        try:
            # 🔴 تنظيف اسم الأغنية
            clean_title = self._clean_search_query(song_title)
            
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            duration_formatted = f"{minutes}:{seconds:02d}"

            start_time = datetime.now()
            end_time = start_time + timedelta(seconds=duration_seconds)

            notification = {
                "song_title": clean_title,
                "duration_formatted": duration_formatted,
                "duration_seconds": duration_seconds,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "timestamp": start_time.isoformat(),
                "requested_by": requested_by,
                "current_progress": 0,
                "elapsed_seconds": 0,
                "elapsed_formatted": "0:00",
                "remaining_formatted": duration_formatted
            }

            with open(self.notifications_file, 'w', encoding='utf-8') as f:
                json.dump(notification, f, ensure_ascii=False, indent=2)

            logger.info(f"📝 Song information saved: {clean_title} - طلب من: {requested_by}")

        except Exception as e:
            logger.error(f"❌ Error saving information: {e}")

    def stream_song_smart(self, audio_file: str, song_title: str) -> bool:
        """تشغيل الأغنية بالنظام الذكي"""
        try:
            msg, _ = BotResponses.STREAM_PLAYING
            
            # 🔴 استخراج معلومات المستخدم والمدة من song_title
            requested_by = "افتراضي"
            song_duration = 180  # افتراضي 3 دقائق
            
            if '|' in song_title:
                parts = song_title.split('|')
                clean_song_title = self._clean_search_query(parts[0].strip())
                if len(parts) > 1:
                    requested_by = parts[1].strip()
                if len(parts) > 2:
                    try:
                        song_duration = int(parts[2].strip())
                    except:
                        song_duration = 180
            else:
                clean_song_title = self._clean_search_query(song_title)
            
            logger.info(msg.format(title=clean_song_title))
            logger.info(f"👤 طلب من: {requested_by} | ⏱️ المدة الأصلية: {song_duration}")

            # الحصول على المدة الحقيقية للأغنية
            duration = self.timer_system.get_song_duration(clean_song_title)
            
            # حفظ معلومات الأغنية مع المدة الحقيقية
            self.save_song_notification(song_title, duration, requested_by)
            
            # 🔴 بدء المؤقت الذكي
            asyncio.run(self.timer_system.start_timer_for_song(clean_song_title))
            logger.info(f"⏰ بدء المؤقت الذكي: {duration} ثانية")

            # إضافة صمت بسيط في البداية
            stream_cmd = [
                "ffmpeg",
                "-f", "lavfi",
                "-t", "00.25",  # ربع ثانية فقط
                "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-re",
                "-i", audio_file,
                "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[out]",
                "-map", "[out]",
                "-acodec", "libmp3lame",
                "-b:a", StreamSettings.STREAM_BITRATE,
                "-ar", "44100",
                "-ac", "2",
                "-f", "mp3",
                "-content_type", "audio/mpeg",
                self.stream_url
            ]

            logger.info("🔌 بدء البث إلى Zeno.fm...")
            self.current_process = subprocess.Popen(stream_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # انتظار قصير للتأكد من بدء البث
            time.sleep(1)
            
            # التحقق من أن البث بدأ بنجاح
            if self.current_process.poll() is not None:
                _, stderr = self.current_process.communicate()
                error_msg = stderr.decode('utf-8', errors='ignore') if stderr else 'Unknown error'
                logger.error(f"❌ فشل بدء البث: {error_msg[-300:]}")
                # إلغاء المؤقت
                asyncio.run(self.timer_system.cancel_timer())
                return False
            
            logger.info("✅ البث متصل")

            # مراقبة أثناء التشغيل
            while self.current_process.poll() is None:
                # 1. تحقق من إشارة المؤقت الذكي
                if Path("timer_skip_signal.txt").exists():
                    logger.info("⏰ إشارة المؤقت الذكي - انتهى الوقت")
                    Path("timer_skip_signal.txt").unlink()
                    self.current_process.kill()
                    try:
                        self.current_process.wait(timeout=2)
                    except:
                        pass
                    
                    # تسجيل انتهاء الأغنية
                    self.playlist_manager.mark_song_finished(song_title)
                    logger.info("🔄 الانتقال للأغنية التالية (بسبب المؤقت)")
                    return False

                # 2. تحقق من إشارة التخطي اليدوية
                if Path(self.skip_signal_file).exists():
                    msg, _ = BotResponses.STREAM_SKIP_SIGNAL
                    logger.info(msg)
                    self.current_process.kill()
                    try:
                        self.current_process.wait(timeout=2)
                    except:
                        pass
                    Path(self.skip_signal_file).unlink()
                    # إلغاء المؤقت
                    asyncio.run(self.timer_system.cancel_timer())
                    logger.info("✅ Stream stopped manually")
                    return False

                # 3. تحقق من طلبات جديدة أثناء تشغيل أغنية افتراضية
                user_request = self.playlist_manager.peek_user_request()
                if user_request and not self.playlist_manager.is_playing_user_request:
                    logger.info(f"⏭️ طلب جديد مكتشف: {user_request}")
                    self.current_process.kill()
                    try:
                        self.current_process.wait(timeout=2)
                    except:
                        pass
                    # إلغاء المؤقت
                    asyncio.run(self.timer_system.cancel_timer())
                    logger.info("✅ إيقاف الأغنية الافتراضية للتحول للطلبات")
                    return False

                # 4. تحقق من skip_default_only
                if Path("skip_default_only.txt").exists():
                    if not self.playlist_manager.is_playing_user_request:
                        logger.info("⏭️ تخطي الأغنية الافتراضية (إشارة خاصة)")
                        self.current_process.kill()
                        try:
                            self.current_process.wait(timeout=2)
                        except:
                            pass
                        Path("skip_default_only.txt").unlink()
                        # إلغاء المؤقت
                        asyncio.run(self.timer_system.cancel_timer())
                        logger.info("✅ إيقاف الأغنية الافتراضية")
                        return False
                    else:
                        Path("skip_default_only.txt").unlink()

                time.sleep(0.3)

            # إذا انتهى البث بشكل طبيعي
            if self.current_process.returncode == 0:
                msg, _ = BotResponses.STREAM_ENDED
                logger.info(msg.format(title=clean_song_title))
                
                # تحديث التقدم إلى 100%
                try:
                    if Path(self.notifications_file).exists():
                        with open(self.notifications_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        if data.get('song_title') == clean_song_title:
                            data['current_progress'] = 100.0
                            data['elapsed_formatted'] = data.get('duration_formatted', '0:00')
                            data['remaining_formatted'] = "0:00"
                            
                            with open(self.notifications_file, 'w', encoding='utf-8') as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                except:
                    pass
                
                # تسجيل انتهاء الأغنية
                self.playlist_manager.mark_song_finished(song_title)
                
                # إلغاء المؤقت
                asyncio.run(self.timer_system.cancel_timer())
                
                return True
            else:
                # خطأ في البث
                _, stderr = self.current_process.communicate()
                error_msg = stderr.decode('utf-8', errors='ignore') if stderr else 'Unknown error'
                logger.error(f"❌ Streaming failed with return code {self.current_process.returncode}")
                
                # إلغاء المؤقت
                asyncio.run(self.timer_system.cancel_timer())
                
                return False

        except Exception as e:
            logger.error(f"❌ Streaming error: {e}")
            if self.current_process:
                try:
                    self.current_process.kill()
                    self.current_process.wait(timeout=1)
                except:
                    pass
            # إلغاء المؤقت
            asyncio.run(self.timer_system.cancel_timer())
            return False

    def run(self):
        """تشغيل الخدمة بالنظام الذكي"""
        logger.info("🚀 بدء خدمة البث الذكية مع المؤقت الزمني")
        
        consecutive_plays = 0
        
        while True:
            try:
                consecutive_plays += 1
                logger.info(f"🔄 دورة التشغيل #{consecutive_plays}")
                
                # 1. الحصول على الأغنية التالية
                next_song = self.playlist_manager.get_next_song()
                
                if not next_song:
                    logger.info("⏳ لا توجد أغنية، الانتظار 5 ثواني...")
                    consecutive_plays = 0
                    time.sleep(5)
                    continue
                
                logger.info(f"🎵 الأغنية التالية: {next_song}")
                
                # 2. تنزيل الأغنية
                audio_file = self.download_song(next_song)
                
                if audio_file == "SKIPPED":
                    logger.info("⏭️ تم تخطي الأغنية أثناء التنزيل")
                    consecutive_plays = 0
                    time.sleep(1)
                    continue
                
                if not audio_file:
                    logger.warning("❌ فشل تنزيل الأغنية، الانتقال للتالية")
                    self.playlist_manager.advance_cache_index()
                    consecutive_plays = 0
                    time.sleep(2)
                    continue
                
                # 3. تسجيل بدء التشغيل الناجح
                self.playlist_manager.mark_song_started_successfully(next_song)
                
                # 4. تشغيل الأغنية بالنظام الذكي
                success = self.stream_song_smart(audio_file, next_song)
                
                if success:
                    logger.info("🎉 الأغنية انتهت بنجاح، متابعة التشغيل...")
                    # الانتقال التلقائي للأغنية التالية
                    if not self.playlist_manager.is_playing_user_request:
                        self.playlist_manager.advance_cache_index()
                    time.sleep(0.5)
                else:
                    logger.info("🔄 الانتقال للأغنية التالية...")
                    # الانتقال للأغنية التالية حتى لو فشل التشغيل
                    self.playlist_manager.advance_cache_index()
                    consecutive_plays = 0
                    time.sleep(1)
                
                # حذف الملف إذا لم يكن في الكاش
                if audio_file and not audio_file.startswith(StreamSettings.CACHE_DIR):
                    try:
                        Path(audio_file).unlink()
                    except:
                        pass
                
                # إعادة تعيين العداد إذا وصل لـ 50 أغنية متتالية (حماية)
                if consecutive_plays >= 50:
                    logger.info("🛡️ إعادة تعيين عداد التشغيل المتتالي (حماية)")
                    consecutive_plays = 0
                
            except Exception as e:
                logger.error(f"❌ Service error: {e}")
                consecutive_plays = 0
                time.sleep(10)


if __name__ == "__main__":
    if not StreamSettings.ZENO_PASSWORD:
        logger.error("❌ Please set ZENO_PASSWORD in Secrets")
    else:
        streamer = ZenoStreamer()
        streamer.run()