#!/usr/bin/env python3
# Egyszerű UR Robot vezérlő - Javított bináris protokoll kezeléssel
# Ez a script kifejezetten a port 30002-es (Secondary Client Interface) használatára fókuszál
# és megfelelően kezeli a bináris kommunikációt

import socket
import time
import sys
import os
import glob
import json
import logging
from Dashboard import Dashboard
from rtdeState import RtdeState

#HOME_POSITION = None
DRAWING_HEIGHT = None
#DEFAULT_SPEED = None
#DEFAULT_ACCEL = None
ROBOT_IP = None
ROBOT_PORT = None
RTDE_PORT = None
DASHBOARD_PORT = None

#ROBOT_IP = '10.150.0.1'  # Default Robot IP címe
#ROBOT_PORT = 30002       # Default Secondary Client Interface port
HOME_POSITION = [-37, -295, -42, 2.2, 2.2, 0]  # Default Kezdőpozíció
#DRAWING_HEIGHT = [-37, -295, -144.8, 2.2, 2.2, 0]  # Default drawing height
DEFAULT_SPEED = 0.1
DEFAULT_ACCEL = 0.5

class URScriptClient:
    """Egyszerű kliens a UR robot Secondary interfészéhez (30002)"""
    
    def __init__(self, host, port=30002):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
    
    def connect(self):
        """Kapcsolódás a robothoz"""
        print(f"Kapcsolódás a robothoz ({self.host}:{self.port})...")
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)  # 5 másodperces timeout
            self.socket.connect((self.host, self.port))
            self.connected = True
            print("Sikeresen kapcsolódva!")
            return True
        except Exception as e:
            print(f"Hiba a kapcsolódáskor: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            return False
    
    def send_script(self, script):
        """URScript küldése a robotnak"""
        if not self.connected or not self.socket:
            print("Nincs kapcsolat a robottal!")
            return False
        
        try:
            # Make sure the script ends with a newline
            if not script.endswith('\n'):
                script += '\n'
            
            print(f"Script küldése:\n{script.strip()}")
            # Küldés byte-ként, nem várunk választ
            self.socket.sendall(script.encode('utf-8'))
            
            # Nem próbálunk választ fogadni, mivel az bináris lehet
            # és nem feltétlenül szükséges a működéshez
            return True
        except Exception as e:
            print(f"Hiba a script küldésekor: {e}")
            self.disconnect()
            return False
    
    def disconnect(self):
        """Kapcsolat bontása"""
        if self.socket:
            try:
                self.socket.close()
                print("Kapcsolat bontva.")
            except:
                pass
            self.socket = None
            self.connected = False



def check_robot_status(robot_ip, dashboard_port=29999, rtde_port=30004):
    status_info = {
        "connected": False,
        "power_state": "Unknown",
        "robot_mode": "Unknown",
        "safety_status": "Unknown",
        "program_state": "Unknown",
        "joint_positions": None,
        "detailed_mode": None,
        "error_message": None
    }
    
    try:
        print(f"Connecting to Dashboard server at {robot_ip}:{dashboard_port}...")
        dash = Dashboard(robot_ip)
        dash.connect()
        
        status_info["connected"] = True
        
        robot_mode = dash.sendAndReceive("robotmode")
        status_info["detailed_mode"] = robot_mode
        
        if "RUNNING" in robot_mode:
            status_info["robot_mode"] = "Running"
        elif "IDLE" in robot_mode:
            status_info["robot_mode"] = "Idle"
        elif "POWER_OFF" in robot_mode:
            status_info["robot_mode"] = "Powered off"
        elif "BOOTING" in robot_mode:
            status_info["robot_mode"] = "Booting"
        
        program_state = dash.sendAndReceive("programstate")
        status_info["program_state"] = program_state
        
        power_state = dash.sendAndReceive("isPowerOn")
        status_info["power_state"] = power_state
        
        safety_status = dash.sendAndReceive("safetystatus")
        status_info["safety_status"] = safety_status
        
        dash.close()
        
    except Exception as e:
        print(f"Dashboard connection error: {e}")
        status_info["error_message"] = f"Dashboard error: {str(e)}"
    
    try:
        print(f"Connecting to RTDE at {robot_ip}:{rtde_port}...")
        
        rtde_config = 'rtdeState.xml'
        state_monitor = RtdeState(robot_ip, rtde_config, frequency=125)
        state_monitor.initialize()
        
        state = state_monitor.receive()
        
        if state is not None:
            status_info["connected"] = True
            
            if hasattr(state, 'robot_mode'):
                status_info["robot_mode"] = state_monitor.programState.get(state.robot_mode, "Unknown")
            
            if hasattr(state, 'safety_status'):
                safety_codes = {
                    1: "Normal",
                    2: "Reduced",
                    3: "Protective Stop",
                    4: "Recovery",
                    5: "Safeguard Stop",
                    6: "System Emergency Stop",
                    7: "Robot Emergency Stop",
                    8: "Violation",
                    9: "Fault",
                    10: "Validation",
                    11: "External Emergency Stop"
                }
                status_info["safety_status"] = safety_codes.get(state.safety_status, "Unknown")
            
            if hasattr(state, 'runtime_state'):
                status_info["program_state"] = state_monitor.programState.get(state.runtime_state, "Unknown")
            
            if hasattr(state, 'actual_q'):
                status_info["joint_positions"] = state.actual_q
        
        state_monitor.con.send_pause()
        state_monitor.con.disconnect()
        
    except Exception as e:
        print(f"RTDE connection error: {e}")
        if not status_info["error_message"]:
            status_info["error_message"] = f"RTDE error: {str(e)}"
        else:
            status_info["error_message"] += f" & RTDE error: {str(e)}"
    
    return status_info

def print_robot_status(status_info):
    """
    Print robot status information in a formatted way
    
    Args:
        status_info (dict): Dictionary containing robot status information
    """
    print("\n=== Robot Status ===")
    print(f"Connection: {'Connected' if status_info['connected'] else 'Disconnected'}")
    print(f"Power State: {status_info['power_state']}")
    print(f"Robot Mode: {status_info['robot_mode']}")
    print(f"Program State: {status_info['program_state']}")
    print(f"Safety Status: {status_info['safety_status']}")
    
    if status_info['detailed_mode']:
        print(f"Detailed Mode: {status_info['detailed_mode']}")
    
    if status_info['joint_positions']:
        print("\nJoint Positions:")
        for i, pos in enumerate(status_info['joint_positions']):
            print(f"  Joint {i+1}: {pos:.6f} rad")
    
    if status_info['error_message']:
        print(f"\nError: {status_info['error_message']}")
    print("===================\n")

def mm_to_m(position_mm):
    """Konvertálás milliméterből méterbe (csak az első 3 érték)"""
    position_m = list(position_mm)
    for i in range(3):
        position_m[i] = position_mm[i] / 1000.0
    return position_m

def move_to_position(client, position_mm, speed=DEFAULT_SPEED, acceleration=DEFAULT_ACCEL):
    """TCP mozgatása adott pozícióba (mm/rad)"""
    try:
        # Konvertálás milliméterből méterbe
        position_m = mm_to_m(position_mm)
        
        # Pozíció string formázása
        pos_str = "p[" + ",".join([f"{pos}" for pos in position_m]) + "]"
        
        # Egyszerű mozgási script létrehozása
        script = f"movel({pos_str}, a={acceleration}, v={speed})\n"
        
        # Script küldése
        return client.send_script(script)
    except Exception as e:
        print(f"Hiba a mozgás során: {e}")
        return False

def load_calibration_data():

    calibration_file = os.path.join(os.getcwd(), "calibration.json")
    
    if not os.path.exists(calibration_file):
        print(f"Calibration file not found at: {calibration_file}")
        print("Using default values for HOME_POSITION and DRAWING_HEIGHT")
        return False
    try:
        with open(calibration_file, 'r') as file:
            calibration_data = json.load(file)
        
        if "home_position" in calibration_data:
            global HOME_POSITION
            HOME_POSITION = calibration_data["home_position"]
            print(f"Loaded HOME_POSITION from calibration file: {HOME_POSITION}")
        else:
            print("No home_position data found in calibration file. Using default.")
            
        if "drawing_surface" in calibration_data:
            global DRAWING_HEIGHT
            DRAWING_HEIGHT = calibration_data["drawing_surface"]
            print(f"Loaded drawing height (Z) from calibration file: {DRAWING_HEIGHT}")
        else:
            print("No drawing_surface data found in calibration file. Using default.")

        if "default_speed" in calibration_data:
            global DEFAULT_SPEED
            DEFAULT_SPEED = calibration_data["default_speed"]
            print(f"Loaded default speed from calibration file: {DEFAULT_SPEED}")
        else:
            print("No default speed data found in calibration file. Using default.")

        if "default_acc" in calibration_data:
            global DEFAULT_ACCEL
            DEFAULT_ACCEL = calibration_data["default_acc"]
            print(f"Loaded default_acc from calibration file: {DEFAULT_ACCEL}")
        else:
            print("No default_acc data found in calibration file. Using default.")
        
        if "robot_ip" in calibration_data:
                global ROBOT_IP
                ROBOT_IP = calibration_data["robot_ip"]
                print(f"Loaded ROBOT_IP from calibration file: {ROBOT_IP}")
        else:
                print("No robot_ip found in calibration file. Using default.")
        if "robot_port" in calibration_data:
                global ROBOT_PORT
                ROBOT_PORT = calibration_data["robot_port"]
                print(f"Loaded ROBOT_PORT from calibration file: {ROBOT_PORT}")
        else:
                print("No robot_port found in calibration file. Using default.")
        if "rtde_port" in calibration_data:
            global RTDE_PORT
            RTDE_PORT = calibration_data["rtde_port"]
            print(f"Loaded RTDE_PORT from calibration file: {RTDE_PORT}")
        else: 
            print("No default rtde_port found in calibration file, using default.")
        if "dashboard_port" in calibration_data:
            global DASHBOARD_PORT
            DASHBOARD_PORT = calibration_data["dashboard_port"]
            print(f"Loaded DASHBOARD_PORT from calibration file: {DASHBOARD_PORT}")
        else: 
            print("No default dashboard_port found in calibration file, using default.") 
            
        print("Calibration data loaded successfully.")
        return True
        
    except json.JSONDecodeError:
        print(f"Error: The calibration file contains invalid JSON")
    except Exception as e:
        print(f"Error loading calibration data: {e}")
    
    
    print("Using default values for HOME_POSITION and DRAWING_HEIGHT")
    return False

def load_trajectory_from_json():
    #Ebben van benne az összes json trajektória
    drawing_folder = os.path.join(os.getcwd(), "drawings")
    
    json_files = glob.glob(os.path.join(drawing_folder, "*.json"))
    
    if not json_files:
        print("No JSON files found in the 'drawings' directory.")
        print(f"Drawings directory path: {drawing_folder}")
        return None
    
    print("\nAvailable trajectory files:")
    for i, file in enumerate(json_files, 1):
        print(f"{i}. {os.path.basename(file)}")
    
    while True:
        try:
            choice = input("\nSelect a file number (or 'q' to quit): ")
            
            if choice.lower() == 'q':
                print("Operation cancelled.")
                return None
            
            choice_idx = int(choice) - 1
            
            if 0 <= choice_idx < len(json_files):
                selected_file = json_files[choice_idx]
                break
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(json_files)}.")
        except ValueError:
            print("Please enter a valid number or 'q' to quit.")
    
    print(f"\nLoading trajectory from: {selected_file}")

    # Load the JSON data from the file
    try:
        with open(selected_file, 'r') as file:
            data = json.load(file)
        print(f"Successfully loaded '{os.path.basename(selected_file)}'")

        coordinates = [item[0] for item in data]
        
        print(f"\nExtracted {len(coordinates)} coordinates:")
        for i, coords in enumerate(coordinates):
            print(f"Point {i+1}: {coords}")
        return coordinates    
    
    except FileNotFoundError:
        print(f"Error: File '{selected_file}' not found")
    except json.JSONDecodeError:
        print(f"Error: The file '{os.path.basename(selected_file)}' does not contain valid JSON")
    except Exception as e:
        print(f"Error: An unexpected error occurred: {e}")
    
    return None

