from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, 
                             QGridLayout, QWidget, QPushButton,
                             QScrollArea, QFrame)
from PyQt6.QtCore import Qt
from config import FIELD_TRANSLATIONS, STATUS_TRANSLATIONS

class OrderDetailsDialog(QDialog):
    def __init__(self, order_data, parent=None):
        super().__init__(parent)
        self.order_data = order_data
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("تفاصيل الطلب")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        main_layout = QVBoxLayout()
        
        # إنشاء منطقة قابلة للتمرير
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        
        # معلومات العميل
        client_group = self.create_section("معلومات العميل")
        client_grid = QGridLayout()
        client_fields = ["Name", "Phone", "Email"]
        self.add_fields_to_grid(client_grid, client_fields)
        client_group.setLayout(client_grid)
        content_layout.addWidget(client_group)
        
        # معلومات المشروع
        project_group = self.create_section("معلومات المشروع")
        project_grid = QGridLayout()
        project_fields = ["LandAddress", "LandArea", "Type", "Details"]
        self.add_fields_to_grid(project_grid, project_fields)
        project_group.setLayout(project_grid)
        content_layout.addWidget(project_group)
        
        # معلومات المساحات
        areas_group = self.create_section("تفاصيل المساحات")
        areas_grid = QGridLayout()
        area_fields = ["Basement", "GroundFloor", "Floor1", "Floor2", "Roof"]
        self.add_fields_to_grid(areas_grid, area_fields)
        areas_group.setLayout(areas_grid)
        content_layout.addWidget(areas_group)
        
        # معلومات الحالة
        status_group = self.create_section("حالة الطلب")
        status_grid = QGridLayout()
        status_fields = ["Accept_Reject", "Date", "ModifiedDate"]
        self.add_fields_to_grid(status_grid, status_fields)
        
        # إضافة معلومات المشروع إذا وجدت
        if self.order_data.get('ProjectName'):
            project_info_fields = ["ProjectName", "ProjectNumber", "project_status"]
            self.add_fields_to_grid(status_grid, project_info_fields, row_start=len(status_fields))
            
        status_group.setLayout(status_grid)
        content_layout.addWidget(status_group)
        
        # إضافة المجموعات المخصصة إذا وجدت
        if self.order_data.get('custom_groups'):
            groups = self.order_data['custom_groups'].split(',')
            colors = self.order_data['group_colors'].split(',')
            groups_label = QLabel("المجموعات:")
            groups_text = ", ".join(groups)
            content_layout.addWidget(groups_label)
            content_layout.addWidget(QLabel(groups_text))
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
        # زر الإغلاق
        close_btn = QPushButton("إغلاق")
        close_btn.clicked.connect(self.close)
        main_layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.setLayout(main_layout)
        
    def create_section(self, title):
        group = QFrame()
        group.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        group.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border-radius: 5px;
                margin: 5px;
                padding: 10px;
            }
        """)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #333;")
        layout = QVBoxLayout(group)
        layout.addWidget(title_label)
        return group
        
    def add_fields_to_grid(self, grid, fields, row_start=0):
        for i, field in enumerate(fields):
            if field not in self.order_data:
                continue
                
            row = row_start + i
            label = QLabel(FIELD_TRANSLATIONS.get(field, field) + ":")
            label.setStyleSheet("font-weight: bold;")
            
            value = self.order_data[field]
            if field == 'Accept_Reject':
                value = STATUS_TRANSLATIONS.get(value, value)
            elif isinstance(value, (int, float)):
                value = str(value)
            elif value is None:
                value = "-"
                
            value_label = QLabel(str(value))
            value_label.setWordWrap(True)
            
            grid.addWidget(label, row, 0)
            grid.addWidget(value_label, row, 1)
