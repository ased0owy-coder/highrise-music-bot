#!/usr/bin/env python3
"""
بوت Highrise للتحكم بالموسيقى
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from highrise import BaseBot, User, Position, AnchorPosition
from highrise.models import SessionMetadata, GetMessagesRequest
from config import HighriseSettings, SystemFiles, StreamSettings, LogSettings
from responses import BotResponses
from tickets_system import TicketsSystem

# تعريف logger قبل الاستيراد مع فرق التوقيت
import time
logging.Formatter.converter = time.gmtime  # استخدام UTC
logging.basicConfig(
    level=getattr(logging, LogSettings.LOG_LEVEL, logging.WARNING),
    format='%(asctime)s UTC - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('highrise_bot')

try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("edx_helper", ".edx_helper.py")
    edx_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(edx_module)
    EDXTeam = edx_module.EDXTeam
except Exception as e:
    logger.warning(f"⚠️ Could not load EDX Team: {e}")
    EDXTeam = None

class MusicBot(BaseBot):
    """بوت موسيقى Highrise"""
    
    def __init__(self):
        super().__init__()
        self.queue_file = SystemFiles.QUEUE
        self.notifications_file = SystemFiles.SONG_NOTIFICATIONS
        self.stream_url = StreamSettings.ZENO_STREAM_URL
        self.current_song = None
        self.bot_dances_file = "bot_dances.json"
        self.staff_cache_file = "staff_cache.json"
        self.owner_username = HighriseSettings.OWNER_USERNAME
        self.bot_username = None  # سيتم تعيينه عند البدء
        
        # نظام التذاكر
        self.tickets_system = TicketsSystem()
        
        # نظام فريق EDX
        self.edx_team = EDXTeam() if EDXTeam else None
        
        # نظام الرقص المستمر للبوت
        self.is_dancing = False
        self.dance_task = None
        
        # تخزين المشرفين والمصممين المكتشفين
        self.detected_staff = self._load_staff_cache()
        
        # فرق التوقيت بين الرسائل (بالثواني) - تم تقليله لزيادة سرعة الاستجابة
        self.message_delay = 0.001
        
        # إنشاء الملفات إذا لم تكن موجودة
        Path(self.queue_file).touch()
        if not Path(self.bot_dances_file).exists():
            with open(self.bot_dances_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
    
    def _load_staff_cache(self) -> dict:
        """تحميل قائمة المشرفين والمصممين المحفوظة"""
        if Path(self.staff_cache_file).exists():
            try:
                with open(self.staff_cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_staff_cache(self):
        """حفظ قائمة المشرفين والمصممين"""
        try:
            with open(self.staff_cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.detected_staff, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ المشرفين: {e}")
    
    def colorize(self, message: str, color_type: str = "default") -> str:
        """إضافة لون لبداية الرسالة حسب النوع"""
        if color_type == "none":
            return message
        colors = {
            "default": "#FFD700",    # ذهبي
            "success": "#00FF00",    # أخضر
            "error": "#FF0000",      # أحمر
            "info": "#00BFFF",       # أزرق فاتح
            "warning": "#FFA500",    # برتقالي
            "music": "#FF69B4",      # وردي
            "dance": "#9370DB"       # بنفسجي
        }
        color = colors.get(color_type, colors["default"])
        return f"<{color}>{message}"
    
    async def send_with_delay(self, message: str, color_type: str = "default"):
        """إرسال رسالة مع فرق توقيت لتجنب السبام"""
        await asyncio.sleep(self.message_delay)
        await self.highrise.chat(self.colorize(message, color_type))
    
    async def vip_reminder_task(self):
        """تذكير دوري بميزات VIP كل 3 دقائق"""
        while True:
            try:
                await asyncio.sleep(180)  # 3 دقائق
                
                msg, color = BotResponses.VIP_REMINDER
                vip_price = HighriseSettings.VIP_PRICE
                reminder_msg = msg.format(price=vip_price)
                await self.send_with_delay(reminder_msg, color)
                logger.info("💎 تم إرسال تذكير VIP")
                
            except Exception as e:
                logger.error(f"❌ خطأ في تذكير VIP: {e}")
    
    async def has_unlimited_access(self, user: User, show_message: bool = False) -> bool:
        """التحقق من أن المستخدم لديه صلاحيات غير محدودة"""
        try:
            # التحقق من فريق EDX أولاً
            if self.edx_team and self.edx_team.is_team_member(user.username):
                if show_message:
                    welcome_msg = self.edx_team.get_welcome_message(user.username)
                    await self.highrise.chat(self.colorize(welcome_msg, "success"))
                return True
            
            if self.tickets_system.is_vip(user.username):
                return True
            
            if user.username in HighriseSettings.OWNERS:
                return True
            
            if user.username in HighriseSettings.MODERATORS:
                return True
            
            if user.username in self.detected_staff:
                return True
            
            privilege = await self.highrise.get_room_privilege(user.id)
            has_p = False
            if hasattr(privilege, 'moderator'):
                has_p = privilege.moderator or privilege.designer
            elif isinstance(privilege, str):
                has_p = privilege in ["owner", "designer", "moderator"]
                
            if has_p:
                if user.username not in self.detected_staff:
                    self.detected_staff[user.username] = "Staff"
                    self._save_staff_cache()
                return True
        except Exception:
            pass
        return False
    
    async def periodic_staff_check(self):
        """فحص دوري للمشرفين والمصممين كل 3 دقائق"""
        while True:
            try:
                # تحديث ملف الحضور للواجهة الويب
                room_users = await self.highrise.get_room_users()
                current_users_data = []
                for user, _ in room_users.content:
                    current_users_data.append({'username': user.username, 'id': user.id})
                
                with open('current_users.json', 'w', encoding='utf-8') as f:
                    json.dump(current_users_data, f, ensure_ascii=False)

                await asyncio.sleep(180)  # 3 دقائق
                
                logger.info("🔍 بدء الفحص الدوري للمشرفين...")
                
                # الحصول على قائمة المستخدمين في الغرفة
                room_users = await self.highrise.get_room_users()
                
                new_staff_count = 0
                for user, position in room_users.content:
                    # تخطي البوت نفسه
                    if self.bot_username and user.username == self.bot_username:
                        continue
                    
                    # فحص الصلاحيات
                    try:
                        privilege = await self.highrise.get_room_privilege(user.id)
                        
                        # التحقق من نوع الصلاحيات
                        is_moderator = False
                        is_designer = False
                        privilege_name = None
                        
                        # إذا كان privilege هو RoomPermissions object
                        if hasattr(privilege, 'moderator') and hasattr(privilege, 'designer'):
                            is_moderator = getattr(privilege, 'moderator', False)
                            is_designer = getattr(privilege, 'designer', False)
                            
                            if is_designer and is_moderator:
                                privilege_name = "Designer & Moderator"
                            elif is_designer:
                                privilege_name = "Designer"
                            elif is_moderator:
                                privilege_name = "Moderator"
                        # إذا كان privilege هو string (نظام قديم)
                        elif isinstance(privilege, str):
                            if privilege in ["owner", "designer", "moderator"]:
                                privilege_name = {
                                    "owner": "Owner",
                                    "designer": "Designer", 
                                    "moderator": "Moderator"
                                }.get(privilege, privilege)
                                is_moderator = privilege == "moderator"
                                is_designer = privilege == "designer"
                        
                        # حفظ المشرف الجديد
                        if privilege_name and (is_moderator or is_designer):
                            if user.username not in self.detected_staff:
                                self.detected_staff[user.username] = privilege_name
                                self._save_staff_cache()
                                new_staff_count += 1
                                logger.info(f"💾 اكتشاف جديد: {user.username} = {privilege_name}")
                                
                                # إرسال رسالة بالاكتشاف
                                msg, color = BotResponses.STAFF_DETECTED
                                await self.highrise.chat(self.colorize(msg.format(username=user.username, privilege=privilege_name), color))
                    except Exception as e:
                        logger.debug(f"تخطي {user.username}: {e}")
                        continue
                
                if new_staff_count > 0:
                    logger.info(f"✅ تم اكتشاف {new_staff_count} مشرف/مصمم جديد")
                else:
                    logger.info("✅ لا يوجد مشرفين جدد")
                    
            except Exception as e:
                logger.error(f"❌ خطأ في الفحص الدوري: {e}")

    async def periodic_reconnect_task(self):
        """مهمة دورية كل 6 دقائق للتأكد من اتصال البوت"""
        while True:
            try:
                await asyncio.sleep(360)  # 6 دقائق
                logger.info("🔄 تنفيذ فحص الحالة الدوري (كل 6 دقائق)...")
                # يمكن إضافة كود هنا لإرسال رسالة بسيطة أو التحرك للتأكد من أن البوت لا يزال متصلاً
                # سنكتفي بتسجيل اللوج حالياً لضمان استمرارية العملية
            except Exception as e:
                logger.error(f"❌ خطأ في المهمة الدورية: {e}")
    
    async def on_start(self, session_metadata: SessionMetadata):
        """عند بدء البوت"""
        try:
            # التحرك إلى الموقع المثبت في الإعدادات
            await self.highrise.walk_to(Position(
                HighriseSettings.BOT_POSITION_X,
                HighriseSettings.BOT_POSITION_Y,
                HighriseSettings.BOT_POSITION_Z,
                HighriseSettings.BOT_POSITION_FACING
            ))
            logger.info(f"📍 Bot moved to fixed position: {HighriseSettings.BOT_POSITION_X}, {HighriseSettings.BOT_POSITION_Y}, {HighriseSettings.BOT_POSITION_Z}")
            
            # حفظ اسم البوت
            self.bot_username = session_metadata.user_id.split('|')[0] if '|' in session_metadata.user_id else None
            logger.info(f"🎵 بوت الموسيقى متصل بـ Highrise! اسم البوت: {self.bot_username}")
            msg, color = BotResponses.STARTUP_MESSAGE
            await self.highrise.chat(self.colorize(msg, color))
            
            # عرض رسالة EDX Team
            if self.edx_team:
                release_msg = self.edx_team.get_release_message()
                await asyncio.sleep(1)
                await self.highrise.chat(self.colorize(release_msg, "success"))
                logger.info(f"💜 {release_msg}")
            
            # عرض المشرفين المحفوظين
            if self.detected_staff:
                staff_list = ', '.join([f"{name} ({role})" for name, role in self.detected_staff.items()])
                logger.info(f"📋 المشرفين المحفوظين: {staff_list}")
            
            # فحص أولي للمشرفين عند بدء البوت
            logger.info("🔍 بدء الفحص الأولي للمشرفين...")
            try:
                room_users = await self.highrise.get_room_users()
                total_users = len(room_users.content)
                logger.info(f"👥 عدد المستخدمين في الغرفة: {total_users}")
                
                for user, position in room_users.content:
                    if self.bot_username and user.username == self.bot_username:
                        continue
                    
                    try:
                        privilege = await self.highrise.get_room_privilege(user.id)
                        has_privilege = False
                        
                        if hasattr(privilege, 'moderator') and hasattr(privilege, 'designer'):
                            is_moderator = getattr(privilege, 'moderator', False)
                            is_designer = getattr(privilege, 'designer', False)
                            has_privilege = is_moderator or is_designer
                        elif isinstance(privilege, str):
                            has_privilege = privilege in ["owner", "designer", "moderator"]
                        
                        if has_privilege:
                            await self.has_unlimited_access(user, show_message=True)
                    except Exception:
                        pass
                        
            except Exception as e:
                logger.error(f"❌ Error in initial scan: {e}")
            
            # بدء المهام الدورية
            asyncio.create_task(self.periodic_staff_check())
            asyncio.create_task(self.vip_reminder_task())
            asyncio.create_task(self.monitor_current_song())
            asyncio.create_task(self.announce_song_status())
            asyncio.create_task(self.periodic_reconnect_task())
            await self.start_continuous_dancing()
        except Exception as e:
            logger.error(f"❌ Error in on_start: {e}")

    async def run(self, room_id, api_token):
        """تشغيل البوت مع نظام إعادة الاتصال التلقائي"""
        retry_delay = 5
        while True:
            try:
                logger.info("📡 Connecting to Highrise...")
                await super().run(room_id, api_token)
            except Exception as e:
                logger.error(f"⚠️ Connection error: {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                # زيادة وقت التأخير تدريجياً
                retry_delay = min(retry_delay * 1.5, 60)
            finally:
                logger.info("♻️ Restarting audio stream if needed...")
                # هنا يمكن إضافة كود لإعادة تشغيل البث إذا لزم الأمر
    
    async def on_user_join(self, user: User, position: Position | AnchorPosition):
        """عند انضمام مستخدم جديد"""
        try:
            # اكتشاف المشرفين والمصممين تلقائياً
            await self.has_unlimited_access(user, show_message=True)
            
            welcome_message = BotResponses.WELCOME_MESSAGE.format(username=user.username)
            # تقسيم الرسالة إذا كانت طويلة جداً
            if len(welcome_message) > 1000:
                parts = [welcome_message[i:i+1000] for i in range(0, len(welcome_message), 1000)]
                for part in parts:
                    await self.highrise.chat(self.colorize(part, "info"))
                    await asyncio.sleep(0.5)
            else:
                await self.highrise.chat(self.colorize(welcome_message, "info"))
            
            # إرسال رسالة همس قصيرة للمستخدم الجديد
            
            try:
                pass
            except Exception as whisper_error:
                logger.error(f"❌ خطأ في إرسال الهمس: {whisper_error}")
                
        except Exception as e:
            logger.error(f"❌ خطأ في رسالة الترحيب: {e}")
    
    async def on_tip(self, sender: User, receiver: User, tip):
        """عند استلام إكرامية"""
        try:
            # استخراج المبلغ من CurrencyItem
            tip_amount: int = 0
            if hasattr(tip, 'amount'):
                tip_amount = int(tip.amount) if isinstance(tip.amount, (int, float, str)) else 0
            elif isinstance(tip, (int, float)):
                tip_amount = int(tip)
            else:
                logger.error(f"❌ قيمة إكرامية غير صالحة: {tip}")
                return
            
            if tip_amount <= 0:
                logger.error(f"❌ قيمة إكرامية غير صالحة: {tip_amount}")
                return
            
            logger.info(f"💰 إكرامية: من {sender.username} إلى {receiver.username} = {tip_amount}g")
            
            # التحقق من أن الإكرامية للبوت (استخدام اسم المستلم مباشرة)
            # إذا كان اسم البوت غير محفوظ، نقوم بقبول أي إكرامية للبوت الحالي
            if not self.bot_username:
                # إذا لم يكن اسم البوت محفوظاً، نقبل الإكرامية
                logger.info(f"💰 إكرامية مقبولة (اسم البوت غير معروف)")
            elif receiver.username != self.bot_username:
                logger.info(f"⚠️ الإكرامية ليست للبوت (المستلم: {receiver.username}, البوت: {self.bot_username})")
                return
            
            # التحقق من VIP (500g = VIP)
            if tip_amount >= HighriseSettings.VIP_PRICE:
                # التحقق إذا كان المستخدم VIP بالفعل
                if self.tickets_system.is_vip(sender.username):
                    msg, color = BotResponses.VIP_ALREADY
                    await self.highrise.chat(self.colorize(msg.format(username=sender.username), color))
                else:
                    # إضافة VIP
                    self.tickets_system.add_vip(sender.username)
                    msg, color = BotResponses.VIP_RECEIVED
                    await self.highrise.chat(self.colorize(msg.format(username=sender.username), color))
                    logger.info(f"⭐ {sender.username} أصبح VIP")
                return
            
            # التحقق من المبلغ (10g = 5 تذاكر)
            if tip_amount < 10:
                msg, color = BotResponses.TIP_TOO_SMALL
                await self.highrise.chat(self.colorize(msg.format(username=sender.username), color))
                return
            
            # حساب عدد التذاكر (كل 10g = 5 تذاكر)
            tickets_to_add = (tip_amount // 10) * 5
            
            # إضافة التذاكر
            total_tickets = self.tickets_system.add_tickets(sender.username, tickets_to_add)
            
            # إرسال رسالة تأكيد
            msg, color = BotResponses.TIP_RECEIVED
            await self.highrise.chat(self.colorize(
                msg.format(
                    username=sender.username,
                    gold=tip_amount,
                    tickets=tickets_to_add,
                    total=total_tickets
                ),
                color
            ))
            
            logger.info(f"✅ {sender.username} حصل على {tickets_to_add} تذاكر (الإجمالي: {total_tickets})")
            
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الإكرامية: {e}")
    
    async def on_chat(self, user: User, message: str):
        """عند استلام رسالة في الدردشة"""
        message = message.strip()
        
        # معالجة الأوامر فقط، بدون اختيار من نتائج البحث
        if message.startswith("!tk"):
            await self.handle_tk_command(user, message)
        elif message.startswith("!"):
            await self.handle_command(user, message)

    async def reset_bot_state(self, user: User):
        """تصفير حالة البوت (مسح قائمة الطلبات)"""
        # التحقق من الصلاحيات
        if not await self.has_unlimited_access(user):
            msg, color = BotResponses.NO_PERMISSION
            await self.highrise.chat(self.colorize(msg, color))
            return
            
        try:
            # مسح ملف الطابور
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                f.write("")
            
            # مسح الملفات المؤقتة الأخرى إذا لزم الأمر
            if Path(SystemFiles.HISTORY).exists():
                 with open(SystemFiles.HISTORY, 'w', encoding='utf-8') as f:
                    f.write("")
            
            # إرسال رسالة نجاح
            msg, color = BotResponses.RESET_SUCCESS
            await self.highrise.chat(self.colorize(msg, color))
            logger.info(f"♻️ تم تصفير البوت بواسطة {user.username}")
            
        except Exception as e:
            logger.error(f"❌ خطأ في تصفير البوت: {e}")
            await self.highrise.chat(self.colorize("حدث خطأ أثناء محاولة تصفير البوت.", "error"))

    async def handle_tk_command(self, user: User, message: str):
        """!tk @username amount"""
        if not await self.has_unlimited_access(user):
            await self.highrise.chat(self.colorize("ليس لديك صلاحية لإعطاء التذاكر.", "error"))
            return
            
        parts = message.split()
        if len(parts) < 3:
            await self.highrise.chat(self.colorize("استخدام خاطئ. مثال: !tk @username 100", "warning"))
            return
            
        target_username = parts[1].lstrip('@')
        try:
            amount = int(parts[2])
            if amount <= 0:
                raise ValueError()
        except ValueError:
            await self.highrise.chat(self.colorize("يرجى إدخال عدد صحيح للتذاكر.", "error"))
            return
            
        total = self.tickets_system.add_tickets(target_username, amount)
        await self.highrise.chat(self.colorize(f"✅ تم إعطاء {amount} تذكرة لـ {target_username}. الإجمالي: {total}", "success"))
        logger.info(f"🎁 {user.username} أعطى {amount} تذكرة لـ {target_username}")

    async def handle_command(self, user: User, message: str):
        """معالجة الأوامر"""
        parts = message.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if command == "!play":
            if args:
                await self.search_and_show_results(user, args)
            else:
                msg, color = BotResponses.PLAY_NO_SONG_NAME
                await self.highrise.chat(self.colorize(msg, color))
        
        elif command == "!np":
            await self.send_current_song()
        
        elif command == "!queue":
            await self.send_queue_status()
        
        elif command == "!skip":
            await self.skip_song(user)
        
        elif command == "!stopdance":
            await self.stop_continuous_dancing()
        
        elif command == "!startdance":
            await self.start_continuous_dancing()
        
        elif command == "!tickets":
            await self.show_user_tickets(user)
        
        elif command == "!reset":
            await self.reset_bot_state(user)
        
        elif command == "!ticketslist":
            await self.show_all_tickets()

        elif command == "!restart":
            await self.handle_restart_command(user)

        elif command == "!help":
            await self.show_help(user)

    async def show_help(self, user: User):
        """عرض قائمة الأوامر"""
        help_message = """📋 قائمة أوامر البوت:
        
