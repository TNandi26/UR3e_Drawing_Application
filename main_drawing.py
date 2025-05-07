#!/usr/bin/env python3
# UR3e Rajzoló Alkalmazás

import os
import sys
import time
import logging
import json
from Dashboard import Dashboard
from rtdeState import RtdeState
from interpreter.interpreter import InterpreterHelper

# Naplózás beállítása
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ur3e_drawing.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Robot konfiguráció
ROBOT_HOST = '192.168.0.2'  # Módosítsd a robot IP címének megfelelően!
RTDE_CONFIG = 'rtdeState.xml'  # Az RTDE konfigurációs fájl elérési útja

# Rajzolási konfiguráció
PEN_UP_Z = 0.07  # 7cm fel a papír felületétől - változtatható ha szükséges
PEN_DOWN_Z = 0.0  # A papír felületén (általában 0) - finomítható

# Kalibrációs fájl
CALIBRATION_FILE = 'calibration.json'  # Ide mentjük a kalibrációs adatokat

class UR3eDrawingApp:
    def __init__(self):
        self.dash = None
        self.rtde_state = None
        self.interpreter = None
        self.is_connected = False
        self.home_position = None
        self.surface_z = None
        
        # Kalibrációs adatok betöltése
        self.load_calibration()
    
    def connect_to_robot(self):
        """Kapcsolat létesítése a robottal és állapot ellenőrzése."""
        try:
            # Kapcsolódás a Dashboard szerverhez
            self.dash = Dashboard(ROBOT_HOST)
            self.dash.connect()
            
            # Kapcsolódás az RTDE-hez
            self.rtde_state = RtdeState(ROBOT_HOST, RTDE_CONFIG)
            self.rtde_state.initialize()
            
            # Kapcsolódás az Interpreter-hez
            self.interpreter = InterpreterHelper(ROBOT_HOST)
            self.interpreter.connect()
            
            # Ellenőrizzük, hogy a robot távoli vezérlés módban van-e
            remote_status = self.dash.sendAndReceive('is in remote control')
            if 'false' in remote_status:
                logger.error("A robot nincs távoli vezérlés módban. Kérlek, kapcsold be a távoli vezérlést.")
                return False
            
            # Robot mód ellenőrzése
            powermode = self.dash.sendAndReceive('robotmode')
            logger.info(f"Robot mód: {powermode}")
            
            # Biztonsági állapot ellenőrzése
            state = self.rtde_state.receive()
            if state:
                safety_status = state.safety_status
                logger.info(f"Biztonsági állapot: {safety_status}")
                if safety_status != 1:  # 1 a normál biztonsági állapot
                    logger.warning("A robot nem normál biztonsági állapotban van.")
            
            self.is_connected = True
            logger.info("Sikeresen kapcsolódva a UR3e robothoz.")
            return True
            
        except Exception as e:
            logger.error(f"Sikertelen kapcsolódás a robothoz: {str(e)}")
            self.disconnect_from_robot()
            return False
    
    def disconnect_from_robot(self):
        """Biztonságos lekapcsolódás a robotról."""
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
            logger.info("Lekapcsolódva a robotról.")
        except Exception as e:
            logger.error(f"Hiba a lekapcsolódás során: {str(e)}")
    
    def save_calibration(self):
        """Kalibrációs adatok mentése fájlba."""
        if self.surface_z is None or self.home_position is None:
            logger.error("Nincs kalibrációs adat a mentéshez.")
            return False
        
        calibration_data = {
            "surface_z": self.surface_z,
            "home_position": self.home_position
        }
        
        try:
            with open(CALIBRATION_FILE, 'w') as f:
                json.dump(calibration_data, f, indent=4)
            logger.info("Kalibrációs adatok sikeresen elmentve.")
            return True
        except Exception as e:
            logger.error(f"Sikertelen kalibrációs adat mentés: {str(e)}")
            return False
    
    def load_calibration(self):
        """Kalibrációs adatok betöltése fájlból."""
        if not os.path.exists(CALIBRATION_FILE):
            logger.info("Nem található kalibrációs fájl. Kalibrációra van szükség.")
            return False
        
        try:
            with open(CALIBRATION_FILE, 'r') as f:
                calibration_data = json.load(f)
            
            self.surface_z = calibration_data.get("surface_z")
            self.home_position = calibration_data.get("home_position")
            
            logger.info(f"Kalibrációs adatok betöltve: Felület Z = {self.surface_z}")
            logger.info(f"Home pozíció = {self.format_position(self.home_position)}")
            return True
        except Exception as e:
            logger.error(f"Sikertelen kalibrációs adat betöltés: {str(e)}")
            return False
    
    def format_position(self, position):
        """Pozíció formázása megjelenítéshez."""
        if position is None:
            return "Nincs beállítva"
        
        return f"[X: {position[0]:.4f}, Y: {position[1]:.4f}, Z: {position[2]:.4f}, Rx: {position[3]:.4f}, Ry: {position[4]:.4f}, Rz: {position[5]:.4f}]"
    
    def get_robot_status(self):
        """Átfogó robot állapot információk lekérése."""
        if not self.is_connected:
            return "Nincs kapcsolat a robottal."
        
        status_info = ""
        
        try:
            # Robot mód lekérése a Dashboard-ról
            robot_mode = self.dash.sendAndReceive('robotmode')
            status_info += f"Robot Mód: {robot_mode}\n"
            
            # Robot állapot lekérése a Dashboard-ról
            robot_status = self.dash.sendAndReceive('safetystatus')
            status_info += f"Biztonsági Állapot: {robot_status}\n"
            
            # Program állapot lekérése a Dashboard-ról
            program_state = self.dash.sendAndReceive('programstate')
            status_info += f"Program Állapot: {program_state}\n"
            
            # RTDE állapot lekérése
            state = self.rtde_state.receive()
            if state:
                runtime_state = state.runtime_state
                status_info += f"Futási Állapot: {self.rtde_state.programState.get(runtime_state, 'Ismeretlen')}\n"
                
                safety_status = state.safety_status
                status_info += f"Biztonsági Állapot (RTDE): {safety_status}\n"
                
                robot_mode_rtde = state.robot_mode
                status_info += f"Robot Mód (RTDE): {robot_mode_rtde}\n"
                
                # Aktuális TCP pozíció
                tcp_pose = state.actual_TCP_pose
                status_info += f"Aktuális TCP Pozíció: {self.format_position(tcp_pose)}\n"
                
                # Aktuális csukló pozíciók
                joint_positions = state.actual_q
                joint_str = ", ".join([f"{j:.4f}" for j in joint_positions])
                status_info += f"Csukló Pozíciók: [{joint_str}]\n"
            
            return status_info
            
        except Exception as e:
            logger.error(f"Sikertelen robot állapot lekérés: {str(e)}")
            return f"Hiba a robot állapot lekérésekor: {str(e)}"
    
    def release_brakes(self):
        """Robot fékek kioldása."""
        if not self.is_connected:
            logger.error("Nincs kapcsolat a robottal.")
            return False
            
        try:
            response = self.dash.sendAndReceive('brake release')
            logger.info(f"Fék kioldás válasz: {response}")
            
            # Várunk, hogy a fékek teljesen kioldjanak
            time.sleep(2)
            
            # Ellenőrizzük a robot módot, hogy megerősítsük a fékek kioldását
            state = self.rtde_state.receive()
            robot_mode = state.robot_mode
            
            if robot_mode == 7:  # Futási mód
                logger.info("Fékek sikeresen kioldva.")
                return True
            else:
                logger.warning(f"A robot nincs futási módban a fék kioldás után. Aktuális mód: {robot_mode}")
                return False
                
        except Exception as e:
            logger.error(f"Sikertelen fék kioldás: {str(e)}")
            return False
    
    def move_tcp(self, pose):
        """Robot TCP mozgatása a megadott pozícióba az interpreter használatával."""
        if not self.is_connected:
            logger.error("Nincs kapcsolat a robottal.")
            return False
            
        try:
            # Pozíció formázása megfelelő pontossággal
            pose_str = "p[" + ", ".join([f"{p:.6f}" for p in pose]) + "]"
            cmd = f"movel({pose_str})"
            cmd_id = self.interpreter.execute_command(cmd)
            
            # Várunk a parancs végrehajtására
            while self.interpreter.get_last_executed_id() < cmd_id:
                time.sleep(0.1)
                
            return True
        except Exception as e:
            logger.error(f"TCP mozgatási parancs sikertelen: {str(e)}")
            return False
    
    def get_current_position(self):
        """A robot aktuális TCP pozíciójának lekérése."""
        if not self.is_connected:
            logger.error("Nincs kapcsolat a robottal.")
            return None
            
        try:
            state = self.rtde_state.receive()
            if state is None:
                logger.error("Nem sikerült lekérni az aktuális pozíciót a robottól.")
                return None
                
            return state.actual_TCP_pose
        except Exception as e:
            logger.error(f"Sikertelen aktuális pozíció lekérés: {str(e)}")
            return None
    
    def get_current_joints(self):
        """A robot aktuális csukló pozícióinak lekérése."""
        if not self.is_connected:
            logger.error("Nincs kapcsolat a robottal.")
            return None
            
        try:
            state = self.rtde_state.receive()
            if state is None:
                logger.error("Nem sikerült lekérni az aktuális csukló pozíciókat a robottól.")
                return None
                
            return state.actual_q
        except Exception as e:
            logger.error(f"Sikertelen aktuális csukló pozíciók lekérése: {str(e)}")
            return None
    
    def calibrate_surface(self):
        """A rajzolási felület magasságának kalibrálása."""
        # FONTOS: Ez a kalibrálási lépés kritikus a pontos rajzoláshoz!
        if not self.is_connected:
            logger.error("Nincs kapcsolat a robottal.")
            return False
            
        print("\nFelület Kalibrálás")
        print("-------------------")
        print("Kérlek, mozgasd manuálisan a robotot úgy, hogy a toll hegye éppen érintse a papír felületét.")
        print("Ezután nyomj Enter-t a rajzolási felület magasságának beállításához.")
        input("Nyomj Enter-t, ha kész...")
        
        current_position = self.get_current_position()
        if current_position:
            self.surface_z = current_position[2]  # Z-koordináta
            logger.info(f"Felület magasság kalibrálva Z = {self.surface_z} értékre")
            
            # Ezt a pozíciót (felemelt tollal) állítjuk be kezdőpozíciónak
            raised_position = current_position.copy()
            raised_position[2] = self.surface_z + PEN_UP_Z  # Toll felemelése
            self.home_position = raised_position
            
            # Kalibrációs adatok mentése
            self.save_calibration()
            
            # Toll felemelése a kezdőpozícióba
            return self.move_tcp(self.home_position)
        return False
    
    def pen_up(self):
        """Toll felemelése a papírról."""
        if not self.is_connected or self.surface_z is None:
            logger.error("Nincs kapcsolat vagy a felület nincs kalibrálva.")
            return False
            
        current_position = self.get_current_position()
        if current_position:
            # Megtartjuk az aktuális XY pozíciót, csak a Z-t emeljük
            new_position = current_position.copy()
            new_position[2] = self.surface_z + PEN_UP_Z
            return self.move_tcp(new_position)
        return False
    
    def pen_down(self):
        """Toll leengedése a papírra, biztonsági ellenőrzéssel."""
        # VIGYÁZAT: A toll leengedése óvatosan történik, nehogy kárt tegyünk a papírban vagy a tollban
        if not self.is_connected or self.surface_z is None:
            logger.error("Nincs kapcsolat vagy a felület nincs kalibrálva.")
            return False
            
        current_position = self.get_current_position()
        if current_position:
            # Megtartjuk az aktuális XY pozíciót, csak a Z-t engedjük le
            new_position = current_position.copy()
            new_position[2] = self.surface_z + PEN_DOWN_Z
            
            # Óvatosan, kis lépésekben közelítünk a biztonsági ellenőrzéshez
            steps = 10
            current_z = current_position[2]
            target_z = new_position[2]
            
            for i in range(1, steps + 1):
                intermediate_z = current_z - (current_z - target_z) * (i / steps)
                intermediate_position = new_position.copy()
                intermediate_position[2] = intermediate_z
                
                if not self.move_tcp(intermediate_position):
                    return False
                
                print(f"Toll leeresztése - {i}/{steps}. lépés")
                input("Nyomj Enter-t a leeresztés folytatásához...")
            
            logger.info("Toll leeresztése sikeresen befejezve.")
            return True
        return False
    
    def move_to_home(self):
        """A robot mozgatása a kezdőpozícióba."""
        if not self.home_position:
            logger.error("A kezdőpozíció nincs beállítva.")
            return False
            
        return self.move_tcp(self.home_position)
    
    def test_mobility(self):
        """Robot mozgékonyságának tesztelése egyszerű mintákkal."""
        # TIPP: Ez a teszt segít ellenőrizni, hogy a robot megfelelően mozog-e minden irányban
        if not self.is_connected:
            logger.error("Nincs kapcsolat a robottal.")
            return False
            
        try:
            logger.info("Mozgékonyság teszt indítása...")
            
            # Aktuális pozíció mint kiindulópont
            start_position = self.get_current_position()
            if not start_position:
                return False
                
            # Toll felemelése
            current_position = start_position.copy()
            if self.surface_z:
                current_position[2] = self.surface_z + PEN_UP_Z
                if not self.move_tcp(current_position):
                    return False
            
            print("Mozgékonyság teszt indítása Z-tengely mozgással...")
            input("Nyomj Enter-t a Z-tengely teszt indításához...")
            
            # 1. teszt: Fel-le mozgás (Z-tengely)
            logger.info("Z-tengely mozgás tesztelése...")
            test_position = current_position.copy()
            test_position[2] -= 0.02  # 2cm le (de még mindig fent a felülettől)
            if not self.move_tcp(test_position):
                return False
                
            print("2cm-t lefelé mozdult. Nyomj Enter-t a felfelé mozgáshoz...")
            input()
                
            test_position[2] += 0.04  # 4cm fel
            if not self.move_tcp(test_position):
                return False
                
            print("4cm-t felfelé mozdult. Nyomj Enter-t a kezdeti magassághoz visszatéréshez...")
            input()
                
            test_position[2] -= 0.02  # Vissza a kezdeti magasságra
            if not self.move_tcp(test_position):
                return False
                
            print("Vissza a kezdeti magasságra. Nyomj Enter-t az X-tengely teszt indításához...")
            input()
                
            # 2. teszt: Balra-jobbra mozgás (X-tengely)
            logger.info("X-tengely mozgás tesztelése...")
            test_position = current_position.copy()
            test_position[0] += 0.03  # 3cm jobbra
            if not self.move_tcp(test_position):
                return False
                
            print("3cm-t jobbra mozdult. Nyomj Enter-t balra mozgáshoz...")
            input()
                
            test_position[0] -= 0.06  # 6cm balra
            if not self.move_tcp(test_position):
                return False
                
            print("6cm-t balra mozdult. Nyomj Enter-t középre visszatéréshez...")
            input()
                
            test_position[0] += 0.03  # Vissza középre
            if not self.move_tcp(test_position):
                return False
                
            print("Vissza középre. Nyomj Enter-t az Y-tengely teszt indításához...")
            input()
                
            # 3. teszt: Előre-hátra mozgás (Y-tengely)
            logger.info("Y-tengely mozgás tesztelése...")
            test_position = current_position.copy()
            test_position[1] += 0.03  # 3cm előre
            if not self.move_tcp(test_position):
                return False
                
            print("3cm-t előre mozdult. Nyomj Enter-t a hátra mozgáshoz...")
            input()
                
            test_position[1] -= 0.06  # 6cm hátra
            if not self.move_tcp(test_position):
                return False
                
            print("6cm-t hátra mozdult. Nyomj Enter-t a középre visszatéréshez...")
            input()
                
            test_position[1] += 0.03  # Vissza középre
            if not self.move_tcp(test_position):
                return False
                
            print("Vissza a középre. Nyomj Enter-t a kör teszt indításához...")
            input()
                
            # 4. teszt: Kör mozgás
            logger.info("Körmozgás tesztelése...")
            radius = 0.03  # 3cm sugár
            center_x, center_y = current_position[0], current_position[1]
            
            for angle in range(0, 360, 45):  # 45 fokos lépések
                import math
                rad = math.radians(angle)
                test_position = current_position.copy()
                test_position[0] = center_x + radius * math.cos(rad)
                test_position[1] = center_y + radius * math.sin(rad)
                
                print(f"Mozgás a kör {angle}° pontjához. Nyomj Enter-t a folytatáshoz...")
                input()
                
                if not self.move_tcp(test_position):
                    return False
            
            # Visszatérés a kezdőpozícióba
            print("Kör teszt befejezve. Nyomj Enter-t a kezdőpozícióba visszatéréshez...")
            input()
            
            if not self.move_tcp(current_position):
                return False
                
            logger.info("Mozgékonyság teszt sikeresen befejezve.")
            return True
        except Exception as e:
            logger.error(f"Mozgékonyság teszt sikertelen: {str(e)}")
            return False
    
    def load_trajectory(self, trajectory_file):
        """Trajektória betöltése JSON fájlból."""
        if not os.path.exists(trajectory_file):
            logger.error(f"A trajektória fájl {trajectory_file} nem található.")
            return None
            
        try:
            with open(trajectory_file, 'r') as f:
                trajectory = json.load(f)
            
            logger.info(f"Trajektória betöltve {len(trajectory)} ponttal a {trajectory_file} fájlból.")
            return trajectory
        except Exception as e:
            logger.error(f"Sikertelen trajektória betöltés: {str(e)}")
            return None
    
    def execute_trajectory(self, trajectory):
        """Előre elkészített robot trajektória végrehajtása kézi megerősítéssel a mozgások között."""
        # Ez a függvény minden lépésnél megvárja a felhasználó megerősítését, ami biztonságosabb teszt közben
        if not self.is_connected or not trajectory:
            logger.error("Nincs kapcsolat vagy üres a trajektória.")
            return False
            
        try:
            logger.info(f"Trajektória végrehajtása {len(trajectory)} ponttal...")
            print(f"A trajektória {len(trajectory)} pontot tartalmaz.")
            input("Nyomj Enter-t a végrehajtás indításához...")
            
            # Toll felemelésével kezdünk
            if not self.pen_up():
                return False
                
            print("Toll felemelve. Készen áll a rajzolásra.")
            input("Nyomj Enter-t a folytatáshoz...")
                
            pen_is_down = False
            
            for i, (cmd, pose) in enumerate(trajectory):
                print(f"{i+1}/{len(trajectory)} pont végrehajtása: {cmd}")
                
                if cmd == 'move':
                    # Move parancsoknál gondoskodunk, hogy a toll fel legyen emelve
                    if pen_is_down:
                        print("Toll felemelése...")
                        if not self.pen_up():
                            return False
                        pen_is_down = False
                    
                    # Mozgás a pozícióba
                    print(f"Mozgás a következő pozícióba: {self.format_position(pose)}")
                    if not self.move_tcp(pose):
                        return False
                
                elif cmd == 'line':
                    # Ha a toll még nincs lent, először odamegyünk és leeresztjük
                    if not pen_is_down:
                        # Először felemelt tollal megyünk az XY pozícióba
                        up_pose = pose.copy()
                        up_pose[2] = self.surface_z + PEN_UP_Z
                        
                        print(f"Mozgás a pozícióba felemelt tollal: {self.format_position(up_pose)}")
                        if not self.move_tcp(up_pose):
                            return False
                            
                        # Aztán leeresztjük a tollat
                        print("Toll leeresztése...")
                        if not self.pen_down():
                            return False
                            
                        pen_is_down = True
                    
                    # Folytatjuk a rajzolást leengedett tollal
                    print(f"Rajzolás a következő pozícióba: {self.format_position(pose)}")
                    if not self.move_tcp(pose):
                        return False
                
                # Megerősítést kérünk a folytatáshoz
                if i < len(trajectory) - 1:  # Ne kérdezzünk az utolsó pont után
                    input("Nyomj Enter-t a következő pontra lépéshez...")
            
            # Toll felemelése a végén
            if pen_is_down:
                print("Rajzolás befejezve. Toll felemelése...")
                if not self.pen_up():
                    return False
            
            # Visszatérés a kezdőpozícióba
            print("Mozgás a kezdőpozícióba...")
            if not self.move_to_home():
                return False
                
            logger.info("Trajektória végrehajtás sikeresen befejezve.")
            print("Trajektória végrehajtás sikeresen befejezve.")
            return True
        except Exception as e:
            logger.error(f"Trajektória végrehajtás sikertelen: {str(e)}")
            # Biztonsági intézkedésként felemeljük a tollat hiba esetén
            try:
                self.pen_up()
            except:
                pass
            return False

