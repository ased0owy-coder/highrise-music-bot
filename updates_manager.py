
#!/usr/bin/env python3
"""
نظام إدارة التحديثات والملفات - نسخة محدثة بدون مفتاح API
"""

from flask import Flask, request, jsonify, send_file, render_template_string
from werkzeug.utils import secure_filename
import os
import zipfile
import io
from pathlib import Path
import json
from datetime import datetime
import shutil
import difflib

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max

# المجلدات المستبعدة من التنزيل
EXCLUDED_DIRS = [
    'song_cache',
    '__pycache__',
    '.git',
    'venv',
    'node_modules',
    '.cache',
    'downloads',
    'backups',
    '.upm',
    '.config',
    '.pythonlibs',
    'env',
    '.venv',
    'attached_assets'
]

# امتدادات الملفات المستبعدة (ملفات البيانات)
EXCLUDED_EXTENSIONS = [
    '.log',  # ملفات السجلات
    '.tmp',  # ملفات مؤقتة
    '.cache',  # ملفات الكاش
    '.pyc',  # Python compiled
    '.pyo',  # Python optimized
]

# أسماء ملفات محددة مستبعدة
EXCLUDED_FILES = [
    'tickets_data.json',
    'vip_users.json',
    'staff_cache.json',
    'playlist_state.json',
    'play_history.txt',
    'queue.txt',
    'current_song.json',
    'song_notifications.json',
    'update_history.json',
    '.replit',
    'replit.nix',
    '.env',
    '.gitignore',
    'poetry.lock',
    'package-lock.json',
    'pyproject.toml',
    'uv.lock'
]

# ملفات txt المسموحة
ALLOWED_TXT_FILES = [
    'requirements.txt',
    'README.txt',
]

def should_exclude_from_download(file_path):
    """التحقق من استبعاد الملف من التنزيل"""
    file_path_obj = Path(file_path)
    file_name = file_path_obj.name
    file_str = str(file_path)
    
    # السماح بملفات EDX الخاصة
    if file_name.startswith('.EDX_') or file_name == '.edx_helper.py':
        return False
    
    # استبعاد الملفات المخفية (تبدأ بنقطة) ما عدا .gitkeep و EDX files
    if file_name.startswith('.') and file_name != '.gitkeep':
        return True
    
    # السماح بملفات txt المحددة
    if file_path_obj.suffix.lower() == '.txt' and file_name in ALLOWED_TXT_FILES:
        return False
    
    # استبعاد ملفات txt الأخرى
    if file_path_obj.suffix.lower() == '.txt':
        return True
    
    # استبعاد ملفات json للبيانات
    if file_path_obj.suffix.lower() == '.json' and file_name in EXCLUDED_FILES:
        return True
    
    # استبعاد حسب الامتداد
    if file_path_obj.suffix.lower() in EXCLUDED_EXTENSIONS:
        return True
    
    # استبعاد ملفات محددة
    if file_name in EXCLUDED_FILES:
        return True
    
    # استبعاد المجلدات المحددة
    for excluded_dir in EXCLUDED_DIRS:
        if excluded_dir in file_str:
            return True
    
    # استبعاد ملفات ZIP المؤقتة
    if file_name.startswith('temp_download_'):
        return True
    
    return False

def get_file_similarity(filename1, filename2):
    """حساب نسبة التشابه بين اسمي ملفين"""
    return difflib.SequenceMatcher(None, filename1.lower(), filename2.lower()).ratio() * 100

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    with open('updates.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/api/search-similar-files', methods=['POST'])
def search_similar_files():
    """البحث عن ملفات مشابهة"""
    try:
        data = request.json or {}
        filename = data.get('filename', '')
        
        similar_files = []
        
        for root, dirs, files in os.walk('.'):
            # تصفية المجلدات المستبعدة
            dirs[:] = [d for d in dirs if d not in ['song_cache', '__pycache__', '.git', 'venv', 'backups', 'downloads']]
            
            for file in files:
                file_path = Path(root) / file
                similarity = get_file_similarity(filename, file)
                
                if similarity > 30:  # تشابه أكثر من 30%
                    similar_files.append({
                        'name': file,
                        'path': str(file_path),
                        'size': file_path.stat().st_size,
                        'similarity': round(similarity, 1)
                    })
        
        # ترتيب حسب التشابه
        similar_files.sort(key=lambda x: x['similarity'], reverse=True)
        
        return jsonify({'success': True, 'similar_files': similar_files[:10]})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/add-file-to-project', methods=['POST'])
