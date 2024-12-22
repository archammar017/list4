import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

def get_database_schema():
    load_dotenv()
    
    # قراءة معلومات الاتصال من ملف .env
    config = {
        'host': os.getenv('DB_HOST'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'database': os.getenv('DB_DATABASE_office'),
        'port': os.getenv('DB_PORT')
    }
    
    try:
        # الاتصال بقاعدة البيانات
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        
        # الحصول على قائمة الجداول
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        schema = {}
        
        # لكل جدول، نجلب تفاصيل الأعمدة
        for table in tables:
            table_name = table[0]
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            
            # تخزين معلومات كل عمود
            column_info = []
            for column in columns:
                column_info.append({
                    'name': column[0],
                    'type': column[1],
                    'null': column[2],
                    'key': column[3],
                    'default': column[4],
                    'extra': column[5]
                })
            
            schema[table_name] = column_info
            
            # جلب معلومات المفاتيح الأجنبية
            cursor.execute(f"""
                SELECT 
                    COLUMN_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME 
                FROM
                    INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE
                    TABLE_SCHEMA = '{config['database']}'
                    AND TABLE_NAME = '{table_name}'
                    AND REFERENCED_TABLE_NAME IS NOT NULL
            """)
            
            foreign_keys = cursor.fetchall()
            if foreign_keys:
                schema[table_name + '_foreign_keys'] = [
                    {
                        'column': fk[0],
                        'references_table': fk[1],
                        'references_column': fk[2]
                    }
                    for fk in foreign_keys
                ]
        
        cursor.close()
        connection.close()
        
        return schema
        
    except Error as e:
        print(f"خطأ في الاتصال بقاعدة البيانات: {e}")
        return None

def print_schema():
    schema = get_database_schema()
    if not schema:
        return
    
    print("\n=== هيكل قاعدة البيانات ===\n")
    
    for table_name, columns in schema.items():
        if table_name.endswith('_foreign_keys'):
            continue
            
        print(f"\n📋 جدول: {table_name}")
        print("-" * 80)
        print(f"{'اسم العمود':<20} {'النوع':<15} {'NULL':<6} {'المفتاح':<8} {'القيمة الافتراضية':<15} {'إضافي'}")
        print("-" * 80)
        
        for column in columns:
            print(f"{column['name']:<20} {column['type']:<15} {column['null']:<6} {column['key']:<8} {str(column['default']):<15} {column['extra']}")
        
        # طباعة المفاتيح الأجنبية إن وجدت
        foreign_keys = schema.get(table_name + '_foreign_keys')
        if foreign_keys:
            print("\n🔑 المفاتيح الأجنبية:")
            for fk in foreign_keys:
                print(f"  • العمود {fk['column']} يرتبط مع {fk['references_table']}.{fk['references_column']}")

if __name__ == '__main__':
    print_schema()
