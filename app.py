import sys
import os
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, 
    QLabel, QRadioButton, QVBoxLayout, QButtonGroup, 
    QComboBox, QGroupBox, QFrame, QMessageBox, QSizePolicy
)
from PySide6.QtGui import (
    QPalette, QPainter, QPen, QColor
)
from PySide6.QtCore import (
    Qt, Signal, QSize, QRect, QTimer
)
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.collections import PatchCollection

# Constants
COUNTRY_PATH = "ISO_country_names.txt"
OSAC_DAILY_PATH = "OSAC_daily.csv"
OSAC_MONTHLY_PATH = "OSAC_monthly.csv"


class DataParser:
    
    @staticmethod
    def monthly_df_parsed(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()  # Ensure it's a deep copy, not a view
        current_date = pd.to_datetime('today')
        df.rename(columns={'month': 'date'}, inplace=True)
        df['date'] = pd.to_datetime(df['date'], format='%Y-%m', errors='coerce')
        df['formatted_date'] = df['date'].dt.strftime('%b\n%Y')
        filtered_df = df[(df['date'] >= current_date - pd.DateOffset(months=12))]
        filtered_df = filtered_df.sort_values(by='date', ascending=True)
        filtered_df = filtered_df.reset_index(drop=True)
        return filtered_df
    @staticmethod
    def daily_df_parsed(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()  # Ensure it's a deep copy, not a view
        df.rename(columns={'month': 'date'}, inplace=True)
        current_date = pd.to_datetime('today')
        df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')
        df['formatted_date'] = df['date'].dt.strftime('%b %d\n%Y')
        filtered_df = df.sort_values(by='date', ascending=True)
        filtered_df = filtered_df[
            (filtered_df['date'] >= current_date - pd.DateOffset(days=31)) &
            (filtered_df['date'] <= current_date)
        ]
        filtered_df = filtered_df.reset_index(drop=True)
        filtered_df['group'] = filtered_df.index // 2
        grouped_df = (
            filtered_df
            .groupby('group')
            .agg({
                'country': 'first',
                'date': 'last',  # Take second date in the pair
                'protest': 'max',
                'suppression': 'max',
                'anticipated': 'max',
            })
            .reset_index(drop=True)
        )

        # Add formatted_date again
        grouped_df['formatted_date'] = grouped_df['date'].dt.strftime('%b %d\n%Y')
        return grouped_df
    @staticmethod
    def fast_plot_monthly(df, ax,  n_circles=11):
        circle_radius = 0.15
        circle_gap = 0.4
        bar_width = 0.6

        patches = []
        colors = []

        bar_height = n_circles * (2 * circle_radius + circle_gap)

        for idx, row in enumerate(df[['protest', 'anticipated', 'suppression']].values):
            p, a, s = row

            if (p, a, s) == (1, 1, 1):
                color = 'green'
                solid = True
            elif (p, a, s) == (1, 1, 0):
                color = 'gray'
                solid = True
            elif (p, a, s) in [(1, 0, 1), (0, 1, 1)]:
                color = 'green'
                solid = False
            elif (p, a, s) in [(1, 0, 0), (0, 1, 0), (0, 0, 1)]:
                color = 'gray'
                solid = False
            else:
                continue  # (0,0,0)

            if solid:
                ax.bar(idx, bar_height, color=color, width=bar_width)
            else:
                for i in range(n_circles):
                    y = i * (2 * circle_radius + circle_gap) + circle_radius
                    patches.append(Circle((idx, y), circle_radius))
                    colors.append(color)

        if patches:
            collection = PatchCollection(patches, facecolor=colors, edgecolor=colors)
            ax.add_collection(collection)

        # Formatting
        ax.set_xlim(-0.5, len(df) - 0.5)
        ax.set_xticks(range(len(df)))
        ax.set_xticklabels(df['formatted_date'],fontsize=5)
        ax.set_ylim(0, bar_height + 1)
        ax.set_yticks([])
        # Set equal aspect ratio and manually adjust limits
        ax.set_aspect('equal', adjustable='box')
        # Remove the graph border
        for spine in ax.spines.values():
            spine.set_visible(False)
            
class DataManager:
    """Centralized data loading and management"""
    def __init__(self):
        self.daily_data = None
        self.monthly_data = None
        self.load_data()
    
    def load_data(self):
        """Load all required data files"""
        try:
            self.daily_data = pd.read_csv(OSAC_DAILY_PATH)
            self.monthly_data = pd.read_csv(OSAC_MONTHLY_PATH)
        except Exception as e:
            print(f"Error loading data: {e}")
            self.daily_data = pd.DataFrame()
            self.monthly_data = pd.DataFrame()
    
    def get_country_data(self, period, country) -> pd.DataFrame:
        """Get data for specific country and period"""
        data = self.daily_data if period == "daily" else self.monthly_data
        if 'country' in data.columns:
            return data[data['country'] == country]
        return pd.DataFrame()

class BusySpinner(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Spinner properties
        self._angle = 0
        self._timer_id = None
        self._active = False
        self._color = QColor(70, 130, 180)  # Steel blue
        self._pen_width = 4
        self._size = QSize(60, 60)
        
    def start(self):
        """Start the spinning animation"""
        if not self._active:
            self._active = True
            self._timer_id = self.startTimer(50)  # Update every 50ms
            self.setVisible(True)
            
    def stop(self):
        """Stop the spinning animation"""
        if self._active:
            self.killTimer(self._timer_id)
            self._active = False
            self.setVisible(False)
            self.update()
            
    def timerEvent(self, event):
        """Handle timer events to update animation"""
        if event.timerId() == self._timer_id:
            self._angle = (self._angle + 30) % 360  # Increment angle
            self.update()
            
    def paintEvent(self, event):
        """Custom painting of the spinner"""
        if not self._active:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate centered rectangle
        rect = QRect(0, 0, self._size.width(), self._size.height())
        rect.moveCenter(self.rect().center())
        
        # Configure pen
        pen = QPen()
        pen.setWidth(self._pen_width)
        pen.setCapStyle(Qt.RoundCap)
        pen.setColor(self._color)
        painter.setPen(pen)
        
        # Draw arc (start angle, span angle)
        span_angle = 270 * 16  # 270 degrees in 1/16th of a degree units
        painter.drawArc(rect, self._angle * 16, span_angle)
    
    # Add the missing setColor method
    def setColor(self, color):
        """Set the spinner color"""
        self._color = color
        self.update()
        
    def setPenWidth(self, width):
        """Set the spinner line width"""
        self._pen_width = width
        self.update()
        
    def setSize(self, size):
        """Set the spinner size"""
        self._size = size
        self.update()

class GraphDisplay(QFrame, DataParser):
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.setFrameShape(QFrame.Box)
        self.setStyleSheet("background-color: white;")
        self.setMinimumSize(500, 400)
        
        # Main content
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # Add this
        self.canvas.updateGeometry()  # Add this
        # Create overlay widget for spinner
        self.overlay = QWidget(self)
        self.overlay.setStyleSheet("background-color: rgba(255, 255, 255, 200);")
        self.overlay.hide()
        
        # Create loading spinner
        self.spinner = BusySpinner(self.overlay)
        self.spinner.setColor(QColor(70, 130, 180))
        
        # Layout for overlay
        overlay_layout = QVBoxLayout(self.overlay)
        overlay_layout.addWidget(self.spinner, 0, Qt.AlignCenter)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        
    def show_loading(self, show=True):
        """Show or hide loading spinner"""
        if show:
            self.overlay.resize(self.size())
            self.overlay.raise_()
            self.overlay.show()
            self.spinner.start()
        else:
            self.overlay.hide()
            self.spinner.stop()
        QApplication.processEvents()
        
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        self.overlay.resize(self.size())
    
    def update_data(self, period, country):
        """Update graph data with loading indicator"""
        self.show_loading(True)
        
        try:
            self.figure.clear()
            plt.close('all')  # Close any lingering figures
            ax = self.figure.add_subplot(111)
            
            # Get data from centralized DataManager
            country_data = self.data_manager.get_country_data(period, country)
            if not country_data.empty:
                if period=="monthly":
                    parsed_df = DataParser.monthly_df_parsed(country_data)
                    DataParser.fast_plot_monthly(df=parsed_df, ax = ax)
                    #ax.set_title(f"Monthly Data for {country}", fontsize=10)
                elif period == "daily":
                    parsed_df = DataParser.daily_df_parsed(country_data)
                    DataParser.fast_plot_monthly(df=parsed_df, ax = ax)
                    #ax.set_title(f"Daily Data for {country}", fontsize=10)
            else:
                ax.text(0.5, 0.5, f"No data for {country}", ha='center', va='center')
                
            self.figure.tight_layout()
            self.canvas.draw()
        except Exception as e:
            ax.text(0.5, 0.5, f"Error loading data:\n{str(e)}", 
                   ha='center', va='center')
            self.canvas.draw()
        finally:
            self.show_loading(False)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize data manager
        self.data_manager = DataManager()
        
        # Verify required files exist
        self.verify_files()
        
        self.setWindowTitle("OSAC Data Dashboard")
        self.setGeometry(100, 100, 1000, 700)
        
        # Initialize with default values
        self.current_period = "monthly"
        self.current_country = "United States of America"
        
        self.init_ui()
        self.load_initial_data()
        
    def verify_files(self):
        missing_files = []
        for f in [COUNTRY_PATH, OSAC_DAILY_PATH, OSAC_MONTHLY_PATH]:
            if not os.path.exists(f):
                missing_files.append(f)
        
        if missing_files:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Missing data files")
            msg.setInformativeText(f"Could not find: {', '.join(missing_files)}")
            msg.exec()
            sys.exit(1)
    
    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        grid = QGridLayout(main_widget)
        grid.setSpacing(15)
        grid.setContentsMargins(15, 15, 15, 15)

        # Create widgets with data manager reference
        self.period_selector = PeriodSelector()
        self.country_selector = CountrySelector(default_country=self.current_country)
        self.graph_display = GraphDisplay(self.data_manager)
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
        
    def load_initial_data(self):
        """Load data and trigger initial display"""
        self.current_country = self.country_selector.combo_box.currentText()
        self.update_all_widgets()
        
    def on_period_changed(self, period):
        self.current_period = period
        self.update_all_widgets()
        
    def on_country_changed(self, country):
        self.current_country = country
        self.update_all_widgets()
        
    def update_all_widgets(self):
        """Update all widgets with current parameters"""
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            QApplication.processEvents()
            
            # Get data once and pass to all widgets
            country_data = self.data_manager.get_country_data(
                self.current_period, 
                self.current_country
            )
            
            self.graph_display.update_data(self.current_period, self.current_country)
            self.side_panel.update_data(self.current_period, self.current_country)
            self.bottom_panel.update_data(self.current_period, self.current_country)
        finally:
            QApplication.restoreOverrideCursor()

class PeriodSelector(QGroupBox):
    periodChanged = Signal(str)
    
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
        
        # Connect clicked signals instead of toggled
        self.daily_rb.clicked.connect(lambda: self.emit_period("daily"))
        self.monthly_rb.clicked.connect(lambda: self.emit_period("monthly"))
        
    def emit_period(self, period):
        """Force emit the period regardless of previous state"""
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
        
        try:
            with open(COUNTRY_PATH, 'r', encoding='utf-8') as f:
                countries = [line.strip() for line in f if line.strip()]
            self.combo_box.addItems(countries)
            
            if self.default_country and self.default_country in countries:
                self.combo_box.setCurrentText(self.default_country)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load countries: {str(e)}")
            self.combo_box.addItem("United States of America")
        
        layout.addWidget(self.combo_box)
        self.setLayout(layout)
        self.combo_box.currentTextChanged.connect(self.countryChanged.emit)

class SidePanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Box)
        self.setStyleSheet("background-color: #f0f0f0;")
        self.setMinimumSize(200, 400)
        
        self.label = QLabel("Additional Information")
        self.label.setAlignment(Qt.AlignCenter)
        
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        
    def update_data(self, period, country):
        self.label.setText(f"Country: {country}\nPeriod: {period.capitalize()}")

class BottomPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Box)
        self.setStyleSheet("background-color: #e0e0e0;")
        self.setMinimumHeight(150)
        
        self.label = QLabel("Summary Statistics")
        self.label.setAlignment(Qt.AlignCenter)
        
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        
    def update_data(self, period, country):
        self.label.setText(f"Showing {period} data for {country}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set light theme
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, Qt.white)
    palette.setColor(QPalette.WindowText, Qt.black)
    palette.setColor(QPalette.Base, Qt.white)
    palette.setColor(QPalette.Text, Qt.black)
    palette.setColor(QPalette.Button, Qt.lightGray)
    palette.setColor(QPalette.ButtonText, Qt.black)
    app.setPalette(palette)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

