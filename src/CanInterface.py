import can
from can import Message
import time
from collections import deque

class IsoTpProtocol:
    """
    Handles ISO 15765-3 Transport Protocol for single or multi-frame CAN messages
    Manages segmentation and reassembly of messages longer than 8 bytes
    """
    def __init__(self):
        # Buffer for reassembling multi-frame messages
        self.receive_buffer = {}  # Key: arbitration ID, Value: message data
        # Timeout for incomplete messages (in seconds)
        self.timeout = 1.0
        # Track when we last received parts of messages
        self.last_received = {}

    def _get_current_time(self):
        """Helper to get current time for timeout calculations"""
        return time.time()

    def _cleanup_old_messages(self):
        """Remove incomplete messages that have timed out"""
        current_time = self._get_current_time()
        # Find messages that haven't been updated within timeout period
        to_delete = [arb_id for arb_id, timestamp in self.last_received.items() 
                     if current_time - timestamp > self.timeout]
        # Clean up buffers
        for arb_id in to_delete:
            del self.receive_buffer[arb_id]
            del self.last_received[arb_id]

    def process_received_frame(self, msg):
        """
        Process incoming CAN frame according to ISO-TP
        Returns: tuple (arbitration_id, complete_data) if message is complete
                 None if message is incomplete or invalid
        """
        arb_id = msg.arbitration_id
        data = msg.data
        first_byte = data[0]
        
        # Clean up any old incomplete messages first
        self._cleanup_old_messages()
        
        # --- Single Frame (SF) ---
        # First nibble is 0, length in lower nibble
        if (first_byte >> 4) == 0:
            length = first_byte & 0x0F
            return arb_id, bytes(data[1:1+length])
        
        # --- First Frame (FF) ---
        # First nibble is 1, length in next bytes
        elif (first_byte >> 4) == 1:
            # Calculate total message length
            length = ((first_byte & 0x0F) << 8) + data[1]
            # Initialize receive buffer for this message
            self.receive_buffer[arb_id] = {
                'data': bytearray(data[2:]),  # Store the data after length bytes
                'expected_length': length,     # Total expected bytes
                'remaining': length - (len(data) - 2),  # Bytes still to receive
                'last_seq': 0                 # Last sequence number received
            }
            self.last_received[arb_id] = self._get_current_time()
            return None
        
        # --- Consecutive Frame (CF) ---
        # First nibble is 2, sequence number in lower nibble
        elif (first_byte >> 4) == 2:
            # Check if we have a matching first frame
            if arb_id not in self.receive_buffer:
                return None  # No matching first frame
            
            seq_num = first_byte & 0x0F
            expected_seq = (self.receive_buffer[arb_id]['last_seq'] + 1) % 16
            
            # Check for sequence number errors
            if seq_num != expected_seq:
                # Sequence error, discard the entire message
                del self.receive_buffer[arb_id]
                del self.last_received[arb_id]
                return None
            
            # Append new data to buffer
            self.receive_buffer[arb_id]['data'].extend(data[1:])
            self.receive_buffer[arb_id]['remaining'] -= (len(data) - 1)
            self.receive_buffer[arb_id]['last_seq'] = seq_num
            self.last_received[arb_id] = self._get_current_time()
            
            # Check if message is complete
            if self.receive_buffer[arb_id]['remaining'] <= 0:
                # Return complete message data
                complete_data = bytes(self.receive_buffer[arb_id]['data'])
                del self.receive_buffer[arb_id]
                del self.last_received[arb_id]
                return arb_id, complete_data
            
            return None
        
        return None

    def create_send_frames(self, arb_id, data):
        """
        Create CAN frames for sending data using ISO-TP protocol
        Returns: list of can.Message objects ready to send
        """
        frames = []
        
        # --- Single Frame Case ---
        if len(data) <= 7:  # 7 bytes payload (1 byte for length)
            # First byte is length, followed by data
            frame_data = [len(data)] + list(data)
            # Pad with 0xCC
            frame_data += [0xCC] * (8 - len(frame_data))
            frames.append(Message(
                arbitration_id=arb_id,
                data=frame_data,
                is_extended_id=False
            ))
        
        # --- Multi-Frame Case ---
        else:
            # First frame contains total length
            length = len(data)
            # First byte: 0x10 + upper nibble of length
            # Second byte: lower byte of length
            # Then first 6 bytes of data
            frame_data = [0x10 | ((length >> 8) & 0x0F), length & 0xFF] + list(data[:6])
            frames.append(Message(
                arbitration_id=arb_id,
                data=frame_data,
                is_extended_id=False
            ))
            
            # Split remaining data into consecutive frames
            remaining_data = data[6:]
            seq_num = 1  # Sequence numbers start at 1
            while remaining_data:
                # Each consecutive frame can carry 7 bytes
                chunk = remaining_data[:7]
                # First byte: 0x20 + sequence number
                frame_data = [0x20 | (seq_num & 0x0F)] + list(chunk)
            
                frame_data += [0xCC] * (8 - len(frame_data))
                frames.append(Message(
                    arbitration_id=arb_id,
                    data=frame_data,
                    is_extended_id=False
                ))
                remaining_data = remaining_data[7:]
                seq_num = (seq_num + 1) % 16  # Sequence numbers wrap at 15
        
        return frames


