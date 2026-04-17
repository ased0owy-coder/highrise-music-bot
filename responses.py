"""
ملف ردود البوت - العربية المصرية
كل الرسائل اللي بيبعتها البوت موجودة هنا
"""

class BotResponses:
    """ردود البوت بالألوان"""
    
    # رسائل البداية والترحيب
    STARTUP_MESSAGE = ("🎵 أهلاً! أنا بوت الموسيقى. اكتب !play عشان تطلب أغنية", "music")
    
    WELCOME_MESSAGE = """🎉 أهلاً يا {username}!
📋 الأوامر:
!play <اسم الأغنية> - اطلب أغنية
!np - الأغنية الحالية مع التقدم
!queue - قائمة الانتظار
!tickets - تذاكرك
💡 ابعت تِب للبوت (10g = 5 تذاكر)"""
    
    # رسائل البحث (موجودة أصلاً)
    PLAY_NO_SONG_NAME = ("❌ لازم تكتب اسم الأغنية. مثال: !play فيروز", "error")
    SEARCHING = ("🔍 بدور على: {query}...", "info")
    SEARCH_TIMEOUT = ("⏱️ البحث خد وقت طويل. حاول تاني", "warning")
    SEARCH_FAILED = ("❌ البحث فشل، حاول تاني", "error")
    NO_RESULTS = ("❌ مافيش نتائج", "error")
    SEARCH_ERROR = ("❌ حصل خطأ في البحث", "error")
    
    # رسائل النتائج (موجودة أصلاً)
    SEARCH_RESULTS = ("🎵 نتائج '{query}':{remaining_time}", "music")
    CHOOSE_SONG_MORE = ("اكتب رقم الأغنية أو + عشان تشوف أكتر", "info")
    CHOOSE_SONG = ("اكتب رقم الأغنية", "info")
    NO_MORE_RESULTS = ("❌ مافيش نتائج تانية", "error")
    
    # رسائل الاختيار (موجودة أصلاً)
    INVALID_CHOICE = ("❌ اختيار غلط. اختار من 1 لـ {max}", "error")
    SONG_ADDED = ("✅ تمام، اتضافت: {title}\n⏱️ المدة: {duration}", "success")
    SELECTION_ERROR = ("❌ حصل خطأ في الاختيار", "error")
    
    # 🔴 رسائل الأغنية الحالية **المعدلة**:
    NOW_PLAYING = ("✦━━━━━━━━━━━━━━━━━━━━━✦\n  🎵  {title}\n✦━━━━━━━━━━━━━━━━━━━━━✦\n◈ الطالب  ›  {user}\n◈ المدة   ›  {duration}\n{progress_bar}  {progress_percent:.1f}%\n⌛ {elapsed}  ✦  ⏳ {remaining}", "none")
    
    NOW_PLAYING_DEFAULT = ("✦━━━━━━━━━━━━━━━━━━━━━✦\n  🎵  {title}\n✦━━━━━━━━━━━━━━━━━━━━━✦\n◈ الطالب  ›  تشغيل تلقائي\n◈ المدة   ›  {duration}\n{progress_bar}  {progress_percent:.1f}%\n⌛ {elapsed}  ✦  ⏳ {remaining}", "none")
    
    NO_SONG_INFO = ("🎵 مافيش معلومات عن الأغنية الحالية", "music")
    SONG_INFO_ERROR = ("❌ حصل خطأ في جلب المعلومات", "error")
    
    # رسائل قائمة الانتظار (موجودة أصلاً)
    QUEUE_EMPTY = ("📋 قائمة الانتظار فاضية", "info")
    QUEUE_STATUS = ("📋 قائمة الانتظار ({count} طلب):", "info")
    QUEUE_SONG_ITEM = ("{number}. {song}", "default")
    QUEUE_MORE_ITEMS = ("... و {count} كمان", "info")
    SKIPPING_DEFAULT_FOR_REQUEST = ("⏭️ بتخطى الأغنية العادية عشان أشغل طلبك...", "info")
    
    # رسائل التخطي (موجودة أصلاً)
    SKIP_NOT_OWNER = ("❌ آسف يا {username}, الأمر ده للمالك بس ({owner})", "error")
    SKIPPING_SONG = ("⏭️ بتخطى الأغنية...", "info")
    SKIP_SUCCESS = ("✅ الأغنية اتخطت\n🎵 الجاية: {next_song}", "success")
    SKIP_TRYING = ("⚠️ بحاول أخطي...", "warning")
    SKIP_ERROR = ("❌ حصل خطأ في التخطي", "error")
    
    # رسائل الرقص (موجودة أصلاً)
    NO_DANCES_SAVED = ("⚠️ مافيش رقصات محفوظة للبوت", "warning")
    DANCE_STARTED = ("💃 بديت أرقص! ({count} رقصة)", "dance")
    DANCE_ALREADY_RUNNING = ("💃 أنا برقص أصلاً!", "dance")
    DANCE_ALREADY_STOPPED = ("⚠️ الرقص واقف أصلاً", "warning")
    DANCE_STOPPED = ("⏹️ وقفت الرقص", "warning")
    
    # رسائل نظام التذاكر (موجودة أصلاً)
    NO_TICKETS = ("❌ آسف يا {username}، مامعكش تذاكر. اشتري 5 تذاكر بـ10g", "error")
    TICKET_USED = ("✅ اتخصمت تذكرة واحدة. الباقي: {remaining} تذكرة", "success")
    TICKETS_INFO = ("🎫 معاك {count} تذكرة", "info")
    TIP_RECEIVED = ("💰 شكراً يا {username}!\nاستلمت {gold}g وجبت {tickets} تذكرة\n🎫 مجموع التذاكر: {total}", "success")
    TIP_TOO_SMALL = ("❌ آسف يا {username}، التِب قليل. لازم 10g على الأقل عشان تجيب تذاكر", "warning")
    TICKETS_LIST = ("📋 المستخدمين اللي عندهم تذاكر:", "info")
    NO_USERS_WITH_TICKETS = ("📋 مافيش مستخدمين عندهم تذاكر", "info")
    USER_TICKET_ITEM = ("🎫 {username}: {tickets} تذكرة", "default")
    
    # رسائل نظام VIP (موجودة أصلاً)
    VIP_RECEIVED = ("⭐ مبروك يا {username}!\n💎 انت دلوقتي VIP\n✨ !play و !skip بلا حدود", "success")
    VIP_ALREADY = ("⭐ {username} VIP أصلاً", "warning")
    VIP_SKIP_UNLIMITED = ("⏭️ تخطي بلا حدود", "info")
    NOT_VIP_OR_STAFF = ("❌ آسف يا {username}، !skip للـVIP والمودز والديزاينرز والمالك بس", "error")
    VIP_PLAY_UNLIMITED = ("🎵 طلبات بلا حدود (من غير تذاكر)", "info")
    STAFF_DETECTED = ("🔑 {username} اتكشف كـ{privilege} - صلاحيات بلا حدود", "success")
    VIP_REMINDER = ("💎 عايز أغاني بلا حدود؟\n⭐ اشترك في VIP بـ{price}g!\n✨ طلبات بلا حدود + تخطي بلا حدود\n💬 اكتب !vip عشان تشترك", "info")
    
    # رسائل الإعلانات (موجودة أصلاً)
    TIME_REMAINING = ("⏰ الوقت الباقي: {minutes}:{seconds:02d}\n🎵 الجاية: {next_song}", "default")
    SEARCH_RESULT_ITEM = ("{number}. {title} ({duration})", "default")
    
    # رسائل خدمة البث (موجودة أصلاً)
    STREAM_STARTING = ("🎵 بدء خدمة البث المباشر", "info")
    STREAM_SEARCHING = ("🔍 بدور على: {query}", "info")
    STREAM_DOWNLOADING = ("⬇️ بنزل: {title}", "info")
    STREAM_PLAYING = ("▶️ شغال دلوقتي: {title}", "music")
    STREAM_ENDED = ("✅ البث خلص: {title}", "success")
    STREAM_ERROR = ("❌ خطأ في البث: {error}", "error")
    STREAM_DOWNLOAD_ERROR = ("❌ التنزيل فشل: {error}", "error")
    STREAM_RETRY = ("🔄 بحاول تاني... ({attempt}/{max_attempts})", "warning")
    STREAM_SKIP_SIGNAL = ("⏭️ إشارة التخطي اتلقت", "info")
    STREAM_SWITCHING_DEFAULT = ("🎶 التحويل للأغنية العادية", "info")
    STREAM_NO_SONGS = ("⚠️ مافيش أغاني متاحة", "warning")
    STREAM_QUEUE_EMPTY = ("📋 قائمة الانتظار فاضية", "info")
    
    # رسائل مدير قائمة التشغيل (موجودة أصلاً)
    PLAYLIST_LOADED = ("✅ اتحملت {count} أغنية عادية", "success")
    PLAYLIST_LOADED_ERROR = ("❌ فشل تحميل القائمة العادية", "error")
    PLAYLIST_CREATED = ("✅ اتعملت قائمة عادية بـ{count} أغنية", "success")
    PLAYLIST_STATE_LOADED = ("✅ اتحملت حالة التشغيل المحفوظة", "success")
    PLAYLIST_STATE_NOT_FOUND = ("⚠️ مافيش حالة محفوظة", "warning")
    PLAYLIST_STATE_LOAD_ERROR = ("❌ فشل تحميل حالة القائمة", "error")
    PLAYLIST_STATE_SAVED = ("✅ حالة القائمة اتحفظت", "success")
    PLAYLIST_STATE_SAVE_ERROR = ("❌ فشل حفظ حالة القائمة", "error")
    PLAYLIST_USER_REQUEST = ("🎵 طلب مستخدم (معاينة، محاولة {attempt}): {song}", "info")
    PLAYLIST_DEFAULT_SONG = ("🎶 أغنية عادية: {song}", "info")
    PLAYLIST_REQUEST_SUCCESS = ("✅ بدأ طلب المستخدم بنجاح: {song}", "success")
    PLAYLIST_REQUEST_DELETED = ("✅ الطلب اتمسح بعد التشغيل الناجح", "success")
    PLAYLIST_REQUEST_FAILED = ("❌ الطلب فشل {song} - محاولة {attempt}/{max_attempts}", "error")
    PLAYLIST_MAX_ATTEMPTS = ("⚠️ وصلنا لأقصى محاولات: {song}", "warning")
    PLAYLIST_MOVED_TO_END = ("🔄 الطلب الفاشل اتنقل لآخر القائمة: {song}", "info")
    PLAYLIST_SONG_FINISHED = ("✅ الأغنية خلصت: {song}", "success")
    PLAYLIST_QUEUE_CLEARED = ("🧹 القائمة اتمسحت (فاضية)", "info")
    PLAYLIST_SONG_ADDED = ("✅ الأغنية اتضافت للقائمة العادية: {song}", "success")
    PLAYLIST_SONG_EXISTS = ("⚠️ الأغنية موجودة أصلاً: {song}", "warning")
    PLAYLIST_SONG_REMOVED = ("✅ الأغنية اتشالت: {song}", "success")
    PLAYLIST_SONG_NOT_FOUND = ("⚠️ الأغنية مش موجودة في القائمة: {song}", "warning")
    PLAYLIST_NOW_PLAYING = ("▶️ شغال دلوقتي: {song}", "music")
    PLAYLIST_END = ("✅ القائمة خلصت", "info")
    PLAYLIST_USING_DEFAULT = ("🎶 استخدام القائمة العادية", "info")
    PLAYLIST_EMPTY = ("⚠️ القائمة فاضية", "warning")
    PLAYLIST_SONG_SKIPPED = ("⏭️ الأغنية اتخطت: {song}", "info")
    PLAYLIST_MANAGER_STARTED = ("🎵 مدير قائمة التشغيل المستمرة شغال", "info")
    PLAYLIST_NO_SONGS_AVAILABLE = ("⚠️ مافيش أغاني متاحة", "warning")
    
    # رسائل التحكم في التخطي للبث (موجودة أصلاً)
    STREAM_SKIP_IGNORED_DOWNLOADING = ("🔒 تجاهل إشارة التخطي - بنزل طلب المستخدم", "info")
    STREAM_SKIP_DEFAULT_FOR_USER = ("⏭️ تخطي الأغنية العادية عشان أشغل طلب المستخدم فوراً", "info")
    STREAM_DEFAULT_STOPPED = ("✅ الأغنية العادية وقفت", "success")
    STREAM_SKIP_DEFAULT_SPECIAL = ("⏭️ تخطي الأغنية العادية (إشارة خاصة)", "info")
    STREAM_SKIP_IGNORED_USER_REQUEST = ("🔒 تجاهل إشارة التخطي - الأغنية الحالية طلب مستخدم", "info")
    STREAM_SKIP_CURRENT_FOR_USER = ("⏭️ تخطي الأغنية الحالية عشان أشغل طلب المستخدم فوراً", "info")
    
    # رسائل بدء النظام (موجودة أصلاً)
    SYSTEM_STARTING = ("🚀 بدء نظام Highrise Music Bot", "info")
    SYSTEM_BOT_STARTING = ("🤖 تشغيل بوت Highrise...", "info")
    SYSTEM_STREAMER_STARTING = ("📡 تشغيل خدمة البث...", "info")
    SYSTEM_STOPPING = ("⏹️ إيقاف النظام...", "info")
    SYSTEM_TOKEN_MISSING = ("❌ لازم تحط HIGHRISE_BOT_TOKEN و HIGHRISE_ROOM_ID في Secrets", "error")
    
    # رسائل بوت Highrise (موجودة أصلاً)
    BOT_VIP_REMINDER_SENT = ("💎 تم إرسال تذكير VIP", "info")
    BOT_STAFF_CHECK_PERIODIC = ("🔍 بدء الفحص الدوري للمشرفين...", "info")
    BOT_STAFF_CHECK_INITIAL = ("🔍 بدء الفحص الأولي للمشرفين...", "info")
    BOT_NO_NEW_STAFF = ("✅ مافيش مشرفين جدد", "success")
    BOT_NO_DANCES_SAVED = ("⚠️ مافيش رقصات محفوظة للرقص المستمر", "warning")
    BOT_CONTINUOUS_DANCE_STARTED = ("✅ بدأ الرقص المستمر", "success")
    BOT_CONTINUOUS_DANCE_STOPPED = ("⏹️ وقف الرقص المستمر", "info")
    
    # رسائل التصفير (موجودة أصلاً)
    RESET_SUCCESS = ("♻️ تم تصفير البوت بنجاح! تم مسح جميع الطلبات وقائمة التشغيل.", "success")
    NO_PERMISSION = ("❌ ليس لديك صلاحية لاستخدام هذا الأمر.", "error")