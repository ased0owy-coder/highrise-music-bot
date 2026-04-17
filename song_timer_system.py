#!/usr/bin/env python3
"""
نظام المؤقت الذكي للأغاني
"""

import asyncio
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging

logger = logging.getLogger('song_timer')

class SmartSongTimer:
    """مؤقت ذكي يعتمد على المدة الزمنية الحقيقية"""
    
    def __init__(self, playlist_manager, streamer):
        self.playlist_manager = playlist_manager
        self.streamer = streamer
        self.current_timer = None
        self.is_running = False
        
    def calculate_remaining_time(self, song_title: str, total_duration: int) -> int:
        """حساب الوقت المتبقي للأغنية الحالية"""
        try:
            if Path("song_notifications.json").exists():
                with open("song_notifications.json", 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if data.get('song_title') == song_title:
                    start_time_str = data.get('start_time')
                    if start_time_str:
                        start_time = datetime.fromisoformat(start_time_str)
                        elapsed = (datetime.now() - start_time).total_seconds()
                        remaining = max(0, total_duration - elapsed)
                        return int(remaining)
        
        except Exception as e:
            logger.error(f"❌ خطأ في حساب الوقت: {e}")
        
        return total_duration
    
    async def start_timer_for_song(self, song_title: str, duration_seconds: int):
        """بدء مؤقت للأغنية الجديدة"""
        # إلغاء المؤقت السابق
        await self.cancel_timer()
        
        self.is_running = True
        logger.info(f"⏰ بدء مؤقت لـ {song_title}: {duration_seconds} ثانية")
        
        # حساب الوقت المتبقي إذا كانت الأغنية بدأت بالفعل
        remaining = self.calculate_remaining_time(song_title, duration_seconds)
        
        # بدء المؤقت
        self.current_timer = asyncio.create_task(
            self.timer_callback(song_title, remaining)
        )
    
    async def timer_callback(self, song_title: str, wait_seconds: int):
        """نداء المؤقت عند انتهاء الوقت"""
        try:
            logger.info(f"⏳ انتظار {wait_seconds} ثانية...")
            await asyncio.sleep(wait_seconds)
            
            if self.is_running:
                logger.info(f"⏰ انتهى وقت {song_title}")
                
                # إرسال إشارة التخطي
                Path("timer_skip_signal.txt").touch()
                
                # الانتقال للأغنية التالية
                self.playlist_manager.advance_cache_index()
                
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
        """تحديث التقدم بشكل مستمر"""
        while True:
            try:
                if Path("song_notifications.json").exists():
                    with open("song_notifications.json", 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    song_title = data.get('song_title')
                    duration = data.get('duration_seconds', 0)
                    start_time_str = data.get('start_time')
                    
                    if song_title and duration and start_time_str:
                        start_time = datetime.fromisoformat(start_time_str)
                        elapsed = (datetime.now() - start_time).total_seconds()
                        
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
                
                time.sleep(1)  # تحديث كل ثانية
                
            except Exception as e:
                logger.error(f"❌ خطأ في تحديث التقدم: {e}")
                time.sleep(5)