def create_gui(app):
    """Egyszerű parancssoros felhasználói felület az alkalmazáshoz."""
    # Azonnal kapcsolódunk a robothoz
    if not app.is_connected:
        print("Kapcsolódás a robothoz...")
        if app.connect_to_robot():
            print("Sikeresen kapcsolódva a UR3e robothoz!")
        else:
            print("Sikertelen kapcsolódás a robothoz. Ellenőrizd a beállításokat és a robot állapotát.")
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\n===== UR3e Rajzoló Alkalmazás =====")
        print("\nAktuális Állapot:")
        print(f"Kapcsolódva a robothoz: {'Igen' if app.is_connected else 'Nem'}")
        
        if app.is_connected:
            # Aktuális állapot lekérése
            try:
                state = app.rtde_state.receive()
                if state:
                    print(f"Robot mód: {app.rtde_state.programState.get(state.runtime_state, 'Ismeretlen')}")
                    print(f"Biztonsági állapot: {state.safety_status}")
            except:
                pass
                
        print(f"Felület kalibrálva: {'Igen' if app.surface_z is not None else 'Nem'}")
        print(f"Kezdőpozíció beállítva: {'Igen' if app.home_position is not None else 'Nem'}")
        if app.home_position:
            print(f"Kezdőpozíció: {app.format_position(app.home_position)}")
        
        print("\nVálassz egy opciót:")
        print("1. Robot Fékek Kioldása")
        print("2. Rajzolási Felület Kalibrálása")
        print("3. Mozgékonyság Teszt")
        print("4. Rajzolás Végrehajtása Trajektóriából")
        print("5. Részletes Robot Állapot Ellenőrzése")
        print("0. Kilépés")
        
        choice = input("\nAdd meg a választásodat (0-5): ")
        
        if choice == '0':
            if app.is_connected:
                app.disconnect_from_robot()
            print("\nKilépés az alkalmazásból...")
            break
            
        elif choice == '1':
            if not app.is_connected:
                print("\nNincs kapcsolat a robottal.")
            else:
                print("\nRobot fékek kioldása...")
                if app.release_brakes():
                    print("Fékek sikeresen kioldva!")
                else:
                    print("Sikertelen fék kioldás. Ellenőrizd a naplót a részletekért.")
            input("\nNyomj Enter-t a folytatáshoz...")
            
        elif choice == '2':
            if not app.is_connected:
                print("\nNincs kapcsolat a robottal.")
            else:
                print("\nRajzolási felület kalibrálása...")
                if app.calibrate_surface():
                    print("Felület sikeresen kalibrálva!")
                    print(f"Felület Z = {app.surface_z:.4f}")
                    print(f"Kezdőpozíció = {app.format_position(app.home_position)}")
                else:
                    print("Kalibrálás sikertelen. Ellenőrizd a naplót a részletekért.")
            input("\nNyomj Enter-t a folytatáshoz...")
            
        elif choice == '3':
            if not app.is_connected:
                print("\nNincs kapcsolat a robottal.")
            elif app.surface_z is None:
                print("\nA felület nincs kalibrálva. Kérlek, először kalibráld.")
            else:
                print("\nMozgékonyság teszt futtatása...")
                if app.test_mobility():
                    print("Mozgékonyság teszt sikeresen befejezve!")
                else:
                    print("Mozgékonyság teszt sikertelen. Ellenőrizd a naplót a részletekért.")
            input("\nNyomj Enter-t a folytatáshoz...")
            
        elif choice == '4':
            if not app.is_connected:
                print("\nNincs kapcsolat a robottal.")
            elif app.surface_z is None:
                print("\nA felület nincs kalibrálva. Kérlek, először kalibráld.")
            else:
                trajectory_file = input("\nAdd meg a trajektória fájl elérési útját (.json): ")
                if os.path.exists(trajectory_file):
                    print(f"\nTrajektória betöltése innen: {trajectory_file}...")
                    trajectory = app.load_trajectory(trajectory_file)
                    
                    if trajectory:
                        print(f"Trajektória betöltve {len(trajectory)} ponttal.")
                        print("Készen áll a rajzolásra.")
                        
                        confirm = input("Folytatod a rajzolást? (i/n): ")
                        if confirm.lower() == 'i':
                            if app.execute_trajectory(trajectory):
                                print("Rajzolás sikeresen befejezve!")
                            else:
                                print("Rajzolás sikertelen. Ellenőrizd a naplót a részletekért.")
                    else:
                        print("Sikertelen trajektória betöltés. Ellenőrizd a fájl formátumát.")
                else:
                    print(f"A fájl {trajectory_file} nem található.")
            input("\nNyomj Enter-t a folytatáshoz...")
            
        elif choice == '5':
            if not app.is_connected:
                print("\nNincs kapcsolat a robottal.")
            else:
                print("\nRészletes Robot Állapot:")
                print("=====================")
                status_info = app.get_robot_status()
                print(status_info)
            input("\nNyomj Enter-t a folytatáshoz...")
            
        else:
            print("\nÉrvénytelen választás. Próbáld újra.")
            input("\nNyomj Enter-t a folytatáshoz...")

if __name__ == "__main__":
    app = UR3eDrawingApp()
    create_gui(app)