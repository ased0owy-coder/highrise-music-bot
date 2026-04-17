#!/usr/bin/env python3
"""
ملف التشغيل الرئيسي
"""

import subprocess
import logging
import threading
import os
import sys
import time
import urllib.request
import tarfile
import stat
from datetime import datetime
from pathlib import Path
from flask import Flask
from config import HighriseSettings, LogSettings

logging.basicConfig(
    level=getattr(logging, LogSettings.LOG_LEVEL, logging.WARNING),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('main')


def ensure_ffmpeg():
    """تنزيل ffmpeg تلقائياً إذا لم يكن موجوداً"""
    result = subprocess.run(['which', 'ffmpeg'], capture_output=True)
    if result.returncode == 0:
        return

    bin_dir = Path(__file__).parent / 'bin'
    ffmpeg_path = bin_dir / 'ffmpeg'

    if ffmpeg_path.exists():
        os.environ['PATH'] = str(bin_dir) + ':' + os.environ.get('PATH', '')
        return

    bin_dir.mkdir(exist_ok=True)
    print("📥 جاري تنزيل ffmpeg...")

    try:
        url = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz"
        tarball = bin_dir / 'ffmpeg.tar.xz'
        urllib.request.urlretrieve(url, tarball)

        with tarfile.open(tarball, 'r:xz') as tar:
            for member in tar.getmembers():
                if member.name.endswith('/ffmpeg'):
                    member.name = 'ffmpeg'
                    tar.extract(member, bin_dir)
                    break

        tarball.unlink()
        ffmpeg_path.chmod(ffmpeg_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        os.environ['PATH'] = str(bin_dir) + ':' + os.environ.get('PATH', '')
        print("✅ تم تنزيل ffmpeg")
    except Exception as e:
        print(f"⚠️ لم يتم تنزيل ffmpeg: {e}")


def run_bot():
    """تشغيل البوت في subprocess مع إعادة التشغيل التلقائي"""
    while True:
        try:
            print("🤖 جاري تشغيل البوت...")
            result = subprocess.run([
                sys.executable, "-m", "highrise",
                "highrise_music_bot:MusicBot",
                HighriseSettings.ROOM_ID,
                HighriseSettings.BOT_TOKEN
            ])
            print(f"⚠️ البوت خرج بكود {result.returncode}، إعادة تشغيل...")
        except Exception as e:
            print(f"❌ خطأ في البوت: {e}")
        time.sleep(10)


def run_streamer():
    """تشغيل خدمة البث"""
    while True:
        try:
            time.sleep(8)
            print("📡 تشغيل خدمة البث...")
            from streamer import ZenoStreamer
            streamer = ZenoStreamer()
            streamer.run()
        except Exception as e:
            print(f"❌ خطأ في البث: {e}")
        time.sleep(15)


def run_updates_server():
    """تشغيل سيرفر التحديثات"""
    try:
        time.sleep(3)
        from updates_manager import app as updates_app
        port = int(os.environ.get('UPDATES_PORT', 8080))
        updates_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"❌ خطأ في سيرفر التحديثات: {e}")


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
        print(f"🌐 Keep Alive على البورت {port}")
        keep_alive_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"❌ Keep Alive Error: {e}")


def main():
    print("=" * 50)
    print("🚀 الإصدار: v5 - 2026-04-17")
    print("=" * 50)

    ensure_ffmpeg()

    Path("queue.txt").touch()
    Path("downloads").mkdir(exist_ok=True)
    Path("backups").mkdir(exist_ok=True)
    Path("song_cache").mkdir(exist_ok=True)

    threading.Thread(target=run_keep_alive, daemon=True).start()
    threading.Thread(target=run_updates_server, daemon=True).start()
    threading.Thread(target=run_streamer, daemon=True).start()
    threading.Thread(target=run_bot, daemon=True).start()

    # الخيط الرئيسي يبقى شغّالاً إلى الأبد
    print("✅ جميع الخدمات شغّالة")
    while True:
        time.sleep(30)


if __name__ == "__main__":
    main()
