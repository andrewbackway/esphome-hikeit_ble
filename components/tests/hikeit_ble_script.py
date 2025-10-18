#!/usr/bin/env python3
"""
HIKE IT BLE Communication Script
Handles complete BLE communication with HIKE IT devices
"""

import asyncio
import sys
from bleak import BleakScanner, BleakClient
from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

# BLE UUIDs
SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

# Protocol constants
HEADER = "AA55"
SCAN_PREFIX = "HIKE"


class SpeedModel(Enum):
    """Speed model enumeration"""
    ECONOMY = (0, "Economy")
    NORMAL = (1, "Normal")
    CRUISE = (2, "Cruise")
    SPORT = (3, "Sport")
    HIKE_IT = (4, "Hike IT")
    AUTO = (5, "Auto")
    LAUNCH = (6, "Launch")
    ANIT_SLIP = (7, "Anti-Slip")
    VALET = (8, "Valet")
    SL = (9, "SL")

    def __init__(self, code, desc):
        self.code = code
        self.desc = desc


@dataclass
class ParsedMessage:
    """Parsed BLE message data"""
    raw: str
    count: int
    msg_type: int
    content: str
    device_id: str
    checksum: str
    speed_model: Optional[SpeedModel] = None
    step_economy: int = 0
    step_cruise: int = 0
    step_sport: int = 0
    step_hike: int = 0
    deep_cx: int = 0
    deep_sc: int = 0
    version: str = ""
    is_safe_model: bool = False
    notice: str = ""
    study_state: int = 0
    study_time: int = 0
    at_flag: int = 0
    support_sl: bool = True

    def __str__(self):
        result = f"Message Type {self.msg_type:02X} | Count: {self.count} | ID: {self.device_id}"
        if self.msg_type == 2:
            result += f"\n  Speed Model: {self.speed_model.desc if self.speed_model else 'Unknown'}"
            result += f"\n  Steps: Eco={self.step_economy}, Cruise={self.step_cruise}, Sport={self.step_sport}, Hike={self.step_hike}"
            result += f"\n  Deep: CX={self.deep_cx}, SC={self.deep_sc}"
            result += f"\n  Version: {self.version}, Locked: {self.is_safe_model}, AT: {self.at_flag}"
            if self.notice:
                result += f"\n  Notice: {self.notice}"
            result += f"\n  Study: State={self.study_state}, Time={self.study_time}"
        return result


