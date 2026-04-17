
"""
نظام التذاكر - إدارة التذاكر والإكراميات
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger('tickets_system')

class TicketsSystem:
    """نظام إدارة التذاكر و VIP"""
    
    def __init__(self, tickets_file: str = "tickets_data.json", vip_file: str = "vip_users.json"):
        self.tickets_file = tickets_file
        self.vip_file = vip_file
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """التأكد من وجود ملفات التذاكر و VIP"""
        if not Path(self.tickets_file).exists():
            with open(self.tickets_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
        
        if not Path(self.vip_file).exists():
            with open(self.vip_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def get_user_tickets(self, username: str) -> int:
        """الحصول على عدد تذاكر المستخدم"""
        try:
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get(username, 0)
        except Exception as e:
            logger.error(f"خطأ في قراءة التذاكر: {e}")
            return 0
    
    def add_tickets(self, username: str, amount: int) -> int:
        """إضافة تذاكر للمستخدم"""
        try:
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            current = data.get(username, 0)
            new_total = current + amount
            data[username] = new_total
            
            with open(self.tickets_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ تم إضافة {amount} تذكرة لـ {username} (الإجمالي: {new_total})")
            return new_total
        except Exception as e:
            logger.error(f"خطأ في إضافة التذاكر: {e}")
            return 0
    
    def use_ticket(self, username: str) -> bool:
        """استخدام تذكرة واحدة"""
        try:
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            current = data.get(username, 0)
            
            if current <= 0:
                return False
            
            data[username] = current - 1
            
            with open(self.tickets_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"🎫 {username} استخدم تذكرة (المتبقي: {current - 1})")
            return True
        except Exception as e:
            logger.error(f"خطأ في استخدام التذكرة: {e}")
            return False
    
    def get_all_users_with_tickets(self) -> dict:
        """الحصول على قائمة جميع المستخدمين وتذاكرهم"""
        try:
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {k: v for k, v in data.items() if v > 0}
        except Exception as e:
            logger.error(f"خطأ في قراءة القائمة: {e}")
            return {}
    
    def add_vip(self, username: str) -> bool:
        """إضافة مستخدم إلى قائمة VIP"""
        try:
            with open(self.vip_file, 'r', encoding='utf-8') as f:
                vip_users = json.load(f)
            
            if username not in vip_users:
                vip_users.append(username)
                
                with open(self.vip_file, 'w', encoding='utf-8') as f:
                    json.dump(vip_users, f, ensure_ascii=False, indent=2)
                
                logger.info(f"⭐ {username} أصبح VIP")
                return True
            
            return False
        except Exception as e:
            logger.error(f"خطأ في إضافة VIP: {e}")
            return False
    
    def is_vip(self, username: str) -> bool:
        """التحقق من أن المستخدم VIP"""
        try:
            with open(self.vip_file, 'r', encoding='utf-8') as f:
                vip_users = json.load(f)
            return username in vip_users
        except Exception as e:
            logger.error(f"خطأ في التحقق من VIP: {e}")
            return False
    
    def get_all_vips(self) -> list:
        """الحصول على قائمة جميع VIP"""
        try:
            with open(self.vip_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"خطأ في قراءة قائمة VIP: {e}")
            return []
