import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QScrollArea, QMenu, QLabel,
                            QFrame, QPushButton, QLineEdit, QGridLayout, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QFont
from database import Database
from config import STATUS_COLORS, STATUS_TRANSLATIONS, STATUS_LIGHT_COLORS
from order_details import OrderDetailsDialog
import json
import os

class OrdersUpdateThread(QThread):
    orders_updated = pyqtSignal(list)
    
    def __init__(self, db):
        super().__init__()
        self.db = db
    
    def run(self):
        try:
            orders = self.db.get_orders()
            self.orders_updated.emit(orders)
        except Exception as e:
            print(f"Error fetching orders: {e}")
            self.orders_updated.emit([])

class StatusUpdateThread(QThread):
    status_updated = pyqtSignal(bool, int, str)  # success, order_id, new_status
    
    def __init__(self, db, order_id, new_status):
        super().__init__()
        self.db = db
        self.order_id = order_id
        self.new_status = new_status
    
    def run(self):
        try:
            self.db.update_order_status(self.order_id, self.new_status)
            self.status_updated.emit(True, self.order_id, self.new_status)
        except Exception as e:
            print(f"Error updating status: {e}")
            self.status_updated.emit(False, self.order_id, self.new_status)

class SidebarButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setAutoExclusive(True)
        self.setMinimumHeight(32)  
        self.setStyleSheet("""
            QPushButton {
                text-align: right;
                padding: 4px 12px;
                border: none;
                border-radius: 0;
                color: #333;
                font-size: 10pt;
            }
            QPushButton:checked {
                background-color: #f0f0f0;
                font-weight: bold;
            }
            QPushButton:hover:!checked {
                background-color: #f8f8f8;
            }
        """)

