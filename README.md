# نظام إدارة طلبات التصميم

برنامج سطح مكتب لإدارة طلبات التصميم مع واجهة مستخدم رسومية باستخدام PyQt6.

## المميزات
- عرض الطلبات على شكل بطاقات
- إمكانية تغيير حالة الطلب من القائمة المنسدلة
- عرض تفاصيل الطلب عند النقر المزدوج
- دعم اللغة العربية
- ألوان مختلفة لكل حالة

## المتطلبات
- Python 3.8+
- PyQt6
- python-dotenv
- mysql-connector-python

## التثبيت
1. قم بتثبيت المتطلبات:
```bash
pip install -r requirements.txt
```

2. قم بإعداد ملف `.env` مع معلومات قاعدة البيانات:
```
DB_HOST=your_host
DB_USER=your_user
DB_PASSWORD=your_password
DB_DATABASE_office=your_database
DB_PORT=3306
```

## التشغيل
```bash
python main.py
```
