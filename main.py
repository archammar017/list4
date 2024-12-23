import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QScrollArea, QMenu, QLabel,
                            QFrame, QPushButton, QLineEdit, QGridLayout, QSizePolicy,
                            QButtonGroup)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QDateTime
from PyQt6.QtGui import QAction, QFont
from database import Database
from config import STATUS_COLORS, STATUS_TRANSLATIONS, STATUS_LIGHT_COLORS
from order_details import OrderDetailsDialog
import json
import os
from functools import partial

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

class SelectionCircle(QLabel):
    clicked = pyqtSignal()
    
    # تدرجات اللون الأخضر من الفاتح إلى الغامق
    SELECTION_COLORS = [
        '#FFFFFF',  # أبيض
        '#E8F5E9',
        '#C8E6C9',
        '#A5D6A7',
        '#81C784',
        '#66BB6A',
        '#4CAF50',
        '#43A047',
        '#388E3C',
        '#2E7D32',
        '#1B5E20'   # أخضر غامق
    ]
    
    def __init__(self, level=0, parent=None):
        super().__init__(parent)
        self.setObjectName("selectionCircle")
        self.level = level
        self.update_color()
        self.setStyleSheet("""
            QLabel#selectionCircle {
                min-width: 20px;
                min-height: 20px;
                max-width: 20px;
                max-height: 20px;
                border-radius: 10px;
                border: 2px solid #ddd;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def update_color(self):
        self.setStyleSheet(f"""
            QLabel#selectionCircle {{
                min-width: 20px;
                min-height: 20px;
                max-width: 20px;
                max-height: 20px;
                border-radius: 10px;
                border: 2px solid {self.SELECTION_COLORS[self.level]};
                background-color: {self.SELECTION_COLORS[self.level]};
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

class OrderCard(QFrame):
    status_changed = pyqtSignal(int, str)
    
    def __init__(self, order_data, available_statuses, parent=None):
        super().__init__(parent)
        self.order_data = order_data
        self.available_statuses = available_statuses
        self.selection_level = 0
        self.db = Database()
        self.context_menu = None
        self.status_actions = []
        self.update_thread = None
        self.load_selection_state()
        self.load_selection_date()
        
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
            QLabel#dateLabel {
                color: #666;
                font-size: 11px;
                padding: 2px 5px;
            }
        """)
        
        # إنشاء التخطيط الرئيسي
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
        
        # حاوية للدائرة والتاريخ
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(10, 5, 0, 5)
        left_layout.setSpacing(2)
        
        # دائرة التحديد
        self.selection_circle = SelectionCircle(self.selection_level)
        self.selection_circle.level = self.selection_level
        self.selection_circle.update_color()
        self.selection_circle.clicked.connect(self.toggle_selection)
        left_layout.addWidget(self.selection_circle)
        
        # تاريخ آخر تحديث
        self.date_label = QLabel()
        self.date_label.setObjectName("dateLabel")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_date_label()  # تحديث نص التاريخ
        left_layout.addWidget(self.date_label)
        
        main_layout.addWidget(left_container)
        
        # محتوى الكرت
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 8, 10, 8)
        content_layout.setSpacing(4)
        
        # إضافة التخطيطات الأخرى هنا
        self.setup_content(content_layout)
        
        main_layout.addWidget(content_widget)
        
    def mousePressEvent(self, event):
        # نلغي تفعيل الضغط على الكرت
        super().mousePressEvent(event)
        
    def mouseDoubleClickEvent(self, event):
        # فتح نافذة تفاصيل الطلب
        details_dialog = OrderDetailsDialog(self.order_data['ID'], Database())
        details_dialog.exec()
        
    def contextMenuEvent(self, event):
        # إنشاء قائمة جديدة في كل مرة
        if self.context_menu:
            self.context_menu.deleteLater()
        
        self.context_menu = QMenu(self)
        self.context_menu.setStyleSheet("""
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
        
        # حذف الـ actions القديمة
        for action in self.status_actions:
            action.deleteLater()
        self.status_actions.clear()
        
        # إنشاء actions جديدة
        for status in self.available_statuses:
            if status != self.order_data['Accept_Reject']:
                action = QAction(STATUS_TRANSLATIONS.get(status, status), self)
                # استخدام functools.partial لتجنب مشكلة الـ lambda
                action.triggered.connect(partial(self.change_status, status))
                self.context_menu.addAction(action)
                self.status_actions.append(action)
        
        self.context_menu.exec(event.globalPos())
    
    def toggle_selection(self):
        # زيادة المستوى وإعادته إلى 0 إذا وصل للحد الأقصى
        self.selection_level = (self.selection_level + 1) % 11
        
        # تحديث التاريخ إذا كان المستوى > 0
        if self.selection_level > 0:
            now = QDateTime.currentDateTime()
            self.selection_date = now.toString("yyyy/MM/dd hh:mm")
        else:
            self.selection_date = None
        
        # تحديث الواجهة
        self.selection_circle.level = self.selection_level
        self.selection_circle.update_color()
        self.update_date_label()
        
        # حفظ الحالة
        self.save_selection_state()
        self.save_selection_date()
        
    def load_selection_state(self):
        try:
            if os.path.exists('selected_cards.json'):
                with open('selected_cards.json', 'r') as f:
                    selections = json.load(f)
                    # تحويل القيم القديمة (true/false) إلى المستوى الجديد
                    if str(self.order_data['ID']) in selections:
                        value = selections[str(self.order_data['ID'])]
                        if isinstance(value, bool):
                            self.selection_level = 1 if value else 0
                        else:
                            self.selection_level = int(value) if str(value).isdigit() else 0
                    else:
                        self.selection_level = 0
        except Exception as e:
            print(f"Error loading selection state: {e}")
            self.selection_level = 0
            
    def save_selection_state(self):
        try:
            selections = {}
            if os.path.exists('selected_cards.json'):
                with open('selected_cards.json', 'r') as f:
                    selections = json.load(f)
            
            selections[str(self.order_data['ID'])] = self.selection_level
            
            with open('selected_cards.json', 'w') as f:
                json.dump(selections, f)
        except Exception as e:
            print(f"Error saving selection state: {e}")
    
    def load_selection_date(self):
        """تحميل تاريخ التحديد من الملف"""
        try:
            if os.path.exists('selection_dates.json'):
                with open('selection_dates.json', 'r') as f:
                    dates = json.load(f)
                    self.selection_date = dates.get(str(self.order_data['ID']), None)
            else:
                self.selection_date = None
        except Exception as e:
            print(f"Error loading selection date: {e}")
            self.selection_date = None
    
    def save_selection_date(self):
        """حفظ تاريخ التحديد في الملف"""
        try:
            dates = {}
            if os.path.exists('selection_dates.json'):
                with open('selection_dates.json', 'r') as f:
                    dates = json.load(f)
            
            # تحديث أو حذف التاريخ
            if self.selection_level > 0:
                dates[str(self.order_data['ID'])] = self.selection_date
            else:
                dates.pop(str(self.order_data['ID']), None)
            
            with open('selection_dates.json', 'w', encoding='utf-8') as f:
                json.dump(dates, f, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving selection date: {e}")
    
    def update_date_label(self):
        """تحديث نص التاريخ في الواجهة"""
        if hasattr(self, 'date_label'):
            if self.selection_level > 0 and self.selection_date:
                self.date_label.setText(self.selection_date)
                self.date_label.show()
            else:
                self.date_label.hide()

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
        
    def change_status(self, new_status):
        """تغيير حالة الطلب"""
        if new_status == self.order_data['Accept_Reject']:
            return
            
        old_status = self.order_data['Accept_Reject']
        self.order_data['Accept_Reject'] = new_status
        
        # تحديث الواجهة
        self.setup_content(self.layout().itemAt(2).widget().layout())
        self.status_changed.emit(self.order_data['ID'], new_status)
        
        # إذا كان هناك thread قديم، ننتظر انتهاءه
        if self.update_thread and self.update_thread.isRunning():
            self.update_thread.wait()
        
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
            
class SidebarButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setAutoExclusive(True)  # يضمن أن زر واحد فقط يمكن تحديده
        self.setMinimumHeight(32)
        self.setStyleSheet("""
            QPushButton {
                text-align: right;
                padding: 8px 15px;
                border: none;
                border-radius: 0;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
            QPushButton:checked {
                background-color: #0078D4;
                color: white;
            }
        """)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.available_statuses = self.db.get_order_statuses()
        self.orders_cache = []
        self.current_filter = 'Pending'
        self.show_selected_only = False
        self.sort_descending = True  # ترتيب تنازلي افتراضياً
        self.search_text = ''
        self.setup_ui()
        self.load_orders()
        
        # إعداد المؤقت للتحديث التلقائي
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.load_orders)
        self.update_timer.start(60000)

    def setup_ui(self):
        self.setWindowTitle("نظام إدارة طلبات التصميم")
        self.setMinimumSize(800, 600)
        
        # الحاوية الرئيسية
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # الشريط الجانبي
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border-left: 1px solid #dee2e6;
            }
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # إنشاء مجموعة للأزرار
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        
        # زر المحددة مع قائمة الترتيب
        selected_container = QWidget()
        selected_layout = QHBoxLayout(selected_container)
        selected_layout.setContentsMargins(0, 0, 0, 0)
        selected_layout.setSpacing(0)
        
        selected_button = SidebarButton("المحددة")
        selected_button.setCheckable(True)
        selected_button.clicked.connect(self.toggle_selected_filter)
        selected_layout.addWidget(selected_button)
        
        sort_button = QPushButton("⇅")  # زر الترتيب
        sort_button.setFixedWidth(30)
        sort_button.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                color: #666;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        sort_button.clicked.connect(self.toggle_sort_order)
        selected_layout.addWidget(sort_button)
        
        sidebar_layout.addWidget(selected_container)
        
        # فاصل
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #dee2e6; margin: 5px 10px;")
        sidebar_layout.addWidget(separator)
        
        # زر جميع الطلبات
        all_button = SidebarButton("جميع الطلبات")
        self.button_group.addButton(all_button)
        all_button.clicked.connect(self.show_all_orders)
        sidebar_layout.addWidget(all_button)
        
        # أزرار الحالات
        for status in self.available_statuses:
            btn = SidebarButton(STATUS_TRANSLATIONS.get(status, status))
            self.button_group.addButton(btn)
            if status == 'Pending':
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, s=status: self.filter_by_status(s))
            sidebar_layout.addWidget(btn)
        
        sidebar_layout.addStretch()
        
        # زر الإغلاق
        close_button = QPushButton("إغلاق البرنامج")
        close_button.setObjectName("closeButton")
        close_button.clicked.connect(self.close_application)
        close_button.setStyleSheet("""
            QPushButton#closeButton {
                background-color: #dc3545;
                color: white;
                margin: 10px;
                border-radius: 4px;
                text-align: center;
            }
            QPushButton#closeButton:hover {
                background-color: #c82333;
            }
        """)
        sidebar_layout.addWidget(close_button)
        
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
            self.orders_cache = orders
            
            # حفظ حالة التحديد والتواريخ للكروت الحالية
            current_selections = {}
            current_dates = {}
            for i in range(self.orders_layout.count()):
                widget = self.orders_layout.itemAt(i).widget()
                if isinstance(widget, OrderCard):
                    order_id = str(widget.order_data['ID'])
                    current_selections[order_id] = widget.selection_level
                    if hasattr(widget, 'selection_date'):
                        current_dates[order_id] = widget.selection_date

            # حذف جميع الكروت الموجودة
            while self.orders_layout.count():
                item = self.orders_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # تجهيز قائمة الكروت مع تواريخها
            cards_data = []
            for order in orders:
                # فحص الفلتر الحالي
                status_filter = self.current_filter == 'all' or order['Accept_Reject'] == self.current_filter
                # فحص البحث
                search_filter = self.search_text.lower() in order.get('customer_name', '').lower() or \
                              self.search_text.lower() in str(order.get('customer_phone', '')).lower()
                # فحص التحديد
                order_id = str(order['ID'])
                selection_level = current_selections.get(order_id, 0)
                selected_filter = not self.show_selected_only or selection_level > 0

                if status_filter and search_filter and selected_filter:
                    selection_date = current_dates.get(order_id)
                    cards_data.append((order, selection_level, selection_date))

            # ترتيب الكروت حسب التاريخ إذا كان فلتر المحددة مفعل
            if self.show_selected_only:
                cards_data.sort(
                    key=lambda x: x[2] if x[2] else "0",  # استخدام التاريخ للترتيب
                    reverse=self.sort_descending  # ترتيب تنازلي أو تصاعدي
                )

            # إضافة الكروت المرتبة
            for order, selection_level, _ in cards_data:
                card = OrderCard(order, self.available_statuses)
                order_id = str(order['ID'])
                # استعادة حالة التحديد والتاريخ
                if order_id in current_selections:
                    card.selection_level = current_selections[order_id]
                    card.selection_circle.level = card.selection_level
                    card.selection_circle.update_color()
                    if order_id in current_dates:
                        card.selection_date = current_dates[order_id]
                        card.update_date_label()
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

    def toggle_selected_filter(self):
        """تبديل فلتر العناصر المحددة"""
        self.show_selected_only = not self.show_selected_only
        self.update_orders(self.orders_cache)

    def toggle_sort_order(self):
        """تبديل اتجاه الترتيب"""
        self.sort_descending = not self.sort_descending
        self.update_orders(self.orders_cache)
    
    def close_application(self):
        try:
            # إيقاف المؤقت
            self.update_timer.stop()
            
            # انتظار انتهاء جميع الـ threads
            for i in range(self.orders_layout.count()):
                widget = self.orders_layout.itemAt(i).widget()
                if isinstance(widget, OrderCard) and hasattr(widget, 'update_thread'):
                    if widget.update_thread and widget.update_thread.isRunning():
                        widget.update_thread.wait()
            
            # إغلاق اتصال قاعدة البيانات
            self.db.close_connection()
            
            # إغلاق التطبيق
            self.close()
            QApplication.quit()
        except Exception as e:
            print(f"Error closing application: {e}")
            self.close()
            QApplication.quit()

    def closeEvent(self, event):
        try:
            # إيقاف المؤقت
            self.update_timer.stop()
            
            # انتظار انتهاء جميع الـ threads
            for i in range(self.orders_layout.count()):
                widget = self.orders_layout.itemAt(i).widget()
                if isinstance(widget, OrderCard) and hasattr(widget, 'update_thread'):
                    if widget.update_thread and widget.update_thread.isRunning():
                        widget.update_thread.wait()
            
            # إغلاق اتصال قاعدة البيانات
            self.db.close_connection()
                
            event.accept()
        except Exception as e:
            print(f"Error during window closure: {e}")
            event.accept()
            
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