class OrderCard(QFrame):
    status_changed = pyqtSignal(int, str)  # order_id, new_status
    
    def __init__(self, order_data, available_statuses, parent=None):
        super().__init__(parent)
        self.order_data = order_data
        self.available_statuses = available_statuses
        self.db = Database()
        self.selected = False
        self.load_selection_state()
        
        # تطبيق ستايل الكرت
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 4px;
                margin: 4px;
            }
            QFrame:hover {
                background-color: #f8f9fa;
            }
            QLabel#selectionCircle {
                min-width: 20px;
                min-height: 20px;
                max-width: 20px;
                max-height: 20px;
                border-radius: 10px;
                border: 2px solid #ddd;
                background-color: white;
            }
            QLabel#selectionCircle[selected="true"] {
                background-color: #28a745;
                border-color: #28a745;
            }
        """)
        
        # إنشاء التخطيط الرئيسي مباشرة
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)

        # شريط الحالة الجانبي
        status = self.order_data.get('Accept_Reject', '')
        status_bar = QFrame()
        status_bar.setFixedWidth(3)
        status_bar.setStyleSheet(f"""
            background-color: {STATUS_COLORS.get(status, '#ddd')};
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
        """)
        main_layout.addWidget(status_bar)
        
        # دائرة التحديد
        self.selection_circle = QLabel()
        self.selection_circle.setObjectName("selectionCircle")
        self.selection_circle.setProperty("selected", "true" if self.selected else "false")
        
        # إضافة padding للدائرة
        circle_container = QWidget()
        circle_layout = QHBoxLayout(circle_container)
        circle_layout.setContentsMargins(10, 0, 0, 0)
        circle_layout.addWidget(self.selection_circle)
        
        main_layout.addWidget(circle_container)
        
        # محتوى الكرت
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 8, 10, 8)
        content_layout.setSpacing(4)
        
        # إضافة التخطيطات الأخرى هنا
        self.setup_content(content_layout)
        
        main_layout.addWidget(content_widget)
        
    def setup_content(self, content_layout):
        # استخدام Grid Layout للتنسيق كجدول
        header_layout = QGridLayout()
        header_layout.setSpacing(0)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # اسم العميل - عامود 0
        name_label = QLabel(self.order_data.get('customer_name', ''))
        name_label.setStyleSheet("""
            font-size: 10pt;
            font-weight: bold;
            color: #333;
            padding-right: 15px;
            min-width: 150px;
        """)
        name_label.setFixedWidth(200)
        header_layout.addWidget(name_label, 0, 0)
        
        # رقم الجوال - عامود 1
        phone = str(self.order_data.get('customer_phone', ''))
        if phone.startswith('0'):
            phone = '966' + phone[1:]
        elif not phone.startswith('966'):
            phone = '966' + phone
            
        formatted_phone = ' '.join([phone[:3], phone[3:6], phone[6:]])
        phone_label = QLabel(f"<b>{formatted_phone}</b> |")
        phone_label.setStyleSheet("""
            font-size: 9pt;
            color: #666;
            padding: 0 15px;
            font-family: monospace;
            min-width: 130px;
        """)
        phone_label.setFixedWidth(150)
        phone_label.setTextFormat(Qt.TextFormat.RichText)
        header_layout.addWidget(phone_label, 0, 1)
        
        # الحالة - عامود 2
        status = self.order_data.get('Accept_Reject', '')
        status_text = STATUS_TRANSLATIONS.get(status, status)
        status_label = QLabel(status_text)
        status_label.setStyleSheet(f"""
            color: {STATUS_COLORS.get(status, '#666')};
            font-size: 9pt;
            padding: 1px 6px;
            border-radius: 3px;
        """)
        header_layout.addWidget(status_label, 0, 2)
        
        # إضافة stretch للمسافة المتبقية
        header_layout.setColumnStretch(2, 1)
        
        content_layout.addLayout(header_layout)
        
        # عروض الأسعار
        if self.order_data.get('Offers'):
            offers_layout = QHBoxLayout()
            offers = self.order_data['Offers'].replace(';', ' | ')
            offers_label = QLabel(offers)
            offers_label.setStyleSheet("""
                color: #666;
                font-size: 9pt;
                padding: 2px 0;
            """)
            offers_layout.addWidget(offers_label)
            offers_layout.addStretch()
            
            date_label = QLabel(self.order_data['Date'].strftime('%Y-%m-%d'))
            date_label.setStyleSheet("color: #666; font-size: 8pt;")
            offers_layout.addWidget(date_label)
            
            content_layout.addLayout(offers_layout)
        
        # المجموعات (إذا وجدت)
        if self.order_data.get('custom_groups'):
            groups = self.order_data['custom_groups'].split(',')
            colors = self.order_data['group_colors'].split(',') if self.order_data.get('group_colors') else []
            
            groups_layout = QHBoxLayout()
            for i, group in enumerate(groups):
                color = colors[i] if i < len(colors) else '#666'
                dot = QLabel('•')
                dot.setStyleSheet(f'color: {color}; font-size: 14pt; padding: 0 2px;')
                groups_layout.addWidget(dot)
                
                group_label = QLabel(group.strip())
                group_label.setStyleSheet('color: #666; font-size: 9pt;')
                groups_layout.addWidget(group_label)
            
            groups_layout.addStretch()
            content_layout.addLayout(groups_layout)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_selection()
        super().mousePressEvent(event)
        
    def mouseDoubleClickEvent(self, event):
        # فتح نافذة تفاصيل الطلب
        details_dialog = OrderDetailsDialog(self.order_data['ID'], self.db)
        details_dialog.exec()
        
    def contextMenuEvent(self, event):
        context_menu = QMenu(self)
        context_menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #ddd;
            }
            QMenu::item {
                padding: 6px 20px;
            }
            QMenu::item:selected {
                background-color: #f0f0f0;
            }
        """)
        
        for status in self.available_statuses:
            if status != self.order_data['Accept_Reject']:
                action = QAction(STATUS_TRANSLATIONS.get(status, status), self)
                action.triggered.connect(lambda checked, s=status: self.change_status(s))
                context_menu.addAction(action)
            
        context_menu.exec(event.globalPos())
    
    def toggle_selection(self):
        self.selected = not self.selected
        self.selection_circle.setProperty("selected", "true" if self.selected else "false")
        self.selection_circle.style().unpolish(self.selection_circle)
        self.selection_circle.style().polish(self.selection_circle)
        self.save_selection_state()
        
    def load_selection_state(self):
        try:
            if os.path.exists('selected_cards.json'):
                with open('selected_cards.json', 'r') as f:
                    selections = json.load(f)
                    self.selected = selections.get(str(self.order_data['ID']), False)
        except Exception as e:
            print(f"Error loading selection state: {e}")
            self.selected = False
            
    def save_selection_state(self):
        try:
            selections = {}
            if os.path.exists('selected_cards.json'):
                with open('selected_cards.json', 'r') as f:
                    selections = json.load(f)
            
            selections[str(self.order_data['ID'])] = self.selected
            
            with open('selected_cards.json', 'w') as f:
                json.dump(selections, f)
        except Exception as e:
            print(f"Error saving selection state: {e}")
    
    def change_status(self, new_status):
        # حفظ الحالة القديمة للرجوع إليها في حالة الفشل
        old_status = self.order_data['Accept_Reject']
        
        # تحديث واجهة المستخدم فوراً
        self.order_data['Accept_Reject'] = new_status
        self.setup_content(self.layout().itemAt(2).widget().layout())
        self.status_changed.emit(self.order_data['ID'], new_status)
        
        # تحديث قاعدة البيانات في الخلفية
        self.update_thread = StatusUpdateThread(self.db, self.order_data['ID'], new_status)
        self.update_thread.status_updated.connect(lambda success, order_id, status: 
            self.handle_status_update(success, order_id, status, old_status))
        self.update_thread.start()
    
    def handle_status_update(self, success, order_id, new_status, old_status):
        if not success:
            # إذا فشل التحديث، نرجع للحالة القديمة
            print(f"فشل تحديث الحالة في قاعدة البيانات. الرجوع للحالة السابقة.")
            self.order_data['Accept_Reject'] = old_status
            self.setup_content(self.layout().itemAt(2).widget().layout())
            self.status_changed.emit(order_id, old_status)
            
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.available_statuses = self.db.get_order_statuses()
        self.orders_cache = []  # تغيير من dict إلى list
        self.current_filter = 'Pending'  # تعيين الفلتر الافتراضي إلى قيد المراجعة
        self.search_text = ''
        self.setup_ui()
        self.load_orders()
        
        # إعداد المؤقت للتحديث التلقائي
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.load_orders)
        self.update_timer.start(60000)  # تحديث كل دقيقة

    def setup_ui(self):
        self.setWindowTitle("نظام إدارة طلبات التصميم")
        self.setMinimumSize(800, 600)  
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # القائمة الجانبية
        sidebar = QWidget()
        sidebar.setFixedWidth(160)  
        sidebar.setStyleSheet("background-color: white; border-left: 1px solid #e0e0e0;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 6, 0, 6)
        sidebar_layout.setSpacing(1)
        
        all_orders_btn = SidebarButton("جميع الطلبات")
        all_orders_btn.clicked.connect(lambda: self.show_all_orders())
        sidebar_layout.addWidget(all_orders_btn)
        
        for status in self.available_statuses:
            btn = SidebarButton(STATUS_TRANSLATIONS.get(status, status))
            btn.setCheckable(True)
            # تفعيل زر "قيد المراجعة" عند بدء التشغيل
            if status == 'Pending':
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, s=status: self.filter_by_status(s))
            sidebar_layout.addWidget(btn)
        
        sidebar_layout.addStretch()
        main_layout.addWidget(sidebar)
        
        # منطقة الطلبات
        orders_widget = QWidget()
        orders_layout = QVBoxLayout(orders_widget)
        orders_layout.setContentsMargins(0, 0, 0, 0)
        
        # شريط البحث
        search_widget = QWidget()
        search_widget.setStyleSheet("background-color: white; border-bottom: 1px solid #e0e0e0;")
        search_layout = QHBoxLayout(search_widget)
        search_layout.setContentsMargins(10, 6, 10, 6)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("بحث...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 4px 8px;
                border: 1px solid #e0e0e0;
                border-radius: 3px;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border-color: #0078D4;
            }
        """)
        self.search_input.textChanged.connect(self.search_orders)
        search_layout.addWidget(self.search_input)
        orders_layout.addWidget(search_widget)
        
        # قائمة الطلبات
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #f5f5f5; }")
        
        self.orders_container = QWidget()
        self.orders_layout = QVBoxLayout(self.orders_container)
        self.orders_layout.setContentsMargins(15, 15, 15, 15)
        self.orders_layout.addStretch()
        
        scroll_area.setWidget(self.orders_container)
        orders_layout.addWidget(scroll_area)
        
        main_layout.addWidget(orders_widget)
        
    def load_orders(self):
        self.update_thread = OrdersUpdateThread(self.db)
        self.update_thread.orders_updated.connect(self.update_orders)
        self.update_thread.start()
    
    def update_orders(self, orders):
        try:
            self.orders_cache = orders  # تحديث الكاش
            # حذف جميع الكروت الموجودة
            while self.orders_layout.count():
                item = self.orders_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # إضافة الكروت الجديدة
            for order in orders:
                if self.current_filter == 'all' or order['Accept_Reject'] == self.current_filter:
                    if self.search_text.lower() in order.get('customer_name', '').lower() or \
                       self.search_text.lower() in str(order.get('customer_phone', '')).lower():
                        card = OrderCard(order, self.available_statuses)
                        card.status_changed.connect(self.on_status_changed)
                        self.orders_layout.addWidget(card)

            # إضافة widget فارغ في النهاية لدفع الكروت للأعلى
            spacer = QWidget()
            spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.orders_layout.addWidget(spacer)
        except Exception as e:
            print(f"Error updating orders: {e}")

    def on_status_changed(self, order_id, new_status):
        # تحديث الواجهة بعد تغيير الحالة
        try:
            # تحديث الكاش
            for order in self.orders_cache:
                if order['ID'] == order_id:
                    order['Accept_Reject'] = new_status
                    break
            # تحديث الواجهة
            self.update_orders(self.orders_cache)
        except Exception as e:
            print(f"Error in status change: {e}")

    def filter_by_status(self, status):
        self.current_filter = status
        self.update_orders(self.orders_cache)
            
    def show_all_orders(self):
        self.current_filter = 'all'
        self.update_orders(self.orders_cache)

    def search_orders(self):
        self.search_text = self.search_input.text().lower()
        self.update_orders(self.orders_cache)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    app.setStyleSheet("""
        QMainWindow {
            background-color: white;
        }
    """)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
