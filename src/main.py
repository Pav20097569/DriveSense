from CanInterface import CanInterface
from Display import Display
import time

class MainApp:
    def __init__(self):
        self.can_interface = CanInterface()
        self.display = Display(self.can_interface.is_connected())
        
        # Connect signals
        self.display.refresh_requested.connect(self._refresh_data)
        self.display.clear_dtcs_requested.connect(self._clear_dtcs)
        
        # Initial data refresh
        self._refresh_data()
    
    def _refresh_data(self):
        """Handle refresh button click"""
        can_data = self.can_interface.read_data()
        if can_data is None:
            can_data = {'connected': False}
        self.display.update_data(can_data)
    
    def _clear_dtcs(self):
        """Handle clear DTCs button click"""
        if self.can_interface.clear_dtcs():
            self._refresh_data()  # Refresh to show cleared DTCs
    
    def run(self):
        """Run the application"""
        try:
            self.display.run()
        finally:
            self.can_interface.shutdown()

if __name__ == "__main__":
    app = MainApp()
    app.run()