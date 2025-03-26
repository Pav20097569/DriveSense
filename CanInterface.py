import can

# Create a connection to the Vector CAN interface
bus = can.Bus(interface="vector", channel=0, bitrate=500000) 
# Create a CAN message
msg = can.Message(
    arbitration_id=0x123,  # CAN ID
    data=[0x11, 0x22, 0x33, 0x44],  # Message data (up to 8 bytes)
    is_extended_id=False  # False for standard ID, True for extended ID
)

# Send the message
bus.send(msg)
print("Message sent!")

# Receive a message
received_msg = bus.recv(timeout=1.0)  # Wait 1 second for a message
if received_msg:
    print(f"Received: {received_msg}")

# Close the bus connection
bus.shutdown()
