import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QScrollArea, QMenu, QLabel,
                            QFrame, QPushButton, QLineEdit)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QFont
from database import Database
from config import STATUS_COLORS, STATUS_TRANSLATIONS, STATUS_LIGHT_COLORS
from order_details import OrderDetailsDialog

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
    def __init__(self, order_data, parent=None):
        super().__init__(parent)
        self.order_data = order_data
        self.setup_ui()
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.NoFrame)
        status = self.order_data['Accept_Reject']
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
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # شريط الحالة الجانبي
        status_bar = QFrame()
        status_bar.setFixedWidth(3)
        status_bar.setStyleSheet(f"""
            background-color: {STATUS_COLORS.get(status, '#ddd')};
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
        """)
        layout.addWidget(status_bar)
        
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
        layout.addWidget(content)
        
        self.setLayout(layout)
        
    def mouseDoubleClickEvent(self, event):
        dialog = OrderDetailsDialog(self.order_data, self)
        dialog.exec()
        
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
        
        status_menu = context_menu.addMenu("تغيير الحالة")
        db = Database()
        statuses = db.get_order_statuses()
        
        for status in statuses:
            action = QAction(STATUS_TRANSLATIONS.get(status, status), self)
            action.triggered.connect(lambda checked, s=status: self.change_status(s))
            status_menu.addAction(action)
            
        context_menu.exec(event.globalPos())
        
    def change_status(self, new_status):
        db = Database()
        db.update_order_status(self.order_data['ID'], new_status)
        self.order_data['Accept_Reject'] = new_status
        self.setup_ui()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.setup_ui()
        self.load_orders()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.load_orders)
        self.timer.start(60000)
        
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
        all_orders_btn.setChecked(True)
        all_orders_btn.clicked.connect(lambda: self.show_all_orders())
        sidebar_layout.addWidget(all_orders_btn)
        
        statuses = self.db.get_order_statuses()
        for status in statuses:
            btn = SidebarButton(STATUS_TRANSLATIONS.get(status, status))
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
        for i in reversed(range(self.orders_layout.count()-1)): 
            self.orders_layout.itemAt(i).widget().setParent(None)
        
        orders = self.db.get_orders()
        for order in orders:
            card = OrderCard(order)
            self.orders_layout.insertWidget(self.orders_layout.count()-1, card)
            
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
