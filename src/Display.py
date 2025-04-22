from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLCDNumber, QTableWidget, QTableWidgetItem, 
                            QPushButton)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt

class VehicleDashboard(QMainWindow):
    refresh_requested = pyqtSignal()
    clear_dtcs_requested = pyqtSignal()

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
        
        # Apply dark theme
        self.set_dark_theme()
        
        # Initial update
        self.update_connection_status()

    def setup_gauges(self, parent_layout):
        """Create live data gauges panel"""
        gauges_panel = QWidget()
        layout = QVBoxLayout()
        
        # Connection status
        self.connection_status = QLabel("CONNECTING...")
        self.connection_status.setFont(QFont("Arial", 14, QFont.Bold))
        self.connection_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.connection_status)
        
        # RPM Display
        rpm_container = QWidget()
        rpm_layout = QVBoxLayout()
        rpm_label = QLabel("Engine RPM")
        rpm_label.setFont(QFont("Arial", 10))
        rpm_label.setAlignment(Qt.AlignCenter)
        
        self.rpm_display = QLCDNumber()
        self.rpm_display.setDigitCount(5)
        self.rpm_display.setSegmentStyle(QLCDNumber.Filled)
        self.rpm_display.setStyleSheet("""
            QLCDNumber {
                background-color: black;
                color: green;
            }
            QLCDNumber[valueWarning="true"] {
                color: red;
            }
        """)
        
        rpm_layout.addWidget(rpm_label)
        rpm_layout.addWidget(self.rpm_display)
        rpm_container.setLayout(rpm_layout)
        layout.addWidget(rpm_container)
        
        # Speed Display
        speed_container = QWidget()
        speed_layout = QVBoxLayout()
        speed_label = QLabel("Speed (km/h)")
        speed_label.setFont(QFont("Arial", 10))
        speed_label.setAlignment(Qt.AlignCenter)
        
        self.speed_display = QLCDNumber()
        self.speed_display.setDigitCount(3)
        self.speed_display.setSegmentStyle(QLCDNumber.Filled)
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_display)
        speed_container.setLayout(speed_layout)
        layout.addWidget(speed_container)
        
        # Temperature and Fuel
        temp_fuel_container = QWidget()
        temp_fuel_layout = QHBoxLayout()
        
        # Temperature
        temp_widget = QWidget()
        temp_layout = QVBoxLayout()
        temp_label = QLabel("Coolant Temp (°C)")
        temp_label.setFont(QFont("Arial", 10))
        temp_label.setAlignment(Qt.AlignCenter)
        
        self.temp_display = QLCDNumber()
        self.temp_display.setDigitCount(3)
        self.temp_display.setSegmentStyle(QLCDNumber.Filled)
        self.temp_display.setStyleSheet("""
            QLCDNumber {
                background-color: black;
                color: blue;
            }
            QLCDNumber[valueWarning="true"] {
                color: orange;
            }
        """)
        
        temp_layout.addWidget(temp_label)
        temp_layout.addWidget(self.temp_display)
        temp_widget.setLayout(temp_layout)
        temp_fuel_layout.addWidget(temp_widget)
        
        # Fuel
        fuel_widget = QWidget()
        fuel_layout = QVBoxLayout()
        fuel_label = QLabel("Fuel Level (%)")
        fuel_label.setFont(QFont("Arial", 10))
        fuel_label.setAlignment(Qt.AlignCenter)
        
        self.fuel_display = QLCDNumber()
        self.fuel_display.setDigitCount(3)
        self.fuel_display.setSegmentStyle(QLCDNumber.Filled)
        self.fuel_display.setStyleSheet("""
            QLCDNumber {
                background-color: black;
                color: white;
            }
            QLCDNumber[valueWarning="true"] {
                color: red;
            }
        """)
        
        fuel_layout.addWidget(fuel_label)
        fuel_layout.addWidget(self.fuel_display)
        fuel_widget.setLayout(fuel_layout)
        temp_fuel_layout.addWidget(fuel_widget)
        
        temp_fuel_container.setLayout(temp_fuel_layout)
        layout.addWidget(temp_fuel_container)
        
        gauges_panel.setLayout(layout)
        parent_layout.addWidget(gauges_panel, stretch=1)

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
        self.dtc_table.horizontalHeader().setStretchLastSection(True)
        self.dtc_table.setColumnWidth(0, 100)
        self.dtc_table.setColumnWidth(1, 300)
        layout.addWidget(self.dtc_table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.clear_btn = QPushButton("Clear DTCs")
        self.refresh_btn = QPushButton("Refresh Data")
        
        self.clear_btn.clicked.connect(self.clear_dtcs_requested.emit)
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(self.refresh_btn)
        layout.addLayout(btn_layout)
        
        dtc_panel.setLayout(layout)
        parent_layout.addWidget(dtc_panel, stretch=2)
        
        self.update_dtc_connection_status()

    def set_dark_theme(self):
        """Apply dark theme to the application"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #333333;
            }
            QLabel {
                color: #FFFFFF;
            }
            QPushButton {
                background-color: #555555;
                color: white;
                border: 1px solid #666666;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
            QPushButton:pressed {
                background-color: #444444;
            }
            QTableWidget {
                background-color: #252525;
                color: #FFFFFF;
                gridline-color: #444444;
            }
            QHeaderView::section {
                background-color: #3A3A3A;
                color: white;
                padding: 4px;
                border: 1px solid #444444;
            }
        """)

    def update_connection_status(self):
        """Update UI based on connection state"""
        if self.can_connected:
            self.connection_status.setText("CONNECTED TO CAN BUS")
            self.connection_status.setStyleSheet("color: green;")
        else:
            self.show_service_unavailable()

    def update_dtc_connection_status(self):
        """Update DTC panel connection status"""
        if self.can_connected:
            self.dtc_connection_msg.setText("Connected to ECU")
            self.dtc_connection_msg.setStyleSheet("color: green;")
            self.clear_btn.setEnabled(True)
            self.refresh_btn.setEnabled(True)
        else:
            self.dtc_connection_msg.setText("ECU not connected")
            self.dtc_connection_msg.setStyleSheet("color: red;")
            self.clear_btn.setEnabled(False)
            self.refresh_btn.setEnabled(False)

    def show_service_unavailable(self):
        """Display service unavailable state"""
        self.connection_status.setText("SERVICE NOT AVAILABLE")
        self.connection_status.setStyleSheet("color: orange;")
        
        self.rpm_display.display("-----")
        self.speed_display.display("-----")
        self.temp_display.display("-----")
        self.fuel_display.display("-----")
        
        self.update_dtc_connection_status()

    def update_data(self, can_data):
        """Update the dashboard with CAN data"""
        self.can_connected = can_data.get('connected', False)
        
        if not self.can_connected:
            self.show_service_unavailable()
            return
            
        try:
            # Update RPM
            rpm = can_data.get('rpm', 0)
            self.rpm_display.display(rpm)
            self.rpm_display.setProperty("valueWarning", "true" if rpm > 3000 else "false")
            
            # Update Speed
            self.speed_display.display(can_data.get('speed', 0))
            
            # Update Temperature
            temp = can_data.get('temp', 0)
            self.temp_display.display(temp)
            self.temp_display.setProperty("valueWarning", "true" if temp > 100 else "false")
            
            # Update Fuel
            fuel = can_data.get('fuel', 0)
            self.fuel_display.display(fuel)
            self.fuel_display.setProperty("valueWarning", "true" if fuel < 15 else "false")
            
            # Update DTCs
            if 'dtcs' in can_data:
                self.update_dtc_table(can_data['dtcs'])
                
            # Update connection status
            self.update_connection_status()
                
        except Exception as e:
            print(f"Data update error: {e}")
            self.can_connected = False
            self.show_service_unavailable()

    def update_dtc_table(self, dtcs):
        """Update DTC table with codes and severity coloring"""
        self.dtc_table.setRowCount(len(dtcs))
        for row, dtc in enumerate(dtcs):
            self.dtc_table.setItem(row, 0, QTableWidgetItem(dtc["code"]))
            self.dtc_table.setItem(row, 1, QTableWidgetItem(dtc["description"]))
            
            status_item = QTableWidgetItem(dtc.get("status", "Active"))
            if dtc.get("severity") == "High":
                status_item.setBackground(QColor(255, 100, 100))  # Light red
            elif dtc.get("severity") == "Medium":
                status_item.setBackground(QColor(255, 200, 100))  # Orange
            self.dtc_table.setItem(row, 2, status_item)