class BLEProtocol:
    """BLE Protocol handler"""
    
    def __init__(self):
        self.sequence_counter = 0
        self.device_id = "00000000"
    
    def get_sequence(self) -> str:
        """Get current sequence and increment"""
        seq = f"{self.sequence_counter:02X}"
        self.sequence_counter = (self.sequence_counter + 1) % 256
        return seq
    
    def calculate_checksum(self, data: str) -> str:
        """Calculate checksum for message"""
        total = 0
        # Convert hex string to bytes and sum them
        for i in range(0, len(data), 2):
            total += int(data[i:i+2], 16)
        checksum = total & 0xFF
        return f"{checksum:02X}"
    
    def build_message(self, msg_type: str, content: str) -> str:
        """Build a complete message with header, sequence, checksum"""
        seq = self.get_sequence()
        body = seq + msg_type + content + self.device_id
        checksum = self.calculate_checksum(body)
        return HEADER + body + checksum
    
    def build_verify_connect(self) -> str:
        """Build verification connect command (Type 09, subtype 03)"""
        return self.build_message("09", "03000000000000000000")
    
    def build_verify_disconnect(self) -> str:
        """Build verification disconnect command (Type 09, subtype 04)"""
        return self.build_message("09", "04000000000000000000")
    
    def build_study_mode(self) -> str:
        """Build study mode command (Type 01)"""
        return self.build_message("01", "16000000000000000000")
    
    def build_screen_cmd(self) -> str:
        """Build screen command (Type 08)"""
        return self.build_message("08", "24000000000000000000")
    
    def build_model_cmd(self, model: SpeedModel, at_flag: int, current_content: str) -> str:
        """Build speed model command (Type 02)"""
        # Parse current content to preserve other settings
        content_bytes = bytes.fromhex(current_content)
        new_bytes = bytearray(content_bytes)
        
        if model.code <= 5:
            new_bytes[0] = model.code
            new_bytes[3] = 0
        elif model == SpeedModel.LAUNCH:
            new_bytes[3] = 1
        elif model == SpeedModel.ANIT_SLIP:
            new_bytes[3] = 2
        else:
            new_bytes[3] = 4
        
        new_bytes[3] = new_bytes[3] | (at_flag << 7)
        new_bytes[4] = 0
        new_bytes[5] = 0
        new_bytes[6] = 0
        
        return self.build_message("02", new_bytes.hex().upper())
    
    def build_step_cmd(self, step: int, model: SpeedModel, current_content: str) -> str:
        """Build step adjustment command (Type 02)"""
        content_bytes = bytes.fromhex(current_content)
        new_bytes = bytearray(content_bytes)
        
        step = max(0, step)
        
        if model == SpeedModel.ECONOMY:
            new_bytes[1] = (new_bytes[1] & 0xF0) | (step & 0x0F)
        elif model == SpeedModel.CRUISE:
            new_bytes[1] = (new_bytes[1] & 0x0F) | ((step << 4) & 0xF0)
        elif model == SpeedModel.SPORT:
            new_bytes[2] = (new_bytes[2] & 0xF0) | (step & 0x0F)
        elif model == SpeedModel.HIKE_IT:
            new_bytes[2] = (new_bytes[2] & 0x0F) | ((step << 4) & 0xF0)
        
        return self.build_message("02", new_bytes.hex().upper())
    
    def build_safe_mode_cmd(self, password: str, enable: bool) -> str:
        """Build safe mode lock/unlock command (Type 05/06)
        
        Args:
            password: 1-4 digit PIN (e.g., "123" or "1234")
            enable: True to lock (Type 05), False to unlock (Type 06)
        
        Returns:
            Complete hex command string
        
        Raises:
            ValueError: If password is not numeric
        """
        # Validate password
        if not password.isdigit():
            raise ValueError("Password must be numeric digits only")
        
        if len(password) > 4:
            raise ValueError("Password must be 1-4 digits")
        
        msg_type = "05" if enable else "06"
        
        # Pad to 4 digits (takes last 4 chars, matching Java behavior)
        pwd = ("0000" + password)[-4:]
        
        # Byte swap to little-endian (e.g., "0123" becomes "2301")
        pwd_swapped = pwd[2:4] + pwd[0:2]
        
        # Duplicate password and pad with zeros
        content = (pwd_swapped + pwd_swapped + "000000000000").upper()
        
        return self.build_message(msg_type, content)
    
    def parse_message(self, hex_data: str) -> Optional[ParsedMessage]:
        """Parse received BLE message"""
        if not hex_data.startswith(HEADER):
            return None
        
        if len(hex_data) != 38:
            return None
        
        try:
            data_bytes = bytes.fromhex(hex_data)
            
            count = data_bytes[2]
            msg_type = data_bytes[3]
            content = hex_data[8:28]
            device_id = hex_data[28:36]
            checksum = hex_data[36:38]
            
            parsed = ParsedMessage(
                raw=hex_data,
                count=count,
                msg_type=msg_type,
                content=content,
                device_id=device_id,
                checksum=checksum
            )
            
            # Parse Type 02 messages (status/model info)
            if msg_type == 2:
                self._parse_type02(parsed, data_bytes)
            
            return parsed
        
        except Exception as e:
            print(f"Error parsing message: {e}")
            return None
    
    def _parse_type02(self, parsed: ParsedMessage, data_bytes: bytes):
        """Parse Type 02 message details"""
        b1 = data_bytes[5]  # content byte 1
        b2 = data_bytes[6]  # content byte 2
        b3 = data_bytes[7]  # content byte 3
        
        b3_val = b3 & 0xFF
        parsed.at_flag = b3_val >> 7
        parsed.support_sl = ((b3_val >> 4) & 1) == 1
        
        # Determine speed model
        if (b3 & 0x07) == 0:
            model_byte = data_bytes[4]
            if model_byte == 0:
                parsed.speed_model = SpeedModel.ECONOMY
                parsed.step_economy = b1 & 0x0F
            elif model_byte == 1:
                parsed.speed_model = SpeedModel.NORMAL
            elif model_byte == 2:
                parsed.speed_model = SpeedModel.CRUISE
                parsed.step_cruise = ((b1 & 0xFF) >> 4) & 0x0F
            elif model_byte == 3:
                parsed.speed_model = SpeedModel.SPORT
                parsed.step_sport = b2 & 0x0F
            elif model_byte == 4:
                parsed.speed_model = SpeedModel.HIKE_IT
                parsed.step_hike = ((b2 & 0xFF) >> 4) & 0x0F
            elif model_byte == 5:
                parsed.speed_model = SpeedModel.AUTO
        elif (b3 & 0x01) == 1:
            parsed.speed_model = SpeedModel.LAUNCH
        elif ((b3_val >> 1) & 1) == 1:
            parsed.speed_model = SpeedModel.ANIT_SLIP
        elif ((b3_val >> 2) & 1) == 1:
            parsed.speed_model = SpeedModel.VALET
        elif ((b3_val >> 3) & 1) == 1:
            parsed.speed_model = SpeedModel.SL
        
        # Parse additional data
        parsed.deep_cx = data_bytes[8] & 0xFF
        parsed.deep_sc = data_bytes[9] & 0xFF
        
        b10 = data_bytes[10]
        study_high = b10 >> 4
        if study_high == 1:
            parsed.study_state = 1
            parsed.study_time = b10 & 0x0F
        elif study_high > 1:
            parsed.study_state = 0 if (b10 & 0x0F) == 0 else 3
        
        parsed.version = f"V{data_bytes[11] / 10.0:.1f}"
        parsed.is_safe_model = data_bytes[12] == 0
        
        b13 = data_bytes[13]
        if ((b13 >> 2) & 1) == 1:
            parsed.notice = "C1"
        elif ((b13 >> 3) & 1) == 1:
            parsed.notice = "C2"
        elif ((b13 >> 4) & 1) == 1:
            parsed.notice = "C3"


