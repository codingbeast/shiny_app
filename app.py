import sys, os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout, 
                              QLabel, QRadioButton, QVBoxLayout, QButtonGroup, 
                              QComboBox, QGroupBox, QFrame)
from PySide6.QtGui import QPalette
from PySide6.QtCore import Qt, Signal

# --------------------------
# Component Widget Classes
# --------------------------

COUNTRY_PATH = "ISO_country_names.txt"
OSAC_DAILY_PATH = "OSAC_daily.csv"
OSAC_MONTHLY_PATH = "OSAC_monthly.csv"


class PeriodSelector(QGroupBox):
    periodChanged = Signal(str)  # 'daily' or 'monthly'
    
    def __init__(self):
        super().__init__("Period")
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        self.button_group = QButtonGroup()
        
        self.daily_rb = QRadioButton("Daily")
        self.monthly_rb = QRadioButton("Monthly")
        self.monthly_rb.setChecked(True)
        
        self.button_group.addButton(self.daily_rb)
        self.button_group.addButton(self.monthly_rb)
        
        layout.addWidget(self.daily_rb)
        layout.addWidget(self.monthly_rb)
        self.setLayout(layout)
        
        # Connect signals
        self.daily_rb.toggled.connect(self.on_period_changed)
        
    def on_period_changed(self, checked):
        if checked:
            period = "daily" if self.daily_rb.isChecked() else "monthly"
            self.periodChanged.emit(period)

class CountrySelector(QGroupBox):
    countryChanged = Signal(str)
    
    def __init__(self, default_country=None):
        super().__init__("Country")
        self.default_country = default_country
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        self.combo_box = QComboBox()
        with open(COUNTRY_PATH, 'r', encoding='utf-8') as f:
            countries = [line.strip() for line in f]
        self.combo_box.addItems(countries)
        
        # Set default selection
        if self.default_country in countries:
            self.combo_box.setCurrentText(self.default_country)
        layout.addWidget(self.combo_box)
        self.setLayout(layout)
        
        # Connect signal
        self.combo_box.currentTextChanged.connect(self.countryChanged.emit)

class GraphDisplay(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Box)
        self.setStyleSheet("background-color: white;")
        self.setMinimumSize(500, 400)
        
    def update_data(self, period, country):
        """Update graph based on new parameters"""
        print(f"Updating graph for {country} ({period})")  # Replace with actual graph update

class SidePanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Box)
        self.setStyleSheet("background-color: #f0f0f0;")
        self.setMinimumSize(200, 400)
        
    def update_data(self, period, country):
        """Update side panel content"""
        print(f"Updating side panel for {country} ({period})")

class BottomPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Box)
        self.setStyleSheet("background-color: #e0e0e0;")
        self.setMinimumHeight(150)
        
    def update_data(self, period, country):
        """Update bottom panel content"""
        print(f"Updating bottom panel for {country} ({period})")

# --------------------------
# Main Window
# --------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        if not os.path.exists(COUNTRY_PATH):
            print(f"Error: {COUNTRY_PATH} not found.")
            sys.exit(1)
        elif not os.path.exists(OSAC_DAILY_PATH):
            print(f"Error: {OSAC_DAILY_PATH} not found.")
            sys.exit(1)
        elif not os.path.exists(OSAC_MONTHLY_PATH):
            print(f"Error: {OSAC_MONTHLY_PATH} not found.")
            sys.exit(1)
            
        
        self.setWindowTitle("Dashboard")
        self.setGeometry(100, 100, 1000, 700)
        
        # Current state
        self.current_period = "monthly"
        self.current_country = "United States of America"
        
        self.init_ui()
        
    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        grid = QGridLayout(main_widget)
        grid.setSpacing(15)
        grid.setContentsMargins(15, 15, 15, 15)

        # Create widgets
        self.period_selector = PeriodSelector()
        self.country_selector = CountrySelector()
        self.country_selector = CountrySelector(default_country=self.current_country)
        self.graph_display = GraphDisplay()
        self.side_panel = SidePanel()
        self.bottom_panel = BottomPanel()

        # Add to grid
        grid.addWidget(self.period_selector, 0, 1)
        grid.addWidget(self.country_selector, 0, 2)
        grid.addWidget(self.graph_display, 1, 1, 2, 2)
        grid.addWidget(self.side_panel, 1, 3, 2, 1)
        grid.addWidget(self.bottom_panel, 3, 0, 1, 3)

        # Set stretch factors
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 3)
        grid.setColumnStretch(2, 3)
        grid.setColumnStretch(3, 2)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 3)
        grid.setRowStretch(2, 3)
        grid.setRowStretch(3, 1)

        # Connect signals
        self.period_selector.periodChanged.connect(self.on_period_changed)
        self.country_selector.countryChanged.connect(self.on_country_changed)
        
    def on_period_changed(self, period):
        self.current_period = period
        self.update_all_widgets()
        
    def on_country_changed(self, country):
        self.current_country = country
        self.update_all_widgets()
        
    def update_all_widgets(self):
        """Update all widgets with current parameters"""
        self.graph_display.update_data(self.current_period, self.current_country)
        self.side_panel.update_data(self.current_period, self.current_country)
        self.bottom_panel.update_data(self.current_period, self.current_country)

# --------------------------
# Application Setup
# --------------------------

def force_light_mode():
    app = QApplication.instance()
    app.setStyle("Fusion")
    
    light_palette = QPalette()
    light_palette.setColor(QPalette.Window, Qt.white)
    light_palette.setColor(QPalette.WindowText, Qt.black)
    light_palette.setColor(QPalette.Base, Qt.white)
    light_palette.setColor(QPalette.Text, Qt.black)
    light_palette.setColor(QPalette.Button, Qt.lightGray)
    light_palette.setColor(QPalette.ButtonText, Qt.black)
    app.setPalette(light_palette)
    
    app.setStyleSheet("""
        QToolTip {
            color: black;
            background-color: white;
            border: 1px solid gray;
        }
    """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    force_light_mode()
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())