def add_file_to_project():
    """إضافة ملف جديد للمشروع"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'لا يوجد ملف'}), 400
        
        file = request.files['file']
        file_path = request.form.get('file_path', file.filename) or file.filename
        
        # التأكد من المسار
        target_path = Path(file_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # حفظ الملف
        file.save(str(target_path))
        
        return jsonify({
            'success': True,
            'message': f'تم إضافة الملف {file_path} بنجاح',
            'file_path': file_path
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/update-existing-file', methods=['POST'])
def update_existing_file():
    """تحديث ملف موجود مع حفظ نسخة احتياطية"""
    try:
        if 'new_file' not in request.files:
            return jsonify({'success': False, 'error': 'لا يوجد ملف'}), 400
        
        new_file = request.files['new_file']
        target_file_path = request.form.get('target_file_path')
        
        if not target_file_path:
            return jsonify({'success': False, 'error': 'لم يتم تحديد الملف المستهدف'}), 400
        
        target_path = Path(target_file_path)
        
        # حفظ نسخة احتياطية
        backup_path = None
        if target_path.exists():
            backup_dir = Path('backups')
            backup_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = backup_dir / f"{target_path.name}_{timestamp}.backup"
            shutil.copy2(target_path, backup_path)
        
        # حفظ الملف الجديد
        new_file.save(str(target_path))
        
        return jsonify({
            'success': True,
            'message': f'تم تحديث {target_file_path} بنجاح',
            'backup_path': str(backup_path) if backup_path else None
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analyze-update-file', methods=['POST'])
def analyze_update_file():
    """تحليل ملف ZIP قبل التطبيق"""
    try:
        if 'update_file' not in request.files:
            return jsonify({'success': False, 'error': 'لا يوجد ملف'}), 400
        
        update_file = request.files['update_file']
        
        # حفظ مؤقت
        temp_path = Path('temp_update.zip')
        update_file.save(str(temp_path))
        
        analysis = {
            'total_files': 0,
            'new_files': [],
            'updated_files': [],
            'python_files': [],
            'web_files': [],
            'estimated_time': 0
        }
        
        with zipfile.ZipFile(temp_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            analysis['total_files'] = len(file_list)
            
            for file_name in file_list:
                if file_name.endswith('/'):
                    continue
                
                file_info = zip_ref.getinfo(file_name)
                file_size = file_info.file_size
                
                file_data = {
                    'name': Path(file_name).name,
                    'path': file_name,
                    'size': f'{file_size / 1024:.1f} KB' if file_size > 1024 else f'{file_size} B',
                    'status': 'جديد' if not Path(file_name).exists() else 'تحديث'
                }
                
                if Path(file_name).exists():
                    analysis['updated_files'].append(file_data)
                else:
                    analysis['new_files'].append(file_data)
                
                # تصنيف الملفات
                if file_name.endswith('.py'):
                    analysis['python_files'].append(file_data)
                elif file_name.endswith(('.html', '.css', '.js')):
                    analysis['web_files'].append(file_data)
            
            # تقدير الوقت (0.1 ثانية لكل ملف)
            analysis['estimated_time'] = len(file_list) * 0.1
        
        # حذف الملف المؤقت
        temp_path.unlink()
        
        return jsonify({'success': True, 'analysis': analysis})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/apply-local-update', methods=['POST'])
def apply_local_update():
    """تطبيق تحديث ZIP محلي"""
    try:
        if 'update_file' not in request.files:
            return jsonify({'success': False, 'error': 'لا يوجد ملف'}), 400
        
        update_file = request.files['update_file']
        
        # حفظ الملف
        update_path = Path('temp_update.zip')
        update_file.save(str(update_path))
        
        # إنشاء نسخة احتياطية
        backup_dir = Path('backups')
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        files_processed = 0
        new_files = []
        updated_files = []
        
        start_time = datetime.now()
        
        # استخراج الملفات
        with zipfile.ZipFile(update_path, 'r') as zip_ref:
            for file_name in zip_ref.namelist():
                if file_name.endswith('/'):
                    continue
                
                target_path = Path(file_name)
                
                # حفظ نسخة احتياطية للملفات الموجودة
                if target_path.exists():
                    backup_path = backup_dir / f"{target_path.name}_{timestamp}.backup"
                    shutil.copy2(target_path, backup_path)
                    updated_files.append(file_name)
                else:
                    new_files.append(file_name)
                
                # إنشاء المجلدات إذا لزم الأمر
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # استخراج الملف
                with zip_ref.open(file_name) as source, open(target_path, 'wb') as target:
                    shutil.copyfileobj(source, target)
                
                files_processed += 1
        
        # حذف الملف المؤقت
        update_path.unlink()
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # حفظ سجل التحديث
        update_log = {
            'filename': update_file.filename,
            'applied_date': datetime.now().isoformat(),
            'files_processed': files_processed,
            'processing_time': processing_time
        }
        
        log_file = Path('update_history.json')
        history = []
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        
        history.insert(0, update_log)
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(history[:50], f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'تم تطبيق التحديث بنجاح',
            'files_processed': files_processed,
            'processing_time': processing_time,
            'backup_path': str(backup_dir),
            'summary': {
                'new_files': new_files,
                'updated_files': updated_files
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get-room-users', methods=['GET'])
def get_room_users():
    """جلب قائمة المستخدمين في الغرفة"""
    try:
        # قراءة قائمة المشرفين من الملف
        staff = {}
        if os.path.exists('staff_cache.json'):
            with open('staff_cache.json', 'r', encoding='utf-8') as f:
                staff = json.load(f)
        
        # قراءة التذاكر لمعرفة الـ VIP
        vip_users = []
        if os.path.exists('vip_users.json'):
            with open('vip_users.json', 'r', encoding='utf-8') as f:
                vip_users = json.load(f)
                
        # بما أننا لا نستطيع التواصل مباشرة مع البوت، سنعتمد على البيانات المحفوظة
        # في بيئة الإنتاج، يمكن للبوت كتابة قائمة الحضور الحالية في ملف JSON
        current_users_file = Path('current_users.json')
        users = []
        if current_users_file.exists():
            with open(current_users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
        
        # إضافة تصنيف لكل مستخدم
        for user in users:
            username = user.get('username', '')
            if username == os.environ.get('OWNER_USERNAME', 'Owner'):
                user['role'] = 'ملك 👑'
            elif username in staff:
                user['role'] = f'مشرف ({staff[username]}) 🛡️'
            elif username in vip_users:
                user['role'] = 'VIP ✨'
            else:
                user['role'] = 'عادي 👤'
                
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/execute-command', methods=['POST'])
def execute_command():
    """تنفيذ أمر برمجي برمز سري"""
    try:
        data = request.json or {}
        password = data.get('password', '')
        command = data.get('command', '')
        
        admin_password = os.environ.get("ADMIN_PASSWORD", "101010")
        if password != admin_password:
            return jsonify({'success': False, 'error': 'كلمة مرور خاطئة'}), 403
            
        # كتابة الأمر في ملف queue.txt ليقوم البوت بمعالجته
        # أو تنفيذ إجراءات معينة مباشرة
        if command == 'reset':
            with open('queue.txt', 'w', encoding='utf-8') as f:
                f.write('')
            return jsonify({'success': True, 'message': 'تم تصفير قائمة الانتظار'})
        elif command == 'skip':
            with open('skip_signal.txt', 'w', encoding='utf-8') as f:
                f.write('skip')
            return jsonify({'success': True, 'message': 'تم إرسال إشارة التخطي'})
            
        return jsonify({'success': False, 'error': 'أمر غير معروف'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/download-core', methods=['POST'])
def download_core_files():
    """تنزيل الملفات الأساسية (بدون ملفات البيانات والتنزيلات)"""
    temp_zip_path = None
    try:
        data = request.get_json()
        password = data.get('password', '') if data else ''
        
        core_download_password = os.environ.get("CORE_DOWNLOAD_PASSWORD", "0101")
        if password != core_download_password:
            return jsonify({'success': False, 'error': 'كلمة مرور خاطئة'}), 403
        
        # اسم الملف برقم الإصدار الثابت
        version = '1.53.0'
        temp_zip_path = Path(f'temp_download_{version}.zip')
        
        # حذف الملف المؤقت إذا كان موجوداً
        if temp_zip_path.exists():
            temp_zip_path.unlink()
        
        # إنشاء ملف ZIP
        files_added = 0
        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk('.'):
                # تصفية المجلدات المستبعدة
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith('.')]
                
                for file in files:
                    file_path = Path(root) / file
                    
                    if not should_exclude_from_download(file_path):
                        try:
                            zf.write(file_path, arcname=str(file_path))
                            files_added += 1
                            print(f"✅ إضافة: {file_path}")
                        except Exception as e:
                            print(f"⚠️ تخطي ملف {file_path}: {e}")
        
        # التحقق من أن الملف تم إنشاؤه بنجاح
        if not temp_zip_path.exists() or temp_zip_path.stat().st_size == 0:
            raise Exception("فشل في إنشاء ملف ZIP")
        
        print(f"✅ تم إنشاء ZIP بنجاح: {files_added} ملف")
        
        # إرسال الملف
        def generate():
            with open(temp_zip_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    yield chunk
            # حذف الملف بعد الإرسال
            try:
                temp_zip_path.unlink()
            except:
                pass
        
        return app.response_class(
            generate(),
            mimetype='application/zip',
            headers={
                'Content-Disposition': f'attachment; filename=highrise_bot_v{version}.zip',
                'Content-Type': 'application/zip'
            }
        )
    
    except Exception as e:
        # حذف الملف المؤقت في حالة الخطأ
        if temp_zip_path and temp_zip_path.exists():
            try:
                temp_zip_path.unlink()
            except:
                pass
        print(f"❌ خطأ في تنزيل ZIP: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/check-updates', methods=['GET'])
def check_updates():
    """التحقق من التحديثات المتاحة"""
    return jsonify({'success': True, 'updates': []})

@app.route('/api/system-info', methods=['GET'])
def system_info():
    """معلومات النظام وسجل التحديثات"""
    try:
        log_file = Path('update_history.json')
        history = []
        
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        
        return jsonify({
            'success': True,
            'system_info': {
                'installed_updates': history
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # إنشاء مجلد النسخ الاحتياطية
    Path('backups').mkdir(exist_ok=True)
    
    # تشغيل السيرفر
    port = int(os.environ.get('UPDATES_PORT', 8080))
    print("=" * 60)
    print(f"🚀 سيرفر التحديثات يعمل على البورت: {port}")
    print(f"📱 افتح الرابط: http://0.0.0.0:{port}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=False)
