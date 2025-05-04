#!/usr/bin/env python3
# UR3e Drawing Application

import os
import sys
import time
import logging
import math
import json
import xml.etree.ElementTree as ET
from Dashboard import Dashboard
from rtdeState import RtdeState
from interpreter.interpreter import InterpreterHelper
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ur3e_drawing.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Robot configuration
ROBOT_HOST = '192.168.0.2'  # Change this to your robot's IP
RTDE_CONFIG = 'rtdeState.xml'  # Path to your RTDE configuration file

# Drawing configuration
PEN_UP_Z = 0.07  # 7cm up from the paper surface
PEN_DOWN_Z = 0.0  # At the paper surface

# A4 paper dimensions in meters
A4_WIDTH = 0.210
A4_HEIGHT = 0.297

# Calibration file
CALIBRATION_FILE = 'calibration.json'

class UR3eDrawingApp:
    def __init__(self):
        self.dash = None
        self.rtde_state = None
        self.interpreter = None
        self.is_connected = False
        self.home_position = None
        self.surface_z = None
        
        # Try to load calibration data
        self.load_calibration()
    
    def connect_to_robot(self):
        """Establish connection to the robot and check status."""
        try:
            # Connect to Dashboard server
            self.dash = Dashboard(ROBOT_HOST)
            self.dash.connect()
            
            # Connect to RTDE
            self.rtde_state = RtdeState(ROBOT_HOST, RTDE_CONFIG)
            self.rtde_state.initialize()
            
            # Connect to Interpreter
            self.interpreter = InterpreterHelper(ROBOT_HOST)
            self.interpreter.connect()
            
            # Verify robot is in remote control mode
            remote_status = self.dash.sendAndReceive('is in remote control')
            if 'false' in remote_status:
                logger.error("Robot is not in remote control mode. Please switch to remote mode.")
                return False
            
            # Check robot mode
            powermode = self.dash.sendAndReceive('robotmode')
            logger.info(f"Robot mode: {powermode}")
            
            # Check safety status
            state = self.rtde_state.receive()
            if state:
                safety_status = state.safety_status
                logger.info(f"Safety status: {safety_status}")
                if safety_status != 1:  # 1 is normal safety status
                    logger.warning("Robot is not in normal safety state.")
            
            self.is_connected = True
            logger.info("Successfully connected to UR3e robot.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to robot: {str(e)}")
            self.disconnect_from_robot()
            return False
    
    def disconnect_from_robot(self):
        """Safely disconnect from the robot."""
        try:
            if self.dash:
                self.dash.close()
            
            if self.rtde_state:
                self.rtde_state.con.send_pause()
                self.rtde_state.con.disconnect()
                
            if self.interpreter:
                try:
                    self.interpreter.end_interpreter()
                except:
                    pass
                
            self.is_connected = False
            logger.info("Disconnected from robot.")
        except Exception as e:
            logger.error(f"Error during disconnection: {str(e)}")
    
    def save_calibration(self):
        """Save calibration data to file."""
        if self.surface_z is None or self.home_position is None:
            logger.error("No calibration data to save.")
            return False
        
        calibration_data = {
            "surface_z": self.surface_z,
            "home_position": self.home_position
        }
        
        try:
            with open(CALIBRATION_FILE, 'w') as f:
                json.dump(calibration_data, f, indent=4)
            logger.info("Calibration data saved successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to save calibration data: {str(e)}")
            return False
    
    def load_calibration(self):
        """Load calibration data from file."""
        if not os.path.exists(CALIBRATION_FILE):
            logger.info("No calibration file found. Calibration needed.")
            return False
        
        try:
            with open(CALIBRATION_FILE, 'r') as f:
                calibration_data = json.load(f)
            
            self.surface_z = calibration_data.get("surface_z")
            self.home_position = calibration_data.get("home_position")
            
            logger.info(f"Loaded calibration data: Surface Z = {self.surface_z}")
            logger.info(f"Home position = {self.format_position(self.home_position)}")
            return True
        except Exception as e:
            logger.error(f"Failed to load calibration data: {str(e)}")
            return False
    
    def format_position(self, position):
        """Format position for display."""
        if position is None:
            return "Not set"
        
        return f"[X: {position[0]:.4f}, Y: {position[1]:.4f}, Z: {position[2]:.4f}, Rx: {position[3]:.4f}, Ry: {position[4]:.4f}, Rz: {position[5]:.4f}]"
    
    def release_brakes(self):
        """Release the robot brakes."""
        if not self.is_connected:
            logger.error("Not connected to robot.")
            return False
            
        try:
            response = self.dash.sendAndReceive('brake release')
            logger.info(f"Brake release response: {response}")
            
            # Wait for brakes to fully release
            time.sleep(2)
            
            # Check robot mode to confirm brakes are released
            state = self.rtde_state.receive()
            robot_mode = state.robot_mode
            
            if robot_mode == 7:  # Running mode
                logger.info("Brakes released successfully.")
                return True
            else:
                logger.warning(f"Robot not in running mode after brake release. Current mode: {robot_mode}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to release brakes: {str(e)}")
            return False
    
    def move_joints(self, joint_positions):
        """Move the robot joints to specified positions using interpreter."""
        if not self.is_connected:
            logger.error("Not connected to robot.")
            return False
            
        try:
            # Format joint positions with proper precision
            joints_str = "[" + ", ".join([f"{j:.6f}" for j in joint_positions]) + "]"
            cmd = f"movej({joints_str})"
            cmd_id = self.interpreter.execute_command(cmd)
            
            # Wait for command to be executed
            while self.interpreter.get_last_executed_id() < cmd_id:
                time.sleep(0.1)
                
            return True
        except Exception as e:
            logger.error(f"Move joints command failed: {str(e)}")
            return False
    
    def move_tcp(self, pose):
        """Move the robot TCP to specified pose using interpreter."""
        if not self.is_connected:
            logger.error("Not connected to robot.")
            return False
            
        try:
            # Format pose with proper precision
            pose_str = "p[" + ", ".join([f"{p:.6f}" for p in pose]) + "]"
            cmd = f"movel({pose_str})"
            cmd_id = self.interpreter.execute_command(cmd)
            
            # Wait for command to be executed
            while self.interpreter.get_last_executed_id() < cmd_id:
                time.sleep(0.1)
                
            return True
        except Exception as e:
            logger.error(f"Move TCP command failed: {str(e)}")
            return False
    
    def get_current_position(self):
        """Get the current TCP position of the robot."""
        if not self.is_connected:
            logger.error("Not connected to robot.")
            return None
            
        try:
            state = self.rtde_state.receive()
            if state is None:
                logger.error("Could not get current position from robot.")
                return None
                
            return state.actual_TCP_pose
        except Exception as e:
            logger.error(f"Failed to get current position: {str(e)}")
            return None
    
    def get_current_joints(self):
        """Get the current joint positions of the robot."""
        if not self.is_connected:
            logger.error("Not connected to robot.")
            return None
            
        try:
            state = self.rtde_state.receive()
            if state is None:
                logger.error("Could not get current joint positions from robot.")
                return None
                
            return state.actual_q
        except Exception as e:
            logger.error(f"Failed to get current joint positions: {str(e)}")
            return None
    
    def calibrate_surface(self):
        """Calibrate the surface height for pen drawing."""
        if not self.is_connected:
            logger.error("Not connected to robot.")
            return False
            
        print("\nSurface Calibration")
        print("-------------------")
        print("Please manually move the robot so the pen tip is touching the paper surface.")
        print("Then press Enter to set this as the drawing surface height.")
        input("Press Enter when ready...")
        
        current_position = self.get_current_position()
        if current_position:
            self.surface_z = current_position[2]  # Z-coordinate
            logger.info(f"Surface height calibrated to Z = {self.surface_z}")
            
            # Also set this position (with pen raised) as home
            raised_position = current_position.copy()
            raised_position[2] = self.surface_z + PEN_UP_Z  # Raise pen
            self.home_position = raised_position
            
            # Save calibration data
            self.save_calibration()
            
            # Move pen up to the home position
            return self.move_tcp(self.home_position)
        return False
    
    def pen_up(self):
        """Lift the pen up from the paper."""
        if not self.is_connected or self.surface_z is None:
            logger.error("Not connected or surface not calibrated.")
            return False
            
        current_position = self.get_current_position()
        if current_position:
            # Keep current XY position, but raise Z
            new_position = current_position.copy()
            new_position[2] = self.surface_z + PEN_UP_Z
            return self.move_tcp(new_position)
        return False
    
    def pen_down(self):
        """Lower the pen to the paper with safety check."""
        if not self.is_connected or self.surface_z is None:
            logger.error("Not connected or surface not calibrated.")
            return False
            
        current_position = self.get_current_position()
        if current_position:
            # Keep current XY position, but lower Z to the surface
            new_position = current_position.copy()
            new_position[2] = self.surface_z + PEN_DOWN_Z
            
            # Approach slowly in small increments for safety
            steps = 10
            current_z = current_position[2]
            target_z = new_position[2]
            
            for i in range(1, steps + 1):
                intermediate_z = current_z - (current_z - target_z) * (i / steps)
                intermediate_position = new_position.copy()
                intermediate_position[2] = intermediate_z
                
                if not self.move_tcp(intermediate_position):
                    return False
                
            logger.info("Pen down completed successfully.")
            return True
        return False
    
    def move_to_home(self):
        """Move the robot to the home position."""
        if not self.home_position:
            logger.error("Home position not set.")
            return False
            
        return self.move_tcp(self.home_position)
    
    def test_mobility(self):
        """Test the robot's mobility through simple patterns."""
        if not self.is_connected:
            logger.error("Not connected to robot.")
            return False
            
        try:
            logger.info("Starting mobility test...")
            
            # Get current position as starting point
            start_position = self.get_current_position()
            if not start_position:
                return False
                
            # Ensure pen is up
            current_position = start_position.copy()
            if self.surface_z:
                current_position[2] = self.surface_z + PEN_UP_Z
                if not self.move_tcp(current_position):
                    return False
            
            # Test 1: Move up and down (Z-axis)
            logger.info("Testing Z-axis movement...")
            test_position = current_position.copy()
            test_position[2] -= 0.02  # Move down 2cm (but still up from surface)
            if not self.move_tcp(test_position):
                return False
                
            test_position[2] += 0.04  # Move up 4cm
            if not self.move_tcp(test_position):
                return False
                
            test_position[2] -= 0.02  # Back to starting height
            if not self.move_tcp(test_position):
                return False
                
            # Test 2: Move left and right (X-axis)
            logger.info("Testing X-axis movement...")
            test_position = current_position.copy()
            test_position[0] += 0.03  # Move right 3cm
            if not self.move_tcp(test_position):
                return False
                
            test_position[0] -= 0.06  # Move left 6cm
            if not self.move_tcp(test_position):
                return False
                
            test_position[0] += 0.03  # Back to center
            if not self.move_tcp(test_position):
                return False
                
            # Test 3: Move forward and backward (Y-axis)
            logger.info("Testing Y-axis movement...")
            test_position = current_position.copy()
            test_position[1] += 0.03  # Move forward 3cm
            if not self.move_tcp(test_position):
                return False
                
            test_position[1] -= 0.06  # Move backward 6cm
            if not self.move_tcp(test_position):
                return False
                
            test_position[1] += 0.03  # Back to center
            if not self.move_tcp(test_position):
                return False
                
            # Test 4: Circle movement
            logger.info("Testing circular movement...")
            radius = 0.03  # 3cm radius
            center_x, center_y = current_position[0], current_position[1]
            
            for angle in range(0, 360, 30):  # 30-degree steps
                rad = math.radians(angle)
                test_position = current_position.copy()
                test_position[0] = center_x + radius * math.cos(rad)
                test_position[1] = center_y + radius * math.sin(rad)
                if not self.move_tcp(test_position):
                    return False
            
            # Return to starting position
            if not self.move_tcp(current_position):
                return False
                
            logger.info("Mobility test completed successfully.")
            return True
        except Exception as e:
            logger.error(f"Mobility test failed: {str(e)}")
            return False
    
    def convert_svg_to_trajectory(self, svg_file):
        """Convert SVG file to a trajectory of 6D vectors."""
        try:
            # Parse the SVG file
            tree = ET.parse(svg_file)
            root = tree.getroot()
            
            # Find all path elements
            paths = []
            for path in root.findall('.//{http://www.w3.org/2000/svg}path'):
                d = path.get('d')
                if d:
                    paths.append(d)
                    
            if not paths:
                logger.error("No paths found in SVG file.")
                return []
            
            # Convert SVG paths to a series of points
            # This requires simplifying SVG paths to basic move and line commands
            trajectory_points = []
            
            # Process each path
            for path_d in paths:
                # Parse the path data
                commands = path_d.replace(',', ' ').split()
                i = 0
                current_cmd = None
                absolute_position = [0, 0]  # Current position in SVG coordinates
                
                while i < len(commands):
                    if commands[i] in 'MLmlHhVvZz':
                        current_cmd = commands[i]
                        i += 1
                    elif current_cmd in 'Mm' and i+1 < len(commands):
                        try:
                            x = float(commands[i])
                            y = float(commands[i+1])
                            
                            # Adjust for relative coordinates
                            if current_cmd == 'm':
                                x += absolute_position[0]
                                y += absolute_position[1]
                            
                            absolute_position = [x, y]
                            trajectory_points.append(('move', x, y))
                            i += 2
                        except ValueError:
                            i += 1
                    elif current_cmd in 'Ll' and i+1 < len(commands):
                        try:
                            x = float(commands[i])
                            y = float(commands[i+1])
                            
                            # Adjust for relative coordinates
                            if current_cmd == 'l':
                                x += absolute_position[0]
                                y += absolute_position[1]
                            
                            absolute_position = [x, y]
                            trajectory_points.append(('line', x, y))
                            i += 2
                        except ValueError:
                            i += 1
                    elif current_cmd in 'Hh' and i < len(commands):
                        try:
                            x = float(commands[i])
                            # Horizontal line - only X changes
                            if current_cmd == 'h':
                                x += absolute_position[0]
                            
                            absolute_position = [x, absolute_position[1]]
                            trajectory_points.append(('line', x, absolute_position[1]))
                            i += 1
                        except ValueError:
                            i += 1
                    elif current_cmd in 'Vv' and i < len(commands):
                        try:
                            y = float(commands[i])
                            # Vertical line - only Y changes
                            if current_cmd == 'v':
                                y += absolute_position[1]
                            
                            absolute_position = [absolute_position[0], y]
                            trajectory_points.append(('line', absolute_position[0], y))
                            i += 1
                        except ValueError:
                            i += 1
                    elif current_cmd in 'Zz':
                        # Close path - return to first point
                        # We need to find the first point in this path
                        first_point = None
                        for point in trajectory_points:
                            if point[0] == 'move':
                                first_point = point
                                break
                        
                        if first_point:
                            trajectory_points.append(('line', first_point[1], first_point[2]))
                        
                        i += 1
                    else:
                        # Skip unsupported commands
                        i += 1
            
            # Scale and convert to robot coordinates
            robot_trajectory = self.scale_trajectory_to_a4(trajectory_points)
            
            return robot_trajectory
            
        except Exception as e:
            logger.error(f"Failed to convert SVG to trajectory: {str(e)}")
            return []
    
    def scale_trajectory_to_a4(self, trajectory_points):
        """Scale trajectory points to fit A4 paper and convert to 6D robot coordinates."""
        if not trajectory_points or self.surface_z is None:
            return []
            
        # Find the bounds of the drawing in SVG coordinates
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for cmd in trajectory_points:
            if cmd[0] in ('move', 'line'):
                x, y = cmd[1], cmd[2]
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
        
        # Calculate scaling factors for A4 paper (use 90% of paper to leave margins)
        svg_width = max_x - min_x
        svg_height = max_y - min_y
        
        # SVG normally uses 210x297 units for A4, but we'll check the bounds
        scale_x = (A4_WIDTH * 0.9) / svg_width if svg_width > 0 else 1
        scale_y = (A4_HEIGHT * 0.9) / svg_height if svg_height > 0 else 1
        
        # Use the smaller scaling factor to maintain aspect ratio
        scale = min(scale_x, scale_y)
        
        # Get current position as the center point
        current_position = self.get_current_position()
        if not current_position:
            return []
            
        # Center of A4 paper should align with current XY position
        center_x = current_position[0]
        center_y = current_position[1]
        
        # Convert to full 6D robot trajectory
        robot_trajectory = []
        for cmd in trajectory_points:
            if cmd[0] == 'move' or cmd[0] == 'line':
                # Normalize to SVG center, scale, then offset to robot center
                x_norm = cmd[1] - (min_x + svg_width/2)
                y_norm = cmd[2] - (min_y + svg_height/2)
                
                x = center_x + x_norm * scale
                y = center_y + y_norm * scale
                
                # Z position depends on whether pen is up or down
                z = self.surface_z + (PEN_UP_Z if cmd[0] == 'move' else PEN_DOWN_Z)
                
                # Keep the same orientation as the current position
                rx = current_position[3]
                ry = current_position[4]
                rz = current_position[5]
                
                # Create a full 6D vector
                robot_trajectory.append((cmd[0], [x, y, z, rx, ry, rz]))
        
        return robot_trajectory
    
    def execute_trajectory(self, trajectory):
        """Execute a prepared robot trajectory."""
        if not self.is_connected or not trajectory:
            logger.error("Not connected or empty trajectory.")
            return False
            
        try:
            logger.info(f"Executing trajectory with {len(trajectory)} points...")
            
            # Start with pen up
            if not self.pen_up():
                return False
                
            pen_is_down = False
            
            for cmd, pose in trajectory:
                if cmd == 'move':
                    # Ensure pen is up for move commands
                    if pen_is_down:
                        if not self.pen_up():
                            return False
                        pen_is_down = False
                    
                    # Move to position
                    if not self.move_tcp(pose):
                        return False
                
                elif cmd == 'line':
                    # If pen isn't down yet, move to position and then lower pen
                    if not pen_is_down:
                        # First move with pen up to the XY position
                        up_pose = pose.copy()
                        up_pose[2] = self.surface_z + PEN_UP_Z
                        if not self.move_tcp(up_pose):
                            return False
                            
                        # Then lower the pen
                        if not self.pen_down():
                            return False
                            
                        # Now move to the exact position with pen down
                        if not self.move_tcp(pose):
                            return False
                            
                        pen_is_down = True
                    else:
                        # Continue drawing with pen down
                        if not self.move_tcp(pose):
                            return False
            
            # Lift pen up when done
            if pen_is_down:
                if not self.pen_up():
                    return False
            
            # Return to the raised position
            if not self.move_to_home():
                return False
                
            logger.info("Trajectory execution completed successfully.")
            return True
        except Exception as e:
            logger.error(f"Trajectory execution failed: {str(e)}")
            # Ensure pen is up in case of failure
            try:
                self.pen_up()
            except:
                pass
            return False
    
    def execute_drawing(self, svg_file):
        """Execute drawing from an SVG file using trajectory approach."""
        if not self.is_connected or self.surface_z is None:
            logger.error("Not connected or surface not calibrated.")
            return False
            
        try:
            # Convert SVG to trajectory
            logger.info(f"Converting {svg_file} to robot trajectory...")
            trajectory = self.convert_svg_to_trajectory(svg_file)
            
            if not trajectory:
                logger.error("Failed to create trajectory from SVG file.")
                return False
                
            logger.info(f"Created trajectory with {len(trajectory)} points.")
            
            # Execute the trajectory
            return self.execute_trajectory(trajectory)
            
        except Exception as e:
            logger.error(f"Drawing execution failed: {str(e)}")
            return False

