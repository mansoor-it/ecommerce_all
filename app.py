from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from database import db
from flask import Flask, request, url_for
from werkzeug.utils import secure_filename

# استيراد محرك البحث بالصورة
from image_search.search_engine import ImageSearchEngine
from image_search.vectorizer import get_image_embedding
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
# -----------------------------------
# إعدادات البحث بالصورة
# -----------------------------------

# المجلد الذي توجد به صور المنتجات (قاعدة البيانات) التي نريد البحث ضمنها
# يمكنك اختيار مجلد jpg أو png أو كلاهما. في المثال التالي سنأخذ مجلد jpg.
IMAGES_DB_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads', 'jpg')

# مجلد حفظ الصورة التي سيقوم المستخدم برفعها لأجل البحث
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads', 'png')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# بناء محرك البحث FAISS عند بدء التطبيق
image_search_engine = ImageSearchEngine(IMAGES_DB_FOLDER)
image_search_engine.build_index()


def allowed_file(filename):
    """
    للتأكد من أن امتداد الملف ضمن المسموح به (png, jpg, jpeg).
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# -----------------------------------
# إنشاء مجلد الصور إذا لم يكن موجوداً
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.email = user_data['email']
        self.user_type = user_data['user_type']
        self.store_id = user_data.get('store_id')

@login_manager.user_loader
def load_user(user_id):
    user_data = db.get_user_by_id(user_id)
    if user_data:
        return User(user_data)
    return None

# تعريف الصور الافتراضية للأقسام
DEFAULT_CATEGORY_IMAGES = {
    'ملابس رجالية': 'https://images.unsplash.com/photo-1617137968427-85924c800a22?w=800&auto=format&fit=crop',
    'ملابس نسائية': 'https://images.unsplash.com/photo-1483985988355-763728e1935b?w=800&auto=format&fit=crop',
    'أطفال': 'https://images.unsplash.com/photo-1622290291468-a28f7a7dc6a8?w=800&auto=format&fit=crop',
    'إلكترونيات': 'https://images.unsplash.com/photo-1550009158-9ebf69173e03?w=800&auto=format&fit=crop',
    'هواتف': 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=800&auto=format&fit=crop',
    'أحذية': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800&auto=format&fit=crop'
}

print("\n=== قاموس الصور الافتراضية ===")
for name, image in DEFAULT_CATEGORY_IMAGES.items():
    print(f"اسم القسم في القاموس: '{name}'")
    print(f"طول الاسم: {len(name)}")
    print(f"الصورة: {image}")
    print("---")

# Routes
@app.route('/')
def home():
    try:
        # التحقق من الاتصال بقاعدة البيانات
        if not db.is_connected():
            flash('لا يمكن الاتصال بقاعدة البيانات حالياً', 'error')
            return render_template('home.html', categories=[], stores=[], products=[])

        # جلب الأقسام
        categories = db.get_all_categories()
        print("\n=== الأقسام الموجودة في قاعدة البيانات ===")
        for cat in categories:
            print(f"اسم القسم: '{cat['name']}'")
            print(f"طول الاسم: {len(cat['name'])}")
            print("---")
        
        # إضافة الصور الافتراضية للأقسام
        for category in categories:
            print(f"\nمعالجة القسم: '{category['name']}'")
            print(f"هل يوجد صورة في القاموس؟ {category['name'] in DEFAULT_CATEGORY_IMAGES}")
            print(f"مقارنة مباشرة:")
            for dict_name in DEFAULT_CATEGORY_IMAGES.keys():
                print(f"- '{dict_name}' == '{category['name']}'? {dict_name == category['name']}")
            category['image'] = DEFAULT_CATEGORY_IMAGES.get(category['name'], 'https://images.unsplash.com/photo-1498049794561-7780e7231661?w=800&auto=format&fit=crop')
            print(f"الصورة المخصصة: {category['image']}")

        # جلب المتاجر المميزة
        stores = db.get_featured_stores()
        
        # جلب المنتجات الأكثر مبيعاً
        products = db.get_top_products()
        
        return render_template('home.html', 
                             categories=categories,
                             stores=stores,
                             products=products)
    except Exception as e:
        print(f"خطأ في الصفحة الرئيسية: {str(e)}")
        flash('حدث خطأ أثناء تحميل الصفحة الرئيسية', 'error')
        return render_template('home.html', categories=[], stores=[], products=[])

@app.route('/category/<category>')
def category(category):
    if not db.is_connected():
        flash('لا يمكن الاتصال بقاعدة البيانات. يرجى المحاولة لاحقاً')
        return render_template('error.html', message='خطأ في الاتصال بقاعدة البيانات')
    
    try:
        category_data = db.get_category_by_id(category)
        if not category_data:
            flash('القسم غير موجود')
            return redirect(url_for('home'))
        
        stores = db.get_stores_by_category(category)
        print(f"تم جلب {len(stores)} متجر للقسم {category_data['name']}")  # للتأكد من عدد المتاجر
        
        return render_template('category.html', 
                             stores=stores, 
                             category=category_data)
    except Exception as e:
        print(f"خطأ في صفحة القسم: {str(e)}")  # للتأكد من الأخطاء
        flash('حدث خطأ أثناء جلب البيانات')
        return render_template('error.html', message=str(e))

@app.route('/store/<store_id>')
def store(store_id):
    if not db.is_connected():
        flash('لا يمكن الاتصال بقاعدة البيانات. يرجى المحاولة لاحقاً')
        return render_template('error.html', message='خطأ في الاتصال بقاعدة البيانات')
    
    try:
        store = db.get_store_by_id(store_id)
        if not store:
            flash('المتجر غير موجود')
            return redirect(url_for('home'))
        
        products = db.get_store_products(store_id)
        category = db.get_category_by_id(store['category'])
        
        return render_template('store/store.html',
                             store=store,
                             products=products,
                             category=category)
    except Exception as e:
        print(f"خطأ في صفحة المتجر: {str(e)}")  # للتأكد من الأخطاء
        flash('حدث خطأ أثناء جلب البيانات')
        return render_template('error.html', message=str(e))

@app.route('/store/<store_id>')
def store_view(store_id):
    """صفحة عرض المتجر للزبائن"""
    if not db.is_connected():
        flash('لا يمكن الاتصال بقاعدة البيانات. يرجى المحاولة لاحقاً')
        return render_template('error.html', message='خطأ في الاتصال بقاعدة البيانات')
    
    try:
        store = db.get_store_by_id(store_id)
        if not store:
            flash('المتجر غير موجود')
            return redirect(url_for('home'))
        
        products = db.get_store_products(store_id)
        category = db.get_category_by_id(store['category'])
        
        return render_template('store/store_view.html',
                             store=store,
                             products=products,
                             category=category)
    except Exception as e:
        print(f"خطأ في صفحة عرض المتجر: {str(e)}")
        flash('حدث خطأ أثناء جلب البيانات')
        return render_template('error.html', message=str(e))

@app.route('/store/dashboard')
@login_required
def store_dashboard():
    store = db.get_store_by_owner(current_user.id)
    if not store:
        flash('يجب إنشاء متجر أولاً', 'warning')
        return redirect(url_for('create_store'))
    
    # الحصول على المنتجات
    products = db.get_store_products(store['_id'])
    
    # الحصول على القسم
    category = db.get_category_by_id(store['category']) if store.get('category') else None
    
    # حساب الإحصائيات
    total_products = len(products)
    active_products = len([p for p in products if p.get('is_active', True)])
    
    # الحصول على الطلبات الجديدة (آخر 24 ساعة)
    new_orders = db.get_store_orders(store['_id'], days=1)
    new_orders_count = len(new_orders)
    
    # حساب إجمالي المبيعات
    total_sales = sum(order.get('total', 0) for order in new_orders)
    
    return render_template('store/dashboard.html',
                         store=store,
                         products=products,
                         category=category,
                         total_products=total_products,
                         active_products=active_products,
                         new_orders_count=new_orders_count,
                         total_sales=total_sales)

# مسارات السلة
@app.route('/cart')
@login_required
def cart():
    print("\n=== عرض السلة ===")
    print(f"المستخدم الحالي: {current_user.id}")
    
    if not db.is_connected():
        print("خطأ: لا يوجد اتصال بقاعدة البيانات")
        flash('لا يمكن الاتصال بقاعدة البيانات. يرجى المحاولة لاحقاً', 'error')
        return render_template('error.html', message='خطأ في الاتصال بقاعدة البيانات')
    
    try:
        print("جاري جلب محتويات السلة...")
        cart_items = db.get_cart(current_user.id)
        print(f"تم جلب {len(cart_items)} عنصر من السلة")
        
        if not cart_items:
            print("السلة فارغة")
            return render_template('cart.html', cart_items=[], total=0)
        
        total = sum(item['price'] * item['quantity'] for item in cart_items)
        print(f"المجموع الكلي: {total}")
        
        return render_template('cart.html', cart_items=cart_items, total=total)
    except Exception as e:
        print(f"خطأ في عرض السلة: {str(e)}")
        import traceback
        print(traceback.format_exc())
        flash('حدث خطأ أثناء عرض السلة', 'error')
        return render_template('error.html', message=str(e))

@app.route('/cart/add/<product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    try:
        success = db.add_to_cart(current_user.id, product_id)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/cart/update/<product_id>', methods=['POST'])
def update_cart_item(product_id):
    """تحديث كمية منتج في السلة"""
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'message': 'يجب تسجيل الدخول أولاً'})
    
    try:
        quantity = int(request.form.get('quantity', 1))
        if quantity < 1:
            return jsonify({'success': False, 'message': 'الكمية يجب أن تكون 1 على الأقل'})
        
        # الحصول على الحجم واللون من المنتج في السلة
        cart = db.get_cart(current_user.id)
        item = next((item for item in cart if item['id'] == product_id), None)
        
        if not item:
            return jsonify({'success': False, 'message': 'المنتج غير موجود في السلة'})
        
        # تحديث الكمية
        success = db.update_cart_item_quantity(
            current_user.id,
            product_id,
            item['quantity'] + quantity,
            item.get('size'),
            item.get('color')
        )
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'حدث خطأ أثناء تحديث الكمية'})
            
    except Exception as e:
        print(f"خطأ في تحديث الكمية: {str(e)}")
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء تحديث الكمية'})

@app.route('/cart/remove/<product_id>', methods=['POST'])
def remove_cart_item(product_id):
    """حذف منتج من السلة"""
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'message': 'يجب تسجيل الدخول أولاً'})
    
    try:
        # الحصول على الحجم واللون من المنتج في السلة
        cart = db.get_cart(current_user.id)
        item = next((item for item in cart if item['id'] == product_id), None)
        
        if not item:
            return jsonify({'success': False, 'message': 'المنتج غير موجود في السلة'})
        
        # حذف المنتج
        success = db.remove_from_cart(
            current_user.id,
            product_id,
            item.get('size'),
            item.get('color')
        )
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'حدث خطأ أثناء حذف المنتج'})
            
    except Exception as e:
        print(f"خطأ في حذف المنتج: {str(e)}")
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء حذف المنتج'})

@app.route('/cart/clear', methods=['POST'])
@login_required
def clear_cart():
    try:
        success = db.clear_cart(current_user.id)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']
        name = request.form['name']
        
        if db.get_user_by_email(email):
            flash('البريد الإلكتروني مستخدم بالفعل')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        user_id = db.create_user(email, hashed_password, user_type, name)
        
        if user_id:
            flash('تم إنشاء الحساب بنجاح')
            return redirect(url_for('login'))
        else:
            flash('حدث خطأ أثناء إنشاء الحساب')
            return redirect(url_for('register'))
    
    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = db.get_user_by_email(email)
        if user and check_password_hash(user['password'], password):
            login_user(User(user))
            flash('تم تسجيل الدخول بنجاح!', 'success')
            
            # التحقق من وجود متجر للمستخدم
            store = db.get_store_by_owner(user['_id'])
            if not store:
                return redirect(url_for('create_store'))
            return redirect(url_for('home'))
            
        flash('البريد الإلكتروني أو كلمة المرور غير صحيحة', 'danger')
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    """لوحة تحكم صاحب المتجر"""
    if current_user.user_type != 'store_owner':
        flash('غير مصرح لك بالوصول إلى لوحة التحكم', 'danger')
        return redirect(url_for('home'))
    
    try:
        # التحقق من وجود متجر للمستخدم
        store = db.get_store_by_owner(current_user.id)
        if not store:
            flash('يجب إنشاء متجر أولاً', 'warning')
            return redirect(url_for('create_store'))
        
        # الحصول على المنتجات
        products = db.get_store_products(store['_id'])
        
        # الحصول على القسم
        category = db.get_category_by_id(store['category']) if store.get('category') else None
        
        # حساب الإحصائيات
        total_products = len(products)
        active_products = len([p for p in products if p.get('is_active', True)])
        
        # الحصول على الطلبات الجديدة (آخر 24 ساعة)
        new_orders = db.get_store_orders(store['_id'], days=1)
        new_orders_count = len(new_orders)
        
        # حساب إجمالي المبيعات
        total_sales = sum(order.get('total', 0) for order in new_orders)
        
        return render_template('store/dashboard.html',
                             store=store,
                             products=products,
                             category=category,
                             total_products=total_products,
                             active_products=active_products,
                             new_orders_count=new_orders_count,
                             total_sales=total_sales)
    except Exception as e:
        print(f"خطأ في لوحة التحكم: {str(e)}")
        flash('حدث خطأ أثناء تحميل لوحة التحكم', 'error')
        return redirect(url_for('home'))

@app.route('/create_store', methods=['GET', 'POST'])
@login_required
def create_store():
    # التحقق من وجود متجر للمستخدم
    store = db.get_store_by_owner(current_user.id)
    if store:
        flash('لديك متجر بالفعل!', 'warning')
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            address = request.form.get('address')
            category = request.form.get('category')
            image = request.files.get('image')
            
            if not all([name, description, address, category]):
                flash('يرجى ملء جميع الحقول المطلوبة', 'danger')
                return redirect(url_for('create_store'))
            
            filename = None
            if image and image.filename:
                print(f"تم استلام صورة: {image.filename}")  # رسالة تصحيح
                filename = secure_filename(image.filename)
                print(f"اسم الملف بعد التأمين: {filename}")  # رسالة تصحيح
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                print(f"مسار الحفظ: {upload_path}")  # رسالة تصحيح
                image.save(upload_path)
                print(f"تم حفظ الصورة بنجاح في: {upload_path}")  # رسالة تصحيح
                
            store_id = db.create_store(name, description, address, category, filename, current_user.id)
            if store_id:
                flash('تم إنشاء المتجر بنجاح!', 'success')
                return redirect(url_for('home'))
            else:
                flash('حدث خطأ أثناء إنشاء المتجر', 'danger')
        except Exception as e:
            print(f"حدث خطأ أثناء إنشاء المتجر: {str(e)}")  # رسالة تصحيح
            flash(f'حدث خطأ: {str(e)}', 'danger')
            
    # جلب الأقسام من قاعدة البيانات
    categories = db.get_all_categories()
    return render_template('store/create_store.html', categories=categories)

@app.route('/store/edit', methods=['GET', 'POST'])
@login_required
def edit_store():
    if current_user.user_type != 'store_owner':
        return redirect(url_for('dashboard'))
    
    store = db.get_store_by_owner(current_user.id)
    if not store:
        return redirect(url_for('create_store'))
    
    if request.method == 'POST':
        store_data = {
            'name': request.form['name'],
            'address': request.form['address'],
            'category': request.form['category']
        }
        
        if 'image' in request.files:
            image = request.files['image']
            if image and image.filename:
                filename = secure_filename(image.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                store_data['image'] = filename
        
        if db.update_store(store['_id'], store_data):
            flash('تم تحديث معلومات المتجر بنجاح')
            return redirect(url_for('dashboard'))
        else:
            flash('حدث خطأ أثناء تحديث معلومات المتجر')
    
    categories = db.get_all_categories()
    return render_template('edit_store.html', store=store, categories=categories)

@app.route('/product/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if current_user.user_type != 'store_owner':
        return redirect(url_for('dashboard'))
    
    store = db.get_store_by_owner(current_user.id)
    if not store:
        return redirect(url_for('create_store'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            price = float(request.form.get('price'))
            
            if not all([name, description, price]):
                flash('يرجى ملء جميع الحقول المطلوبة', 'danger')
                return redirect(url_for('add_product'))
            
            # جمع الأحجام والألوان المحددة
            pants_sizes = request.form.getlist('pants_sizes')
            clothes_sizes = request.form.getlist('clothes_sizes')
            colors = request.form.getlist('colors')
            
            filename = None
            if 'image' in request.files:
                image = request.files['image']
                if image and image.filename:
                    filename = secure_filename(image.filename)
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            product_id = db.create_product(
                name=name,
                description=description,
                price=price,
                store_id=str(store['_id']),
                category=store['category'],
                image=filename,
                pants_sizes=pants_sizes,
                clothes_sizes=clothes_sizes,
                colors=colors
            )
            
            if product_id:
                flash('تم إضافة المنتج بنجاح', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('حدث خطأ أثناء إضافة المنتج', 'danger')
        except Exception as e:
            flash(f'حدث خطأ: {str(e)}', 'danger')
    
    return render_template('store/add_product.html')

@app.route('/product/edit/<product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    if current_user.user_type != 'store_owner':
        return redirect(url_for('dashboard'))
    
    store = db.get_store_by_owner(current_user.id)
    if not store:
        return redirect(url_for('create_store'))
    
    product = db.get_product_by_id(product_id)
    if not product or product['store_id'] != str(store['_id']):
        flash('المنتج غير موجود')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        product_data = {
            'name': request.form['name'],
            'description': request.form['description'],
            'price': float(request.form['price'])
        }
        
        if 'image' in request.files:
            image = request.files['image']
            if image and image.filename:
                filename = secure_filename(image.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                product_data['image'] = filename
        
        if db.update_product(product_id, product_data):
            flash('تم تحديث المنتج بنجاح')
            return redirect(url_for('dashboard'))
        else:
            flash('حدث خطأ أثناء تحديث المنتج')
    
    return render_template('edit_product.html', product=product)

@app.route('/product/delete/<product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    if current_user.user_type != 'store_owner':
        return jsonify({'success': False, 'message': 'غير مصرح لك بحذف المنتجات'})
    
    store = db.get_store_by_owner(current_user.id)
    if not store:
        return jsonify({'success': False, 'message': 'المتجر غير موجود'})
    
    product = db.get_product_by_id(product_id)
    if not product or product['store_id'] != str(store['_id']):
        return jsonify({'success': False, 'message': 'المنتج غير موجود'})
    
    if db.delete_product(product_id):
        return jsonify({'success': True, 'message': 'تم حذف المنتج بنجاح'})
    else:
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء حذف المنتج'})

@app.route('/profile')
@login_required
def profile():
    user_data = db.get_user_by_id(current_user.id)
    store = db.get_store_by_owner(current_user.id)
    return render_template('auth/profile.html', user=user_data, store=store)

# مسارات المشرف
@app.route('/admin')
@login_required
def admin_dashboard():
    """لوحة تحكم المشرف"""
    if current_user.user_type != 'admin':
        flash('غير مصرح لك بالوصول إلى لوحة تحكم المشرف', 'danger')
        return redirect(url_for('admin_login'))
    
    try:
        # إحصائيات عامة
        total_stores = db.get_total_stores()
        total_products = db.get_total_products()
        total_users = db.get_total_users()
        total_orders = db.get_total_orders()
        
        # آخر المتاجر المضافة
        recent_stores = db.get_recent_stores(5)
        
        # آخر المنتجات المضافة
        recent_products = db.get_recent_products(5)
        
        # آخر المستخدمين المسجلين
        recent_users = db.get_recent_users(5)
        
        return render_template('admin/dashboard.html',
                             total_stores=total_stores,
                             total_products=total_products,
                             total_users=total_users,
                             total_orders=total_orders,
                             recent_stores=recent_stores,
                             recent_products=recent_products,
                             recent_users=recent_users)
    except Exception as e:
        flash('حدث خطأ أثناء جلب البيانات')
        return render_template('error.html', message=str(e))

@app.route('/admin/stores')
@login_required
def admin_stores():
    print("\n=== محاولة الوصول إلى صفحة المتاجر ===")
    print(f"نوع المستخدم الحالي: {current_user.user_type}")
    
    if not current_user.is_authenticated or current_user.user_type != 'admin':
        print("خطأ: المستخدم غير مصرح له بالوصول")
        flash('يجب تسجيل الدخول كمشرف للوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('admin_login'))
    
    try:
        # التحقق من الاتصال بقاعدة البيانات
        if not db.ensure_connection():
            print("خطأ: لا يمكن الاتصال بقاعدة البيانات")
            flash('حدث خطأ في الاتصال بقاعدة البيانات', 'danger')
            return render_template('admin/stores.html', stores=[])
        
        # جلب المتاجر
        print("جاري جلب المتاجر...")
        stores = db.get_all_stores()
        
        if stores is None:
            print("تم استلام None من قاعدة البيانات")
            stores = []
        elif not isinstance(stores, list):
            print(f"تم استلام نوع بيانات غير متوقع: {type(stores)}")
            stores = []
            
        print(f"تم جلب {len(stores)} متجر")
        
        if not stores:
            print("لم يتم العثور على متاجر")
            flash('لا توجد متاجر في النظام', 'info')
        else:
            print(f"تم العثور على {len(stores)} متجر")
            for store in stores:
                print(f"متجر: {store.get('name', 'بدون اسم')} - {store.get('_id', 'بدون معرف')}")
        
        return render_template('admin/stores.html', stores=stores)
        
    except Exception as e:
        print(f"خطأ في جلب المتاجر: {str(e)}")
        import traceback
        print(traceback.format_exc())
        flash('حدث خطأ أثناء جلب البيانات', 'danger')
        return render_template('admin/stores.html', stores=[])

@app.route('/admin/stores/<store_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_store(store_id):
    """تعديل متجر"""
    if current_user.user_type != 'admin':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة')
        return redirect(url_for('home'))
    
    try:
        store = db.get_store_by_id(store_id)
        if not store:
            flash('المتجر غير موجود')
            return redirect(url_for('admin_stores'))
        
        if request.method == 'POST':
            name = request.form.get('name')
            description = request.form.get('description')
            address = request.form.get('address')
            category = request.form.get('category')
            is_featured = 'is_featured' in request.form
            
            image = request.files.get('image')
            filename = store.get('image')
            if image and image.filename:
                filename = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            success = db.update_store(store_id, {
                'name': name,
                'description': description,
                'address': address,
                'category': category,
                'image': filename,
                'is_featured': is_featured
            })
            
            if success:
                flash('تم تحديث المتجر بنجاح')
                return redirect(url_for('admin_stores'))
            else:
                flash('حدث خطأ أثناء تحديث المتجر')
        
        categories = db.get_all_categories()
        return render_template('admin/edit_store.html', 
                             store=store, 
                             categories=categories)
    except Exception as e:
        flash('حدث خطأ أثناء تحديث المتجر')
        return render_template('error.html', message=str(e))

@app.route('/admin/stores/<store_id>/delete', methods=['POST'])
@login_required
def admin_delete_store(store_id):
    """حذف متجر"""
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'message': 'غير مصرح لك بهذه العملية'})
    
    try:
        success = db.delete_store(store_id)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/products')
@login_required
def admin_products():
    """إدارة المنتجات"""
    if current_user.user_type != 'admin':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('admin_login'))
    
    try:
        products = db.get_all_products()
        return render_template('admin/products.html', products=products)
    except Exception as e:
        flash('حدث خطأ أثناء جلب البيانات')
        return render_template('error.html', message=str(e))

@app.route('/admin/products/<product_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_product(product_id):
    """تعديل منتج"""
    if current_user.user_type != 'admin':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة')
        return redirect(url_for('home'))
    
    try:
        product = db.get_product_by_id(product_id)
        if not product:
            flash('المنتج غير موجود')
            return redirect(url_for('admin_products'))
        
        if request.method == 'POST':
            name = request.form.get('name')
            description = request.form.get('description')
            price = float(request.form.get('price'))
            store_id = request.form.get('store_id')
            category = request.form.get('category')
            
            pants_sizes = request.form.getlist('pants_sizes')
            clothes_sizes = request.form.getlist('clothes_sizes')
            colors = request.form.getlist('colors')
            
            image = request.files.get('image')
            filename = product.get('image')
            if image and image.filename:
                filename = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            success = db.update_product(product_id, {
                'name': name,
                'description': description,
                'price': price,
                'store_id': store_id,
                'category': category,
                'image': filename,
                'pants_sizes': pants_sizes,
                'clothes_sizes': clothes_sizes,
                'colors': colors
            })
            
            if success:
                flash('تم تحديث المنتج بنجاح')
                return redirect(url_for('admin_products'))
            else:
                flash('حدث خطأ أثناء تحديث المنتج')
        
        stores = db.get_all_stores()
        categories = db.get_all_categories()
        return render_template('admin/edit_product.html', 
                             product=product, 
                             stores=stores,
                             categories=categories)
    except Exception as e:
        flash('حدث خطأ أثناء تحديث المنتج')
        return render_template('error.html', message=str(e))

@app.route('/admin/products/<product_id>/delete', methods=['POST'])
@login_required
def admin_delete_product(product_id):
    """حذف منتج"""
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'message': 'غير مصرح لك بهذه العملية'})
    
    try:
        success = db.delete_product(product_id)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/users')
@login_required
def admin_users():
    """إدارة المستخدمين"""
    if current_user.user_type != 'admin':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('admin_login'))
    
    try:
        users = db.get_all_users()
        # جلب معلومات المتاجر لكل مستخدم
        for user in users:
            if user['user_type'] == 'store_owner':
                store = db.get_store_by_owner(str(user['_id']))
                if store:
                    user['store_id'] = str(store['_id'])
                    user['store_name'] = store['name']
                else:
                    user['store_id'] = None
                    user['store_name'] = None
        return render_template('admin/users.html', users=users)
    except Exception as e:
        flash('حدث خطأ أثناء جلب البيانات')
        return render_template('error.html', message=str(e))

@app.route('/admin/users/<user_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    """تعديل مستخدم"""
    if current_user.user_type != 'admin':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة')
        return redirect(url_for('home'))
    
    try:
        user = db.get_user_by_id(user_id)
        if not user:
            flash('المستخدم غير موجود')
            return redirect(url_for('admin_users'))
        
        if request.method == 'POST':
            email = request.form.get('email')
            name = request.form.get('name')
            user_type = request.form.get('user_type')
            
            success = db.update_user(user_id, {
                'email': email,
                'name': name,
                'user_type': user_type
            })
            
            if success:
                flash('تم تحديث المستخدم بنجاح')
                return redirect(url_for('admin_users'))
            else:
                flash('حدث خطأ أثناء تحديث المستخدم')
        
        return render_template('admin/edit_user.html', user=user)
    except Exception as e:
        flash('حدث خطأ أثناء تحديث المستخدم')
        return render_template('error.html', message=str(e))

@app.route('/admin/users/<user_id>/delete', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    """حذف مستخدم"""
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'message': 'غير مصرح لك بهذه العملية'})
    
    try:
        success = db.delete_user(user_id)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """تسجيل دخول المشرف"""
    print("\n=== محاولة تسجيل دخول المشرف ===")
    
    # إذا كان المستخدم مسجل دخوله بالفعل كمشرف، قم بتوجيهه إلى لوحة التحكم
    if current_user.is_authenticated:
        print(f"المستخدم مسجل دخوله بالفعل. نوع المستخدم: {current_user.user_type}")
        if current_user.user_type == 'admin':
            return redirect(url_for('admin_dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        print(f"محاولة تسجيل دخول: {email}")
        
        if db.check_admin_credentials(email, password):
            user = db.get_user_by_email(email)
            if user:
                print(f"تم العثور على المستخدم: {user.get('email')}")
                print(f"نوع المستخدم: {user.get('user_type')}")
                login_user(User(user))
                flash('تم تسجيل الدخول بنجاح!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                print("لم يتم العثور على المستخدم بعد التحقق من البيانات")
        else:
            print("فشل التحقق من بيانات تسجيل الدخول")
            
        flash('البريد الإلكتروني أو كلمة المرور غير صحيحة', 'danger')
    
    return render_template('admin/login.html')

@app.route('/admin/setup', methods=['GET', 'POST'])
def admin_setup():
    """إنشاء حساب المشرف الأول"""
    # التحقق من وجود مشرفين في النظام
    if db.get_admin_count() > 0:
        flash('تم إعداد المشرف بالفعل', 'warning')
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        if not all([email, password, name]):
            flash('يرجى ملء جميع الحقول المطلوبة', 'danger')
            return redirect(url_for('admin_setup'))
        
        # التحقق من عدم وجود البريد الإلكتروني
        if db.get_user_by_email(email):
            flash('البريد الإلكتروني مستخدم بالفعل', 'danger')
            return redirect(url_for('admin_setup'))
        
        # إنشاء حساب المشرف
        hashed_password = generate_password_hash(password)
        user_id = db.create_user(email, hashed_password, 'admin', name)
        
        if user_id:
            flash('تم إنشاء حساب المشرف بنجاح! يمكنك الآن تسجيل الدخول', 'success')
            return redirect(url_for('admin_login'))
        else:
            flash('حدث خطأ أثناء إنشاء حساب المشرف', 'danger')
    
    return render_template('admin/setup.html')

@app.route('/checkout')
@login_required
def checkout():
    print("\n=== بدء عملية إتمام الشراء ===")
    print(f"المستخدم الحالي: {current_user.id}")
    
    if not db.is_connected():
        print("خطأ: لا يوجد اتصال بقاعدة البيانات")
        flash('لا يمكن الاتصال بقاعدة البيانات. يرجى المحاولة لاحقاً', 'error')
        return render_template('error.html', message='خطأ في الاتصال بقاعدة البيانات')
    
    try:
        print("جاري جلب محتويات السلة...")
        cart_items = db.get_cart(current_user.id)
        print(f"تم جلب {len(cart_items)} عنصر من السلة")
        
        if not cart_items:
            print("السلة فارغة")
            flash('السلة فارغة', 'warning')
            return redirect(url_for('cart'))
        
        total = sum(item['price'] * item['quantity'] for item in cart_items)
        print(f"المجموع الكلي: {total}")
        
        print("جاري تحميل صفحة إتمام الشراء...")
        return render_template('checkout.html', cart_items=cart_items, total=total)
    except Exception as e:
        print(f"خطأ في صفحة إتمام الشراء: {str(e)}")
        import traceback
        print(traceback.format_exc())
        flash('حدث خطأ أثناء تحميل صفحة إتمام الشراء', 'error')
        return redirect(url_for('cart'))

@app.route('/process_order', methods=['POST'])
@login_required
def process_order():
    print("\n=== بدء معالجة الطلب ===")
    print(f"المستخدم الحالي: {current_user.id}")
    
    if not db.is_connected():
        print("خطأ: لا يوجد اتصال بقاعدة البيانات")
        flash('لا يمكن الاتصال بقاعدة البيانات. يرجى المحاولة لاحقاً', 'error')
        return render_template('error.html', message='خطأ في الاتصال بقاعدة البيانات')
    
    try:
        print("جاري جلب محتويات السلة...")
        cart_items = db.get_cart(current_user.id)
        print(f"تم جلب {len(cart_items)} عنصر من السلة")
        
        if not cart_items:
            print("السلة فارغة")
            flash('السلة فارغة', 'warning')
            return redirect(url_for('cart'))
        
        total = sum(item['price'] * item['quantity'] for item in cart_items)
        print(f"المجموع الكلي: {total}")
        
        # جلب بيانات النموذج
        payment_method = request.form.get('payment_method')
        name = request.form.get('name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        print(f"طريقة الدفع: {payment_method}")
        print(f"الاسم: {name}")
        print(f"الهاتف: {phone}")
        print(f"العنوان: {address}")
        
        # التحقق من البيانات المطلوبة
        if not all([payment_method, name, phone, address]):
            print("بيانات ناقصة في النموذج")
            flash('يرجى ملء جميع الحقول المطلوبة', 'warning')
            return redirect(url_for('checkout'))
        
        transfer_image = None
        if payment_method == 'bank':
            print("التحقق من صورة إشعار التحويل...")
            if 'transfer_image' not in request.files:
                print("لم يتم إرفاق صورة إشعار التحويل")
                flash('يرجى إرفاق صورة إشعار التحويل', 'warning')
                return redirect(url_for('checkout'))
            
            file = request.files['transfer_image']
            if file.filename == '':
                print("لم يتم اختيار ملف")
                flash('لم يتم اختيار ملف', 'warning')
                return redirect(url_for('checkout'))
            
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                transfer_image = filename
                print(f"تم حفظ صورة إشعار التحويل: {filename}")
            else:
                print("نوع الملف غير مسموح به")
                flash('نوع الملف غير مسموح به', 'warning')
                return redirect(url_for('checkout'))
        
        # إنشاء الطلب
        print("جاري إنشاء الطلب...")
        order_id = db.create_order(
            current_user.id,
            cart_items,
            total,
            payment_method,
            name,
            phone,
            address,
            transfer_image
        )
        
        if order_id:
            print(f"تم إنشاء الطلب بنجاح: {order_id}")
            # تفريغ السلة
            db.clear_cart(current_user.id)
            flash('تم إنشاء الطلب بنجاح', 'success')
            return redirect(url_for('order_success', order_id=order_id))
        else:
            print("فشل في إنشاء الطلب")
            flash('حدث خطأ أثناء إنشاء الطلب', 'error')
            return redirect(url_for('checkout'))
            
    except Exception as e:
        print(f"خطأ في معالجة الطلب: {str(e)}")
        import traceback
        print(traceback.format_exc())
        flash('حدث خطأ أثناء معالجة الطلب', 'error')
        return redirect(url_for('checkout'))

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/order_success/<order_id>')
@login_required
def order_success(order_id):
    order = db.get_order_by_id(order_id)
    if not order or order['user_id'] != current_user.id:
        flash('الطلب غير موجود', 'error')
        return redirect(url_for('home'))
    return render_template('order_success.html', order=order)

@app.route('/admin/orders')
@login_required
def admin_orders():
    """إدارة الطلبات"""
    print("\n=== عرض قائمة الطلبات للمشرف ===")
    
    if current_user.user_type != 'admin':
        print("خطأ: المستخدم غير مصرح له بالوصول")
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('admin_login'))
    
    try:
        # التأكد من الاتصال بقاعدة البيانات
        if not db.ensure_connection():
            print("خطأ: لا يمكن الاتصال بقاعدة البيانات")
            flash('لا يمكن الاتصال بقاعدة البيانات', 'error')
            return render_template('error.html', message='خطأ في الاتصال بقاعدة البيانات')
        
        # جلب معايير التصفية
        status = request.args.get('status')
        payment_method = request.args.get('payment_method')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        print(f"معايير التصفية:")
        print(f"- الحالة: {status}")
        print(f"- طريقة الدفع: {payment_method}")
        print(f"- من تاريخ: {start_date}")
        print(f"- إلى تاريخ: {end_date}")
        
        # جلب الطلبات مع التصفية
        print("جاري جلب الطلبات...")
        orders = db.get_all_orders(
            status=status,
            payment_method=payment_method,
            start_date=start_date,
            end_date=end_date
        )
        
        if not orders:
            print("لم يتم العثور على طلبات")
            flash('لا توجد طلبات حالياً', 'info')
        else:
            print(f"تم جلب {len(orders)} طلب")
        
        print("جاري تحميل قالب الطلبات...")
        return render_template('admin/orders.html', orders=orders)
        
    except Exception as e:
        print(f"خطأ في جلب الطلبات: {str(e)}")
        import traceback
        print(traceback.format_exc())
        flash('حدث خطأ أثناء جلب الطلبات', 'error')
        return render_template('error.html', message=str(e))

@app.route('/admin/orders/<order_id>/complete', methods=['POST'])
@login_required
def complete_order(order_id):
    if current_user.user_type != 'admin':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('home'))
    
    try:
        # تحديث حالة الطلب إلى مكتمل
        if db.update_order_status(order_id, 'completed'):
            # حذف الطلب بعد إكماله
            if db.delete_order(order_id):
                flash('تم إكمال وحذف الطلب بنجاح', 'success')
            else:
                flash('تم إكمال الطلب ولكن حدث خطأ أثناء حذفه', 'warning')
        else:
            flash('حدث خطأ أثناء إكمال الطلب', 'danger')
    except Exception as e:
        flash(f'حدث خطأ: {str(e)}', 'danger')
    
    return redirect(url_for('admin_orders'))

@app.route('/admin/orders/<order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    if current_user.user_type != 'admin':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('home'))
    
    if db.update_order_status(order_id, 'cancelled'):
        flash('تم إلغاء الطلب بنجاح', 'success')
    else:
        flash('حدث خطأ أثناء إلغاء الطلب', 'danger')
    
    return redirect(url_for('admin_orders'))

@app.route('/product/<product_id>')
def product_details(product_id):
    """صفحة تفاصيل المنتج"""
    if not db.is_connected():
        flash('لا يمكن الاتصال بقاعدة البيانات. يرجى المحاولة لاحقاً')
        return render_template('error.html', message='خطأ في الاتصال بقاعدة البيانات')
    
    try:
        product = db.get_product_by_id(product_id)
        if not product:
            flash('المنتج غير موجود')
            return redirect(url_for('home'))
        
        store = db.get_store_by_id(product['store_id'])
        if not store:
            flash('المتجر غير موجود')
            return redirect(url_for('home'))
        
        return render_template('store/product_details.html',
                             product=product,
                             store=store)
    except Exception as e:
        print(f"خطأ في صفحة تفاصيل المنتج: {str(e)}")
        flash('حدث خطأ أثناء جلب البيانات')
        return render_template('error.html', message=str(e))

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

@app.route('/admin/stores/<store_id>/toggle-featured', methods=['POST'])
@login_required
def toggle_featured_store(store_id):
    """تحديد/إلغاء تحديد المتجر كمميز"""
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'message': 'غير مصرح لك بهذه العملية'})
    
    try:
        is_featured = request.json.get('is_featured', False)
        success = db.toggle_featured_store(store_id, is_featured)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/products/<product_id>/toggle-featured', methods=['POST'])
@login_required
def toggle_featured_product(product_id):
    """تحديد/إلغاء تحديد المنتج كمميز"""
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'message': 'غير مصرح لك بهذه العملية'})
    
    try:
        is_featured = request.json.get('is_featured', False)
        success = db.toggle_featured_product(product_id, is_featured)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/store/<store_id>/rate', methods=['POST'])
@login_required
def rate_store(store_id):
    """تقييم المتجر"""
    try:
        rating = int(request.form.get('rating', 0))
        comment = request.form.get('comment', '')
        
        if not 1 <= rating <= 5:
            return jsonify({'success': False, 'message': 'التقييم يجب أن يكون بين 1 و 5'})
        
        # التحقق من وجود تقييم سابق
        if db.has_user_rated_store(store_id, current_user.id):
            # تحديث التقييم
            success = db.update_store_rating(store_id, current_user.id, rating, comment)
        else:
            # إضافة تقييم جديد
            success = db.add_store_rating(store_id, current_user.id, rating, comment)
        
        if success:
            return jsonify({'success': True, 'message': 'تم إضافة التقييم بنجاح'})
        else:
            return jsonify({'success': False, 'message': 'حدث خطأ أثناء إضافة التقييم'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/product/<product_id>/rate', methods=['POST'])
@login_required
def rate_product(product_id):
    """تقييم المنتج"""
    try:
        rating = int(request.form.get('rating', 0))
        comment = request.form.get('comment', '')
        
        if not 1 <= rating <= 5:
            return jsonify({'success': False, 'message': 'التقييم يجب أن يكون بين 1 و 5'})
        
        # التحقق من وجود تقييم سابق
        if db.has_user_rated_product(product_id, current_user.id):
            # تحديث التقييم
            success = db.update_product_rating(product_id, current_user.id, rating, comment)
        else:
            # إضافة تقييم جديد
            success = db.add_product_rating(product_id, current_user.id, rating, comment)
        
        if success:
            return jsonify({'success': True, 'message': 'تم إضافة التقييم بنجاح'})
        else:
            return jsonify({'success': False, 'message': 'حدث خطأ أثناء إضافة التقييم'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/store/<store_id>/ratings')
def get_store_ratings(store_id):
    """جلب تقييمات المتجر"""
    try:
        ratings = db.get_store_ratings(store_id)
        average_rating = db.get_store_average_rating(store_id)
        return jsonify({
            'success': True,
            'ratings': ratings,
            'average_rating': average_rating
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/product/<product_id>/ratings')
def get_product_ratings(product_id):
    """جلب تقييمات المنتج"""
    try:
        ratings = db.get_product_ratings(product_id)
        average_rating = db.get_product_average_rating(product_id)
        return jsonify({
            'success': True,
            'ratings': ratings,
            'average_rating': average_rating
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
@app.route('/search-by-image', methods=['POST'])
def search_by_image():
    """
    يستقبل صورة من المستخدم (input[type=file]) ويبحث عن منتجات مشابهة.
    يعيد render لصفحة search_results.html مع قائمة النتائج.
    """
    # 1. التأكد من وجود الملف في الطلب
    if 'image' not in request.files:
        return render_template('search_results.html', results=[])

    file = request.files['image']
    if file.filename == '':
        return render_template('search_results.html', results=[])

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)

        try:
            # 2. حساب embedding للصورة المرفوعة
            query_emb = get_image_embedding(save_path)
        except:
            return render_template('search_results.html', results=[])

        # 3. البحث عن أقرب 5 صور
        similar_paths = image_search_engine.search(query_emb, k=5)

        # 4. إعداد قائمة النتائج لتمريرها للقالب
        results = []
        for img_path in similar_paths:
            fname = os.path.basename(img_path)
            # URL سيتم عرضه في الصفحة:
            img_url = url_for('static', filename=f'uploads/jpg/{fname}')
            # إذا لديك طريقة لربط fname بمنتج في DB:
            # product = get_product_by_image_filename(fname)
            # ثم تمرر اسم المنتج ورابط التفاصيل:
            # إذا ليس لديك، يمكن عرض الصورة فقط:
            results.append({
                'image_url': img_url,
                'name': None,          # أو product['name'] إذا استعلمت DB
                'detail_url': '#'      # أو url_for('product_details', product_id=...)
            })

        return render_template('search_results.html', results=results)

    return render_template('search_results.html', results=[])

if __name__ == '__main__':
    if not db.is_connected():
        print("تحذير: لم يتم الاتصال بقاعدة البيانات. سيتم تشغيل التطبيق في وضع العرض فقط")
    app.run(debug=True) 