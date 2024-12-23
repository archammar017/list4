import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QScrollArea, QMenu, QLabel,
                            QFrame, QPushButton, QLineEdit)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QFont
from database import Database
from config import STATUS_COLORS, STATUS_TRANSLATIONS, STATUS_LIGHT_COLORS
from order_details import OrderDetailsDialog

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
        self.main_layout = None
        self.setup_ui()
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.NoFrame)
        status = self.order_data['Accept_Reject']
        
        # إعادة تعيين الستايل للبطاقة
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 4px;
                margin: 2px 6px;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
            }}
            QFrame:hover {{
                background-color: #fafafa;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
            }}
        """)
        
        # إزالة التخطيط القديم إذا وجد
        if self.main_layout:
            # إزالة كل العناصر من التخطيط
            while self.main_layout.count():
                item = self.main_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            # إزالة التخطيط نفسه
            QWidget().setLayout(self.main_layout)
        
        # إنشاء تخطيط جديد
        self.main_layout = QHBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # شريط الحالة الجانبي
        status_bar = QFrame()
        status_bar.setFixedWidth(3)
        status_bar.setStyleSheet(f"""
            background-color: {STATUS_COLORS.get(status, '#ddd')};
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
        """)
        self.main_layout.addWidget(status_bar)
        
        # محتوى البطاقة
        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(10, 8, 10, 8)
        content_layout.setSpacing(4)
        
        # اسم العميل والحالة
        header_layout = QHBoxLayout()
        name_label = QLabel(self.order_data['customer_name'])
        name_label.setStyleSheet("font-size: 10pt; font-weight: bold; color: #333;")
        header_layout.addWidget(name_label)
        
        status_text = STATUS_TRANSLATIONS.get(status, status)
        status_label = QLabel(status_text)
        status_label.setStyleSheet(f"""
            color: {STATUS_COLORS.get(status, '#666')};
            font-size: 9pt;
            padding: 1px 6px;
            background: #f5f5f5;
            border-radius: 3px;
        """)
        header_layout.addStretch()
        header_layout.addWidget(status_label)
        content_layout.addLayout(header_layout)
        
        # معلومات الاتصال والتاريخ في سطر واحد
        info_layout = QHBoxLayout()
        contact_info = QLabel(f"{self.order_data['customer_phone']}")
        if self.order_data.get('customer_email'):
            contact_info.setText(f"{self.order_data['customer_phone']} | {self.order_data['customer_email']}")
        contact_info.setStyleSheet("color: #666; font-size: 9pt;")
        info_layout.addWidget(contact_info)
        
        info_layout.addStretch()
        
        date_label = QLabel(self.order_data['Date'].strftime('%Y-%m-%d'))
        date_label.setStyleSheet("color: #666; font-size: 8pt;")
        info_layout.addWidget(date_label)
        
        content_layout.addLayout(info_layout)
        
        # المجموعات (إذا وجدت)
        if self.order_data.get('custom_groups'):
            groups = self.order_data['custom_groups'].split(',')
            groups_label = QLabel(" • ".join(groups))
            groups_label.setStyleSheet("color: #666; font-size: 8pt;")
            content_layout.addWidget(groups_label)
        
        content.setLayout(content_layout)
        self.main_layout.addWidget(content)
        
        self.setLayout(self.main_layout)
        
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
    
    def change_status(self, new_status):
        # حفظ الحالة القديمة للرجوع إليها في حالة الفشل
        old_status = self.order_data['Accept_Reject']
        
        # تحديث واجهة المستخدم فوراً
        self.order_data['Accept_Reject'] = new_status
        self.setup_ui()  # إعادة إنشاء واجهة البطاقة بالكامل
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
            self.setup_ui()  # إعادة إنشاء واجهة البطاقة بالكامل
            self.status_changed.emit(order_id, old_status)
            
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.available_statuses = self.db.get_order_statuses()
        self.orders_cache = {}  # تخزين مؤقت للطلبات
        self.setup_ui()
        self.load_orders()
        
        # تحديث كامل كل دقيقة
        self.full_update_timer = QTimer()
        self.full_update_timer.timeout.connect(self.load_orders)
        self.full_update_timer.start(60000)
        
        # تحديث سريع كل 10 ثواني للطلبات المتغيرة فقط
        self.quick_update_timer = QTimer()
        self.quick_update_timer.timeout.connect(self.quick_update)
        self.quick_update_timer.start(10000)
        
        # تطبيق الفلتر الافتراضي (قيد المراجعة)
        self.filter_by_status("Pending")
    
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
            btn.clicked.connect(lambda checked, s=status: self.filter_by_status(s))
            sidebar_layout.addWidget(btn)
            # تحديد زر "قيد المراجعة" كافتراضي
            if status == "Pending":
                btn.setChecked(True)
        
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
        self.search_input.textChanged.connect(self.filter_orders)
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
        self.update_thread.orders_updated.connect(self.on_orders_updated)
        self.update_thread.start()
    
    def on_orders_updated(self, orders):
        # حذف البطاقات القديمة
        for i in reversed(range(self.orders_layout.count()-1)): 
            widget = self.orders_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # إنشاء بطاقات جديدة
        for order in orders:
            card = OrderCard(order, self.available_statuses)
            card.status_changed.connect(self.on_order_status_changed)
            self.orders_layout.insertWidget(self.orders_layout.count()-1, card)
            self.orders_cache[order['ID']] = order
        
        # تطبيق فلتر قيد المراجعة على جميع البطاقات
        for i in range(self.orders_layout.count()-1):
            card = self.orders_layout.itemAt(i).widget()
            if isinstance(card, OrderCard):
                card.setVisible(card.order_data['Accept_Reject'] == "Pending")
    
    def on_order_status_changed(self, order_id, new_status):
        # تحديث الذاكرة المؤقتة
        if order_id in self.orders_cache:
            self.orders_cache[order_id]['Accept_Reject'] = new_status
        
        # إعادة تطبيق الفلتر الحالي
        current_filter = None
        for button in self.findChildren(SidebarButton):
            if button.isChecked():
                current_filter = button.text()
                break
        
        if current_filter:
            status = next((k for k, v in STATUS_TRANSLATIONS.items() if v == current_filter), None)
            if status:
                self.filter_by_status(status)
    
    def background_update(self):
        # تحديث كامل كل دقيقة
        self.load_orders()
    
    def quick_update(self):
        # تحديث سريع للطلبات المتغيرة فقط
        try:
            changed_orders = self.db.get_recently_changed_orders()  # تحتاج لإضافة هذه الدالة في database.py
            if changed_orders:
                for order in changed_orders:
                    if order['ID'] in self.orders_cache:
                        self.orders_cache[order['ID']] = order
                        # تحديث البطاقة المعنية فقط
                        for i in range(self.orders_layout.count()-1):
                            widget = self.orders_layout.itemAt(i).widget()
                            if isinstance(widget, OrderCard) and widget.order_data['ID'] == order['ID']:
                                widget.order_data = order
                                widget.setup_ui()
                                break
        except Exception as e:
            print(f"Error in quick update: {e}")

    def filter_orders(self):
        search_text = self.search_input.text().lower()
        
        for i in range(self.orders_layout.count()-1):
            card = self.orders_layout.itemAt(i).widget()
            order = card.order_data
            
            text_match = (
                search_text in order['customer_name'].lower() or
                search_text in order['customer_phone'].lower() or
                (order.get('customer_email') and search_text in order['customer_email'].lower())
            )
            
            card.setVisible(text_match)
            
    def filter_by_status(self, status):
        for i in range(self.orders_layout.count()-1):
            card = self.orders_layout.itemAt(i).widget()
            card.setVisible(card.order_data['Accept_Reject'] == status)
            
    def show_all_orders(self):
        for i in range(self.orders_layout.count()-1):
            card = self.orders_layout.itemAt(i).widget()
            card.setVisible(True)

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