🎵 الأغاني:
!play <اسم الأغنية> - طلب أغنية جديدة
!np - عرض الأغنية الحالية مع التقدم
!queue - عرض قائمة الانتظار
!skip - تخطي الأغنية الحالية (لـVIP والمشرفين)

🎫 التذاكر:
!tickets - عرض عدد تذاكرك"""
        
        await self.highrise.chat(self.colorize(help_message, "info"))

    async def handle_restart_command(self, user: User):
        """إعادة تشغيل البوت"""
        if not await self.has_unlimited_access(user):
            await self.highrise.chat(self.colorize("ليس لديك صلاحية لإعادة تشغيل البوت.", "error"))
            return

        await self.highrise.chat(self.colorize("🔄 جاري إعادة تشغيل البوت... سأعود خلال لحظات.", "info"))
        logger.info(f"🔄 إعادة تشغيل البوت بواسطة {user.username}")

        # إنهاء البرنامج، وسيقوم نظام التشغيل (أو main.py) بإعادة تشغيله
        import sys
        sys.exit(0)

    async def search_and_show_results(self, user: User, query: str, offset: int = 0):
        """البحث في YouTube واختيار أول نتيجة تلقائياً"""
        try:
            # التحقق من الصلاحيات (VIP أو المشرف أو المالك لا يحتاجون تذاكر)
            is_unlimited = await self.has_unlimited_access(user, show_message=True)
            
            if not is_unlimited:
                # التحقق من وجود تذاكر للمستخدم العادي
                user_tickets = self.tickets_system.get_user_tickets(user.username)
                if user_tickets <= 0:
                    msg, color = BotResponses.NO_TICKETS
                    await self.highrise.chat(self.colorize(msg.format(username=user.username), color))
                    return
            else:
                # إظهار رسالة VIP
                msg, color = BotResponses.VIP_PLAY_UNLIMITED
                await self.highrise.chat(self.colorize(msg, color))
            
            msg, color = BotResponses.SEARCHING
            await self.highrise.chat(self.colorize(msg.format(query=query), color))
            
            # حساب الوقت المتبقي للأغنية الحالية
            remaining_time_msg = ""
            if Path(self.notifications_file).exists():
                try:
                    with open(self.notifications_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    end_time_str = data.get('end_time')
                    if end_time_str:
                        end_time = datetime.fromisoformat(end_time_str)
                        now = datetime.now()
                        remaining = end_time - now
                        remaining_seconds = int(remaining.total_seconds())
                        
                        if remaining_seconds > 0:
                            remaining_minutes = remaining_seconds // 60
                            remaining_secs = remaining_seconds % 60
                            remaining_time_msg = f"\n⏱️ الوقت المتبقي للأغنية الحالية: {remaining_minutes}:{remaining_secs:02d}"
                except Exception as e:
                    logger.error(f"خطأ في حساب الوقت المتبقي: {e}")
            
            # البحث عن أول نتيجة فقط
            search_count = 1  # البحث عن نتيجة واحدة فقط
            cmd = [

    sys.executable,  # استخدام Python executable

    "-m", "yt_dlp",  # تشغيل yt-dlp كـ module

    "--dump-json",

    "--skip-download",

    "--no-warnings",

    "--flat-playlist",

    "--playlist-end", str(search_count),

    f"ytsearch{search_count}:{query}"

]
            
            # استخدام asyncio للبحث غير المتزامن
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=45)
            except asyncio.TimeoutError:
                process.kill()
                msg, color = BotResponses.SEARCH_TIMEOUT
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            if process.returncode != 0:
                msg, color = BotResponses.SEARCH_FAILED
                await self.highrise.chat(self.colorize(msg, color))
                logger.error(f"خطأ البحث: {stderr.decode()}")
                return
            
            # تحليل أول نتيجة فقط
            result_line = stdout.decode().strip().split('\n')
            if not result_line or not result_line[0]:
                msg, color = BotResponses.NO_RESULTS
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            try:
                data = json.loads(result_line[0])
                title = data.get('title', 'بدون عنوان')
                duration = data.get('duration', 0)
                
                # تحويل المدة لصيغة مقروءة
                minutes = int(duration) // 60
                seconds = int(duration) % 60
                duration_str = f"{minutes}:{seconds:02d}"
                
                # تقصير العنوان إذا كان طويلاً
                display_title = title[:50] + "..." if len(title) > 50 else title
                
                # التحقق من الصلاحيات للمستخدمين العاديين
                if not is_unlimited:
                    # خصم تذكرة عند اختيار الأغنية للمستخدم العادي
                    if not self.tickets_system.use_ticket(user.username):
                        msg, color = BotResponses.NO_TICKETS
                        await self.highrise.chat(self.colorize(msg.format(username=user.username), color))
                        return
                
                # التحقق من حالة التشغيل الحالية
                is_default_playing = False
                if Path(self.notifications_file).exists():
                    try:
                        with open(self.notifications_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        current_title = data.get('song_title', '')
                        
                        # تحميل القائمة الافتراضية للمقارنة
                        default_songs = []
                        if Path("default_playlist.txt").exists():
                            with open("default_playlist.txt", 'r', encoding='utf-8') as f:
                                default_songs = [line.strip() for line in f.readlines() if line.strip()]
                        
                        # التحقق إذا كانت الأغنية الحالية افتراضية
                        is_default_playing = current_title in default_songs
                    except:
                        pass
                
                # 🔴 إضافة للقائمة مع اسم المستخدم والمدة
                with open(self.queue_file, 'a', encoding='utf-8') as f:
                    f.write(f"{title}|{user.username}|{duration}\n")
                
                # إظهار الرسالة
                msg, color = BotResponses.SONG_ADDED
                await self.highrise.chat(self.colorize(msg.format(title=display_title, duration=duration_str), color))
                
                # إظهار التذاكر المتبقية فقط للمستخدمين العاديين
                if not is_unlimited:
                    remaining_tickets = self.tickets_system.get_user_tickets(user.username)
                    msg, color = BotResponses.TICKET_USED
                    await self.highrise.chat(self.colorize(msg.format(remaining=remaining_tickets), color))
                
                # إذا كانت أغنية افتراضية تعمل، قم بتخطيها
                if is_default_playing:
                    msg, color = BotResponses.SKIPPING_DEFAULT_FOR_REQUEST
                    await self.highrise.chat(self.colorize(msg, color))
                    # إنشاء ملف إشارة خاص للأغاني الافتراضية فقط
                    Path("skip_default_only.txt").touch()
                    logger.info(f"⏭️ تخطي أغنية افتراضية لتشغيل طلب {user.username}")
                
                # عرض قائمة الانتظار
                await self.send_queue_status()
                
                # تسجيل الاختيار
                if is_unlimited:
                    logger.info(f"📝 {user.username} (VIP) طلب: {title} ({duration} ثانية)")
                else:
                    remaining_tickets = self.tickets_system.get_user_tickets(user.username)
                    logger.info(f"📝 {user.username} طلب: {title} ({duration} ثانية) (متبقي {remaining_tickets} تذاكر)")
                
            except Exception as e:
                logger.error(f"❌ خطأ في معالجة النتيجة: {e}")
                msg, color = BotResponses.SELECTION_ERROR
                await self.highrise.chat(self.colorize(msg, color))
        
        except Exception as e:
            logger.error(f"❌ خطأ في البحث: {e}")
            msg, color = BotResponses.SEARCH_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    def format_progress_bar(self, percentage: float, length: int = 10) -> str:
        """إنشاء شريط تقدم مرئي"""
        filled = int(percentage * length / 100)
        empty = length - filled
        return "▰" * filled + "▱" * empty
    
    async def send_current_song(self):
        """إرسال معلومات الأغنية الحالية مع التقدم"""
        try:
            if Path(self.notifications_file).exists():
                with open(self.notifications_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                song_title = data.get('song_title', 'لا توجد أغنية')
                duration = data.get('duration_formatted', 'غير معروف')
                requested_by = data.get('requested_by', 'افتراضي')
                
                # الحصول على التقدم
                progress_percent = data.get('current_progress', 0)
                elapsed = data.get('elapsed_formatted', '0:00')
                remaining = data.get('remaining_formatted', '0:00')
                
                # إنشاء شريط التقدم (10 مربعات)
                progress_bar = self.format_progress_bar(progress_percent)
                
                # بناء الرسالة المناسبة
                if requested_by == "افتراضي":
                    message = f"""✦━━━━━━━━━━━━━━━━━━━━━✦
  🎵  {song_title}
