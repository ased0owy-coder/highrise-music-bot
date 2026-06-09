#!/usr/                    queue_linesself.dance_task = asyncio.create_task(self.continuous_dance_loop())
            logger.info("✅ تم بدء الرقص المستمر")
        except Exception as e:
            logger.error(f"❌ Error starting dance: {e}")
    
    async def stop_continuous_dancing(self):
        """إيقاف الرقص المستمر للبوت"""logger.error(f"خطأ في عرض القائمة: {e}")
