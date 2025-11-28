# منصة تسويق المتاجر

منصة تسويق متكاملة تتيح للمستخدمين إنشاء متاجرهم الخاصة وعرض منتجاتهم للبيع.

## المميزات

- نظام تسجيل دخول وإنشاء حساب
- نوعين من المستخدمين: صاحب متجر وزبون
- إنشاء وإدارة المتاجر
- إدارة المنتجات
- عرض المتاجر حسب الأقسام
- لوحة تحكم للمتاجر
- لوحة تحكم رئيسية للمشرف

## متطلبات النظام

- Python 3.8+
- MongoDB
- Flask
- المتطلبات الأخرى موجودة في ملف requirements.txt

## التثبيت

1. قم بتثبيت MongoDB على جهازك
2. قم بنسخ المشروع:
```bash
git clone [رابط المشروع]
cd ecommerce_marketplace
```

3. قم بإنشاء بيئة افتراضية وتفعيلها:
```bash
python -m venv venv
source venv/bin/activate  # على Linux/Mac
venv\Scripts\activate     # على Windows
```

4. قم بتثبيت المتطلبات:
```bash
pip install -r requirements.txt
```

5. قم بإنشاء مجلد للصور:
```bash
mkdir static/uploads
```

6. قم بتشغيل التطبيق:
```bash
python app.py
```

## هيكل المشروع

```
ecommerce_marketplace/
├── app.py              # الملف الرئيسي للتطبيق
├── requirements.txt    # متطلبات المشروع
├── static/            # الملفات الثابتة
│   ├── css/          # ملفات CSS
│   └── uploads/      # مجلد الصور
└── templates/        # قوالب HTML
```

## الاستخدام

1. قم بفتح المتصفح وانتقل إلى `http://localhost:5000`
2. قم بإنشاء حساب جديد
3. اختر نوع الحساب (صاحب متجر أو زبون)
4. إذا كنت صاحب متجر، يمكنك إنشاء متجرك الخاص
5. قم بإدارة منتجاتك من لوحة التحكم

## المساهمة

نرحب بمساهماتكم! يرجى اتباع الخطوات التالية:

1. قم بعمل Fork للمشروع
2. قم بإنشاء فرع جديد (`git checkout -b feature/amazing-feature`)
3. قم بعمل Commit للتغييرات (`git commit -m 'Add some amazing feature'`)
4. قم بعمل Push للفرع (`git push origin feature/amazing-feature`)
5. قم بفتح طلب Pull Request

## الترخيص

هذا المشروع مرخص تحت رخصة MIT - انظر ملف LICENSE للمزيد من التفاصيل. 