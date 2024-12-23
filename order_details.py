from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, 
                             QGridLayout, QWidget, QPushButton,
                             QScrollArea, QFrame, QHBoxLayout)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from config import FIELD_TRANSLATIONS, STATUS_TRANSLATIONS

class DataLoaderThread(QThread):
    data_loaded = pyqtSignal(dict)
    
    def __init__(self, db, order_id):
        super().__init__()
        self.db = db
        self.order_id = order_id
        
    def run(self):
        data = self.db.get_order_details(self.order_id)
        self.data_loaded.emit(data)

class LoadingLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dots = 0
        self.setText("جاري تحميل البيانات")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                font-size: 14pt;
                color: #7f8c8d;
                margin: 20px;
            }
        """)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_dots)
        self.timer.start(500)  # كل نصف ثانية
        
    def update_dots(self):
        self.dots = (self.dots + 1) % 4
        self.setText("جاري تحميل البيانات" + "." * self.dots)
        
    def stop(self):
        self.timer.stop()

class OrderDetailsDialog(QDialog):
    def __init__(self, order_id, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.order_id = order_id
        self.order_data = {}
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        self.setWindowTitle("تفاصيل الطلب")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)  # تغيير الاتجاه إلى اليسار
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                font-family: 'Segoe UI', 'Arial';
                font-size: 11pt;
            }
            QLabel[heading="true"] {
                font-size: 13pt;
                font-weight: bold;
                color: #2c3e50;
                padding: 5px 0;
                margin-top: 10px;
            }
            QFrame#separator {
                background-color: #ecf0f1;
                margin: 5px 0;
            }
        """)
        
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        
        # إنشاء منطقة قابلة للتمرير
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background-color: white; }")
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(20)
        
        # إضافة مؤشر التحميل المتحرك
        self.loading_label = LoadingLabel()
        self.content_layout.addWidget(self.loading_label)
        
        self.scroll.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll)
        
        # زر الإغلاق
        self.close_btn = QPushButton("إغلاق")
        self.close_btn.setFixedWidth(120)
        self.close_btn.setFixedHeight(35)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                border: none;
                border-radius: 4px;
                font-family: 'Segoe UI';
                font-size: 10pt;
                font-weight: bold;
                color: white;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #2472a4;
            }
        """)
        self.close_btn.clicked.connect(self.close)
        self.main_layout.addWidget(self.close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.setLayout(self.main_layout)
    
    def load_data(self):
        self.loader_thread = DataLoaderThread(self.db, self.order_id)
        self.loader_thread.data_loaded.connect(self.on_data_loaded)
        self.loader_thread.start()
    
    def on_data_loaded(self, data):
        self.order_data = data
        self.loading_label.stop()
        self.loading_label.deleteLater()
        self.update_ui()
    
    def update_ui(self):
        # معلومات العميل
        self.content_layout.addWidget(self.create_section_label("معلومات العميل"))
        self.content_layout.addLayout(self.create_info_grid(["Name", "Phone", "Email"]))
        self.content_layout.addWidget(self.create_separator())
        
        # معلومات المشروع
        self.content_layout.addWidget(self.create_section_label("معلومات المشروع"))
        self.content_layout.addLayout(self.create_info_grid(["LandAddress", "LandArea", "Type"]))
        self.content_layout.addWidget(self.create_separator())
        
        # تفاصيل المساحات
        self.content_layout.addWidget(self.create_section_label("تفاصيل المساحات"))
        self.content_layout.addLayout(self.create_info_grid(["Basement", "GroundFloor", "Floor1", "Floor2", "Roof"]))
        
        # عروض الأسعار
        self.content_layout.addWidget(self.create_separator())
        self.content_layout.addWidget(self.create_section_label("عروض الأسعار"))
        if self.order_data.get('Offers'):
            offers_container = QWidget()
            offers_container.setStyleSheet("""
                QWidget {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 5px;
                }
            """)
            offers_layout = QVBoxLayout(offers_container)
            offers_layout.setContentsMargins(10, 8, 10, 8)
            offers_layout.setSpacing(5)
            
            offer_label = QLabel(str(self.order_data['Offers']))
            offer_label.setWordWrap(True)
            offer_label.setStyleSheet("""
                color: #2c3e50;
                padding: 2px;
            """)
            offers_layout.addWidget(offer_label)
            
            self.content_layout.addWidget(offers_container)
        else:
            no_offers = QLabel("لا توجد عروض أسعار")
            no_offers.setStyleSheet("""
                color: #7f8c8d;
                padding: 10px;
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
            """)
            no_offers.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.addWidget(no_offers)
        
        # طلبات التصميم
        if self.order_data.get('Details'):
            self.content_layout.addWidget(self.create_separator())
            self.content_layout.addWidget(self.create_section_label("طلبات التصميم"))
            self.content_layout.addLayout(self.create_info_grid(["Details"]))
        
        # معلومات المشروع (إذا وجدت)
        if self.order_data.get('ProjectName'):
            self.content_layout.addWidget(self.create_separator())
            self.content_layout.addWidget(self.create_section_label("تفاصيل المشروع"))
            self.content_layout.addLayout(self.create_info_grid(["ProjectName", "ProjectNumber", "project_status"]))
        
        # معلومات الحالة
        self.content_layout.addWidget(self.create_separator())
        self.content_layout.addWidget(self.create_section_label("حالة الطلب"))
        self.content_layout.addLayout(self.create_info_grid(["Accept_Reject", "Date", "ModifiedDate"]))
        
        # المجموعات المخصصة
        if self.order_data.get('custom_groups'):
            self.content_layout.addWidget(self.create_separator())
            self.content_layout.addWidget(self.create_section_label("المجموعات"))
            groups = self.order_data['custom_groups'].split(',')
            groups_text = "، ".join(groups)
            groups_label = QLabel(groups_text)
            groups_label.setWordWrap(True)
            groups_label.setStyleSheet("""
                color: #333;
                padding: 5px;
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
            """)
            self.content_layout.addWidget(groups_label)

    def create_section_label(self, text):
        label = QLabel(text)
        label.setProperty("heading", True)
        return label
    
    def create_separator(self):
        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFixedHeight(1)
        separator.setFrameShape(QFrame.Shape.HLine)
        return separator
        
    def create_info_grid(self, fields):
        grid = QGridLayout()
        grid.setSpacing(15)  # المسافة بين الصفوف والحقول
        grid.setContentsMargins(20, 0, 20, 0)
        
        row = 0
        col = 0
        
        for field in fields:
            if field not in self.order_data:
                continue
                
            # إنشاء حاوية للحقل
            field_container = QWidget()
            field_container.setStyleSheet("""
                QWidget {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 5px;
                }
            """)
            
            # تخطيط أفقي للحقل
            field_layout = QHBoxLayout(field_container)
            field_layout.setContentsMargins(10, 8, 10, 8)
            field_layout.setSpacing(10)
            
            # تسمية الحقل
            label = QLabel(FIELD_TRANSLATIONS.get(field, field) + ":")
            label.setStyleSheet("""
                color: #34495e;
                font-weight: bold;
                padding: 2px;
            """)
            label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            
            # قيمة الحقل
            value = self.order_data[field]
            if field == 'Accept_Reject':
                value = STATUS_TRANSLATIONS.get(value, value)
            elif isinstance(value, (int, float)):
                value = str(value)
            elif value is None:
                value = "-"
            
            value_label = QLabel(str(value))
            value_label.setWordWrap(True)
            value_label.setStyleSheet("""
                color: #2c3e50;
                padding: 2px;
            """)
            value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            
            # إضافة العناصر إلى الحاوية
            field_layout.addWidget(label)
            field_layout.addWidget(value_label)
            field_layout.setStretch(0, 1)  # نسبة عرض العنوان
            field_layout.setStretch(1, 2)  # نسبة عرض القيمة
            
            # إضافة الحاوية إلى الشبكة
            grid.addWidget(field_container, row, col)
            
            # الانتقال إلى العمود التالي أو الصف التالي
            col += 1
            if col >= 2:  # بعد كل حقلين
                col = 0
                row += 1
        
        return grid
