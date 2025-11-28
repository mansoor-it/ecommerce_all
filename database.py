from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from datetime import datetime
from bson.objectid import ObjectId
from werkzeug.security import check_password_hash
from flask import url_for
import logging
import time

class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        try:
            # إعداد التسجيل
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)
            
            # معلومات الاتصال
            connection_string = "mongodb+srv://nooraldeennbeel2:nooraldeen.as@cluster0.wuowemk.mongodb.net/ecommerceDB?retryWrites=true&w=majority&appName=Cluster0"
            
            print("\n=== محاولة الاتصال بقاعدة البيانات ===")
            print("جاري الاتصال بقاعدة البيانات...")
            
            # خيارات الاتصال المحسنة
            self.client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=30000,  # 30 ثانية
                connectTimeoutMS=30000,
                socketTimeoutMS=30000,
                maxPoolSize=50,
                minPoolSize=10,
                retryWrites=True,
                retryReads=True,
                w='majority',
                readPreference='primary',
                tls=True,
                tlsAllowInvalidCertificates=True,
                directConnection=False
            )
            
            # اختبار الاتصال
            print("جاري اختبار الاتصال...")
            try:
                self.client.admin.command('ping')
                print("تم الاتصال بقاعدة البيانات بنجاح")
            except Exception as e:
                print(f"فشل اختبار الاتصال: {str(e)}")
                raise
            
            # تهيئة قاعدة البيانات
            self.db = self.client.ecommerceDB
            print("تم تهيئة قاعدة البيانات")
            
            # التحقق من المجموعات الموجودة
            try:
                collections = self.db.list_collection_names()
                print(f"المجموعات الموجودة: {collections}")
                
                # التحقق من وجود مجموعة الطلبات
                if 'orders' not in collections:
                    print("إنشاء مجموعة الطلبات...")
                    self.db.create_collection('orders')
                    print("تم إنشاء مجموعة الطلبات")
            except Exception as e:
                print(f"خطأ في التحقق من المجموعات: {str(e)}")
                raise
            
            print("=== تم الاتصال بقاعدة البيانات بنجاح ===\n")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"فشل الاتصال بقاعدة البيانات: {str(e)}")
            self.client = None
            self.db = None
            raise
        except Exception as e:
            print(f"حدث خطأ غير متوقع: {str(e)}")
            self.client = None
            self.db = None
            raise
    
    def _create_default_categories(self):
        if not self.is_connected():
            return
        
        try:
            print("\n=== بدء تحديث الأقسام ===")
            # حذف جميع الأقسام الحالية
            delete_result = self.db.categories.delete_many({})
            print(f"تم حذف {delete_result.deleted_count} قسم")
            
            # إنشاء الأقسام الجديدة
            default_categories = [
                {
                    'name': 'ملابس رجالية',
                    'description': 'جميع أنواع الملابس الرجالية',
                    'icon': 'fa-male',
                    'image': 'https://images.unsplash.com/photo-1617137968427-85924c800a22?w=800&auto=format&fit=crop'
                },
                {
                    'name': 'ملابس نسائية',
                    'description': 'جميع أنواع الملابس النسائية',
                    'icon': 'fa-female',
                    'image': 'https://images.unsplash.com/photo-1581044777550-4cfa60707c03?w=800&auto=format&fit=crop'
                },
                {
                    'name': 'أحذية',
                    'description': 'جميع أنواع الأحذية والصنادل',
                    'icon': 'fa-shoe-prints',
                    'image': 'https://images.unsplash.com/photo-1549298916-b41d501d3772?w=800&auto=format&fit=crop'
                },
                {
                    'name': 'أطفال',
                    'description': 'ملابس وألعاب الأطفال',
                    'icon': 'fa-child',
                    'image': 'https://images.unsplash.com/photo-1622290291468-a28f7a7dc6a8?w=800&auto=format&fit=crop'
                },
                {
                    'name': 'إلكترونيات',
                    'description': 'الأجهزة الإلكترونية وملحقاتها',
                    'icon': 'fa-laptop',
                    'image': 'https://images.unsplash.com/photo-1498049794561-7780e7231661?w=800&auto=format&fit=crop'
                },
                {
                    'name': 'هواتف',
                    'description': 'الهواتف الذكية وملحقاتها',
                    'icon': 'fa-mobile-alt',
                    'image': 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=800&auto=format&fit=crop'
                }
            ]
            
            # إدخال الأقسام الجديدة
            insert_result = self.db.categories.insert_many(default_categories)
            print(f"تم إضافة {len(insert_result.inserted_ids)} قسم جديد")
            
            # التحقق من الأقسام المضافة
            categories = list(self.db.categories.find())
            print("\nالأقسام المضافة:")
            for category in categories:
                print(f"- {category['name']}: {category['image']}")
            
            print("\n=== تم إنشاء الأقسام الافتراضية بنجاح ===\n")
        except Exception as e:
            print(f"خطأ في إنشاء الأقسام الافتراضية: {str(e)}")
            import traceback
            print(traceback.format_exc())
    
    def is_connected(self):
        return self.db is not None
    
    def get_all_categories(self):
        if not self.is_connected():
            return []
        try:
            categories = list(self.db.categories.find())
            print(f"تم العثور على {len(categories)} قسم")  # للتأكد من وجود الأقسام
            return categories
        except Exception as e:
            print(f"خطأ في جلب الأقسام: {str(e)}")
            return []
    
    def get_category_by_id(self, category_id):
        if not self.is_connected():
            return None
        try:
            category = self.db.categories.find_one({'_id': ObjectId(category_id)})
            print(f"تم البحث عن القسم: {category_id}")  # للتأكد من البحث
            if category:
                print(f"تم العثور على القسم: {category['name']}")
            else:
                print("لم يتم العثور على القسم")
            return category
        except Exception as e:
            print(f"خطأ في البحث عن القسم: {str(e)}")
            return None
    
    # دوال المستخدمين
    def create_user(self, email, password, user_type, name):
        """إنشاء مستخدم جديد"""
        if not self.is_connected():
            return None
        
        try:
            # التحقق من نوع المستخدم
            if user_type not in ['admin', 'store_owner', 'customer']:
                print(f"نوع مستخدم غير صالح: {user_type}")
                return None
            
            # التحقق من عدم وجود البريد الإلكتروني
            existing_user = self.get_user_by_email(email)
            if existing_user:
                print(f"البريد الإلكتروني {email} مستخدم بالفعل")
                return None
            
            user_data = {
                'email': email,
                'password': password,
                'user_type': user_type,
                'name': name,
                'username': email.split('@')[0],  # استخدام جزء البريد الإلكتروني قبل @ كاسم مستخدم
                'created_at': datetime.utcnow()
            }
            
            print(f"إنشاء مستخدم جديد: {user_type} - {email}")
            result = self.db.users.insert_one(user_data)
            print(f"تم إنشاء المستخدم بنجاح: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            print(f"خطأ في إنشاء المستخدم: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None
    
    def get_user_by_email(self, email):
        if not self.is_connected():
            return None
        return self.db.users.find_one({'email': email})
    
    def get_user_by_id(self, user_id):
        if not self.is_connected():
            return None
        try:
            return self.db.users.find_one({'_id': ObjectId(user_id)})
        except:
            return None
    
    # دوال المتاجر
    def create_store(self, name, description, address, category, image, owner_id):
        """إنشاء متجر جديد"""
        try:
            store = {
                'name': name,
                'description': description,
                'address': address,
                'category': category,
                'image': image,
                'owner_id': owner_id,
                'created_at': datetime.now()
            }
            print(f"محاولة إنشاء متجر: {store}")  # للتأكد من بيانات المتجر
            result = self.db.stores.insert_one(store)
            print(f"تم إنشاء المتجر بنجاح: {result.inserted_id}")  # للتأكد من نجاح العملية
            return str(result.inserted_id)
        except Exception as e:
            print(f"خطأ في إنشاء المتجر: {e}")
            return None
    
    def get_store_by_owner(self, owner_id):
        if not self.is_connected():
            return None
        try:
            return self.db.stores.find_one({'owner_id': str(owner_id)})
        except:
            return None
    
    def get_stores_by_category(self, category):
        if not self.is_connected():
            return []
        try:
            stores = list(self.db.stores.find({'category': category}))
            print(f"تم البحث عن المتاجر في القسم: {category}")
            print(f"تم العثور على {len(stores)} متجر")
            return stores
        except Exception as e:
            print(f"خطأ في جلب متاجر القسم: {str(e)}")
            return []
    
    def get_featured_stores(self, limit=6):
        if not self.is_connected():
            return []
        try:
            stores = list(self.db.stores.find())
            print(f"تم العثور على {len(stores)} متجر")  # للتأكد من وجود المتاجر
            return stores
        except Exception as e:
            print(f"خطأ في جلب المتاجر: {str(e)}")
            return []
    
    def get_store_by_id(self, store_id):
        if not self.is_connected():
            return None
        try:
            return self.db.stores.find_one({'_id': ObjectId(store_id)})
        except:
            return None
    
    def update_store(self, store_id, store_data):
        if not self.is_connected():
            return False
        
        try:
            result = self.db.stores.update_one(
                {'_id': ObjectId(store_id)},
                {'$set': store_data}
            )
            return result.modified_count > 0
        except:
            return False
    
    # دوال المنتجات
    def create_product(self, name, description, price, store_id, category, image=None, pants_sizes=None, clothes_sizes=None, colors=None):
        if not self.is_connected():
            return None
        
        product_data = {
            'name': name,
            'description': description,
            'price': price,
            'store_id': store_id,
            'category': category,
            'image': image,
            'pants_sizes': pants_sizes or [],
            'clothes_sizes': clothes_sizes or [],
            'colors': colors or [],
            'sales': 0,
            'created_at': datetime.utcnow()
        }
        
        try:
            result = self.db.products.insert_one(product_data)
            return str(result.inserted_id)
        except Exception as e:
            print(f"خطأ في إنشاء المنتج: {str(e)}")
            return None
    
    def get_top_products(self, limit=8):
        if not self.is_connected():
            return []
        return list(self.db.products.find().sort('sales', -1).limit(limit))
    
    def get_store_products(self, store_id):
        """الحصول على منتجات المتجر"""
        print(f"\n=== جلب منتجات المتجر {store_id} ===")
        if not self.is_connected():
            print("خطأ: لا يوجد اتصال بقاعدة البيانات")
            return []
        try:
            products = list(self.db.products.find({'store_id': str(store_id)}))
            print(f"تم العثور على {len(products)} منتج")
            for product in products:
                print(f"- {product.get('name', 'بدون اسم')} ({product.get('_id')})")
            return products
        except Exception as e:
            print(f"خطأ في جلب منتجات المتجر: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return []
    
    def get_product_by_id(self, product_id):
        """الحصول على منتج بواسطة المعرف"""
        print(f"\n=== محاولة جلب منتج بواسطة المعرف ===")
        print(f"معرف المنتج: {product_id}")
        
        if not self.is_connected():
            print("خطأ: لا يوجد اتصال بقاعدة البيانات")
            return None
            
        try:
            # تحويل المعرف إلى ObjectId إذا كان نصياً
            if isinstance(product_id, str):
                try:
                    product_id = ObjectId(product_id)
                except Exception as e:
                    print(f"خطأ في تحويل المعرف: {str(e)}")
                    return None
            
            product = self.db.products.find_one({'_id': product_id})
            
            if product:
                print(f"تم العثور على المنتج: {product.get('name', 'بدون اسم')}")
                return product
            else:
                print("لم يتم العثور على المنتج")
                return None
                
        except Exception as e:
            print(f"خطأ في جلب المنتج: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None
    
    def update_product(self, product_id, product_data):
        if not self.is_connected():
            return False
        
        try:
            result = self.db.products.update_one(
                {'_id': ObjectId(product_id)},
                {'$set': product_data}
            )
            return result.modified_count > 0
        except:
            return False
    
    def delete_product(self, product_id):
        if not self.is_connected():
            return False
        
        try:
            result = self.db.products.delete_one({'_id': ObjectId(product_id)})
            return result.deleted_count > 0
        except:
            return False
    
    # دوال السلة
    def get_cart(self, user_id):
        """الحصول على محتويات سلة المستخدم"""
        print(f"\n=== جلب محتويات السلة للمستخدم {user_id} ===")
        try:
            if not self.is_connected():
                print("خطأ: لا يوجد اتصال بقاعدة البيانات")
                return []
            
            cart = self.db.carts.find_one({'user_id': user_id})
            print(f"تم العثور على السلة: {cart is not None}")
            
            if not cart:
                print("لم يتم العثور على سلة للمستخدم")
                return []
            
            items = []
            for item in cart.get('items', []):
                print(f"معالجة العنصر: {item}")
                product = self.get_product_by_id(item['product_id'])
                if product:
                    print(f"تم العثور على المنتج: {product['name']}")
                    store = self.get_store_by_id(product['store_id'])
                    print(f"تم العثور على المتجر: {store['name'] if store else 'غير معروف'}")
                    
                    items.append({
                        'id': str(product['_id']),
                        'name': product['name'],
                        'description': product.get('description', ''),
                        'price': product['price'],
                        'quantity': item['quantity'],
                        'size': item.get('size', ''),
                        'color': item.get('color', ''),
                        'image_url': url_for('static', filename='uploads/' + product['image']) if product.get('image') else None,
                        'store_name': store['name'] if store else 'متجر غير معروف'
                    })
                else:
                    print(f"لم يتم العثور على المنتج: {item['product_id']}")
            
            print(f"تم جلب {len(items)} عنصر من السلة")
            return items
        except Exception as e:
            print(f"خطأ في جلب محتويات السلة: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return []
    
    def add_to_cart(self, user_id, product_id, size=None, color=None):
        """إضافة منتج إلى سلة المستخدم"""
        print(f"\n=== محاولة إضافة منتج إلى السلة ===")
        print(f"معرف المستخدم: {user_id}")
        print(f"معرف المنتج: {product_id}")
        print(f"الحجم: {size}")
        print(f"اللون: {color}")
        
        try:
            if not self.is_connected():
                print("خطأ: لا يوجد اتصال بقاعدة البيانات")
                return False
            
            # التحقق من وجود المنتج
            product = self.get_product_by_id(product_id)
            if not product:
                print("لم يتم العثور على المنتج")
                return False
            
            print(f"تم العثور على المنتج: {product.get('name', 'بدون اسم')}")
            
            # التحقق من وجود السلة
            cart = self.db.carts.find_one({'user_id': user_id})
            if not cart:
                print("إنشاء سلة جديدة للمستخدم")
                cart = {
                    'user_id': user_id,
                    'items': []
                }
                self.db.carts.insert_one(cart)
            
            # إضافة المنتج إلى السلة
            cart_item = {
                'product_id': str(product_id),  # تحويل إلى سلسلة نصية
                'quantity': 1,
                'price': product['price'],
                'size': size,
                'color': color,
                'added_at': datetime.now()
            }
            
            print("جاري التحقق من وجود المنتج في السلة...")
            
            # التحقق من وجود المنتج في السلة
            existing_item = self.db.carts.find_one({
                'user_id': user_id,
                'items.product_id': str(product_id),
                'items.size': size,
                'items.color': color
            })
            
            if existing_item:
                print("المنتج موجود في السلة، جاري تحديث الكمية...")
                # تحديث الكمية
                result = self.db.carts.update_one(
                    {
                        'user_id': user_id,
                        'items.product_id': str(product_id),
                        'items.size': size,
                        'items.color': color
                    },
                    {'$inc': {'items.$.quantity': 1}}
                )
                print(f"تم تحديث الكمية: {result.modified_count > 0}")
            else:
                print("إضافة منتج جديد إلى السلة...")
                # إضافة منتج جديد
                result = self.db.carts.update_one(
                    {'user_id': user_id},
                    {'$push': {'items': cart_item}}
                )
                print(f"تم إضافة المنتج: {result.modified_count > 0}")
            
            return True
            
        except Exception as e:
            print(f"خطأ في إضافة المنتج إلى السلة: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False
    
    def update_cart_item_quantity(self, user_id, product_id, quantity, size=None, color=None):
        """تحديث كمية منتج في سلة المستخدم"""
        print(f"\n=== محاولة تحديث كمية المنتج في السلة ===")
        print(f"معرف المستخدم: {user_id}")
        print(f"معرف المنتج: {product_id}")
        print(f"الكمية الجديدة: {quantity}")
        print(f"الحجم: {size}")
        print(f"اللون: {color}")
        
        try:
            if not self.is_connected():
                print("خطأ: لا يوجد اتصال بقاعدة البيانات")
                return False
            
            # التحقق من وجود السلة
            cart = self.db.carts.find_one({'user_id': user_id})
            if not cart:
                print("لم يتم العثور على سلة للمستخدم")
                return False
            
            print("تم العثور على السلة")
            
            # التحقق من وجود المنتج في السلة
            existing_item = self.db.carts.find_one({
                'user_id': user_id,
                'items.product_id': str(product_id),
                'items.size': size,
                'items.color': color
            })
            
            if not existing_item:
                print("لم يتم العثور على المنتج في السلة")
                return False
            
            print("تم العثور على المنتج في السلة")
            
            # تحديث الكمية مباشرة في قاعدة البيانات
            result = self.db.carts.update_one(
                {
                    'user_id': user_id,
                    'items.product_id': str(product_id),
                    'items.size': size,
                    'items.color': color
                },
                {'$set': {'items.$.quantity': max(1, quantity)}}
            )
            
            if result.modified_count > 0:
                print("تم تحديث الكمية بنجاح")
                return True
            else:
                print("لم يتم تحديث الكمية")
                return False
                
        except Exception as e:
            print(f"خطأ في تحديث كمية المنتج: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False
    
    def remove_from_cart(self, user_id, product_id, size=None, color=None):
        """إزالة منتج من سلة المستخدم"""
        try:
            print(f"\n=== محاولة إزالة منتج من السلة ===")
            print(f"معرف المستخدم: {user_id}")
            print(f"معرف المنتج: {product_id}")
            print(f"الحجم: {size}")
            print(f"اللون: {color}")
            
            if not self.is_connected():
                print("خطأ: لا يوجد اتصال بقاعدة البيانات")
                return False
            
            cart = self.db.carts.find_one({'user_id': user_id})
            if not cart:
                print("لم يتم العثور على سلة للمستخدم")
                return False
            
            # تحديث السلة بإزالة العنصر المطابق
            result = self.db.carts.update_one(
                {'user_id': user_id},
                {'$pull': {
                    'items': {
                        'product_id': str(product_id),
                        'size': size,
                        'color': color
                    }
                }}
            )
            
            if result.modified_count > 0:
                print("تم إزالة المنتج بنجاح")
                
                # التحقق مما إذا كانت السلة فارغة
                cart = self.db.carts.find_one({'user_id': user_id})
                if cart and not cart.get('items'):
                    print("السلة فارغة، جاري حذفها")
                    self.db.carts.delete_one({'user_id': user_id})
                
                return True
            else:
                print("لم يتم العثور على المنتج في السلة")
                return False
                
        except Exception as e:
            print(f"خطأ في إزالة المنتج من السلة: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False
    
    def clear_cart(self, user_id):
        """تفريغ سلة المستخدم"""
        try:
            result = self.db.carts.delete_one({'user_id': user_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error clearing cart: {str(e)}")
            return False

    def get_admin_count(self):
        """الحصول على عدد المشرفين في النظام"""
        try:
            return self.db.users.count_documents({'user_type': 'admin'})
        except Exception as e:
            print(f"خطأ في الحصول على عدد المشرفين: {str(e)}")
            return 0

    def check_admin_credentials(self, email, password):
        """التحقق من بيانات تسجيل دخول المشرف"""
        print(f"\n=== التحقق من بيانات تسجيل دخول المشرف ===")
        print(f"البريد الإلكتروني: {email}")
        
        if not self.is_connected():
            print("خطأ: لا يوجد اتصال بقاعدة البيانات")
            return False
            
        try:
            user = self.get_user_by_email(email)
            if user:
                print(f"تم العثور على المستخدم:")
                print(f"البريد الإلكتروني: {user.get('email')}")
                print(f"نوع المستخدم: {user.get('user_type')}")
                
                # التحقق من نوع المستخدم
                user_type = user.get('user_type')
                if user_type != 'admin':
                    print(f"نوع المستخدم غير صحيح: {user_type}")
                    return False
                
                # التحقق من كلمة المرور
                password_match = check_password_hash(user.get('password', ''), password)
                print(f"هل كلمة المرور صحيحة؟ {password_match}")
                
                return password_match
            else:
                print("لم يتم العثور على المستخدم")
                return False
        except Exception as e:
            print(f"خطأ في التحقق من بيانات المستخدم: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def get_total_stores(self):
        """الحصول على إجمالي عدد المتاجر"""
        try:
            return self.db.stores.count_documents({})
        except Exception as e:
            print(f"خطأ في الحصول على عدد المتاجر: {str(e)}")
            return 0

    def get_total_products(self):
        """الحصول على إجمالي عدد المنتجات"""
        try:
            return self.db.products.count_documents({})
        except Exception as e:
            print(f"خطأ في الحصول على عدد المنتجات: {str(e)}")
            return 0

    def get_total_users(self):
        """الحصول على إجمالي عدد المستخدمين"""
        try:
            return self.db.users.count_documents({})
        except Exception as e:
            print(f"خطأ في الحصول على عدد المستخدمين: {str(e)}")
            return 0

    def get_total_orders(self):
        """الحصول على إجمالي عدد الطلبات"""
        try:
            return self.db.orders.count_documents({})
        except Exception as e:
            print(f"خطأ في الحصول على عدد الطلبات: {str(e)}")
            return 0

    def get_recent_stores(self, limit=5):
        """الحصول على آخر المتاجر المضافة"""
        try:
            return list(self.db.stores.find().sort('created_at', -1).limit(limit))
        except Exception as e:
            print(f"خطأ في الحصول على المتاجر الأخيرة: {str(e)}")
            return []

    def get_recent_products(self, limit=5):
        """الحصول على آخر المنتجات المضافة"""
        try:
            return list(self.db.products.find().sort('created_at', -1).limit(limit))
        except Exception as e:
            print(f"خطأ في الحصول على المنتجات الأخيرة: {str(e)}")
            return []

    def get_recent_users(self, limit=5):
        """الحصول على آخر المستخدمين المسجلين"""
        try:
            return list(self.db.users.find().sort('created_at', -1).limit(limit))
        except Exception as e:
            print(f"خطأ في الحصول على المستخدمين الأخيرين: {str(e)}")
            return []

    def verify_and_fix_stores(self):
        """التحقق من المتاجر وإصلاحها إذا لزم الأمر"""
        print("\n=== بدء التحقق من المتاجر ===")
        
        if not self.is_connected():
            print("خطأ: لا يوجد اتصال بقاعدة البيانات")
            return False
            
        try:
            # التحقق من وجود مجموعة المتاجر
            if 'stores' not in self.db.list_collection_names():
                print("إنشاء مجموعة المتاجر...")
                self.db.create_collection('stores')
            
            # التحقق من عدد المتاجر
            store_count = self.db.stores.count_documents({})
            print(f"عدد المتاجر الحالي: {store_count}")
            
            # التحقق من صحة بيانات المتاجر
            stores = list(self.db.stores.find())
            print(f"تم جلب {len(stores)} متجر للتحقق")
            
            for store in stores:
                try:
                    # التحقق من وجود المعرف
                    if '_id' not in store:
                        print(f"تم حذف متجر بدون معرف")
                        continue
                    
                    # التحقق من البيانات الأساسية
                    updates = {}
                    if 'name' not in store or not store['name']:
                        updates['name'] = 'متجر جديد'
                    if 'description' not in store:
                        updates['description'] = ''
                    if 'address' not in store:
                        updates['address'] = 'غير محدد'
                    if 'category' not in store:
                        updates['category'] = 'غير محدد'
                    if 'created_at' not in store:
                        updates['created_at'] = datetime.now()
                    
                    # تحديث البيانات إذا لزم الأمر
                    if updates:
                        print(f"تحديث بيانات المتجر: {store.get('name', 'بدون اسم')}")
                        self.db.stores.update_one(
                            {'_id': store['_id']},
                            {'$set': updates}
                        )
                
                except Exception as e:
                    print(f"خطأ في التحقق من المتجر: {str(e)}")
                    continue
            
            # التحقق النهائي
            final_count = self.db.stores.count_documents({})
            print(f"عدد المتاجر بعد التحقق: {final_count}")
            print("=== انتهى التحقق من المتاجر ===\n")
            
            return True
            
        except Exception as e:
            print(f"خطأ في التحقق من المتاجر: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def create_sample_store(self):
        """إنشاء متجر تجريبي إذا لم تكن هناك متاجر"""
        print("\n=== إنشاء متجر تجريبي ===")
        
        if not self.is_connected():
            print("خطأ: لا يوجد اتصال بقاعدة البيانات")
            return False
            
        try:
            # التحقق من وجود متاجر
            store_count = self.db.stores.count_documents({})
            if store_count > 0:
                print(f"يوجد {store_count} متجر بالفعل")
                return True
            
            # إنشاء متجر تجريبي
            sample_store = {
                'name': 'متجر تجريبي',
                'description': 'هذا متجر تجريبي للاختبار',
                'address': 'عنوان تجريبي',
                'category': 'إلكترونيات',
                'created_at': datetime.now()
            }
            
            result = self.db.stores.insert_one(sample_store)
            print(f"تم إنشاء متجر تجريبي: {result.inserted_id}")
            print("=== انتهى إنشاء المتجر التجريبي ===\n")
            return True
            
        except Exception as e:
            print(f"خطأ في إنشاء المتجر التجريبي: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def get_all_stores(self):
        """الحصول على جميع المتاجر"""
        print("\n=== بدء جلب المتاجر ===")
        
        if not self.is_connected():
            print("خطأ: لا يوجد اتصال بقاعدة البيانات")
            return []
            
        try:
            # التحقق من المتاجر أولاً
            self.verify_and_fix_stores()
            
            # إنشاء متجر تجريبي إذا لم تكن هناك متاجر
            store_count = self.db.stores.count_documents({})
            if store_count == 0:
                print("لا توجد متاجر، جاري إنشاء متجر تجريبي...")
                self.create_sample_store()
            
            # جلب المتاجر
            stores = []
            cursor = self.db.stores.find()
            
            for store in cursor:
                try:
                    if not store or '_id' not in store:
                        continue
                        
                    store_data = {
                        '_id': str(store['_id']),
                        'name': store.get('name', 'بدون اسم'),
                        'description': store.get('description', ''),
                        'address': store.get('address', 'غير محدد'),
                        'category': store.get('category', 'غير محدد'),
                        'image': store.get('image', ''),
                        'created_at': store.get('created_at')
                    }
                    stores.append(store_data)
                    print(f"تم إضافة متجر: {store_data['name']} - {store_data['_id']}")
                except Exception as e:
                    print(f"خطأ في تنسيق بيانات المتجر: {str(e)}")
                    continue
            
            print(f"\nتم جلب {len(stores)} متجر بنجاح")
            print("=== انتهى جلب المتاجر ===\n")
            return stores
            
        except Exception as e:
            print(f"خطأ في الحصول على المتاجر: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return []

    def get_all_products(self):
        """الحصول على جميع المنتجات"""
        try:
            return list(self.db.products.find())
        except Exception as e:
            print(f"خطأ في الحصول على المنتجات: {str(e)}")
            return []

    def get_all_users(self):
        """الحصول على جميع المستخدمين"""
        try:
            return list(self.db.users.find())
        except Exception as e:
            print(f"خطأ في الحصول على المستخدمين: {str(e)}")
            return []

    def delete_store(self, store_id):
        """حذف متجر وجميع منتجاته"""
        try:
            if not self.is_connected():
                print("خطأ: لا يوجد اتصال بقاعدة البيانات")
                return False

            # حذف جميع منتجات المتجر أولاً
            products_result = self.db.products.delete_many({'store_id': store_id})
            print(f"تم حذف {products_result.deleted_count} منتج من المتجر")

            # حذف المتجر
            store_result = self.db.stores.delete_one({'_id': ObjectId(store_id)})
            if store_result.deleted_count > 0:
                print(f"تم حذف المتجر بنجاح: {store_id}")
                return True
            else:
                print(f"لم يتم العثور على المتجر: {store_id}")
                return False

        except Exception as e:
            print(f"خطأ في حذف المتجر: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def delete_user(self, user_id):
        """حذف مستخدم ومتجره وجميع منتجاته"""
        try:
            if not self.is_connected():
                print("خطأ: لا يوجد اتصال بقاعدة البيانات")
                return False

            # البحث عن متجر المستخدم
            store = self.db.stores.find_one({'owner_id': str(user_id)})
            if store:
                store_id = str(store['_id'])
                # حذف جميع منتجات المتجر
                products_result = self.db.products.delete_many({'store_id': store_id})
                print(f"تم حذف {products_result.deleted_count} منتج من متجر المستخدم")

                # حذف المتجر
                store_result = self.db.stores.delete_one({'_id': ObjectId(store_id)})
                print(f"تم حذف متجر المستخدم: {store_id}")

            # حذف المستخدم
            user_result = self.db.users.delete_one({'_id': ObjectId(user_id)})
            if user_result.deleted_count > 0:
                print(f"تم حذف المستخدم بنجاح: {user_id}")
                return True
            else:
                print(f"لم يتم العثور على المستخدم: {user_id}")
                return False

        except Exception as e:
            print(f"خطأ في حذف المستخدم: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def update_user(self, user_id, user_data):
        """تحديث بيانات المستخدم"""
        try:
            result = self.db.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': user_data}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"خطأ في تحديث بيانات المستخدم: {str(e)}")
            return False

    def ensure_connection(self):
        """التأكد من الاتصال بقاعدة البيانات وإعادة الاتصال إذا لزم الأمر"""
        print("\n=== التحقق من الاتصال بقاعدة البيانات ===")
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                if not self.is_connected():
                    print(f"محاولة إعادة الاتصال {retry_count + 1} من {max_retries}")
                    self._initialize()
                
                # التحقق من الاتصال
                print("جاري التحقق من الاتصال...")
                try:
                    self.client.admin.command('ping')
                    print("الاتصال بقاعدة البيانات نشط")
                    
                    # التحقق من وجود مجموعة الطلبات
                    if 'orders' not in self.db.list_collection_names():
                        print("إنشاء مجموعة الطلبات...")
                        self.db.create_collection('orders')
                        print("تم إنشاء مجموعة الطلبات")
                    
                    return True
                except Exception as e:
                    print(f"فشل التحقق من الاتصال: {str(e)}")
                    raise
                
            except Exception as e:
                retry_count += 1
                print(f"فشل محاولة الاتصال {retry_count}: {str(e)}")
                if retry_count < max_retries:
                    print("انتظار 3 ثواني قبل المحاولة التالية...")
                    time.sleep(3)
                else:
                    print("فشلت جميع محاولات الاتصال")
                    return False
        
        return False

    def create_order(self, user_id, items, total, payment_method, name, phone, address, transfer_image=None):
        """إنشاء طلب جديد"""
        print("\n=== إنشاء طلب جديد ===")
        print(f"معرف المستخدم: {user_id}")
        print(f"عدد العناصر: {len(items)}")
        print(f"المجموع: {total}")
        print(f"طريقة الدفع: {payment_method}")
        
        try:
            # التحقق من الاتصال
            if not self.is_connected():
                print("خطأ: لا يوجد اتصال بقاعدة البيانات")
                return None
            
            # إنشاء الطلب
            order = {
                'user_id': user_id,
                'items': items,
                'total': total,
                'payment_method': payment_method,
                'name': name,
                'phone': phone,
                'address': address,
                'transfer_image': transfer_image,
                'status': 'pending',
                'created_at': datetime.utcnow()
            }
            
            print("جاري إدخال الطلب في قاعدة البيانات...")
            result = self.db.orders.insert_one(order)
            
            if result.inserted_id:
                print(f"تم إنشاء الطلب بنجاح: {result.inserted_id}")
                return str(result.inserted_id)
            else:
                print("فشل في إنشاء الطلب")
                return None
                
        except Exception as e:
            print(f"خطأ في إنشاء الطلب: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None

    def get_user_orders(self, user_id):
        """الحصول على طلبات المستخدم"""
        try:
            return list(self.db.orders.find({'user_id': user_id}).sort('created_at', -1))
        except Exception as e:
            print(f"خطأ في جلب طلبات المستخدم: {str(e)}")
            return []

    def get_all_orders(self, status=None, payment_method=None, start_date=None, end_date=None):
        """جلب جميع الطلبات مع إمكانية التصفية"""
        print("\n=== بدء جلب الطلبات ===")
        try:
            # التأكد من الاتصال
            if not self.ensure_connection():
                print("خطأ: لا يمكن الاتصال بقاعدة البيانات")
                return []
            
            # بناء الاستعلام
            query = {}
            if status:
                query['status'] = status
            if payment_method:
                query['payment_method'] = payment_method
            if start_date or end_date:
                query['created_at'] = {}
                if start_date:
                    query['created_at']['$gte'] = datetime.strptime(start_date, '%Y-%m-%d')
                if end_date:
                    query['created_at']['$lte'] = datetime.strptime(end_date, '%Y-%m-%d')
            
            print(f"استعلام الطلبات: {query}")
            
            try:
                # التحقق من وجود مجموعة الطلبات
                if 'orders' not in self.db.list_collection_names():
                    print("مجموعة الطلبات غير موجودة")
                    return []
                
                # جلب الطلبات
                print("جاري جلب الطلبات...")
                orders_cursor = self.db.orders.find(query)
                
                # تحويل النتائج إلى قائمة
                orders_list = []
                order_count = 0
                
                for order in orders_cursor:
                    try:
                        order_count += 1
                        print(f"معالجة الطلب رقم {order_count}")
                        
                        # التحقق من وجود المعرف
                        if '_id' not in order:
                            print("تم تخطي طلب بدون معرف")
                            continue
                            
                        # إنشاء نسخة جديدة من الطلب
                        processed_order = {
                            '_id': str(order['_id']),
                            'user_id': str(order.get('user_id', '')),
                            'name': order.get('name', ''),
                            'phone': order.get('phone', ''),
                            'address': order.get('address', ''),
                            'total': float(order.get('total', 0)),
                            'status': order.get('status', 'pending'),
                            'payment_method': order.get('payment_method', ''),
                            'transfer_image': order.get('transfer_image', ''),
                            'created_at': order.get('created_at'),
                            'order_items': []
                        }
                        
                        # معالجة العناصر
                        order_items = order.get('items', [])
                        if isinstance(order_items, list):
                            for item in order_items:
                                if isinstance(item, dict):
                                    processed_item = {
                                        'name': str(item.get('name', '')),
                                        'price': float(item.get('price', 0)),
                                        'quantity': int(item.get('quantity', 0)),
                                        'size': str(item.get('size', '')),
                                        'color': str(item.get('color', ''))
                                    }
                                    processed_order['order_items'].append(processed_item)
                                else:
                                    print(f"تم تخطي عنصر غير صالح: {item}")
                        else:
                            print(f"تم تخطي قائمة عناصر غير صالحة: {order_items}")
                        
                        orders_list.append(processed_order)
                        print(f"تم معالجة طلب: {processed_order['_id']}")
                        
                    except Exception as e:
                        print(f"خطأ في معالجة طلب: {str(e)}")
                        continue
                
                print(f"تم معالجة {len(orders_list)} طلب بنجاح")
                return orders_list
                
            except Exception as e:
                print(f"خطأ في جلب الطلبات من قاعدة البيانات: {str(e)}")
                import traceback
                print(traceback.format_exc())
                return []
            
        except Exception as e:
            print(f"خطأ عام في جلب الطلبات: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return []

    def update_order_status(self, order_id, status):
        """تحديث حالة الطلب"""
        try:
            result = self.db.orders.update_one(
                {'_id': ObjectId(order_id)},
                {'$set': {'status': status}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"خطأ في تحديث حالة الطلب: {str(e)}")
            return False

    def get_order_by_id(self, order_id):
        """الحصول على طلب بواسطة المعرف"""
        try:
            return self.db.orders.find_one({'_id': ObjectId(order_id)})
        except Exception as e:
            print(f"خطأ في جلب الطلب: {str(e)}")
            return None

    def complete_order(self, order_id):
        """إكمال طلب معين"""
        print(f"بدء عملية إكمال الطلب في قاعدة البيانات: {order_id}")
        try:
            if not self.is_connected():
                print("خطأ: لا يمكن الاتصال بقاعدة البيانات")
                return False
            
            result = self.db.orders.update_one(
                {'_id': ObjectId(order_id)},
                {'$set': {'status': 'completed'}}
            )
            
            if result.modified_count > 0:
                print(f"تم إكمال الطلب بنجاح: {order_id}")
                return True
            else:
                print(f"لم يتم العثور على الطلب: {order_id}")
                return False
        except Exception as e:
            print(f"خطأ في إكمال الطلب: {str(e)}")
            return False

    def cancel_order(self, order_id):
        """إلغاء طلب معين"""
        print(f"بدء عملية إلغاء الطلب في قاعدة البيانات: {order_id}")
        try:
            if not self.is_connected():
                print("خطأ: لا يمكن الاتصال بقاعدة البيانات")
                return False
            
            result = self.db.orders.update_one(
                {'_id': ObjectId(order_id)},
                {'$set': {'status': 'cancelled'}}
            )
            
            if result.modified_count > 0:
                print(f"تم إلغاء الطلب بنجاح: {order_id}")
                return True
            else:
                print(f"لم يتم العثور على الطلب: {order_id}")
                return False
        except Exception as e:
            print(f"خطأ في إلغاء الطلب: {str(e)}")
            return False

    def get_store_orders(self, store_id, days=None):
        """الحصول على طلبات المتجر"""
        try:
            if not self.is_connected():
                print("خطأ: لا يمكن الاتصال بقاعدة البيانات")
                return []
            
            # إنشاء فلتر للبحث
            filter_query = {"store_id": store_id}
            
            # إذا تم تحديد عدد الأيام، نضيف فلتر التاريخ
            if days:
                from datetime import datetime, timedelta
                start_date = datetime.now() - timedelta(days=days)
                filter_query["created_at"] = {"$gte": start_date}
            
            # البحث عن الطلبات
            orders = list(self.db.orders.find(filter_query))
            print(f"تم العثور على {len(orders)} طلب للمتجر {store_id}")
            return orders
        except Exception as e:
            print(f"خطأ في الحصول على طلبات المتجر: {str(e)}")
            return []

    def get_db(self):
        if self.db is None:
            self.logger.warning("لم يتم الاتصال بقاعدة البيانات. سيتم تشغيل التطبيق في وضع العرض فقط")
        return self.db
    
    def close(self):
        if self.client:
            self.client.close()
            self.logger.info("تم إغلاق الاتصال بقاعدة البيانات")

# إنشاء نسخة وحيدة من قاعدة البيانات
try:
    db = Database()
except Exception as e:
    print(f"فشل تهيئة قاعدة البيانات: {str(e)}")
    print("سيتم تشغيل التطبيق في وضع العرض فقط")
    # إنشاء كائن Database فارغ
    db = Database.__new__(Database)
    db.client = None
    db.db = None
    db.logger = logging.getLogger(__name__) 