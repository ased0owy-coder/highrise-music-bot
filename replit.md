# Highrise Music Bot

بوت موسيقى لمنصة Highrise يبث الأغاني مباشرة عبر Zeno.fm

## المتطلبات

### حزم Python (requirements.txt)
- `highrise-bot-sdk==24.1.0`
- `aiohttp`
- `yt-dlp`
- `flask`
- `werkzeug`
- `requests`

### حزم النظام (apt.txt)
- `ffmpeg` — لمعالجة الصوت والبث

## المتغيرات البيئية المطلوبة

يجب إعدادها في لوحة تحكم WispByte أو أي منصة استضافة:

| المتغير | الوصف |
|---|---|
| `HIGHRISE_BOT_TOKEN` | توكن بوت Highrise |
| `HIGHRISE_ROOM_ID` | معرف الغرفة |
| `ZENO_PASSWORD` | كلمة مرور بث Zeno.fm |
| `PORT` | بورت Keep-Alive (افتراضي: 5000) |
| `UPDATES_PORT` | بورت سيرفر التحديثات (افتراضي: 8080) |

## أمر التشغيل

```
python main.py
```

## هيكل الملفات

- `main.py` — نقطة البداية، يشغل 3 عمليات متوازية
- `highrise_music_bot.py` — منطق البوت والأحداث
- `streamer.py` — خدمة البث إلى Zeno.fm
- `updates_manager.py` — واجهة إدارة الويب (Flask)
- `config.py` — الإعدادات المركزية
- `tickets_system.py` — نظام التذاكر والـ VIP
- `responses.py` — ردود البوت باللغة العربية
- `continuous_playlist_manager.py` — إدارة قائمة التشغيل الافتراضية

## الميزات

- بث الأغاني من YouTube إلى Zeno.fm باستخدام ffmpeg
- نظام طلبات بالأوامر: `!play`, `!np`, `!queue`, `!skip`
- نظام تذاكر وعضوية VIP مقابل الذهب
- لوحة تحكم ويب للإدارة عن بُعد
- إعادة اتصال تلقائية عند الانقطاع
