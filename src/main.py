from CanInterface import CanInterface
from Display import VehicleDashboard
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import sys

class MainApp:
    def __init__(self):
        # Initialize CAN interface
        self.can_interface = CanInterface()
        
        # Create dashboard with connection status
        self.dashboard = VehicleDashboard(self.can_interface.is_connected())
        
        # Setup periodic data refresh
        self.timer = QTimer()
        self.timer.timeout.connect(self._refresh_data)
        self.timer.start(1000)  # Refresh every second
        
        # Connect signals
        self.dashboard.refresh_requested.connect(self._refresh_data)
        self.dashboard.clear_dtcs_requested.connect(self._clear_dtcs)
        
        # Initial data refresh
        self._refresh_data()

    def _refresh_data(self):
        """Handle data refresh"""
        can_data = self.can_interface.read_data()
        if can_data is None:
            can_data = {'connected': False}
        self.dashboard.update_data(can_data)

    def _clear_dtcs(self):
        """Handle clear DTCs request"""
        if self.can_interface.clear_dtcs():
            self._refresh_data()  # Refresh to show cleared DTCs
    
    def run(self):
        """Run the application"""
        try:
            self.dashboard.show()
            QApplication.instance().exec_()
        finally:
            self.can_interface.shutdown()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_app = MainApp()
    sys.exit(main_app.run())