#!/usr/bin/env python3
"""
UR3e Robot Test Script
This script performs testing of the UR3e robot functionality.
"""

import time
import logging
import sys
import os

# Add the current directory to sys.path to find the module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from ur3e_robot_script import UR3eController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ur3e_test')

def test_movement_accuracy(robot, iterations=5):
    """
    Test the accuracy of the robot's movements by moving between two points 
    multiple times.
    """
    logger.info("Testing movement accuracy")
    
    # Define test points
    point_a = [0.4, -0.2, 0.3, 0, 3.14, 0]
    point_b = [0.4, 0.2, 0.3, 0, 3.14, 0]
    
    # Move to initial position
    robot.move_linear(point_a)
    time.sleep(2)
    
    # Perform accuracy test
    for i in range(iterations):
        logger.info(f"Accuracy test iteration {i+1}/{iterations}")
        
        # Move to point B
        robot.move_linear(point_b)
        time.sleep(1)
        
        # Get current position at point B
        pos_b = robot.get_current_pose()
        logger.info(f"Position at B: {pos_b}")
        
        # Move to point A
        robot.move_linear(point_a)
        time.sleep(1)
        
        # Get current position at point A
        pos_a = robot.get_current_pose()
        logger.info(f"Position at A: {pos_a}")
    
    logger.info("Movement accuracy test completed")

def test_gripper_operation(robot, cycles=3):
    """
    Test the gripper by opening and closing it multiple times.
    """
    logger.info(f"Testing gripper operation for {cycles} cycles")
    
    if not robot.gripper_attached:
        logger.warning("No gripper attached. Skipping gripper test.")
        return
    
    for i in range(cycles):
        logger.info(f"Gripper test cycle {i+1}/{cycles}")
        
        # Open gripper
        logger.info("Opening gripper")
        robot.open_gripper()
        time.sleep(1)
        
        # Close gripper with different force values
        force_values = [20, 50, 80]  # Test different force values (in N)
        force = force_values[i % len(force_values)]
        logger.info(f"Closing gripper with force: {force}N")
        robot.close_gripper(force)
        time.sleep(1)
    
    logger.info("Gripper operation test completed")
"""
def test_pick_and_place(robot, cycles=3):
    #Test a pick and place operation.
    logger.info(f"Testing pick and place operation for {cycles} cycles")
    
    # Define positions
    pick_position = [0.4, -0.2, 0.1, 0, 3.14, 0]  # Position to pick object
    place_position = [0.4, 0.2, 0.1, 0, 3.14, 0]  # Position to place object
    approach_height = 0.1  # Height to approach from
    
    for i in range(cycles):
        logger.info(f"Pick and place cycle {i+1}/{cycles}")
        
        # 1. Move to pick approach position
        pick_approach = pick_position.copy()
        pick_approach[2] += approach_height
        robot.move_linear(pick_approach)
        time.sleep(1)
        
        # 2. Move down to pick position
        robot.move_linear(pick_position)
        time.sleep(1)
        
        # 3. Close gripper to grasp object
        robot.close_gripper(40)  # 40N force
        time.sleep(1)
        
        # 4. Move up to pick approach position with object
        robot.move_linear(pick_approach)
        time.sleep(1)
        
        # 5. Move to place approach position
        place_approach = place_position.copy()
        place_approach[2] += approach_height
        robot.move_linear(place_approach)
        time.sleep(1)
        
        # 6. Move down to place position
        robot.move_linear(place_position)
        time.sleep(1)
        
        # 7. Open gripper to release object
        robot.open_gripper()
        time.sleep(1)
        
        # 8. Move up to place approach position
        robot.move_linear(place_approach)
        time.sleep(1)
    
    logger.info("Pick and place test completed")"""