def main():
    # Létrehozzuk és csatlakoztatjuk a klienst
    client = URScriptClient(ROBOT_IP, ROBOT_PORT)
    
    if not client.connect():
        print("Nem sikerült kapcsolódni a robothoz. Kilépés...")
        return
    
    try:
        print("\n=== UR Robot Egyszerű Mozgásvezérlő ===")
        print("\nAz alábbi opciókat választhatod:")
        print("1. Mozgás a kezdőpozícióba")
        print("2. Rajzolás trajektória alapján")
        print("3. Robot állapot ellenőrzése")  # Új opció
        print("0. Kilépés\n")
        
        while True:
            choice = input("Válassz egy opciót (0-3): ")
            
            if choice == '0':
                print("Kilépés...")
                break
                
            elif choice == '1':
                print(HOME_POSITION)
                print("\nMozgás a kezdőpozícióba...")
                if move_to_position(client, HOME_POSITION):
                    print("Parancs elküldve! A robot mozog...")
                    time.sleep(1)  # Várunk, amíg a robot befejezi a mozgást

            elif choice == '2':
                trajectory = load_trajectory_from_json()
                
                if trajectory:
                    if move_to_position(client, HOME_POSITION):
                        print("Robot is at home")
                        input()
                    DRAWING_POS = HOME_POSITION.copy()
                    DRAWING_POS[2] = DRAWING_HEIGHT
                    if move_to_position(client, DRAWING_POS):
                        print("Rajzolasi magassagnal van a robot")
                        time.sleep(1)
                    print("Lent van a toll vege, rajzolas mehet")
                    input()
                    for i in range(len(trajectory)):
                        if i != 0 and i != len(trajectory) - 1:
                            trajectory[i][2] = DRAWING_HEIGHT
                        if move_to_position(client, trajectory[i]):
                            time.sleep(0.35)
                            print(f"Epp a(z) {i}. vonalat rajzolom")
                    time.sleep(1)
                    move_to_position(client, HOME_POSITION)
                    time.sleep(1)
                    print("Robot otthon van")
                
            elif choice == '3':
                print("\nRobot állapot ellenőrzése...")
                # Temporarily disconnect the script client to avoid port conflicts
                client.disconnect()
                
                # Check robot status
                robot_status = check_robot_status(ROBOT_IP)
                print_robot_status(robot_status)
                
                # Reconnect after status check
                if not client.connect():
                    print("Nem sikerült újrakapcsolódni a robothoz. Kilépés...")
                    return

            else:
                print("Érvénytelen választás. Próbáld újra.")
            
            input("\nNyomj Enter-t a folytatáshoz...")
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n=== UR Robot Egyszerű Mozgásvezérlő ===")
            print("\nAz alábbi opciókat választhatod:")
            print("1. Mozgás a kezdőpozícióba")
            print("2. Rajzolás trajektória alapján")
            print("3. Robot állapot ellenőrzése")  # Új opció
            print("0. Kilépés\n")
    
    except KeyboardInterrupt:
        print("\nProgram megszakítva.")
    
    finally:
        # Kapcsolat bontása
        client.disconnect()
        print("Program befejezve.")

if __name__ == "__main__":
    load_calibration_data()
    print("Calibration data has been loaded...")
    main()  