class CanInterface:
    """CAN Bus Interface"""
    # DTC descriptions dictionary
    DTC_DESCRIPTIONS = {
        'P0100': 'Mass or Volume Air Flow Circuit Malfunction',
        'P0101': 'Mass or Volume Air Flow Circuit Range/Performance Problem',
        'P0102': 'Mass or Volume Air Flow Circuit Low Input',
        'P0103': 'Mass or Volume Air Flow Circuit High Input',
        'P0120': 'Throttle/Pedal Position Sensor/Switch A Circuit Malfunction',
        'P0121': 'Throttle/Pedal Position Sensor/Switch A Circuit Range/Performance Problem',
        'P0122': 'Throttle/Pedal Position Sensor/Switch A Circuit Low Input',
        'P0123': 'Throttle/Pedal Position Sensor/Switch A Circuit High Input',
    }

    def __init__(self):
        self.bus = None
        self.connected = False
        self.isotp = IsoTpProtocol()
        self.pending_requests = {}
        self.default_timeout = 2.0
        self.active_dtcs = []
        
        # Connection attempt order: Physical CAN -> Virtual CAN in CANoe -> Python virtual
        connection_attempts = [
            {"type": "physical", "interface": "vector", "channel": 0, "bitrate": 500000},
            {"type": "virtual", "interface": "vector", "channel": 0, "bitrate": 500000},
            {"type": "fallback", "interface": "virtual", "channel": 1, "bitrate": 500000}
        ]
        
        for attempt in connection_attempts:
            try:
                print(f"Attempting {attempt['type']} connection...")
                self.bus = can.Bus(
                    interface=attempt['interface'],
                    channel=attempt['channel'],
                    bitrate=attempt['bitrate'],
                    receive_own_messages=True
                )
                self.connected = True
                print(f"Successfully connected to {attempt['type']} CAN interface")
                break
            except Exception as e:
                print(f"Failed {attempt['type']} connection: {str(e)}")
                continue
        
        if not self.connected:
            print("Warning: Could not connect to any CAN interface")

    def is_connected(self):
        return self.connected
    
    def send_isotp_message(self, arb_id, data, response_arb_id=None, timeout=None):
        if timeout is None:
            timeout = self.default_timeout
        
        frames = self.isotp.create_send_frames(arb_id, data)
        
        for frame in frames:
            try:
                self.bus.send(frame)
                time.sleep(0.01)
            except Exception as e:
                print(f"Error sending CAN frame: {e}")
                return None
        
        if response_arb_id is not None:
            return self._wait_for_isotp_response(response_arb_id, timeout)
        return None
    
    def _wait_for_isotp_response(self, arb_id, timeout):
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            msg = self.bus.recv(timeout=0.1)
            if msg:
                result = self.isotp.process_received_frame(msg)
                if result and result[0] == arb_id:
                    return result[1]
        
        return None
    
    def read_data(self):
        if not self.connected:
            return None
            
        try:
            msg = self.bus.recv(timeout=0.1)
            if msg:
                isotp_result = self.isotp.process_received_frame(msg)
                if isotp_result:
                    arb_id, data = isotp_result
                    print(f"Received ISO-TP message from {hex(arb_id)}: {data.hex()}")
                    return {
                        'isotp': True,
                        'arb_id': arb_id,
                        'data': data.hex(),
                        'raw_data': data
                    }
                
                return {
                    'connected': True,
                    'isotp': False,
                    'rpm': (msg.data[0] << 8) + msg.data[1] if len(msg.data) >= 2 else 0,
                    'speed': msg.data[2] if len(msg.data) >= 3 else 0,
                    'temp': msg.data[3] if len(msg.data) >= 4 else 0,
                    'fuel': msg.data[4] if len(msg.data) >= 5 else 0,
                    'dtcs': self.read_dtcs()  # Changed from _read_dtcs to read_dtcs
                }
            return None
        except Exception as e:
            print(f"Error reading CAN data: {e}")
            self.connected = False
            return None
    
    def _convert_raw_dtc(self, dtc_raw):
        """Convert raw DTC value to string code (e.g., P0123)"""
        # First two bits represent the letter (P, C, B, or U)
        letter_code = (dtc_raw >> 14) & 0x03
        letters = ['P', 'C', 'B', 'U']
        letter = letters[letter_code]
        
        # Next 6 bits represent the first digit
        digit1 = (dtc_raw >> 12) & 0x03
        
        # Following 4 bits represent the second digit
        digit2 = (dtc_raw >> 8) & 0x0F
        
        # Last 8 bits represent the third and fourth digits
        digit3 = (dtc_raw >> 4) & 0x0F
        digit4 = dtc_raw & 0x0F
        
        return f"{letter}{digit1}{digit2}{digit3}{digit4}"
    
    def read_dtcs(self):
        """Read Diagnostic Trouble Codes with descriptions"""
        if not self.connected:
            return [{'code': dtc, 'description': self.DTC_DESCRIPTIONS.get(dtc, 'Unknown')} 
                    for dtc in self.active_dtcs]
        
        try:    
            # Send Mode 03 request to read stored DTCs
            request = bytes([0x03])
            response = self.send_isotp_message(0x7E0, request, 0x7E8)

            if response:
                # Parse DTCs from response
                # Response format: [0x43, DTC1-H, DTC1-L, DTC2-H, DTC2-L, ...]
                if response[0] == 0x43:
                    dtcs = []
                    for i in range(1, len(response), 2):
                        if i + 1 < len(response):
                            dtc_raw = (response[i] << 8) | response[i + 1]
                            dtc_code = self._convert_raw_dtc(dtc_raw)
                            if dtc_code:
                                dtcs.append(dtc_code)
                    self.active_dtcs = dtcs

            return [{'code': dtc, 'description': self.DTC_DESCRIPTIONS.get(dtc, 'Unknown')} 
                    for dtc in self.active_dtcs]

        except Exception as e:
            print(f"Error reading DTCs: {e}")
            return []

    def clear_dtcs(self):
        """Clear Diagnostic Trouble Codes"""
        try:
            if self.connected:
                # Send Mode 04 request to clear DTCs
                request = bytes([0x04])
                response = self.send_isotp_message(0x7E0, request, 0x7E8)

                # Check if response is valid (0x44 indicates success)
                if response and response[0] == 0x44:
                    self.active_dtcs = []
                    return True
                else:
                    print("Failed to clear DTCs: Invalid or no response")
                    return False
            else:
                print("Not connected to ECU")
                return False
        except Exception as e:
            print(f"Error clearing DTCs: {e}")
            return False

    def simulate_new_dtc(self, dtc_code):
        """Simulate a new DTC appearing (for testing)"""
        if dtc_code not in self.active_dtcs:
            self.active_dtcs.append(dtc_code)
            print(f"Simulated new DTC: {dtc_code}")

    def simulate_dtc_clear(self, dtc_code):
        """Simulate clearing a specific DTC (for testing)"""
        if dtc_code in self.active_dtcs:
            self.active_dtcs.remove(dtc_code)
            print(f"Simulated DTC cleared: {dtc_code}")

    def shutdown(self):
        if self.bus:
            self.bus.shutdown()
            print("CAN interface shutdown")