def run_comprehensive_tests(robot):
    """
    Run a series of comprehensive tests on the robot.
    """
    # Initial setup - move to a safe starting position
    logger.info("Moving to home position")
    home_joints = [0, -1.57, 0, -1.57, 0, 0]  # Approximate home position
    robot.move_joints(home_joints)
    time.sleep(3)
    
    # Run tests
    test_movement_accuracy(robot)
    test_gripper_operation(robot)
    #test_pick_and_place(robot)
    
    # Return to home position
    logger.info("Returning to home position")
    robot.move_joints(home_joints)
    
    logger.info("All tests completed successfully")

if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='UR3e Robot Test Script')
    parser.add_argument('--ip', type=str, default="192.168.0.2", help='IP address of the robot')
    parser.add_argument('--port', type=int, default=30004, help='Port for RTDE communication')
    parser.add_argument('--test', choices=['all', 'movement', 'gripper', 'pick_place'], 
                        default='all', help='Test to run')
    parser.add_argument('--status', action='store_true', help='Check robot status')
    parser.add_argument('--brake-release', action='store_true', help='Release robot brakes')
    parser.add_argument('--power-on', action='store_true', help='Power on the robot')
    parser.add_argument('--power-off', action='store_true', help='Power off the robot')
    args = parser.parse_args()
    
    # Create robot controller
    robot = UR3eController(args.ip, args.port)
    
    try:
        # Connect to robot
        if robot.connect():
            logger.info(f"Connected to UR3e robot at {args.ip}")
            
            # Handle dashboard commands
            if args.status:
                if robot.dashboard:
                    logger.info("Checking robot status...")
                    
                    # Check if robot is in remote control mode
                    remote_status = robot.dashboard.sendAndReceive('is in remote control')
                    logger.info(f"Remote control: {remote_status}")
                    
                    # Get power and operational mode
                    power_mode = robot.dashboard.sendAndReceive('robotmode')
                    logger.info(f"Robot mode: {power_mode}")
                    
                    # Get safety status
                    safety_status = robot.dashboard.sendAndReceive('safetystatus')
                    logger.info(f"Safety status: {safety_status}")
                    
                    # Get program state
                    program_state = robot.dashboard.sendAndReceive('programstate')
                    logger.info(f"Program state: {program_state}")
                else:
                    logger.error("Dashboard connection not available")
            
            elif args.brake_release:
                if robot.dashboard:
                    logger.info("Releasing brakes...")
                    result = robot.dashboard.sendAndReceive('brake release')
                    logger.info(f"Result: {result}")
                else:
                    logger.error("Dashboard connection not available")
            
            elif args.power_on:
                if robot.dashboard:
                    logger.info("Powering on robot...")
                    # First check current mode
                    power_mode = robot.dashboard.sendAndReceive('robotmode')
                    
                    if 'POWER_OFF' in power_mode:
                        logger.info("Robot is powered off. Powering on...")
                        result = robot.dashboard.sendAndReceive('power on')
                        logger.info(f"Power on result: {result}")
                        
                        # Release brakes after power on
                        time.sleep(2)  # Wait for power on
                        result = robot.dashboard.sendAndReceive('brake release')
                        logger.info(f"Brake release result: {result}")
                    else:
                        logger.info(f"Robot is already powered on: {power_mode}")
                else:
                    logger.error("Dashboard connection not available")
            
            elif args.power_off:
                if robot.dashboard:
                    logger.info("Powering off robot...")
                    result = robot.dashboard.sendAndReceive('power off')
                    logger.info(f"Result: {result}")
                else:
                    logger.error("Dashboard connection not available")
            
            # Run specified test if no dashboard commands were given
            elif args.test == 'all':
                run_comprehensive_tests(robot)
            elif args.test == 'movement':
                test_movement_accuracy(robot)
            elif args.test == 'gripper':
                test_gripper_operation(robot)
            elif args.test == 'pick_place':
                test_pick_and_place(robot)
            
        else:
            logger.error(f"Failed to connect to robot at {args.ip}")
    
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    
    except Exception as e:
        logger.error(f"Error during testing: {e}")
    
    finally:
        # Disconnect from robot
        robot.disconnect()
        logger.info("Test script completed")