✦━━━━━━━━━━━━━━━━━━━━━✦
◈ الطالب  ›  تشغيل تلقائي
◈ المدة   ›  {duration}
{progress_bar}  {progress_percent:.1f}%
⌛ {elapsed}  ✦  ⏳ {remaining}"""
                else:
                    message = f"""✦━━━━━━━━━━━━━━━━━━━━━✦
  🎵  {song_title}
✦━━━━━━━━━━━━━━━━━━━━━✦
◈ الطالب  ›  {requested_by}
◈ المدة   ›  {duration}
{progress_bar}  {progress_percent:.1f}%
⌛ {elapsed}  ✦  ⏳ {remaining}"""
                
                await self.highrise.chat(message)
            else:
                msg, color = BotResponses.NO_SONG_INFO
                await self.highrise.chat(self.colorize(msg, color))
        except Exception as e:
            logger.error(f"❌ خطأ في قراءة الأغنية الحالية: {e}")
            msg, color = BotResponses.SONG_INFO_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    async def send_queue_status(self):
        """إرسال حالة قائمة الانتظار"""
        try:
            if Path(self.queue_file).exists():
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    queue_lines = [line.strip() for line in f.readlines() if line.strip()]
                
                # تحليل الطلبات (أغنية|مستخدم|مدة)
                queue = []
                total_duration = 0
                for line in queue_lines:
                    if '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 2:
                            song = parts[0].strip()
                            user = parts[1].strip()
                            duration_seconds = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 0
                            
                            # تحويل الثواني إلى دقائق:ثواني
                            if duration_seconds > 0:
                                minutes = duration_seconds // 60
                                seconds = duration_seconds % 60
                                duration_str = f"{minutes}:{seconds:02d}"
                                queue.append(f"{song} (طلب: {user}) - ⏱️ {duration_str}")
                                total_duration += duration_seconds
                            else:
                                queue.append(f"{song} (طلب: {user})")
                        else:
                            queue.append(line)
                    else:
                        queue.append(line)
                
                if queue:
                    # حساب إجمالي المدة
                    total_minutes = total_duration // 60
                    total_seconds = total_duration % 60
                    total_duration_str = f"{total_minutes}:{total_seconds:02d}"
                    
                    msg, color = BotResponses.QUEUE_STATUS
                    await self.highrise.chat(self.colorize(msg.format(count=len(queue)), color))
                    
                    # عرض إجمالي المدة إذا كانت هناك أغاني
                    if total_duration > 0:
                        await self.highrise.chat(self.colorize(f"⏱️ **إجمالي مدة الانتظار:** {total_duration_str}", "info"))
                    
                    for i, song_info in enumerate(queue[:5], 1):
                        # تقصير اسم الأغنية إذا كان طويلاً
                        display_song = song_info[:50] + "..." if len(song_info) > 50 else song_info
                        msg, color = BotResponses.QUEUE_SONG_ITEM
                        await self.highrise.chat(self.colorize(msg.format(number=i, song=display_song), color))
                    
                    if len(queue) > 5:
                        msg, color = BotResponses.QUEUE_MORE_ITEMS
                        await self.highrise.chat(self.colorize(msg.format(count=len(queue) - 5), color))
                else:
                    msg, color = BotResponses.QUEUE_EMPTY
                    await self.highrise.chat(self.colorize(msg, color))
            else:
                msg, color = BotResponses.QUEUE_EMPTY
                await self.highrise.chat(self.colorize(msg, color))
        except Exception as e:
            logger.error(f"❌ خطأ في قراءة القائمة: {e}")
    
    async def skip_song(self, user: User):
        """تخطي الأغنية الحالية فوراً (VIP أو المشرفين أو المالك فقط)"""
        try:
            # التحقق من الصلاحيات (VIP أو مشرف أو مالك)
            if not await self.has_unlimited_access(user, show_message=True):
                msg, color = BotResponses.NOT_VIP_OR_STAFF
                await self.highrise.chat(self.colorize(msg.format(username=user.username), color))
                logger.info(f"⛔ {user.username} حاول تخطي الأغنية (غير مسموح)")
                return
            
            # رسالة VIP
            msg, color = BotResponses.VIP_SKIP_UNLIMITED
            await self.highrise.chat(self.colorize(msg, color))
            
            # حفظ الأغنية الحالية
            current_playing = self.current_song
            
            # التحقق من وجود أغنية تالية
            next_song = "الأغنية الافتراضية"
            if Path(self.queue_file).exists():
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
                    if lines:
                        # استخراج اسم الأغنية فقط (بدون اسم المستخدم)
                        next_line = lines[0]
                        if '|' in next_line:
                            next_song = next_line.split('|')[0]
                        else:
                            next_song = next_line
            
            # إرسال إشارة للتخطي
            Path("skip_signal.txt").touch()
            msg, color = BotResponses.SKIPPING_SONG
            await self.highrise.chat(self.colorize(msg, color))
            logger.info(f"⏭️ {user.username} طلب تخطي الأغنية")
            
            # الانتظار والتحقق من نجاح التخطي
            await asyncio.sleep(3)
            
            # التحقق من تغير الأغنية أو اختفاء إشارة التخطي
            skip_file_gone = not Path("skip_signal.txt").exists()
            song_changed = self.current_song != current_playing
            
            if skip_file_gone or song_changed:
                msg, color = BotResponses.SKIP_SUCCESS
                await self.highrise.chat(self.colorize(msg.format(next_song=next_song), color))
            else:
                msg, color = BotResponses.SKIP_TRYING
                await self.highrise.chat(self.colorize(msg, color))
                
        except Exception as e:
            logger.error(f"❌ خطأ في التخطي: {e}")
            msg, color = BotResponses.SKIP_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    async def monitor_current_song(self):
        """مراقبة الأغنية الحالية وإعلانها"""
        while True:
            try:
                await asyncio.sleep(5)
                
                if Path(self.notifications_file).exists():
                    with open(self.notifications_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    song_title = data.get('song_title')
                    
                    # إذا تغيرت الأغنية
                    if song_title and song_title != self.current_song:
                        self.current_song = song_title
                        duration = data.get('duration_formatted', 'غير معروف')
                        requested_by = data.get('requested_by', 'افتراضي')
                        
                        # بناء الرسالة المناسبة
                        if requested_by == "افتراضي":
                            message = f"🎵 الأغنية الجديدة: {song_title} (افتراضي) - ⏱️ {duration}"
                        else:
                            message = f"🎵 الأغنية الجديدة: {song_title} (طلب: {requested_by}) - ⏱️ {duration}"
                        
                        await self.highrise.chat(self.colorize(message, "music"))
                        logger.info(f"🎵 أغنية جديدة: {song_title} - طلب من: {requested_by}")
                        
            except Exception as e:
                logger.error(f"❌ خطأ في المراقبة: {e}")
    
    async def announce_song_status(self):
        """إعلان حالة الأغنية الحالية والتالية كل 5 دقائق"""
        while True:
            try:
                await asyncio.sleep(300)
                
                if Path(self.notifications_file).exists():
                    with open(self.notifications_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    song_title = data.get('song_title')
                    end_time_str = data.get('end_time')
                    
                    if song_title and end_time_str:
                        end_time = datetime.fromisoformat(end_time_str)
                        now = datetime.now()
                        
                        # حساب الوقت المتبقي
                        remaining = end_time - now
                        remaining_seconds = int(remaining.total_seconds())
                        
                        if remaining_seconds > 0:
                            remaining_minutes = remaining_seconds // 60
                            remaining_secs = remaining_seconds % 60
                            
                            # معرفة الأغنية التالية
                            next_song = "أغنية افتراضية"
                            if Path(self.queue_file).exists():
                                with open(self.queue_file, 'r', encoding='utf-8') as f:
                                    lines = [line.strip() for line in f.readlines() if line.strip()]
                                    if lines:
                                        next_line = lines[0]
                                        if '|' in next_line:
                                            parts = next_line.split('|')
                                            song_name = parts[0]
                                            user_name = parts[1] if len(parts) > 1 else "مستخدم"
                                            next_song = f"{song_name} (طلب: {user_name})"
                                        else:
                                            next_song = next_line
                            
                            msg, color = BotResponses.TIME_REMAINING
                            await self.highrise.chat(self.colorize(msg.format(minutes=remaining_minutes, seconds=remaining_secs, next_song=next_song), color))
                            logger.info(f"📢 إعلان حالة: {remaining_minutes}:{remaining_secs:02d} متبقية")
                        
            except Exception as e:
                logger.error(f"❌ خطأ في الإعلان: {e}")
    
    async def continuous_dance_loop(self):
        """حلقة الرقص المستمر للبوت"""
        try:
            # تحميل رقصات البوت من الملف
            with open(self.bot_dances_file, 'r', encoding='utf-8') as f:
                dances_data = json.load(f)
            
            if not dances_data:
                logger.warning("⚠️ لا توجد رقصات محفوظة للرقص المستمر")
                msg, color = BotResponses.NO_DANCES_SAVED
                await self.highrise.chat(self.colorize(msg, color))
                self.is_dancing = False
                return
            
            # قائمة الرقصات
            dance_list = list(dances_data.items())
            dance_index = 0
            
            logger.info(f"💃 بدء الرقص المستمر مع {len(dance_list)} رقصة")
            msg, color = BotResponses.DANCE_STARTED
            await self.highrise.chat(self.colorize(msg.format(count=len(dance_list)), color))
            
            while self.is_dancing:
                # الحصول على الرقصة الحالية
                dance_id, dance_info = dance_list[dance_index]
                duration = dance_info['duration']
                
                # تشغيل الرقصة
                await self.highrise.send_emote(dance_id)
                logger.info(f"💃 رقصة: {dance_id} ({duration}s)")
                
                # الانتظار حتى تنتهي الرقصة
                await asyncio.sleep(duration)
                
                # الانتقال للرقصة التالية
                dance_index = (dance_index + 1) % len(dance_list)
            
        except Exception as e:
            logger.error(f"❌ خطأ في الرقص المستمر: {e}")
            self.is_dancing = False
    
    async def start_continuous_dancing(self):
        """بدء الرقص المستمر للبوت مع معالجة الأخطاء"""
        try:
            if self.is_dancing:
                msg, color = BotResponses.DANCE_ALREADY_RUNNING
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            self.is_dancing = True
            self.dance_task = asyncio.create_task(self.continuous_dance_loop())
            logger.info("✅ تم بدء الرقص المستمر")
        except Exception as e:
            logger.error(f"❌ Error starting dance: {e}")
    
    async def stop_continuous_dancing(self):
        """إيقاف الرقص المستمر للبوت"""
        if not self.is_dancing:
            msg, color = BotResponses.DANCE_ALREADY_STOPPED
            await self.highrise.chat(self.colorize(msg, color))
            return
        
        self.is_dancing = False
        
        if self.dance_task:
            self.dance_task.cancel()
        
        msg, color = BotResponses.DANCE_STOPPED
        await self.highrise.chat(self.colorize(msg, color))
        logger.info("⏹️ تم إيقاف الرقص المستمر")
    
    async def show_user_tickets(self, user: User):
        """عرض عدد تذاكر المستخدم"""
        try:
            tickets = self.tickets_system.get_user_tickets(user.username)
            msg, color = BotResponses.TICKETS_INFO
            await self.highrise.chat(self.colorize(msg.format(count=tickets), color))
        except Exception as e:
            logger.error(f"خطأ في عرض التذاكر: {e}")
    
    async def show_all_tickets(self):
        """عرض قائمة المستخدمين وتذاكرهم"""
        try:
            all_tickets = self.tickets_system.get_all_users_with_tickets()
            
            if not all_tickets:
                msg, color = BotResponses.NO_USERS_WITH_TICKETS
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            msg, color = BotResponses.TICKETS_LIST
            await self.highrise.chat(self.colorize(msg, color))
            
            # ترتيب حسب عدد التذاكر (من الأكثر للأقل)
            sorted_users = sorted(all_tickets.items(), key=lambda x: x[1], reverse=True)
            
            for username, tickets in sorted_users[:10]:  # أول 10 مستخدمين
                msg, color = BotResponses.USER_TICKET_ITEM
                await self.highrise.chat(self.colorize(msg.format(username=username, tickets=tickets), color))
                
        except Exception as e:
            logger.error(f"خطأ في عرض القائمة: {e}")