"""
Direct Motor Service for LeLamp - bypasses lerobot library
Uses raw serial protocol for Feetech STS3215 servos
Supports position offsets so current position can be treated as 0°
"""
import os
import csv
import json
import time
import serial
import threading
import logging
from typing import Any, List

logger = logging.getLogger(__name__)


class DirectMotorsService:
    """Direct motor control bypassing lerobot library"""
    
    # STS3215 Protocol constants
    INST_WRITE = 0x03
    INST_READ = 0x02
    INST_SYNC_WRITE = 0x83
    ADDR_TORQUE_ENABLE = 40
    ADDR_GOAL_POSITION = 42
    ADDR_PRESENT_POSITION = 56
    
    MOTOR_NAMES = ['base_yaw', 'base_pitch', 'elbow_pitch', 'wrist_roll', 'wrist_pitch']
    
    def __init__(self, port: str, fps: int = 30, baudrate: int = 1000000):
        self.port = port
        self.fps = fps
        self.baudrate = baudrate
        self.ser = None
        self.running = False
        self._thread = None
        self._idle_thread = None
        self._is_animating = False
        self._event_queue = []
        self._lock = threading.Lock()
        self.recordings_dir = os.path.join(os.path.dirname(__file__), "..", "..", "recordings")
        
        # Position offsets: current_position = offset + animation_value
        # Loaded from motor_offsets.json or default to 2048 (center)
        self.offsets = {name: 2048 for name in self.MOTOR_NAMES}
        self._load_offsets()
    
    def _load_offsets(self):
        """Load position offsets from file"""
        offsets_file = os.path.join(os.path.dirname(__file__), "..", "..", "..", "motor_offsets.json")
        if os.path.exists(offsets_file):
            try:
                with open(offsets_file, 'r') as f:
                    loaded = json.load(f)
                for name in self.MOTOR_NAMES:
                    if name in loaded:
                        self.offsets[name] = loaded[name]
                logger.info(f"Loaded motor offsets from {offsets_file}")
            except Exception as e:
                logger.warning(f"Could not load offsets: {e}")
    
    def start(self):
        """Start the motor service"""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.5)
            time.sleep(0.3)
            
            # Enable torque on all motors
            for motor_id in range(1, 6):
                self._set_torque(motor_id, True)
            
            self.running = True
            self._thread = threading.Thread(target=self._process_queue, daemon=True)
            self._thread.start()
            
            # Start idle breathing animation thread
            self._idle_thread = threading.Thread(target=self._idle_loop, daemon=True)
            self._idle_thread.start()
            print("🌬️ Idle breathing animation started")
            
            logger.info(f"DirectMotorsService connected to {self.port}")
            logger.info(f"Using offsets: {self.offsets}")
        except Exception as e:
            logger.error(f"Failed to start motors: {e}")
            raise
    
    def _idle_loop(self):
        """Subtle idle movements to keep lamp feeling alive"""
        import math
        phase = 0
        while self.running:
            if not self._is_animating:
                # Gentle breathing/looking motion
                # Wrist pitch: up/down nod (+/- 10 degrees)
                nod = math.sin(phase) * 10
                offset = self.offsets.get('wrist_pitch', 2048)
                pos = int(offset + (nod / 180.0) * 2048)
                self._set_position(5, max(0, min(4095, pos)))
                
                # Base yaw: slow side-to-side sway (+/- 5 degrees)
                sway = math.sin(phase * 0.3) * 5
                offset = self.offsets.get('base_yaw', 2048)
                pos = int(offset + (sway / 180.0) * 2048)
                self._set_position(1, max(0, min(4095, pos)))
                
                phase += 0.15
            time.sleep(0.05)  # 20 FPS for smoother idle
    
    def stop(self):
        """Stop the motor service"""
        self.running = False
        if self.ser:
            # Disable torque
            for motor_id in range(1, 6):
                self._set_torque(motor_id, False)
            self.ser.close()
            self.ser = None
    
    def dispatch(self, event_type: str, payload: Any):
        """Queue an event for processing"""
        with self._lock:
            self._event_queue.append((event_type, payload))
    
    def _process_queue(self):
        """Process events from queue"""
        while self.running:
            event = None
            with self._lock:
                if self._event_queue:
                    event = self._event_queue.pop(0)
            
            if event:
                event_type, payload = event
                if event_type == "play":
                    self._handle_play(payload)
                elif event_type == "home":
                    self._handle_home()
            else:
                time.sleep(0.01)
    
    def _handle_home(self):
        """Return lamp to home/zero position (offsets)"""
        logger.info("Going to home position...")
        
        # Smooth transition to home over 30 frames
        steps = 30
        for step in range(steps + 1):
            for i, name in enumerate(self.MOTOR_NAMES, 1):
                offset = self.offsets.get(name, 2048)
                self._set_position(i, offset)
            time.sleep(1/30)
        
        logger.info("Home position reached")
    
    def _build_packet(self, motor_id: int, instruction: int, params: bytes = b'') -> bytes:
        """Build a Feetech protocol packet"""
        length = len(params) + 2
        packet = bytes([0xFF, 0xFF, motor_id, length, instruction]) + params
        checksum = (~(motor_id + length + instruction + sum(params))) & 0xFF
        return packet + bytes([checksum])
    
    def _set_torque(self, motor_id: int, enable: bool):
        """Enable/disable motor torque"""
        packet = self._build_packet(motor_id, self.INST_WRITE, 
                                    bytes([self.ADDR_TORQUE_ENABLE, 1 if enable else 0]))
        self.ser.write(packet)
        time.sleep(0.002)
        self.ser.read(20)
    
    def _set_position(self, motor_id: int, position: int):
        """Set goal position (0-4095, center is ~2048) - non-blocking"""
        pos = max(0, min(4095, int(position)))
        pos_low = pos & 0xFF
        pos_high = (pos >> 8) & 0xFF
        packet = self._build_packet(motor_id, self.INST_WRITE, 
                                    bytes([self.ADDR_GOAL_POSITION, pos_low, pos_high]))
        self.ser.write(packet)
        # Don't wait for response - just send and continue for speed
    
    def _degrees_to_position(self, degrees: float, motor_name: str = None) -> int:
        """Convert animation degrees to position, applying offset for current zero point"""
        # Animation value is relative: 0° in animation = offset position
        # offset is the position that we want to treat as 0°
        # degrees in animation range from roughly -90 to +90
        # 1 degree = 2048/180 ≈ 11.38 position units
        offset = self.offsets.get(motor_name, 2048) if motor_name else 2048
        position = int(offset + (degrees / 180.0) * 2048)
        return max(0, min(4095, position))
    
    def _handle_play(self, recording_name: str):
        """Play a recording by name - uses relative movement from first frame"""
        csv_filename = f"{recording_name}.csv"
        csv_path = os.path.join(self.recordings_dir, csv_filename)
        
        if not os.path.exists(csv_path):
            logger.error(f"Recording not found: {csv_path}")
            return
        
        self._is_animating = True  # Pause idle animation
        try:
            with open(csv_path, 'r') as csvfile:
                csv_reader = csv.DictReader(csvfile)
                actions = list(csv_reader)
            
            if not actions:
                logger.error(f"No actions in recording: {recording_name}")
                self._is_animating = False
                return
            
            # Get first frame values as base reference
            first_frame = actions[0]
            base_degrees = {}
            for name in self.MOTOR_NAMES:
                key = f"{name}.pos"
                if key in first_frame:
                    base_degrees[name] = float(first_frame[key])
            
            logger.info(f"Playing {len(actions)} frames from {recording_name}")
            
            for row in actions:
                t0 = time.perf_counter()
                
                # Apply relative movement: current_offset + (frame_value - first_frame_value)
                for i, name in enumerate(self.MOTOR_NAMES, 1):
                    key = f"{name}.pos"
                    if key in row and name in base_degrees:
                        current_degrees = float(row[key])
                        delta_degrees = current_degrees - base_degrees[name]
                        # Convert delta to position units and add to offset
                        offset = self.offsets.get(name, 2048)
                        position = int(offset + (delta_degrees / 180.0) * 2048)
                        position = max(0, min(4095, position))
                        self._set_position(i, position)
                
                # Maintain FPS timing
                elapsed = time.perf_counter() - t0
                sleep_time = 1.0 / self.fps - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            logger.info(f"Finished playing: {recording_name}")
            
            # Return to home/0th position after animation
            self._handle_home()
            
        except Exception as e:
            logger.error(f"Error playing {recording_name}: {e}")
        finally:
            self._is_animating = False  # Resume idle animation
    
    def get_available_recordings(self) -> List[str]:
        """Get list of available recording names"""
        if not os.path.exists(self.recordings_dir):
            return []
        
        recordings = []
        for filename in os.listdir(self.recordings_dir):
            if filename.endswith(".csv"):
                recordings.append(filename[:-4])
        
        return sorted(recordings)
