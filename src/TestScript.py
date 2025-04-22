import can
try:
    bus = can.interface.Bus(bustype='vector', channel=0)
    print("Successfully connected to channel 0")
    bus.shutdown()
except Exception as e:
    print(f"Connection failed: {str(e)}")