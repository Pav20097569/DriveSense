import can
try:
 
    bus = can.Bus(type = 'virtual' ,interface='vector', channel=0, bitrate=500000)
    print("Successfully connected to channel 0")
    bus.shutdown()
except Exception as e:
    print(f"Connection failed: {str(e)}")