#!/usr/bin/env python3
"""
ملف التشغيل الرئيسي - يشغل البوت وخدمة البث معاً
"""

import subprocess
import logging
import sys
import threading
import os
import time
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

            logger.info("🤖 Starting Highrise Bot...")

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
        time.sleep(10)


def run_streamer():
    """تشغيل خدمة البث"""
    while True:
        try:
            time.sleep(5)
            logger.info("📡 تشغيل خدمة البث...")
            from streamer import ZenoStreamer
            streamer = ZenoStreamer()
            streamer.run()
        except Exception as e:
            logger.error(f"❌ خطأ في تشغيل البث: {e}")
            import traceback
            traceback.print_exc()
        logger.info("♻️ إعادة تشغيل البث في 10s...")
        time.sleep(10)


def run_updates_server():
    """تشغيل سيرفر التحديثات"""
    try:
        time.sleep(2)
        logger.info("🔄 تشغيل سيرفر التحديثات...")
        from updates_manager import app
        port = int(os.environ.get('UPDATES_PORT', 8080))
        print(f"🚀 سيرفر التحديثات يعمل على البورت: {port}")
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل سيرفر التحديثات: {e}")
        import traceback
        traceback.print_exc()


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
        port = int(os.environ.get('PORT', 3000))
        logger.info(f"🌐 Keep Alive server on port {port}")
        keep_alive_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"❌ Keep Alive Error: {e}")


def main():
    """تشغيل جميع الخدمات معاً"""
    logger.info("🚀 بدء نظام Highrise Music Bot")

    Path("queue.txt").touch()
    Path("downloads").mkdir(exist_ok=True)
    Path("backups").mkdir(exist_ok=True)
    Path("song_cache").mkdir(exist_ok=True)

    threading.Thread(target=run_keep_alive, daemon=True).start()
    threading.Thread(target=run_updates_server, daemon=True).start()
    threading.Thread(target=run_streamer, daemon=True).start()

    # البوت يعمل في الخيط الرئيسي حتى لا يخرج البرنامج
    run_bot()


if __name__ == "__main__":
    main()