def create_sample_svg():
    """Create sample SVG files for testing."""
    # Create drawings directory if it doesn't exist
    os.makedirs('drawings', exist_ok=True)
    
    # Simple square SVG
    square_svg = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <path style="fill:none;stroke:#000000;stroke-width:1px;" d="M 50,50 L 150,50 L 150,150 L 50,150 Z" />
</svg>"""
    
    # Simple circle SVG
    circle_svg = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <circle style="fill:none;stroke:#000000;stroke-width:1px;" cx="105" cy="148.5" r="50" />
</svg>"""
    
    # Spiral SVG
    spiral_path = "M 105,148.5 "
    radius = 5
    for angle in range(0, 1080, 5):
        rad = math.radians(angle)
        radius += 0.2
        x = 105 + radius * math.cos(rad)
        y = 148.5 + radius * math.sin(rad)
        spiral_path += f"L {x},{y} "
    
    spiral_svg = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <path style="fill:none;stroke:#000000;stroke-width:1px;" d="{spiral_path}" />
</svg>"""
    
    # Star SVG
    star_svg = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <path style="fill:none;stroke:#000000;stroke-width:1px;" d="M 105,98.5 L 120,133.5 L 155,133.5 L 130,153.5 L 140,188.5 L 105,168.5 L 70,188.5 L 80,153.5 L 55,133.5 L 90,133.5 Z" />
</svg>"""
    
    # Write files if they don't exist
    if not os.path.exists('drawings/square.svg'):
        with open('drawings/square.svg', 'w') as f:
            f.write(square_svg)
            
    if not os.path.exists('drawings/circle.svg'):
        with open('drawings/circle.svg', 'w') as f:
            f.write(circle_svg)
            
    if not os.path.exists('drawings/spiral.svg'):
        with open('drawings/spiral.svg', 'w') as f:
            f.write(spiral_svg)
            
    if not os.path.exists('drawings/star.svg'):
        with open('drawings/star.svg', 'w') as f:
            f.write(star_svg)
    
    logger.info("Created sample SVG files in 'drawings' directory.")