if __name__ == "__main__":
    # Test the interface with DTC functionality
    can_if = CanInterface()
    try:
        print(f"Connected: {can_if.is_connected()}")
        
        # Display initial DTCs
        print("\nInitial DTCs:")
        for dtc in can_if._read_dtcs():
            print(f"- {dtc['code']}: {dtc['description']}")
        
        # Test ISO-TP communication
        print("\nTesting ISO-TP communication...")
        request_data = bytes([0x22, 0xF1, 0x90])  # UDS request for DID F190
        response = can_if.send_isotp_message(
            arb_id=0x7E0,
            data=request_data,
            response_arb_id=0x7E8,
            timeout=2.0
        )
        
        print(f"Received response: {response.hex() if response else 'None'}")
        
        # Simulate new DTC
        can_if.simulate_new_dtc('P0123')
        print("\nAfter adding P0123:")
        for dtc in can_if._read_dtcs():
            print(f"- {dtc['code']}: {dtc['description']}")
        
        # Clear DTCs
        print("\nClearing DTCs...")
        if can_if.clear_dtcs():
            print("DTCs cleared successfully")
        else:
            print("Failed to clear DTCs")
        
        # Continuous monitoring
        print("\nStarting continuous monitoring...")
        while True:
            data = can_if.read_data()
            if data:
                if 'dtcs' in data:
                    print(f"\nCurrent DTC count: {len(data['dtcs'])}")
                else:
                    print(f"\nReceived data: {data}")
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        can_if.shutdown()