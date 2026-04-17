#!/usr/bin/env python3
"""
ملف التشغيل الرئيسي - يشغل البوت وخدمة البث معاً
"""

import asyncio
import logging
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


def run_streamer():
    """تشغيل خدمة البث في خيط منفصل"""
    while True:
        try:
            time.sleep(8)
            logger.info("📡 تشغيل خدمة البث...")
            from streamer import ZenoStreamer
            streamer = ZenoStreamer()
            streamer.run()
        except Exception as e:
            logger.error(f"❌ خطأ في البث: {e}")
        logger.info("♻️ إعادة تشغيل البث في 15s...")
        time.sleep(15)


def run_updates_server():
    """تشغيل سيرفر التحديثات"""
    try:
        time.sleep(3)
        from updates_manager import app
        port = int(os.environ.get('UPDATES_PORT', 8080))
        logger.info(f"🔄 سيرفر التحديثات على البورت {port}")
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"❌ خطأ في سيرفر التحديثات: {e}")


keep_alive_app = Flask(__name__)

@keep_alive_app.route('/')
def home():
    return {
        "status": "online",
        "bot": "Highrise Music Bot",
        "timestamp": datetime.now().isoformat()
    }, 200


def run_keep_alive():
    try:
        port = int(os.environ.get('PORT', 3000))
        logger.info(f"🌐 Keep Alive على البورت {port}")
        keep_alive_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"❌ Keep Alive Error: {e}")


async def run_bot_async():
    """تشغيل البوت مباشرةً بدون subprocess"""
    from highrise_music_bot import MusicBot

    bot_token = HighriseSettings.BOT_TOKEN
    room_id = HighriseSettings.ROOM_ID

    while True:
        try:
            logger.info("🤖 جاري الاتصال بـ Highrise...")
            bot = MusicBot()
            await bot.run(room_id, bot_token)
        except Exception as e:
            logger.error(f"❌ Bot Error: {e}")

        logger.info("♻️ إعادة الاتصال في 10s...")
        await asyncio.sleep(10)


def main():
    """تشغيل جميع الخدمات"""
    logger.info("🚀 بدء نظام Highrise Music Bot")

    Path("queue.txt").touch()
    Path("downloads").mkdir(exist_ok=True)
    Path("backups").mkdir(exist_ok=True)
    Path("song_cache").mkdir(exist_ok=True)

    threading.Thread(target=run_keep_alive, daemon=True).start()
    threading.Thread(target=run_updates_server, daemon=True).start()
    threading.Thread(target=run_streamer, daemon=True).start()

    # تشغيل البوت في الحلقة الرئيسية لـ asyncio
    asyncio.run(run_bot_async())


if __name__ == "__main__":
    main()