class HikeITBLE:
    """Main BLE communication handler"""
    
    def __init__(self):
        self.client: Optional[BleakClient] = None
        self.protocol = BLEProtocol()
        self.connected = False
        self.verified = False
        self.last_message: Optional[ParsedMessage] = None
    
    async def scan_all_devices(self, duration: int = 10) -> List[Tuple[str, str]]:
        """Scan for all BLE devices"""
        print(f"\n🔍 Scanning for ALL BLE devices for {duration} seconds...")
        devices = await BleakScanner.discover(timeout=duration)
        
        results = []
        for device in devices:
            name = device.name or "Unknown"
            results.append((name, device.address))
        
        return sorted(results, key=lambda x: x[0])
    
    async def scan_hike_devices(self, duration: int = 10) -> List[Tuple[str, str]]:
        """Scan for HIKE IT devices only"""
        print(f"\n🔍 Scanning for HIKE IT devices for {duration} seconds...")
        devices = await BleakScanner.discover(timeout=duration)
        
        results = []
        for device in devices:
            name = device.name or ""
            if SCAN_PREFIX in name.upper():
                results.append((name, device.address))
        
        return sorted(results, key=lambda x: x[0])
    
    def _notification_handler(self, sender, data: bytearray):
        """Handle incoming notifications"""
        hex_data = data.hex().upper()
        print(f"\n📨 RAW RECEIVED: {hex_data}")
        
        # Handle both single (38 char) and double (76 char) messages
        if len(hex_data) == 38:
            self._process_message(hex_data)
        elif len(hex_data) == 76:
            # Split into two messages
            msg1 = hex_data[0:38]
            msg2 = hex_data[38:76]
            self._process_message(msg1)
            self._process_message(msg2)
        else:
            print(f"⚠️  Unexpected message length: {len(hex_data)}")
    
    def _process_message(self, hex_data: str):
        """Process a single message"""
        parsed = self.protocol.parse_message(hex_data)
        
        if parsed:
            print(f"📋 PARSED: {parsed}")
            
            # Extract device ID from first response
            if not self.verified and parsed.device_id != "00000000":
                self.protocol.device_id = parsed.device_id
                print(f"✅ Device ID captured: {parsed.device_id}")
            
            # Check for verification response (Type 09)
            if parsed.msg_type == 9:
                content_bytes = bytes.fromhex(parsed.content)
                if content_bytes[0] != 0:
                    self.verified = True
                    print("✅ Device VERIFIED!")
                else:
                    print("⚠️  Verification FAILED!")
            
            self.last_message = parsed
        else:
            print("⚠️  Failed to parse message")
    
    async def connect(self, mac_address: str) -> bool:
        """Connect to device and complete verification"""
        try:
            print(f"\n🔌 Connecting to {mac_address}...")
            self.client = BleakClient(mac_address)
            await self.client.connect()
            self.connected = True
            print("✅ Connected!")
            
            # Enable notifications
            print("📡 Enabling notifications...")
            await self.client.start_notify(NOTIFY_UUID, self._notification_handler)
            print("✅ Notifications enabled!")
            
            # Wait a moment for connection to stabilize
            await asyncio.sleep(0.5)
            
            # Send verification command
            print("🔐 Sending verification command...")
            verify_cmd = self.protocol.build_verify_connect()
            print(f"📤 SENDING: {verify_cmd}")
            await self.client.write_gatt_char(NOTIFY_UUID, bytes.fromhex(verify_cmd))
            
            # Wait for verification response
            await asyncio.sleep(2)
            
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from device"""
        if self.client and self.connected:
            try:
                # Send disconnect command if verified
                if self.verified:
                    print("📤 Sending disconnect command...")
                    disconnect_cmd = self.protocol.build_verify_disconnect()
                    await self.client.write_gatt_char(NOTIFY_UUID, bytes.fromhex(disconnect_cmd))
                    await asyncio.sleep(0.5)
                
                await self.client.disconnect()
                print("✅ Disconnected")
            except Exception as e:
                print(f"⚠️  Disconnect error: {e}")
            finally:
                self.connected = False
                self.verified = False
    
    async def send_command(self, command: str):
        """Send a command to the device"""
        if not self.connected or not self.client:
            print("❌ Not connected!")
            return
        
        try:
            print(f"📤 SENDING: {command}")
            await self.client.write_gatt_char(NOTIFY_UUID, bytes.fromhex(command))
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"❌ Send failed: {e}")
    
    async def interactive_commands(self):
        """Interactive command menu"""
        while self.connected:
            print("\n" + "="*60)
            print("COMMAND MENU")
            print("="*60)
            print("1. Send Study Mode Command")
            print("2. Send Screen Command")
            print("3. Change Speed Model")
            print("4. Adjust Step (if last message was Type 02)")
            print("5. Lock Device (Safe Mode ON) 🔒")
            print("6. Unlock Device (Safe Mode OFF) 🔓")
            print("7. Send Custom Hex Command")
            print("8. Show Last Received Message")
            print("0. Disconnect and Return")
            print("="*60)
            
            choice = input("\nEnter choice: ").strip()
            
            if choice == "1":
                cmd = self.protocol.build_study_mode()
                await self.send_command(cmd)
            
            elif choice == "2":
                cmd = self.protocol.build_screen_cmd()
                await self.send_command(cmd)
            
            elif choice == "3":
                print("\nSpeed Models:")
                for i, model in enumerate(SpeedModel):
                    print(f"{i}. {model.desc}")
                model_choice = input("Select model: ").strip()
                try:
                    model = list(SpeedModel)[int(model_choice)]
                    at_flag = input("AT flag (0 or 1): ").strip()
                    if self.last_message and self.last_message.msg_type == 2:
                        cmd = self.protocol.build_model_cmd(model, int(at_flag), self.last_message.content)
                        await self.send_command(cmd)
                    else:
                        print("⚠️  Need a Type 02 message first to preserve settings")
                except (ValueError, IndexError):
                    print("❌ Invalid selection")
            
            elif choice == "4":
                if self.last_message and self.last_message.msg_type == 2 and self.last_message.speed_model:
                    step = input(f"Enter step value for {self.last_message.speed_model.desc}: ").strip()
                    try:
                        cmd = self.protocol.build_step_cmd(int(step), self.last_message.speed_model, self.last_message.content)
                        await self.send_command(cmd)
                    except ValueError:
                        print("❌ Invalid step value")
                else:
                    print("⚠️  Need a Type 02 message with speed model first")
            
            elif choice == "5":
                password = input("Enter PIN (1-4 digits, e.g., '123'): ").strip()
                try:
                    cmd = self.protocol.build_safe_mode_cmd(password, enable=True)
                    print(f"🔒 Locking device with PIN: {password}")
                    await self.send_command(cmd)
                except ValueError as e:
                    print(f"❌ {e}")
            
            elif choice == "6":
                password = input("Enter PIN (1-4 digits, e.g., '123'): ").strip()
                try:
                    cmd = self.protocol.build_safe_mode_cmd(password, enable=False)
                    print(f"🔓 Unlocking device with PIN: {password}")
                    await self.send_command(cmd)
                except ValueError as e:
                    print(f"❌ {e}")
            
            elif choice == "7":
                hex_cmd = input("Enter hex command (without AA55 header and checksum): ").strip().upper()
                if len(hex_cmd) == 32:  # 1 seq + 1 type + 10 content + 4 id = 16 bytes = 32 chars
                    checksum = self.protocol.calculate_checksum(hex_cmd)
                    full_cmd = HEADER + hex_cmd + checksum
                    await self.send_command(full_cmd)
                else:
                    print(f"❌ Command must be 32 hex characters (got {len(hex_cmd)})")
            
            elif choice == "8":
                if self.last_message:
                    print(f"\n{self.last_message}")
                    if self.last_message.msg_type == 2:
                        safe_status = "🔒 LOCKED" if self.last_message.is_safe_model else "🔓 UNLOCKED"
                        print(f"\nSafe Mode Status: {safe_status}")
                else:
                    print("⚠️  No messages received yet")
            
            elif choice == "0":
                break
            
            else:
                print("❌ Invalid choice")
            
            # Small delay to show messages
            await asyncio.sleep(0.5)


async def main_menu():
    """Main application menu"""
    ble = HikeITBLE()
    
    while True:
        print("\n" + "="*60)
        print("HIKE IT BLE COMMUNICATION TOOL")
        print("="*60)
        print("1. Scan for ALL BLE devices")
        print("2. Scan for HIKE IT devices")
        print("3. Connect to device")
        print("0. Exit")
        print("="*60)
        
        choice = input("\nEnter choice: ").strip()
        
        if choice == "1":
            devices = await ble.scan_all_devices(10)
            if devices:
                print(f"\n✅ Found {len(devices)} devices:")
                for i, (name, mac) in enumerate(devices, 1):
                    print(f"{i}. {name:30s} | {mac}")
            else:
                print("⚠️  No devices found")
        
        elif choice == "2":
            devices = await ble.scan_hike_devices(10)
            if devices:
                print(f"\n✅ Found {len(devices)} HIKE IT devices:")
                for i, (name, mac) in enumerate(devices, 1):
                    print(f"{i}. {name:30s} | {mac}")
            else:
                print("⚠️  No HIKE IT devices found")
        
        elif choice == "3":
            mac = input("\nEnter MAC address: ").strip()
            if await ble.connect(mac):
                print("\n✅ Connection established!")
                print("   Listening for messages...")
                print("   Use command menu to interact\n")
                
                # Enter interactive command mode
                await ble.interactive_commands()
                await ble.disconnect()
            else:
                print("❌ Connection failed")
        
        elif choice == "0":
            print("\n👋 Goodbye!")
            if ble.connected:
                await ble.disconnect()
            break
        
        else:
            print("❌ Invalid choice")


if __name__ == "__main__":
    try:
        asyncio.run(main_menu())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)