def create_gui(app):
    """Create a simple command-line GUI for the application."""
    # Connect to the robot immediately
    if not app.is_connected:
        print("Connecting to robot...")
        if app.connect_to_robot():
            print("Connected successfully to UR3e robot!")
        else:
            print("Failed to connect to robot. Please check settings and robot status.")
    
    # Create sample SVG files
    create_sample_svg()
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\n===== UR3e Drawing Application =====")
        print("\nCurrent Status:")
        print(f"Connected to robot: {'Yes' if app.is_connected else 'No'}")
        
        if app.is_connected:
            # Get current state
            try:
                state = app.rtde_state.receive()
                if state:
                    print(f"Robot mode: {app.rtde_state.programState.get(state.runtime_state, 'Unknown')}")
                    print(f"Safety status: {state.safety_status}")
            except:
                pass
                
        print(f"Surface calibrated: {'Yes' if app.surface_z is not None else 'No'}")
        print(f"Home position set:  {'Yes' if app.home_position is not None else 'No'}")
        if app.home_position:
            print(f"Home: {app.format_position(app.home_position)}")
        
        print("\nPlease choose an option:")
        print("1. Release Robot Brakes")
        print("2. Calibrate Drawing Surface")
        print("3. Test Mobility")
        print("4. Execute Drawing")
        print("5. Load Custom SVG")
        print("0. Exit")
        
        choice = input("\nEnter your choice (0-5): ")
        
        if choice == '0':
            if app.is_connected:
                app.disconnect_from_robot()
            print("\nExiting application...")
            break
            
        elif choice == '1':
            if not app.is_connected:
                print("\nNot connected to robot.")
            else:
                print("\nReleasing robot brakes...")
                if app.release_brakes():
                    print("Brakes released successfully!")
                else:
                    print("Failed to release brakes. Check logs for details.")
            input("\nPress Enter to continue...")
            
        elif choice == '2':
            if not app.is_connected:
                print("\nNot connected to robot.")
            else:
                print("\nCalibrating drawing surface...")
                if app.calibrate_surface():
                    print("Surface calibrated successfully!")
                    print(f"Surface Z = {app.surface_z:.4f}")
                    print(f"Home position = {app.format_position(app.home_position)}")
                else:
                    print("Calibration failed. Check logs for details.")
            input("\nPress Enter to continue...")
            
        elif choice == '3':
            if not app.is_connected:
                print("\nNot connected to robot.")
            elif app.surface_z is None:
                print("\nSurface not calibrated. Please calibrate first.")
            else:
                print("\nRunning mobility test...")
                if app.test_mobility():
                    print("Mobility test completed successfully!")
                else:
                    print("Mobility test failed. Check logs for details.")
            input("\nPress Enter to continue...")
            
        elif choice == '4':
            if not app.is_connected:
                print("\nNot connected to robot.")
            elif app.surface_z is None:
                print("\nSurface not calibrated. Please calibrate first.")
            else:
                print("\nSelect a drawing to execute:")
                print("1. Square")
                print("2. Circle")
                print("3. Spiral")
                print("4. Star")
                
                drawing_choice = input("\nEnter your choice (1-4): ")
                drawing_file = None
                
                if drawing_choice == '1':
                    drawing_file = 'drawings/square.svg'
                elif drawing_choice == '2':
                    drawing_file = 'drawings/circle.svg'
                elif drawing_choice == '3':
                    drawing_file = 'drawings/spiral.svg'
                elif drawing_choice == '4':
                    drawing_file = 'drawings/star.svg'
                
                if drawing_file and os.path.exists(drawing_file):
                    print(f"\nExecuting drawing from {drawing_file}...")
                    if app.execute_drawing(drawing_file):
                        print("Drawing completed successfully!")
                    else:
                        print("Drawing failed. Check logs for details.")
                else:
                    print("Invalid selection or file not found.")
            input("\nPress Enter to continue...")
            
        elif choice == '5':
            if not app.is_connected:
                print("\nNot connected to robot.")
            elif app.surface_z is None:
                print("\nSurface not calibrated. Please calibrate first.")
            else:
                svg_file = input("\nEnter path to SVG file: ")
                if os.path.exists(svg_file):
                    print(f"\nExecuting drawing from {svg_file}...")
                    if app.execute_drawing(svg_file):
                        print("Drawing completed successfully!")
                    else:
                        print("Drawing failed. Check logs for details.")
                else:
                    print(f"File {svg_file} not found.")
            input("\nPress Enter to continue...")
            
        else:
            print("\nInvalid choice. Please try again.")
            input("\nPress Enter to continue...")

if __name__ == "__main__":
    app = UR3eDrawingApp()
    create_gui(app)