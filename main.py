#!/usr/bin/env python3
"""
UR3e Robot Control Script
This script provides functionality to control a UR3e robot arm, including movement
and gripper operations.
"""

import time
import math
import socket
import struct
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ur3e_control')

class UR3eController:
    """Controller class for UR3e robot."""
    
    def __init__(self, host, port=30004, gripper_attached=True):
        """
        Initialize the UR3e controller.
        
        Args:
            host (str): IP address of the robot
            port (int): Port for communication (usually 30004 for RTDE)
            gripper_attached (bool): Whether a gripper is attached to the robot
        """
        self.host = host
        self.port = port
        self.gripper_attached = gripper_attached
        self.socket = None
        self.connected = False
        self.rtde_connection = None
        self.dashboard = None
        logger.info(f"UR3e controller initialized for robot at {host}:{port}")
        
    def connect(self):
        """Connect to the robot controller using RTDE and Dashboard."""
        try:
            # Import required modules for RTDE connection
            import rtde.rtde as rtde
            import rtde.rtde_config as rtde_config
            from Dashboard import Dashboard
            
            # Connect to Dashboard server
            self.dashboard = Dashboard(self.host)
            self.dashboard.connect()
            logger.info(f"Connected to UR3e Dashboard at {self.host}")
            
            # Connect to RTDE
            config_filename = 'rtdeState.xml'  # Make sure this file exists
            self.rtde_connection = rtde.RTDE(self.host, self.port)
            self.rtde_connection.connect()
            
            # Get controller version to verify connection
            controller_version = self.rtde_connection.get_controller_version()
            logger.info(f"Connected to UR3e RTDE at {self.host} - Controller version: {controller_version}")
            
            # Setup configuration
            conf = rtde_config.ConfigFile(config_filename)
            output_names, output_types = conf.get_recipe('state')
            self.rtde_connection.send_output_setup(output_names, output_types, frequency=125)
            
            # Try to setup input registers
            try:
                set_q_names, set_q_types = conf.get_recipe('set_q')
                self.set_q = self.rtde_connection.send_input_setup(set_q_names, set_q_types)
                
                servo_names, servo_types = conf.get_recipe('servo')
                self.servo = self.rtde_connection.send_input_setup(servo_names, servo_types)
            except Exception as e:
                logger.warning(f"Could not setup all input registers: {e}")
            
            # Start data synchronization
            if not self.rtde_connection.send_start():
                logger.error("Failed to start data synchronization")
                return False
            
            self.connected = True
            logger.info(f"Successfully connected to UR3e at {self.host}")
            return True
        except ImportError as e:
            logger.error(f"Required modules not found: {e}. Falling back to socket connection.")
            return self._connect_socket()
        except Exception as e:
            logger.error(f"Failed to connect to robot using RTDE: {e}. Falling back to socket connection.")
            return self._connect_socket()
    
    def _connect_socket(self):
        """Connect using basic socket as fallback."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.host, 30003))  # Default primary interface port
            self.connected = True
            logger.info(f"Connected to UR3e via socket at {self.host}:30003")
            return True
        except Exception as e:
            logger.error(f"Failed to connect via socket: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from the robot controller."""
        if self.rtde_connection:
            self.rtde_connection.send_pause()
            self.rtde_connection.disconnect()
            logger.info("Disconnected from UR3e RTDE")
        
        if self.dashboard:
            self.dashboard.close()
            logger.info("Disconnected from UR3e Dashboard")
            
        if self.socket:
            self.socket.close()
            logger.info("Disconnected from UR3e socket")
            
        self.connected = False
    
    def _send_command(self, command):
        """
        Send a command string to the robot.
        
        Args:
            command (str): URScript command to send to the robot
        
        Returns:
            bool: Success status
        """
        if not self.connected:
            logger.error("Not connected to robot")
            return False
        
        try:
            if self.dashboard:
                # Try sending through dashboard if applicable
                response = self.dashboard.sendAndReceive(command)
                logger.debug(f"Command sent via dashboard: {command}")
                logger.debug(f"Response: {response}")
                return True
            elif self.socket:
                # Fall back to direct socket communication
                self.socket.send((command + "\n").encode())
                logger.debug(f"Command sent via socket: {command}")
                return True
            else:
                logger.error("No available connection to robot")
                return False
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            return False
    
    def move_joints(self, joint_positions, acceleration=1.0):
        """
        Move robot to specified joint positions.
        
        Args:
            joint_positions (list): List of 6 joint angles in radians
            acceleration (float): Joint acceleration (0.0 to 1.0)
        
        Returns:
            bool: Success status
        """
        if len(joint_positions) != 6:
            logger.error("Joint positions must be a list of 6 values")
            return False
        
        # Clamp acceleration
        acceleration = max(0.01, min(1.0, acceleration))
        
        # If RTDE connection is available, use it for more precise control
        if hasattr(self, 'set_q') and hasattr(self, 'servo') and self.rtde_connection:
            try:
                # Set joint positions using RTDE
                for i in range(6):
                    self.set_q.__dict__[f"input_double_register_{i}"] = joint_positions[i]
                
                # Wait for program to be ready for servoing
                state = self.rtde_connection.receive()
                while state.output_int_register_0 != 1:
                    state = self.rtde_connection.receive()
                
                # Enable servoing
                self.servo.input_int_register_0 = 1
                self.rtde_connection.send(self.servo)
                
                # Send joint positions
                self.rtde_connection.send(self.set_q)
                logger.info(f"Joint positions sent via RTDE: {joint_positions}")
                return True
                
            except Exception as e:
                logger.warning(f"Failed to move joints via RTDE: {e}. Falling back to URScript.")
        
        # Fall back to URScript command
        # Format joint positions as a string
        positions_str = "["
        positions_str += ",".join([str(angle) for angle in joint_positions])
        positions_str += "]"
        
        # Construct and send the command with default velocity
        command = f"movej({positions_str}, a={acceleration}, v=1.0)"
        return self._send_command(command)
    
    def move_linear(self, pose, acceleration=0.5):
        """
        Move linearly to specified pose.
        
        Args:
            pose (list): List of 6 values [x, y, z, rx, ry, rz] 
                        (position in meters, orientation in radians)
            acceleration (float): Tool acceleration in m/s^2
        
        Returns:
            bool: Success status
        """
        if len(pose) != 6:
            logger.error("Pose must be a list of 6 values")
            return False
        
        # Format pose as a string
        pose_str = "p["
        pose_str += ",".join([str(p) for p in pose])
        pose_str += "]"
        
        # Construct and send the command with default velocity
        command = f"movel({pose_str}, a={acceleration}, v=0.1)"
        return self._send_command(command)position in meters, orientation in radians)
            velocity (float): Tool velocity in m/s
            acceleration (float): Tool acceleration in m/s^2
        
        Returns:
            bool: Success status
        """
        if len(pose) != 6:
            logger.error("Pose must be a list of 6 values")
            return False
        
        # Format pose as a string
        pose_str = "p["
        pose_str += ",".join([str(p) for p in pose])
        pose_str += "]"
        
        # Construct and send the command
        command = f"movel({pose_str}, a={acceleration}, v={velocity})"
        return self._send_command(command)
    
    def move_tool(self, offset, velocity=0.1, acceleration=0.5):
        """
        Move tool by a relative offset.
        
        Args:
            offset (list): List of 6 values [dx, dy, dz, drx, dry, drz]
                          (position in meters, orientation in radians)
            velocity (float): Tool velocity in m/s
            acceleration (float): Tool acceleration in m/s^2
        
        Returns:
            bool: Success status
        """
        if len(offset) != 6:
            logger.error("Offset must be a list of 6 values")
            return False
        
        # Format offset as a string
        offset_str = "p["
        offset_str += ",".join([str(o) for o in offset])
        offset_str += "]"
        
        # Construct and send the command
        command = f"tool_offset = {offset_str}\n"
        command += f"movel(pose_trans(get_actual_tcp_pose(), tool_offset), a={acceleration}, v={velocity})"
        return self._send_command(command)
    
    def open_gripper(self, width=0.1):
        """
        Open the gripper to specified width.
        
        Args:
            width (float): Opening width in meters
        
        Returns:
            bool: Success status
        """
        if not self.gripper_attached:
            logger.warning("No gripper attached")
            return False
        
        # This command will need to be adjusted based on the specific gripper model
        command = f"set_tool_digital_out(0, False)  # Example for digital gripper control"
        return self._send_command(command)
    
    def close_gripper(self, force=40):
        """
        Close the gripper with specified force.
        
        Args:
            force (float): Grip force in Newtons (0-100N range)
        
        Returns:
            bool: Success status
        """
        if not self.gripper_attached:
            logger.warning("No gripper attached")
            return False
        
        # Clamp force to valid range
        force = max(0, min(100, force))
        
        # This command will need to be adjusted based on the specific gripper model
        if self.rtde_connection:
            try:
                # Example for sending gripper force using RTDE
                # Assuming there's a register for gripper force
                # This is placeholder code and should be adjusted for your specific gripper
                command = f"set_tool_digital_out(0, True)\n"
                command += f"set_tool_analog_out(0, {force/100.0})"  # Normalize to 0-1 range
                return self._send_command(command)
            except Exception as e:
                logger.warning(f"Failed to set gripper force via RTDE: {e}. Using default command.")
        
        # Fall back to simple digital out
        command = f"set_tool_digital_out(0, True)  # Example for digital gripper control"
        return self._send_command(command)
    
    def get_current_pose(self):
        """
        Get the current pose of the robot.
        
        Returns:
            list: Current pose [x, y, z, rx, ry, rz] or None if failed
        """
        # If using RTDE, get pose directly
        if self.rtde_connection:
            try:
                state = self.rtde_connection.receive()
                if state and hasattr(state, 'actual_TCP_pose'):
                    logger.info(f"Current pose retrieved via RTDE: {state.actual_TCP_pose}")
                    return state.actual_TCP_pose
            except Exception as e:
                logger.warning(f"Failed to get pose via RTDE: {e}. Falling back to URScript.")
        
        # Fall back to URScript command
        if self.socket:
            try:
                command = "current_pose = get_actual_tcp_pose()\nprint(current_pose)"
                self.socket.send((command + "\n").encode())
                
                # Wait for response
                response = b""
                while True:
                    chunk = self.socket.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    if b"]\n" in response:  # Simple check for end of pose data
                        break
                
                # Parse response to extract the pose
                pose_str = response.decode('utf-8')
                start_idx = pose_str.find('[')
                end_idx = pose_str.find(']', start_idx)
                
                if start_idx != -1 and end_idx != -1:
                    pose_values = pose_str[start_idx+1:end_idx].split(',')
                    pose = [float(val.strip()) for val in pose_values]
                    logger.info(f"Current pose retrieved via socket: {pose}")
                    return pose
            except Exception as e:
                logger.error(f"Failed to get pose via socket: {e}")
        
        logger.warning("Could not retrieve current pose, returning default values")
        return [0, 0, 0, 0, 0, 0]  # Default values
    
    def get_current_joints(self):
        """
        Get the current joint positions.
        
        Returns:
            list: Current joint positions or None if failed
        """
        # If using RTDE, get joint positions directly
        if self.rtde_connection:
            try:
                state = self.rtde_connection.receive()
                if state and hasattr(state, 'actual_q'):
                    logger.info(f"Current joint positions retrieved via RTDE: {state.actual_q}")
                    return state.actual_q
            except Exception as e:
                logger.warning(f"Failed to get joint positions via RTDE: {e}. Falling back to URScript.")
        
        # Fall back to URScript command
        if self.socket:
            try:
                command = "current_joints = get_actual_joint_positions()\nprint(current_joints)"
                self.socket.send((command + "\n").encode())
                
                # Wait for response
                response = b""
                while True:
                    chunk = self.socket.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    if b"]\n" in response:  # Simple check for end of joint data
                        break
                
                # Parse response to extract the joint positions
                joints_str = response.decode('utf-8')
                start_idx = joints_str.find('[')
                end_idx = joints_str.find(']', start_idx)
                
                if start_idx != -1 and end_idx != -1:
                    joint_values = joints_str[start_idx+1:end_idx].split(',')
                    joints = [float(val.strip()) for val in joint_values]
                    logger.info(f"Current joint positions retrieved via socket: {joints}")
                    return joints
            except Exception as e:
                logger.error(f"Failed to get joint positions via socket: {e}")
        
        logger.warning("Could not retrieve current joint positions, returning default values")
        return [0, 0, 0, 0, 0, 0]  # Default values

    def move_to_point(self, start_point, end_point, velocity=0.1, acceleration=0.5):
        """
        Move from start_point to end_point linearly.
        
        Args:
            start_point (list): Starting pose [x, y, z, rx, ry, rz]
            end_point (list): Ending pose [x, y, z, rx, ry, rz]
            velocity (float): Tool velocity in m/s
            acceleration (float): Tool acceleration in m/s^2
        
        Returns:
            bool: Success status
        """
        # First move to start point
        success = self.move_linear(start_point, velocity, acceleration)
        if not success:
            logger.error("Failed to move to start point")
            return False
        
        # Wait for the move to complete (simplified)
        time.sleep(2)
        
        # Then move to end point
        success = self.move_linear(end_point, velocity, acceleration)
        if not success:
            logger.error("Failed to move to end point")
            return False
            
        logger.info(f"Successfully moved from {start_point} to {end_point}")
        return True

    def record_path(self, duration=10):
        """
        Record a path of the robot's movement.
        
        Args:
            duration (int): Duration to record movement in seconds
            
        Returns:
            list: List of joint positions
        """
        if not self.rtde_connection:
            logger.error("RTDE connection required for path recording")
            return []
        
        logger.info(f"Recording path for {duration} seconds...")
        joint_positions = []
        
        start_time = time.time()
        while time.time() - start_time < duration:
            state = self.rtde_connection.receive()
            if state and hasattr(state, 'actual_q'):
                joint_positions.append(state.actual_q)
                time.sleep(0.02)  # ~50Hz recording
        
        logger.info(f"Recorded {len(joint_positions)} joint positions")
        return joint_positions
    
    def save_path_to_csv(self, joint_positions, filename="robot_path.csv"):
        """
        Save recorded joint positions to a CSV file.
        
        Args:
            joint_positions (list): List of joint position lists
            filename (str): Name of CSV file to save
            
        Returns:
            bool: Success status
        """
        try:
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile, delimiter=',')
                for positions in joint_positions:
                    writer.writerow(positions)
            logger.info(f"Saved path to {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to save path: {e}")
            return False
    
    def load_path_from_csv(self, filename="robot_path.csv"):
        """
        Load joint positions from a CSV file.
        
        Args:
            filename (str): Name of CSV file to load
            
        Returns:
            list: List of joint position lists
        """
        joint_positions = []
        try:
            with open(filename, 'r') as csvfile:
                reader = csv.reader(csvfile, delimiter=',')
                for row in reader:
                    joint_positions.append([float(val) for val in row])
            logger.info(f"Loaded {len(joint_positions)} joint positions from {filename}")
            return joint_positions
        except Exception as e:
            logger.error(f"Failed to load path: {e}")
            return []
    
    def playback_path(self, joint_positions, velocity=0.5):
        """
        Play back a recorded path.
        
        Args:
            joint_positions (list): List of joint position lists
            velocity (float): Playback velocity scale
            
        Returns:
            bool: Success status
        """
        if not joint_positions:
            logger.error("No joint positions to play back")
            return False
        
        logger.info(f"Playing back {len(joint_positions)} joint positions")
        
        # If RTDE is available, use it for more precise control
        if hasattr(self, 'set_q') and hasattr(self, 'servo') and self.rtde_connection:
            try:
                # Wait for program to be ready for servoing
                state = self.rtde_connection.receive()
                attempt = 0
                while state.output_int_register_0 != 1 and attempt < 10:
                    state = self.rtde_connection.receive()
                    attempt += 1
                    time.sleep(0.1)
                
                if attempt >= 10:
                    logger.warning("Robot not ready for servoing, falling back to movej")
                    # Fall back to movej for each position
                    for positions in joint_positions:
                        self.move_joints(positions, velocity=velocity)
                        time.sleep(0.1)
                    return True
                
                # Enable servoing
                self.servo.input_int_register_0 = 1
                self.rtde_connection.send(self.servo)
                
                # Send each joint position
                for positions in joint_positions:
                    for i in range(6):
                        self.set_q.__dict__[f"input_double_register_{i}"] = positions[i]
                    self.rtde_connection.send(self.set_q)
                    time.sleep(0.02 / velocity)  # Adjust timing based on velocity
                
                # Disable servoing
                self.servo.input_int_register_0 = 0
                self.rtde_connection.send(self.servo)
                
                logger.info("Path playback completed via RTDE")
                return True
                
            except Exception as e:
                logger.warning(f"Failed to play back path via RTDE: {e}. Falling back to movej.")
        
        # Fall back to movej for each position
        for positions in joint_positions:
            self.move_joints(positions, velocity=velocity)
            time.sleep(0.1)
        
        logger.info("Path playback completed via URScript")
        return True
    
    def run_test_cases(self):
        """Run a series of test cases to validate robot functionality."""
        if not self.connected:
            if not self.connect():
                logger.error("Cannot run test cases - not connected")
                return False
        
        logger.info("Starting test cases...")
        
        # Test case 1: Small joint movements
        logger.info("Test case 1: Small joint movements")
        home_joints = [0, -1.57, 0, -1.57, 0, 0]  # Approximate home position
        self.move_joints(home_joints, velocity=0.3)
        time.sleep(3)
        
        # Move each joint slightly
        for i in range(6):
            test_joints = home_joints.copy()
            test_joints[i] += 0.2  # Move joint by 0.2 radians
            logger.info(f"Moving joint {i+1}")
            self.move_joints(test_joints, velocity=0.3)
            time.sleep(2)
            # Move back
            self.move_joints(home_joints, velocity=0.3)
            time.sleep(2)
        
        # Test case 2: Linear movement test
        logger.info("Test case 2: Linear movement test")
        # Assuming robot is in home position
        current_pose = self.get_current_pose()
        if current_pose:
            # Move 10cm in X direction
            test_pose = current_pose.copy()
            test_pose[0] += 0.1  # Add 10cm to X
            logger.info("Moving 10cm in X direction")
            self.move_linear(test_pose, velocity=0.05)
            time.sleep(3)
            
            # Move back
            logger.info("Moving back to original position")
            self.move_linear(current_pose, velocity=0.05)
            time.sleep(3)
            
            # Move 10cm in Y direction
            test_pose = current_pose.copy()
            test_pose[1] += 0.1  # Add 10cm to Y
            logger.info("Moving 10cm in Y direction")
            self.move_linear(test_pose, velocity=0.05)
            time.sleep(3)
            
            # Move back
            logger.info("Moving back to original position")
            self.move_linear(current_pose, velocity=0.05)
            time.sleep(3)
        
        # Test case 3: Gripper test
        if self.gripper_attached:
            logger.info("Test case 3: Gripper test")
            logger.info("Opening gripper")
            self.open_gripper()
            time.sleep(2)
            
            logger.info("Closing gripper")
            self.close_gripper()
            time.sleep(2)
            
            logger.info("Opening gripper again")
            self.open_gripper()
            time.sleep(2)
        
        # Test case 4: Point-to-point movement
        logger.info("Test case 4: Point-to-point movement")
        point_a = [0.4, 0.0, 0.5, 0, 3.14, 0]  # Example pose A
        point_b = [0.4, 0.2, 0.5, 0, 3.14, 0]  # Example pose B, 20cm away in Y
        
        logger.info(f"Moving from point A {point_a} to point B {point_b}")
        self.move_to_point(point_a, point_b, velocity=0.1)
        time.sleep(2)
        
        logger.info(f"Moving back from point B {point_b} to point A {point_a}")
        self.move_to_point(point_b, point_a, velocity=0.1)
        
        # Test case 5: Path recording and playback (if RTDE is available)
        if self.rtde_connection:
            logger.info("Test case 5: Path recording and playback")
            
            # Record a small movement
            logger.info("Please jog the robot for 5 seconds to record a path...")
            recorded_path = self.record_path(duration=5)
            
            if recorded_path:
                # Save to CSV
                self.save_path_to_csv(recorded_path, "test_path.csv")
                
                # Load from CSV
                loaded_path = self.load_path_from_csv("test_path.csv")
                
                # Play back the path
                logger.info("Playing back recorded path...")
                self.playback_path(loaded_path, velocity=0.5)
            else:
                logger.warning("Path recording failed, skipping playback test")
        
        logger.info("All test cases completed")
        return True


# Example usage
if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='UR3e Robot Control Script')
    parser.add_argument('--ip', type=str, default="192.168.0.2", help='IP address of the robot')
    parser.add_argument('--port', type=int, default=30004, help='Port for RTDE communication (default: 30004)')
    parser.add_argument('--test', action='store_true', help='Run test cases')
    parser.add_argument('--record', type=float, default=0, help='Record a path for specified seconds')
    parser.add_argument('--play', type=str, help='Play back a path from specified CSV file')
    parser.add_argument('--gripper', action='store_true', help='Test gripper functionality')
    parser.add_argument('--move', action='store_true', help='Run point-to-point movement test')
    args = parser.parse_args()
    
    # Create a controller instance
    robot = UR3eController(args.ip, args.port)
    
    try:
        # Connect to the robot
        if robot.connect():
            logger.info(f"Successfully connected to robot at {args.ip}")
            
            # Run tests based on command-line arguments
            if args.test:
                logger.info("Running all test cases")
                robot.run_test_cases()
            
            elif args.record > 0:
                logger.info(f"Recording robot path for {args.record} seconds")
                logger.info("Please jog the robot to create a path")
                recorded_path = robot.record_path(duration=args.record)
                if recorded_path:
                    filename = f"recorded_path_{time.strftime('%Y%m%d_%H%M%S')}.csv"
                    robot.save_path_to_csv(recorded_path, filename)
                    logger.info(f"Path saved to {filename}")
            
            elif args.play:
                logger.info(f"Playing back path from {args.play}")
                path = robot.load_path_from_csv(args.play)
                if path:
                    robot.playback_path(path)
                else:
                    logger.error(f"Failed to load path from {args.play}")
            
            elif args.gripper:
                logger.info("Testing gripper functionality")
                robot.open_gripper()
                time.sleep(2)
                robot.close_gripper()
                time.sleep(2)
                robot.open_gripper()
            
            elif args.move:
                # Example of moving from point A to point B
                point_a = [0.4, -0.2, 0.5, 0, 3.14, 0]  # Example coordinates
                point_b = [0.4, 0.2, 0.5, 0, 3.14, 0]   # Example coordinates
                
                logger.info("Demonstrating point-to-point movement with object pickup")
                robot.move_to_point(point_a, point_b)
                
                # Close the gripper to grab an object
                logger.info("Closing gripper to grab object")
                robot.close_gripper()
                time.sleep(1)
                
                # Move back to point A with the object
                logger.info("Moving back to point A with object")
                robot.move_to_point(point_b, point_a)
                
                # Open the gripper to release the object
                logger.info("Opening gripper to release object")
                robot.open_gripper()
            
            else:
                # Default action: check connection and print robot status
                logger.info("Getting robot status")
                current_pose = robot.get_current_pose()
                current_joints = robot.get_current_joints()
                
                logger.info(f"Current TCP pose: {current_pose}")
                logger.info(f"Current joint positions: {current_joints}")
                
                # Check if robot is in remote control mode using Dashboard if available
                if robot.dashboard:
                    remote_status = robot.dashboard.sendAndReceive('is in remote control')
                    logger.info(f"Remote control status: {remote_status}")
                    
                    powermode = robot.dashboard.sendAndReceive('robotmode')
                    logger.info(f"Robot power mode: {powermode}")
                
                logger.info("Use --help to see available command options")
        else:
            logger.error(f"Failed to connect to robot at {args.ip}")
    
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
    
    finally:
        # Always disconnect properly
        robot.disconnect()
        logger.info("Program finished")