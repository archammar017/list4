import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

# تحميل المتغيرات البيئية من الملف
# استخدام المسار الكامل للملف
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(env_path)

class Database:
    def __init__(self):
        self.host = os.getenv('DB_HOST')
        self.user = os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        self.database = os.getenv('DB_DATABASE_office')
        self.port = os.getenv('DB_PORT')
        self.connection = None
        
    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                auth_plugin='mysql_native_password'
            )
            return True
        except Error as e:
            print(f"Error connecting to database: {e}")
            return False
            
    def get_orders(self):
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor(dictionary=True)
        query = """
            SELECT 
                o.*,
                c.Name as customer_name,
                c.Phone as customer_phone,
                c.Email as customer_email,
                GROUP_CONCAT(DISTINCT cg.name) as custom_groups,
                GROUP_CONCAT(DISTINCT cg.color) as group_colors
            FROM orders o 
            JOIN clientdata c ON o.Client_ID = c.ID
            LEFT JOIN task_group_assignments tga ON o.ID = tga.order_id
            LEFT JOIN custom_groups cg ON tga.group_id = cg.id
            WHERE o.Offers IS NOT NULL AND o.Offers != ''
            GROUP BY o.ID
            ORDER BY o.Date DESC
        """
        cursor.execute(query)
        orders = cursor.fetchall()
        cursor.close()
        return orders
        
    def update_order_status(self, order_id, status):
        if not self.connection or not self.connection.is_connected():
            self.connect()
            
        cursor = self.connection.cursor()
        query = "UPDATE orders SET Accept_Reject = %s, ModifiedDate = NOW() WHERE ID = %s"
        cursor.execute(query, (status, order_id))
        self.connection.commit()
        cursor.close()
        
    def get_order_details(self, order_id):
        if not self.connection or not self.connection.is_connected():
            self.connect()
            
        cursor = self.connection.cursor(dictionary=True)
        
        # استعلام منفصل لجلب المجموعات
        groups_query = """
            SELECT 
                GROUP_CONCAT(DISTINCT cg.name) as custom_groups,
                GROUP_CONCAT(DISTINCT cg.color) as group_colors
            FROM orders o 
            LEFT JOIN task_group_assignments tga ON o.ID = tga.order_id
            LEFT JOIN custom_groups cg ON tga.group_id = cg.id
            WHERE o.ID = %s
        """
        cursor.execute(groups_query, (order_id,))
        groups_result = cursor.fetchone()
        
        # استعلام رئيسي لجلب باقي المعلومات
        main_query = """
            SELECT 
                o.*,
                c.*,
                p.ProjectName,
                p.ProjectNumber,
                p.Status as project_status
            FROM orders o 
            JOIN clientdata c ON o.Client_ID = c.ID
            LEFT JOIN projects p ON o.ID = p.QuotationID
            WHERE o.ID = %s
        """
        cursor.execute(main_query, (order_id,))
        order = cursor.fetchone()
        
        # دمج النتائج
        if order and groups_result:
            order.update(groups_result)
            
        cursor.close()
        return order if order else {}

    def get_order_statuses(self):
        return ["Pending", "Accepted", "Rejected"]
        
    def close_connection(self):
        """إغلاق اتصال قاعدة البيانات بشكل آمن"""
        try:
            if self.connection and self.connection.is_connected():
                self.connection.close()
                print("Database connection closed successfully")
        except Error as e:
            print(f"Error closing database connection: {e}")

    def get_custom_groups(self):
        if not self.connection or not self.connection.is_connected():
            self.connect()
            
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM custom_groups WHERE is_active = 1"
        cursor.execute(query)
        groups = cursor.fetchall()
        cursor.close()
        return groups

    def get_recently_changed_orders(self):
        if not self.connection or not self.connection.is_connected():
            self.connect()
            
        cursor = self.connection.cursor(dictionary=True)
        query = """
            SELECT 
                o.ID,
                o.Accept_Reject,
                o.ModifiedDate,
                c.Name as customer_name
            FROM orders o
            JOIN clientdata c ON o.Client_ID = c.ID
            WHERE o.ModifiedDate >= NOW() - INTERVAL 1 MINUTE
        """
        cursor.execute(query)
        orders = cursor.fetchall()
        cursor.close()
        return orders
