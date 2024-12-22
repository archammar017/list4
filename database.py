import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

class Database:
    def __init__(self):
        load_dotenv()
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
                port=self.port
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
        query = """
            SELECT 
                o.*,
                c.*,
                GROUP_CONCAT(DISTINCT cg.name) as custom_groups,
                GROUP_CONCAT(DISTINCT cg.color) as group_colors,
                p.ProjectName,
                p.ProjectNumber,
                p.Status as project_status
            FROM orders o 
            JOIN clientdata c ON o.Client_ID = c.ID
            LEFT JOIN task_group_assignments tga ON o.ID = tga.order_id
            LEFT JOIN custom_groups cg ON tga.group_id = cg.id
            LEFT JOIN projects p ON o.ID = p.QuotationID
            WHERE o.ID = %s
            GROUP BY o.ID
        """
        cursor.execute(query, (order_id,))
        order = cursor.fetchone()
        cursor.close()
        return order

    def get_order_statuses(self):
        if not self.connection or not self.connection.is_connected():
            self.connect()
            
        cursor = self.connection.cursor()
        query = "SHOW COLUMNS FROM orders LIKE 'Accept_Reject'"
        cursor.execute(query)
        result = cursor.fetchone()
        
        # استخراج القيم المسموح بها من نوع enum
        enum_str = result[1]
        statuses = enum_str.replace('enum(', '').replace(')', '').replace("'", '').split(',')
        cursor.close()
        return statuses

    def get_custom_groups(self):
        if not self.connection or not self.connection.is_connected():
            self.connect()
            
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM custom_groups WHERE is_active = 1"
        cursor.execute(query)
        groups = cursor.fetchall()
        cursor.close()
        return groups
