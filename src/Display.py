import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
                            QPushButton, QLCDNumber)
from PyQt5.QtCore import QTimer, Qt, QObject, pyqtSignal
from PyQt5.QtGui import QFont, QColor

class VehicleDashboard(QMainWindow):
    def __init__(self, can_connected=False):
        super().__init__()
        self.can_connected = can_connected
        
        # Window setup
        self.setWindowTitle("Live Vehicle Diagnostics")
        self.setGeometry(100, 100, 1024, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Left panel - Live data gauges
        self.setup_gauges(main_layout)
        
        # Right panel - DTC display
        self.setup_dtc_panel(main_layout)
        
        # Initial update
        self.update_connection_status()

    def setup_gauges(self, parent_layout):
        """Create live data gauges"""
        gauge_panel = QWidget()
        layout = QVBoxLayout()
        
        # Connection status
        self.connection_status = QLabel()
        self.connection_status.setAlignment(Qt.AlignCenter)
        self.connection_status.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(self.connection_status)
        
        # RPM Gauge
        rpm_box = QWidget()
        rpm_layout = QHBoxLayout()
        rpm_layout.addWidget(QLabel("RPM:"))
        self.rpm_display = QLCDNumber()
        self.rpm_display.setDigitCount(5)
        rpm_layout.addWidget(self.rpm_display)
        rpm_box.setLayout(rpm_layout)
        
        # Speed Gauge
        speed_box = QWidget()
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        self.speed_display = QLCDNumber()
        self.speed_display.setDigitCount(3)
        speed_layout.addWidget(self.speed_display)
        speed_box.setLayout(speed_layout)
        
        # Other parameters
        self.temp_display = self.create_parameter_display("Coolant Temp", "°C")
        self.fuel_display = self.create_parameter_display("Fuel Level", "%")
        
        layout.addWidget(rpm_box)
        layout.addWidget(speed_box)
        layout.addWidget(self.temp_display)
        layout.addWidget(self.fuel_display)
        layout.addStretch()
        
        gauge_panel.setLayout(layout)
        parent_layout.addWidget(gauge_panel)

    def create_parameter_display(self, name, unit):
        """Helper for creating parameter displays"""
        box = QWidget()
        layout = QHBoxLayout()
        layout.addWidget(QLabel(f"{name}:"))
        display = QLCDNumber()
        display.setDigitCount(6)
        layout.addWidget(display)
        layout.addWidget(QLabel(unit))
        box.setLayout(layout)
        return box

    def update_connection_status(self):
        """Update UI based on connection state"""
        if self.can_connected:
            self.connection_status.setText("CONNECTED TO CAN BUS")
            self.connection_status.setStyleSheet("color: green;")
        else:
            self.show_service_unavailable()

    def show_service_unavailable(self):
        """Display service unavailable state"""
        self.connection_status.setText("SERVICE NOT AVAILABLE")
        self.connection_status.setStyleSheet("color: orange;")
        
        self.rpm_display.display("-----")
        self.speed_display.display("-----")
        
        for display in [self.temp_display, self.fuel_display]:
            lcd = display.findChild(QLCDNumber)
            lcd.display("-----")
        
        self.update_dtc_connection_status()

    def update_data(self, can_data):
        """Update displays with data"""
        if not self.can_connected:
            self.show_service_unavailable()
            return
            
        try:
            self.rpm_display.display(can_data.get('rpm', 0))
            self.speed_display.display(can_data.get('speed', 0))
            
            temp_lcd = self.temp_display.findChild(QLCDNumber)
            temp_lcd.display(can_data.get('temp', 0))
            
            fuel_lcd = self.fuel_display.findChild(QLCDNumber)
            fuel_lcd.display(can_data.get('fuel', 0))
            
            if 'dtcs' in can_data:
                self.update_dtc_table(can_data['dtcs'])
                
        except Exception as e:
            print(f"Data update error: {e}")
            self.can_connected = False
            self.show_service_unavailable()

    def setup_dtc_panel(self, parent_layout):
        """Create DTC display panel"""
        dtc_panel = QWidget()
        layout = QVBoxLayout()
        
        title = QLabel("Diagnostic Trouble Codes")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        self.dtc_connection_msg = QLabel()
        self.dtc_connection_msg.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.dtc_connection_msg)
        
        self.dtc_table = QTableWidget()
        self.dtc_table.setColumnCount(3)
        self.dtc_table.setHorizontalHeaderLabels(["Code", "Description", "Status"])
        layout.addWidget(self.dtc_table)
        
        btn_layout = QHBoxLayout()
        self.clear_btn = QPushButton("Clear DTCs")
        self.refresh_btn = QPushButton("Refresh")
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(self.refresh_btn)
        layout.addLayout(btn_layout)
        
        dtc_panel.setLayout(layout)
        parent_layout.addWidget(dtc_panel)
        
        self.update_dtc_connection_status()

    def update_dtc_connection_status(self):
        """Update DTC panel status"""
        if self.can_connected:
            self.dtc_connection_msg.setText("Connected to diagnostic system")
            self.dtc_connection_msg.setStyleSheet("color: green;")
            self.clear_btn.setEnabled(True)
            self.refresh_btn.setEnabled(True)
        else:
            self.dtc_connection_msg.setText("Service Not Available")
            self.dtc_connection_msg.setStyleSheet("color: orange;")
            self.clear_btn.setEnabled(False)
            self.refresh_btn.setEnabled(False)
            self.dtc_table.setRowCount(1)
            self.dtc_table.setItem(0, 0, QTableWidgetItem("SERVICE"))
            self.dtc_table.setItem(0, 1, QTableWidgetItem("Not Available"))
            self.dtc_table.setItem(0, 2, QTableWidgetItem("Offline"))

    def update_dtc_table(self, dtcs):
        """Update DTC table with codes"""
        self.dtc_table.setRowCount(len(dtcs))
        for row, dtc in enumerate(dtcs):
            self.dtc_table.setItem(row, 0, QTableWidgetItem(dtc["code"]))
            self.dtc_table.setItem(row, 1, QTableWidgetItem(dtc["desc"]))
            status_item = QTableWidgetItem(dtc.get("status", "Active"))
            self.dtc_table.setItem(row, 2, status_item)

class Display(QObject):
    refresh_requested = pyqtSignal()
    clear_dtcs_requested = pyqtSignal()
    
    def __init__(self, can_connected=False):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.dashboard = VehicleDashboard(can_connected)
        
        # Connect signals
        self.dashboard.refresh_btn.clicked.connect(self.refresh_requested.emit)
        self.dashboard.clear_btn.clicked.connect(self.clear_dtcs_requested.emit)
        
        # Set dark theme
        self.set_dark_theme()
    
    def set_dark_theme(self):
        """Apply dark theme"""
        self.app.setStyle("Fusion")
        palette = self.app.palette()
        palette.setColor(palette.Window, QColor(53, 53, 53))
        palette.setColor(palette.WindowText, Qt.white)
        self.app.setPalette(palette)
    
    def update_data(self, can_data):
        """Update dashboard with data"""
        self.dashboard.can_connected = can_data.get('connected', False)
        self.dashboard.update_data(can_data)
    
    def run(self):
        """Start the application"""
        self.dashboard.show()
        sys.exit(self.app.exec_())

if __name__ == "__main__":
    display = Display()

    display.run()