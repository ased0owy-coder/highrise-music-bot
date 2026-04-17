
#!/usr/bin/env python3
"""
ملف التشغيل الرئيسي - يشغل البوت وخدمة البث معاً
"""

import asyncio
import subprocess
import logging
import sys
import multiprocessing
import threading
import os
from datetime import datetime
from pathlib import Path
from flask import Flask
from config import HighriseSettings, LogSettings

logging.basicConfig(
    level=getattr(logging, LogSettings.LOG_LEVEL, logging.WARNING),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('main')

def run_bot():
    """تشغيل بوت Highrise مع دعم إعادة الاتصال"""
    while True:
        try:
            bot_token = HighriseSettings.BOT_TOKEN
            room_id = HighriseSettings.ROOM_ID
            
            if not bot_token or room_id == "ROOM_ID":
                logger.error("❌ HIGHRISE_BOT_TOKEN or HIGHRISE_ROOM_ID is missing!")
                return
            
            logger.info("🤖 Starting Highrise Bot...")
            
            # تشغيل البوت باستخدام CLI
            subprocess.run([
                sys.executable,
                "-m",
                "highrise",
                "highrise_music_bot:MusicBot",
                room_id,
                bot_token
            ])
            
        except Exception as e:
            logger.error(f"❌ Bot Crash Error: {e}")
        
        logger.info("♻️ Restarting Bot in 10s...")
        import time
        time.sleep(10)

def run_streamer():
    """تشغيل خدمة البث"""
    try:
        import time
        time.sleep(5)  # انتظر 5 ثوانٍ قبل بدء البث
        
        logger.info("📡 تشغيل خدمة البث...")
        from streamer import ZenoStreamer
        
        streamer = ZenoStreamer()
        streamer.run()
        
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل البث: {e}")
        import traceback
        traceback.print_exc()

def run_updates_server():
    """تشغيل سيرفر التحديثات"""
    try:
        import time
        time.sleep(2)  # انتظار قصير قبل البدء
        
        logger.info("🔄 تشغيل سيرفر التحديثات...")
        
        # استيراد وتشغيل السيرفر
        from updates_manager import app
        
        port = int(os.environ.get('UPDATES_PORT', 8080))
        
        print("\n" + "=" * 60)
        print(f"🚀 سيرفر التحديثات يعمل على البورت: {port}")
        print(f"📱 افتح الرابط: http://0.0.0.0:{port}")
        print("=" * 60 + "\n")
        
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل سيرفر التحديثات: {e}")
        import traceback
        traceback.print_exc()

# Keep Alive Server
keep_alive_app = Flask(__name__)

@keep_alive_app.route('/')
def home():
    return {
        "status": "online",
        "bot": "Highrise Music Bot",
        "uptime": "active",
        "timestamp": datetime.now().isoformat()
    }, 200

def run_keep_alive():
    try:
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"🌐 Keep Alive server starting on port {port}")
        keep_alive_app.run(host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"❌ Keep Alive Error: {e}")

def main():
    """تشغيل جميع الخدمات معاً"""
    logger.info("🚀 بدء نظام Highrise Music Bot")
    
    # إنشاء الملفات الضرورية
    Path("queue.txt").touch()
    Path("downloads").mkdir(exist_ok=True)
    Path("backups").mkdir(exist_ok=True)
    
    # Start Keep Alive in a thread
    threading.Thread(target=run_keep_alive, daemon=True).start()

    bot_process = multiprocessing.Process(target=run_bot, name="HighriseBot")
    streamer_process = multiprocessing.Process(target=run_streamer, name="ZenoStreamer")
    updates_process = multiprocessing.Process(target=run_updates_server, name="UpdatesServer")
    
    bot_process.start()
    streamer_process.start()
    updates_process.start()
    
    try:
        bot_process.join()
        streamer_process.join()
        updates_process.join()
    except KeyboardInterrupt:
        logger.info("⏹️ إيقاف النظام...")
        bot_process.terminate()
        streamer_process.terminate()
        updates_process.terminate()

if __name__ == "__main__":
    main()
