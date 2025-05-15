#!/usr/bin/env python3
# UR Robot Rajzoló Vezérlő - Magyar verzió
# Másodlagos kliens interfészt használ (port 30002) a vezérléshez
# Dashboard-ot csak állapotfigyelésre használja

import socket
import time
import sys
from pathlib import Path
import os
import logging
import json
import math
from Dashboard import Dashboard

# Naplózás beállítása részletes információkkal
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ur_drawing.log", encoding='utf-8'),  # UTF-8 kódolás a magyar karakterekhez
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Alkalmazás mappa struktúra
MAIN_FOLDER = os.path.join("C:", "Users", "Nándi", "Desktop", "Python_programok", "Onlab")
DRAWINGS_FOLDER = os.path.join(MAIN_FOLDER, "drawings")
CALIBRATION_FILE = os.path.join(MAIN_FOLDER, "calibration.json")

# Robot konfiguráció
ROBOT_IP = '10.150.0.1'  # Robot IP címe
SECONDARY_PORT = 30002    # Másodlagos kliens interfész port
DASHBOARD_PORT = 29999    # Dashboard szerver port

# Működési konstansok
DEFAULT_MOVE_SPEED = 0.1       # Alapértelmezett mozgási sebesség
DEFAULT_DRAW_SPEED = 0.05      # Alapértelmezett rajzolási sebesség
DEFAULT_WAIT_TIME = 5          # Alapértelmezett várakozási idő mozgásoknál (másodperc)
DEFAULT_SEGMENTS = 10          # Alapértelmezett szegmensek száma biztonsági módban
DEFAULT_PEN_UP_OFFSET = 10     # Alapértelmezett toll felemelési távolság (mm)
DEFAULT_PEN_DOWN_OFFSET = 0    # Alapértelmezett toll leeresztési távolság (mm)
COMMAND_DELAY = 0.5            # Parancsok közötti késleltetés (másodperc)
MIN_SAFETY_DISTANCE = 5        # Minimális biztonsági távolság a papír felületétől (mm)

class URScriptClient:
    """UR robot Másodlagos interfészéhez (30002) kliens"""
    
    def __init__(self, host, port=30002):
        # Robot kapcsolódási paraméterek
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
    
    def connect(self):
        """Kapcsolódás a robot másodlagos interfészéhez
        
        Returns:
            bool: True ha a kapcsolódás sikeres, False ha nem
        """
        logger.info(f"Kapcsolódás a robothoz: {self.host}:{self.port}...")
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)  # 5 másodperces időtúllépés
            self.socket.connect((self.host, self.port))
            self.connected = True
            logger.info("Sikeresen kapcsolódva a Másodlagos Interfészhez!")
            return True
        except Exception as e:
            logger.error(f"Kapcsolódási hiba: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            return False
    
    def send_script(self, script):
        """URScript küldése a robotnak
        
        Args:
            script (str): URScript kód
            
        Returns:
            bool: True ha sikeresen elküldve, False ha nem
        """
        if not self.connected or not self.socket:
            logger.error("Nincs kapcsolat a robottal!")
            return False
        
        try:
            # Bizonyosodjunk meg róla, hogy a szkript újsorral végződik
            if not script.endswith('\n'):
                script += '\n'
            
            logger.info(f"Script küldése: {script.strip()}")
            # Küldés bájt-ként
            self.socket.sendall(script.encode('utf-8'))
            return True
        except Exception as e:
            logger.error(f"Hiba a script küldésekor: {e}")
            self.disconnect()
            return False
    
    def disconnect(self):
        """Kapcsolat bontása a robot másodlagos interfészével"""
        if self.socket:
            try:
                self.socket.close()
                logger.info("Másodlagos Interfész kapcsolat lezárva.")
            except:
                pass
            self.socket = None
            self.connected = False


class URDrawingController:
    """Fő vezérlő a UR robot rajzolási műveleteihez"""
    
    def __init__(self, robot_ip=ROBOT_IP):
        # Robot kapcsolódási paraméterek
        self.robot_ip = robot_ip
        self.secondary_client = None
        self.dashboard = None
        self.is_connected = False
        
        # Működési paraméterek
        self.safety_mode = True  # Biztonsági mód alapértelmezetten bekapcsolva
        
        # Kalibrációs értékek (json-ból lesznek betöltve)
        self.home_position = None
        self.paper_surface_z = None
        self.pen_up_offset = DEFAULT_PEN_UP_OFFSET
        self.pen_down_offset = DEFAULT_PEN_DOWN_OFFSET
        self.paper_corners = None
        self.safe_move_segments = DEFAULT_SEGMENTS
        self.drawing_speed = DEFAULT_DRAW_SPEED
        self.movement_speed = DEFAULT_MOVE_SPEED
        
        # Az utolsó ismert pozíció tárolása
        self.last_known_position = None
        
        # Kalibráció betöltése
        self.load_calibration()
        
    def load_calibration(self, filename=CALIBRATION_FILE):
        """Kalibrációs adatok betöltése JSON fájlból
        
        Args:
            filename (str): A kalibrációs JSON fájl útvonala
            
        Returns:
            bool: True ha sikeresen betöltve, False ha nem
        """
        try:
            # Megpróbáljuk betölteni a kalibrációs fájlt
            with open(filename, 'r') as f:
                calibration = json.load(f)
                
            # Értékek betöltése a kalibrációs fájlból
            self.home_position = calibration.get("home_position")
            self.paper_surface_z = calibration.get("paper_surface_z")
            self.pen_up_offset = calibration.get("pen_up_offset", DEFAULT_PEN_UP_OFFSET)
            self.pen_down_offset = calibration.get("pen_down_offset", DEFAULT_PEN_DOWN_OFFSET)
            self.paper_corners = calibration.get("paper_corners")
            self.safe_move_segments = calibration.get("safe_move_segments", DEFAULT_SEGMENTS)
            self.drawing_speed = calibration.get("drawing_speed", DEFAULT_DRAW_SPEED)
            self.movement_speed = calibration.get("movement_speed", DEFAULT_MOVE_SPEED)
            
            # Az utolsó ismert pozíciót inicializáljuk a kezdőpozícióra
            self.last_known_position = self.home_position
            
            logger.info(f"Kalibráció betöltve innen: {filename}")
            logger.info(f"Kezdőpozíció: {self.format_position(self.home_position)}")
            logger.info(f"Papír felszín Z: {self.paper_surface_z}")
            logger.info(f"Biztonsági mozgások szegmensszáma: {self.safe_move_segments}")
            
            return True
        except Exception as e:
            logger.error(f"Hiba a kalibráció betöltésekor innen: {filename}: {e}")
            # Alapértelmezett értékek beállítása, ha a fájl nem tölthető be
            self.home_position = [-37, -295, -10, 2.2, 2.2, 0]
            self.paper_surface_z = -144
            self.pen_up_offset = DEFAULT_PEN_UP_OFFSET
            self.pen_down_offset = DEFAULT_PEN_DOWN_OFFSET
            self.paper_corners = [
                [-173, -329, -132, 2.2, 2.2, 0],
                [108, -329, -132, 2.2, 2.2, 0],
                [71, -183, -90, 2.2, 2.2, 0],
                [-173, -183, -90, 2.2, 2.2, 0]
            ]
            self.safe_move_segments = DEFAULT_SEGMENTS
            self.drawing_speed = DEFAULT_DRAW_SPEED
            self.movement_speed = DEFAULT_MOVE_SPEED
            
            # Az utolsó ismert pozíciót inicializáljuk a kezdőpozícióra
            self.last_known_position = self.home_position
            
            logger.info("Alapértelmezett kalibrációs értékek használata")
            return False
    
    def connect(self):
        """Kapcsolódás a robothoz a dashboard és másodlagos interfész használatával
        
        Returns:
            bool: True ha a kapcsolódás sikeres, False ha nem
        """
        try:
            # Kapcsolódás a Dashboard-hoz
            logger.info(f"Kapcsolódás a Dashboard szerverhez: {self.robot_ip}:{DASHBOARD_PORT}")
            self.dashboard = Dashboard(self.robot_ip)
            self.dashboard.connect()
            logger.info("Kapcsolódva a Dashboard szerverhez")
            
            # Kapcsolódás a Másodlagos interfészhez
            logger.info(f"Kapcsolódás a Másodlagos Interfészhez: {self.robot_ip}:{SECONDARY_PORT}")
            self.secondary_client = URScriptClient(self.robot_ip, SECONDARY_PORT)
            if not self.secondary_client.connect():
                logger.error("Nem sikerült kapcsolódni a Másodlagos Interfészhez")
                self.disconnect()
                return False
            
            # Ellenőrizzük, hogy a robot távvezérlési módban van-e
            logger.info("Távvezérlési mód ellenőrzése...")
            remote_status = self.dashboard.sendAndReceive('is in remote control')
            if 'false' in remote_status:
                logger.warning("A robot nincs távvezérlési módban. Egyes parancsok nem működhetnek.")
                print("FIGYELMEZTETÉS: A robot nincs távvezérlési módban. Kérlek, engedélyezd a távvezérlést.")
            
            # Robot mód ellenőrzése
            logger.info("Robot mód lekérdezése...")
            robot_mode = self.dashboard.sendAndReceive('robotmode')
            logger.info(f"Robot mód: {robot_mode}")
            
            # Biztonsági állapot ellenőrzése
            logger.info("Biztonsági állapot ellenőrzése...")
            safety_status = self.dashboard.sendAndReceive('safetystatus')
            logger.info(f"Biztonsági állapot: {safety_status}")
            
            self.is_connected = True
            logger.info("Sikeresen kapcsolódva a robothoz!")
            return True
            
        except Exception as e:
            logger.error(f"Kapcsolódási hiba: {e}")
            self.disconnect()
            return False
    
    def disconnect(self):
        """Kapcsolat bontása az összes robot interfésszel"""
        try:
            logger.info("Kapcsolatok bontása...")
            if self.dashboard:
                self.dashboard.close()
                self.dashboard = None
                logger.info("Dashboard kapcsolat lezárva")
            
            if self.secondary_client:
                self.secondary_client.disconnect()
                self.secondary_client = None
                logger.info("Másodlagos interfész kapcsolat lezárva")
                
            self.is_connected = False
            logger.info("Kapcsolatok sikeresen lezárva")
        except Exception as e:
            logger.error(f"Hiba a kapcsolat bontásakor: {e}")
    
    def format_position(self, position):
        """Pozíció formázása megjelenítéshez
        
        Args:
            position (list): 6D vektor [x, y, z, rx, ry, rz]
            
        Returns:
            str: Formázott pozíció string
        """
        if position is None:
            return "Nincs beállítva"
        
        return f"[X: {position[0]:.1f}mm, Y: {position[1]:.1f}mm, Z: {position[2]:.1f}mm, Rx: {position[3]:.2f}, Ry: {position[4]:.2f}, Rz: {position[5]:.2f}]"
    
    def calculate_distance(self, pos1, pos2):
        """Kiszámítja a két pozíció közötti térbeli távolságot
        
        Args:
            pos1 (list): Első pozíció [x, y, z, rx, ry, rz]
            pos2 (list): Második pozíció [x, y, z, rx, ry, rz]
            
        Returns:
            float: Távolság mm-ben
        """
        if pos1 is None or pos2 is None:
            return 0.0
            
        dx = pos2[0] - pos1[0]
        dy = pos2[1] - pos1[1]
        dz = pos2[2] - pos1[2]
        
        return math.sqrt(dx*dx + dy*dy + dz*dz)
    
    def toggle_safety_mode(self):
        """Biztonsági mód be/kikapcsolása
        
        Returns:
            bool: Új biztonsági mód állapot (True = bekapcsolva, False = kikapcsolva)
        """
        self.safety_mode = not self.safety_mode
        logger.info(f"Biztonsági mód {'bekapcsolva' if self.safety_mode else 'kikapcsolva'}")
        return self.safety_mode
    
    def get_robot_status(self):
        """Átfogó robot állapot információk lekérése
        
        Returns:
            str: Többsoros állapot információ
        """
        if not self.is_connected:
            return "Nincs kapcsolat a robottal."
        
        status_info = ""
        
        try:
            # Robot mód lekérése a Dashboard-ról
            logger.info("Robot mód lekérdezése...")
            robot_mode = self.dashboard.sendAndReceive('robotmode')
            status_info += f"Robot Mód: {robot_mode}\n"
            
            # Biztonsági állapot lekérése a Dashboard-ról
            logger.info("Biztonsági állapot lekérdezése...")
            safety_status = self.dashboard.sendAndReceive('safetystatus')
            status_info += f"Biztonsági Állapot: {safety_status}\n"
            
            # Program állapot lekérése a Dashboard-ról
            logger.info("Program állapot lekérdezése...")
            program_state = self.dashboard.sendAndReceive('programstate')
            status_info += f"Program Állapot: {program_state}\n"
            
            # Betöltött program lekérése
            logger.info("Betöltött program lekérdezése...")
            loaded_program = self.dashboard.sendAndReceive('get loaded program')
            status_info += f"Betöltött Program: {loaded_program}\n"
            
            # Másodlagos interfész állapota
            status_info += f"Másodlagos Interfész: {'Kapcsolódva' if self.secondary_client and self.secondary_client.connected else 'Nincs kapcsolat'}\n"
            
            # Biztonsági mód állapota
            status_info += f"Biztonsági Mód: {'Bekapcsolva' if self.safety_mode else 'Kikapcsolva'}\n"
            
            # Kalibrációs információk
            status_info += f"Papír Felszín Z: {self.paper_surface_z}mm\n"
            status_info += f"Kezdőpozíció: {self.format_position(self.home_position)}\n"
            
            # Utolsó ismert pozíció
            status_info += f"Utolsó Ismert Pozíció: {self.format_position(self.last_known_position)}\n"
            
            logger.info("Robot állapotinformációk sikeresen lekérdezve")
            return status_info
            
        except Exception as e:
            logger.error(f"Nem sikerült lekérdezni a robot állapotát: {e}")
            return f"Hiba a robot állapot lekérdezésekor: {e}"
    
    def mm_to_m(self, position_mm):
        """Pozíció konvertálása mm-ből m-be az első 3 koordinátánál
        
        Args:
            position_mm (list): Pozíció mm-ben [x, y, z, rx, ry, rz]
            
        Returns:
            list: Pozíció, az első 3 koordináta méterben [x, y, z, rx, ry, rz]
        """
        # Másolatot készítünk, hogy ne módosítsuk az eredetit
        position_m = list(position_mm)
        for i in range(3):
            position_m[i] = position_mm[i] / 1000.0
        return position_m
    
    def ensure_safe_z(self, target_pose):
        """Biztosítja, hogy a Z koordináta ne menjen a papír felszíne alá egy biztonsági távolsággal
        
        Args:
            target_pose (list): Célpozíció [x, y, z, rx, ry, rz]
            
        Returns:
            list: Korrigált célpozíció biztonságos Z értékkel
        """
        # Másolatot készítünk
        safe_pose = list(target_pose)
        
        # Ellenőrizzük, hogy a papír felszíne + biztonsági távolság alatt van-e
        min_safe_z = self.paper_surface_z + MIN_SAFETY_DISTANCE
        
        # Ha a célpont Z értéke a minimum biztonságos érték alatt van (és nem rajzolási művelet)
        if safe_pose[2] < min_safe_z and safe_pose[2] != (self.paper_surface_z + self.pen_down_offset):
            logger.warning(f"Túl alacsony Z érték ({safe_pose[2]}), korrigálás a minimum biztonságos értékre: {min_safe_z}")
            safe_pose[2] = min_safe_z
        
        return safe_pose
    
    def move_tcp(self, target_pose_mm, speed=None, segments=None, is_drawing=False):
        """Robot TCP mozgatása a célpozícióba (mm-ben)
        
        Args:
            target_pose_mm (list): 6D vektor [x, y, z, rx, ry, rz] mm-ben és radiánban
            speed (float, optional): Mozgási sebesség (0-1)
            segments (int, optional): Szegmensek száma a mozgáshoz (biztonsági mód)
            is_drawing (bool, optional): Rajzolási művelet-e (felülírja a Z biztonsági ellenőrzést)
            
        Returns:
            bool: True ha a mozgás sikeres, False ha nem
        """
        if not self.is_connected:
            logger.error("Nincs kapcsolat a robottal")
            return False
        
        # Biztonsági ellenőrzés a Z koordinátára
        if not is_drawing:
            target_pose_mm = self.ensure_safe_z(target_pose_mm)
        
        # Alapértelmezett értékek használata, ha nincs megadva
        move_speed = speed if speed is not None else self.movement_speed
        move_segments = segments if segments is not None else (self.safe_move_segments if self.safety_mode else 1)
        
        # Naplózzuk a mozgási parancs részleteit
        logger.info(f"TCP mozgatása a következő pozícióba: {self.format_position(target_pose_mm)}")
        logger.info(f"Sebesség: {move_speed}, Szegmensek: {move_segments}, Rajzolás: {'Igen' if is_drawing else 'Nem'}")
        
        try:
            # Ellenőrizzük, hogy van-e kezdő pozíciónk
            if self.last_known_position is None:
                logger.warning("Nincs ismert kezdőpozíció, a kezdőpozíciót használjuk")
                self.last_known_position = self.home_position
            
            # Ha a biztonsági mód ki van kapcsolva vagy csak 1 szegmens
            if move_segments <= 1:
                logger.info("Egyszeri mozgás végrehajtása")
                # Konvertáljuk mm-ből m-be az első 3 koordinátát
                target_pose_m = self.mm_to_m(target_pose_mm)
                
                # Formázzuk a pozíciót megfelelő pontossággal
                pose_str = "p[" + ", ".join([f"{p:.6f}" for p in target_pose_m]) + "]"
                
                # URScript parancs movel használatával
                script = f"movel({pose_str}, a=0.5, v={move_speed})\n"
                
                logger.info(f"Mozgatási parancs küldése: {script.strip()}")
                
                # Script küldése a Másodlagos Interfészen keresztül
                success = self.secondary_client.send_script(script)
                
                if success:
                    # Mivel nem kapunk visszajelzést, várunk, hogy a mozgás befejeződjön
                    wait_time = DEFAULT_WAIT_TIME  # Alapértelmezett várakozási idő másodpercben
                    
                    # Várakozási idő beállítása a becsült távolság alapján (egyszerűsített)
                    # Kiszámoljuk a jelenlegi és a célpont közötti távolságot
                    dx = target_pose_mm[0] - self.last_known_position[0]
                    dy = target_pose_mm[1] - self.last_known_position[1]
                    dz = target_pose_mm[2] - self.last_known_position[2]
                    distance_estimate = math.sqrt(dx*dx + dy*dy + dz*dz) / 100  # mm-ből cm-be konvertálva
                    
                    # Beállítjuk a várakozási időt a távolság alapján, de minimum 3, maximum 10 másodperc
                    wait_time = max(3, min(10, distance_estimate))
                    
                    logger.info(f"Várakozás a mozgás befejezésére (kb. {wait_time:.1f} másodperc)...")
                    time.sleep(wait_time)
                    
                    # Frissítjük az utolsó ismert pozíciót
                    self.last_known_position = target_pose_mm
                    logger.info(f"Mozgás befejezve, új pozíció: {self.format_position(self.last_known_position)}")
                    return True
                else:
                    logger.error("Nem sikerült elküldeni a mozgatási parancsot")
                    return False
            else:
                # BIZTONSÁGI MÓD: A mozgást több szegmensre osztjuk
                logger.info(f"Biztonsági mód: Mozgás felosztása {move_segments} szegmensre")
                
                # Kezdőpontként az utolsó ismert pozíciót használjuk
                start_pose = self.last_known_position
                
                print(f"\nA mozgás {move_segments} szegmensre lesz felosztva a biztonság érdekében")
                print(f"Kezdőpozíció: {self.format_position(start_pose)}")
                print(f"Célpozíció: {self.format_position(target_pose_mm)}")
                print(f"Távolság: {self.calculate_distance(start_pose, target_pose_mm):.1f} mm")
                
                # Felosztjuk a mozgást egyenlő szegmensekre
                for i in range(1, move_segments + 1):
                    # Kiszámítjuk a közbenső pozíciót (i/segments arányban a kezdettől a célig)
                    fraction = i / move_segments
                    intermediate_pose = []
                    
                    for j in range(len(target_pose_mm)):
                        intermediate_pose.append(start_pose[j] + fraction * (target_pose_mm[j] - start_pose[j]))
                    
                    # Biztonsági ellenőrzés a Z koordinátára (kivéve ha rajzolási művelet)
                    if not is_drawing:
                        intermediate_pose = self.ensure_safe_z(intermediate_pose)
                    
                    # Kiszámoljuk a hátralévő mozgás százalékát
                    remaining_percent = 100 * (move_segments - i) / move_segments
                    
                    print(f"\n{i}. szegmens {move_segments}-ből ({(i/move_segments*100):.1f}% kész, {remaining_percent:.1f}% van hátra):")
                    print(f"Következő pozíció: {self.format_position(intermediate_pose)}")
                    
                    # Megerősítést kérünk minden szegmenshez
                    confirm = input("Nyomj Enter-t a folytatáshoz, vagy 'x'-et a megszakításhoz: ")
                    if confirm.lower() == 'x':
                        logger.info("Mozgás megszakítva a felhasználó által")
                        print("Mozgás megszakítva")
                        return False
                    
                    # Konvertáljuk mm-ből m-be az első 3 koordinátát
                    intermediate_pose_m = self.mm_to_m(intermediate_pose)
                    
                    # Formázzuk a pozíciót megfelelő pontossággal
                    pose_str = "p[" + ", ".join([f"{p:.6f}" for p in intermediate_pose_m]) + "]"
                    
                    # URScript parancs movel használatával
                    script = f"movel({pose_str}, a=0.5, v={move_speed})\n"
                    
                    logger.info(f"Mozgatási parancs küldése a {i}. szegmenshez {move_segments}-ből: {script.strip()}")
                    
                    # Script küldése a Másodlagos Interfészen keresztül
                    success = self.secondary_client.send_script(script)
                    
                    if not success:
                        logger.error(f"Nem sikerült elküldeni a mozgatási parancsot a {i}. szegmenshez")
                        return False
                    
                    # Várunk, hogy a szegmens mozgása befejeződjön
                    wait_time = 2  # Rövidebb várakozás a szegmensekhez
                    logger.info(f"Várakozás a szegmens mozgásának befejezésére...")
                    time.sleep(wait_time)
                    
                    # Frissítjük a kezdőpozíciót a következő iterációhoz
                    start_pose = intermediate_pose
                    # Frissítjük az utolsó ismert pozíciót
                    self.last_known_position = intermediate_pose
                    
                    logger.info(f"A {i}. szegmens befejezve, új pozíció: {self.format_position(self.last_known_position)}")
                    print(f"A {i}. szegmens befejezve. Teljesítve: {i}/{move_segments} ({(i/move_segments*100):.1f}%)")
                
                logger.info(f"Minden mozgási szegmens sikeresen befejezve. Teljes távolság: {self.calculate_distance(self.last_known_position, target_pose_mm):.1f} mm")
                logger.info(f"Végső pozíció: {self.format_position(self.last_known_position)}")
                print(f"\nMinden mozgási szegmens sikeresen befejezve ({move_segments}/{move_segments}, 100%)")
                return True
                
        except Exception as e:
            logger.error(f"Hiba a TCP mozgatása közben: {e}")
            return False
    
    def pen_up(self):
        """Toll felemelése a papírról
        
        Returns:
            bool: True ha sikeres, False ha nem
        """
        if not self.is_connected:
            logger.error("Nincs kapcsolat a robottal")
            return False
            
        try:
            logger.info("Toll felemelése...")
            
            # Toll felemelési Z pozíció számítása
            pen_up_z = self.paper_surface_z + self.pen_up_offset
            
            # Biztonsági ellenőrzés a Z értékre
            safe_z = max(pen_up_z, self.paper_surface_z + MIN_SAFETY_DISTANCE)
            
            # URScript létrehozása a toll felemeléséhez
            script = f"""
            def pen_up():
              current_pose = get_actual_tcp_pose()
              current_pose[2] = {safe_z / 1000.0}
              movel(current_pose, a=0.5, v=0.1)
            end
            pen_up()
            """
            
            logger.info(f"Toll felemelése a következő Z pozícióra: {safe_z}mm")
            success = self.secondary_client.send_script(script)
            
            if success:
                # Várunk, hogy a mozgás befejeződjön
                time.sleep(2)
                
                # Frissítjük az utolsó ismert pozíciót - csak a Z értéket változtatjuk
                if self.last_known_position:
                    self.last_known_position[2] = safe_z
                    logger.info(f"Toll felemelve, új Z pozíció: {safe_z}mm")
                
                return True
            else:
                logger.error("Nem sikerült elküldeni a toll felemelési parancsot")
                return False
        except Exception as e:
            logger.error(f"Toll felemelés sikertelen: {e}")
            return False
    
    def pen_down(self):
        """Toll leengedése rajzolási pozícióba
        
        Returns:
            bool: True ha sikeres, False ha nem
        """
        if not self.is_connected:
            logger.error("Nincs kapcsolat a robottal")
            return False
            
        try:
            logger.info("Toll leengedése...")
            
            # Toll leengedési Z pozíció számítása
            pen_down_z = self.paper_surface_z + self.pen_down_offset
            
            # URScript létrehozása a toll leengedéséhez
            script = f"""
            def pen_down():
              current_pose = get_actual_tcp_pose()
              current_pose[2] = {pen_down_z / 1000.0}
              movel(current_pose, a=0.5, v=0.05)
            end
            pen_down()
            """
            
            logger.info(f"Toll leengedése a következő Z pozícióra: {pen_down_z}mm")
            success = self.secondary_client.send_script(script)
            
            if success:
                # Várunk, hogy a mozgás befejeződjön
                time.sleep(2)
                
                # Frissítjük az utolsó ismert pozíciót - csak a Z értéket változtatjuk
                if self.last_known_position:
                    self.last_known_position[2] = pen_down_z
                    logger.info(f"Toll leengedve, új Z pozíció: {pen_down_z}mm")
                
                return True
            else:
                logger.error("Nem sikerült elküldeni a toll leengedési parancsot")
                return False
        except Exception as e:
            logger.error(f"Toll leengedés sikertelen: {e}")
            return False
    
    def move_to_home(self):
        """Robot mozgatása a kezdőpozícióba
        
        Returns:
            bool: True ha sikeres, False ha nem
        """
        if not self.home_position:
            logger.error("Kezdőpozíció nincs beállítva")
            return False
            
        logger.info(f"Mozgás a kezdőpozícióba: {self.format_position(self.home_position)}")
        # Biztonsági módban több szegmenst használunk
        move_segments = self.safe_move_segments if self.safety_mode else 1
        
        # Először emeljük fel a tollat
        logger.info("Toll felemelése a kezdőpozícióba való mozgás előtt...")
        self.pen_up()
        
        return self.move_tcp(self.home_position, speed=self.movement_speed, segments=move_segments)
    
    def movement_test(self):
        """Mozgásteszt végrehajtása négyzet rajzolásával a levegőben
        
        Returns:
            bool: True ha a teszt sikeresen befejeződött, False ha nem
        """
        if not self.is_connected:
            logger.error("Nincs kapcsolat a robottal")
            return False
            
        try:
            # Kezdés a kezdőpozícióból
            print("\nMozgásteszt indítása: Négyzet rajzolása a levegőben")
            print("Bizonyosodj meg róla, hogy a terület szabad!")
            confirm = input("Először mozogjon a kezdőpozícióba? (i/n): ")
            
            if confirm.lower() in ['i', 'igen', 'y', 'yes']:
                print("\nMozgás a kezdőpozícióba...")
                if not self.move_to_home():
                    print("Nem sikerült a kezdőpozícióba mozogni")
                    return False
            
            # Négyzet sarokpontjainak meghatározása a jelenlegi pozícióhoz képest
            # 100mm x 100mm négyzet létrehozása az xy síkban
            square_size = 100  # mm
            
            # Biztonságos kezdőpozíció kiszámítása a papír felett
            start_position = self.last_known_position.copy() if self.last_known_position else self.home_position.copy()
            
            # Bizonyosodjunk meg róla, hogy biztonságos magasságban vagyunk
            safe_z = max(start_position[2], self.paper_surface_z + self.pen_up_offset)
            start_position[2] = safe_z
            
            print("\nMozgás a négyzet kezdőpontjába...")
            logger.info("Mozgás a négyzet kezdőpontjába...")
            if not self.move_tcp(start_position):
                print("Nem sikerült a kezdőpontba mozogni")
                return False
            
            # Négyzet sarokpontjainak meghatározása
            square_corners = [
                start_position.copy(),  # Kezdőpont
                [start_position[0] + square_size, start_position[1], start_position[2], start_position[3], start_position[4], start_position[5]],  # Jobb
                [start_position[0] + square_size, start_position[1] + square_size, start_position[2], start_position[3], start_position[4], start_position[5]],  # Jobb-felső
                [start_position[0], start_position[1] + square_size, start_position[2], start_position[3], start_position[4], start_position[5]],  # Bal-felső
                start_position.copy()  # Vissza a kezdőpontba
            ]
            
            # Négyzet rajzolása
            for i, corner in enumerate(square_corners[1:], 1):
                print(f"\nMozgás a {i}. sarokpontba: {self.format_position(corner)}")
                logger.info(f"Mozgás a négyzet {i}. sarokpontjába: {self.format_position(corner)}")
                
                confirm = input("Nyomj Enter-t a folytatáshoz, vagy 'x'-et a megszakításhoz: ")
                if confirm.lower() == 'x':
                    print("Mozgásteszt megszakítva")
                    return False
                
                if not self.move_tcp(corner, speed=self.drawing_speed, segments=1):
                    print(f"Nem sikerült a {i}. sarokpontba mozogni")
                    return False
            
            print("\nNégyzet mozgásteszt sikeresen befejezve!")
            logger.info("Négyzet mozgásteszt sikeresen befejezve")
            
            # Megkérdezzük, hogy a felhasználó szeretne-e még egy négyzetet rajzolni
            confirm = input("\nSzeretnél még egy négyzetet rajzolni? (i/n): ")
            if confirm.lower() in ['i', 'igen', 'y', 'yes']:
                return self.movement_test()
                
            return True
            
        except Exception as e:
            logger.error(f"Mozgásteszt sikertelen: {e}")
            print(f"Mozgásteszt hiba: {e}")
            return False
    
    def draw_from_json(self, json_file):
        """Rajzolás trajektória követésével JSON fájlból
        
        Args:
            json_file (str): JSON fájl elérési útja, amely tartalmazza a trajektóriát
            
        Returns:
            bool: True ha a rajzolás sikeresen befejeződött, False ha nem
        """
        if not self.is_connected:
            logger.error("Nincs kapcsolat a robottal")
            return False
            
        try:
            # Trajektória betöltése JSON-ból
            logger.info(f"Trajektória betöltése: {json_file}")
            with open(json_file, 'r') as f:
                trajectory = json.load(f)
                
            if not isinstance(trajectory, list) or len(trajectory) < 2:
                logger.error(f"Érvénytelen trajektória adatok: {json_file}")
                print(f"Hiba: Érvénytelen trajektória adatok: {json_file}")
                return False
                
            logger.info(f"Trajektória betöltve {len(trajectory)} ponttal innen: {json_file}")
            print(f"\nTrajektória betöltve {len(trajectory)} ponttal.")
            
            # Ellenőrizzük az aktuális pozíciót
            at_home = False
            if self.last_known_position:
                # Ellenőrizzük, hogy a kezdőpozícióban vagyunk-e már
                dx = abs(self.last_known_position[0] - self.home_position[0])
                dy = abs(self.last_known_position[1] - self.home_position[1])
                dz = abs(self.last_known_position[2] - self.home_position[2])
                
                # Ha elég közel vagyunk a kezdőpozícióhoz, akkor már ott vagyunk
                if dx < 5 and dy < 5 and dz < 5:  # 5mm tolerancia
                    at_home = True
                    logger.info("A robot már a kezdőpozícióban van")
                    print("A robot már a kezdőpozícióban van.")
            
            # Megerősítést kérünk
            confirm = input("Elkezdjük a rajzolást? (i/n): ")
            if confirm.lower() not in ['i', 'igen', 'y', 'yes']:
                print("Rajzolás megszakítva")
                return False
            
            # Ha nem vagyunk még a kezdőpozícióban és a felhasználó akarja, akkor oda mozgunk
            if not at_home:
                move_home = input("Mozogjunk először a kezdőpozícióba? (i/n): ")
                if move_home.lower() in ['i', 'igen', 'y', 'yes']:
                    print("\nMozgás a kezdőpozícióba...")
                    logger.info("Mozgás a kezdőpozícióba a rajzolás előtt...")
                    if not self.move_to_home():
                        print("Nem sikerült a kezdőpozícióba mozogni")
                        return False
            
            # A trajektória első pontja általában egy 'toll-fel' pozíció az első rajzolási pont felett
            # Közvetlenül oda mozgunk
            first_point = trajectory[0]
            print(f"\nMozgás a trajektória kezdőpontjára: {self.format_position(first_point)}")
            logger.info(f"Mozgás a trajektória kezdőpontjára: {self.format_position(first_point)}")
            
            # Toll felemelése, ha még nincs felemelve
            if self.last_known_position and self.last_known_position[2] < self.paper_surface_z + self.pen_up_offset:
                print("\nToll felemelése...")
                logger.info("Toll felemelése a mozgás előtt...")
                self.pen_up()
            
            # Ellenőrizzük, hogy az első pont Z értéke a biztonságos tartományban van-e
            if first_point[2] < self.paper_surface_z + MIN_SAFETY_DISTANCE:
                logger.warning(f"Az első pont Z értéke ({first_point[2]}) túl alacsony, korrigálás")
                first_point[2] = self.paper_surface_z + self.pen_up_offset
            
            # Mozgás az első pontra
            if not self.move_tcp(first_point):
                print("Nem sikerült a trajektória kezdőpontjára mozogni")
                return False
            
            # Ellenőrizzük, hogy a 2. pont toll-leengedést igényel-e
            # Ha a második pont Z koordinátája közel van a rajzolási magassághoz, akkor leengedjük a tollat
            if len(trajectory) > 1:
                second_point = trajectory[1]
                needs_pen_down = abs(second_point[2] - (self.paper_surface_z + self.pen_down_offset)) < 2.0
                
                if needs_pen_down:
                    print("\nToll leengedése rajzolási pozícióba...")
                    logger.info("Toll leengedése rajzolási pozícióba...")
                    self.pen_down()
            
            # Trajektória követése
            # Az első pontot már meglátogattuk, így az 1. indextől kezdve megyünk végig
            for i, point in enumerate(trajectory[1:], 1):
                print(f"Rajzolás {i}/{len(trajectory)-1} pont")
                logger.info(f"Rajzolás a {i}/{len(trajectory)-1} pontra: {self.format_position(point)}")
                
                # Ellenőrizzük, hogy ez a pont toll-fel vagy toll-le pozícióban van-e
                is_pen_down = abs(point[2] - (self.paper_surface_z + self.pen_down_offset)) < 2.0
                is_pen_up = abs(point[2] - (self.paper_surface_z + self.pen_up_offset)) < 2.0
                
                # Ellenőrizzük az előző pozíciót
                prev_pos = trajectory[i-1] if i > 0 else self.last_known_position
                was_pen_down = abs(prev_pos[2] - (self.paper_surface_z + self.pen_down_offset)) < 2.0
                
                # Ha toll állapot váltás van
                if is_pen_down and not was_pen_down:
                    print("Toll leengedése...")
                    logger.info("Toll leengedése a rajzoláshoz...")
                    self.pen_down()
                elif is_pen_up and was_pen_down:
                    print("Toll felemelése...")
                    logger.info("Toll felemelése a mozgáshoz...")
                    self.pen_up()
                
                # Most mozgunk a pontra
                # Ha toll lent, akkor rajzolási sebességgel
                # Ha toll fent, akkor mozgási sebességgel
                speed = self.drawing_speed if is_pen_down else self.movement_speed
                
                # Ha toll fent, és biztonsági mód be van kapcsolva, akkor szegmentáljuk
                segments = 1 if is_pen_down else (self.safe_move_segments if self.safety_mode else 1)
                
                # Mozgás a pontra
                if not self.move_tcp(point, speed=speed, segments=segments, is_drawing=is_pen_down):
                    print(f"Hiba a {i}. trajektória pontnál")
                    # Hiba esetén a tollat felemeljük
                    self.pen_up()
                    return False
            
            # Toll felemelése a végén, ha még nincs felemelve
            if self.last_known_position and self.last_known_position[2] < self.paper_surface_z + self.pen_up_offset:
                print("\nRajzolás befejezve. Toll felemelése...")
                logger.info("Rajzolás befejezve, toll felemelése...")
                self.pen_up()
            else:
                print("\nRajzolás befejezve. Toll már fel van emelve.")
                logger.info("Rajzolás befejezve, toll már fel van emelve.")
            
            # Visszatérés a kezdőpozícióba
            confirm = input("Visszatérünk a kezdőpozícióba? (i/n): ")
            if confirm.lower() in ['i', 'igen', 'y', 'yes']:
                print("\nVisszatérés a kezdőpozícióba...")
                logger.info("Visszatérés a kezdőpozícióba a rajzolás után...")
                self.move_to_home()
            
            print("\nRajzolás sikeresen befejezve!")
            logger.info("Rajzolás sikeresen befejezve")
            return True
            
        except Exception as e:
            logger.error(f"Rajzolás JSON fájlból sikertelen: {e}")
            print(f"Rajzolási hiba: {e}")
            # Bármilyen hiba esetén felemeljük a tollat
            try:
                self.pen_up()
            except:
                pass
            return False
    
    def check_robot_program(self):
        """Ellenőrzi, hogy fut-e program a roboton, ha nem, megpróbál elindítani egyet
        
        Returns:
            bool: True ha a program fut, False ha nem
        """
        try:
            # Program állapot ellenőrzése Dashboard-on keresztül
            logger.info("Program állapot ellenőrzése...")
            program_state = self.dashboard.sendAndReceive('programstate')
            logger.info(f"Program állapot: {program_state}")
            
            if "PLAYING" not in program_state:
                # Nincs futó program, próbálunk betölteni és elindítani egyet
                logger.info("Nincs futó program a roboton. Próbálunk betölteni és elindítani egyet...")
                
                # Ellenőrizzük, hogy van-e már betöltve program
                loaded_program = self.dashboard.sendAndReceive('get loaded program')
                logger.info(f"Betöltött program: {loaded_program}")
                
                # Ha nincs betöltve program, próbálunk egyet
                if "No program loaded" in loaded_program:
                    # Próbálunk egy .urp fájlt a roboton
                    logger.info("Interpret.urp betöltése...")
                    self.dashboard.sendAndReceive('load /programs/RemoteOperation/interpret.urp')
                    time.sleep(1)
                
                # Elindítjuk a programot
                logger.info("Program indítása...")
                self.dashboard.sendAndReceive('play')
                logger.info("Program elindítva")
                
                # Várunk az indulásra
                time.sleep(2)
                
                # Újra ellenőrizzük
                program_state = self.dashboard.sendAndReceive('programstate')
                running = "PLAYING" in program_state
                logger.info(f"Program {'fut' if running else 'nem fut'}")
                return running
            else:
                logger.info("Program már fut")
                return True
                
        except Exception as e:
            logger.error(f"Hiba a robot program ellenőrzésekor: {e}")
            return False


def create_gui(controller):
    """Egyszerű parancssoros felhasználói felület az alkalmazáshoz"""
    # Azonnal kapcsolódunk a robothoz
    if not controller.is_connected:
        print("Kapcsolódás a robothoz...")
        if controller.connect():
            print("Sikeresen kapcsolódva a robothoz!")
        else:
            print("Sikertelen kapcsolódás a robothoz. Ellenőrizd a beállításokat és a robot állapotát.")
            confirm = input("Folytatod kapcsolat nélkül? (i/n): ")
            if confirm.lower() not in ['i', 'igen', 'y', 'yes']:
                return
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\n===== UR Robot Rajzoló Vezérlő =====")
        print("\nAktuális Állapot:")
        print(f"Kapcsolódva a robothoz: {'Igen' if controller.is_connected else 'Nem'}")
        print(f"Másodlagos Interfész: {'Kapcsolódva' if controller.secondary_client and controller.secondary_client.connected else 'Nincs kapcsolat'}")
        print(f"Biztonsági mód: {'BEKAPCSOLVA' if controller.safety_mode else 'KIKAPCSOLVA'}")
        
        if controller.is_connected:
            # Aktuális állapot lekérése a Dashboard-ról
            try:
                program_state = controller.dashboard.sendAndReceive('programstate')
                print(f"Program állapot: {program_state}")
                
                safety_status = controller.dashboard.sendAndReceive('safetystatus')
                print(f"Biztonsági állapot: {safety_status}")
            except:
                pass
                
        print(f"Papír felszín Z: {controller.paper_surface_z}")
        print(f"Kezdőpozíció: {controller.format_position(controller.home_position)}")
        print(f"Utolsó ismert pozíció: {controller.format_position(controller.last_known_position)}")
        
        print("\nVálassz egy opciót:")
        print("1. Mozgásteszt (Négyzet rajzolása a levegőben)")
        print("2. Rajzolás JSON Fájlból")
        print("3. Mozgás a Kezdőpozícióba")
        print("4. Részletes Robot Állapot Ellenőrzése")
        print("5. Program Indítása a Roboton")
        print("6. Biztonsági Mód Be/Kikapcsolása")
        print("7. Újrakapcsolódás a Robothoz")
        print("0. Kilépés")
        
        choice = input("\nAdd meg a választásod (0-7): ")
        
        if choice == '0':
            if controller.is_connected:
                controller.disconnect()
            print("\nKilépés az alkalmazásból...")
            break
            
        elif choice == '1':
            if not controller.is_connected:
                print("\nNincs kapcsolat a robottal.")
                input("\nNyomj Enter-t a folytatáshoz...")
                continue
                
            print("\nMozgásteszt indítása...")
            controller.movement_test()
            input("\nNyomj Enter-t a folytatáshoz...")
            
        elif choice == '2':
            if not controller.is_connected:
                print("\nNincs kapcsolat a robottal.")
                input("\nNyomj Enter-t a folytatáshoz...")
                continue
                
            # Ellenőrizzük, hogy létezik-e a drawings mappa
            if not os.path.exists(DRAWINGS_FOLDER):
                print(f"\nA drawings mappa '{DRAWINGS_FOLDER}' nem található.")
                # Létrehozzuk a mappát, ha nem létezik
                try:
                    os.makedirs(DRAWINGS_FOLDER)
                    print(f"Létrehozva a drawings mappa: {DRAWINGS_FOLDER}")
                except:
                    print("Nem sikerült létrehozni a drawings mappát.")
                    input("\nNyomj Enter-t a folytatáshoz...")
                    continue
                
            # Elérhető JSON fájlok listázása a drawings mappában
            json_files = [f for f in os.listdir(DRAWINGS_FOLDER) if f.endswith('.json')]
            
            if not json_files:
                print(f"\nNincsenek JSON fájlok a {DRAWINGS_FOLDER} mappában.")
                input("\nNyomj Enter-t a folytatáshoz...")
                continue
                
            print(f"\nElérhető JSON fájlok a {DRAWINGS_FOLDER} mappában:")
            for i, json_file in enumerate(json_files, 1):
                print(f"{i}. {json_file}")
                
            file_choice = input("\nAdd meg a fájl számát a rajzoláshoz (vagy '0'-át a megszakításhoz): ")
            
            if file_choice == '0':
                print("Rajz kiválasztás megszakítva")
            elif file_choice.isdigit() and 1 <= int(file_choice) <= len(json_files):
                json_file = os.path.join(DRAWINGS_FOLDER, json_files[int(file_choice)-1])
                print(f"\nRajzolás a következőből: {json_file}...")
                controller.draw_from_json(json_file)
            else:
                print("Érvénytelen választás")
                
            input("\nNyomj Enter-t a folytatáshoz...")
            
        elif choice == '3':
            if not controller.is_connected:
                print("\nNincs kapcsolat a robottal.")
                input("\nNyomj Enter-t a folytatáshoz...")
                continue
                
            print("\nMozgás a kezdőpozícióba...")
            if controller.move_to_home():
                print("Sikeresen a kezdőpozícióba mozgott.")
            else:
                print("Nem sikerült a kezdőpozícióba mozogni.")
                
            input("\nNyomj Enter-t a folytatáshoz...")
            
        elif choice == '4':
            if not controller.is_connected:
                print("\nNincs kapcsolat a robottal.")
                input("\nNyomj Enter-t a folytatáshoz...")
                continue
                
            print("\nRészletes Robot Állapot:")
            print("=====================")
            status_info = controller.get_robot_status()
            print(status_info)
            
            input("\nNyomj Enter-t a folytatáshoz...")
            
        elif choice == '5':
            if not controller.is_connected:
                print("\nNincs kapcsolat a robottal.")
                input("\nNyomj Enter-t a folytatáshoz...")
                continue
                
            print("\nProgram indítása a roboton...")
            if controller.check_robot_program():
                print("Robot program sikeresen elindítva vagy már fut!")
            else:
                print("Nem sikerült elindítani a robot programot.")
                
            input("\nNyomj Enter-t a folytatáshoz...")
            
        elif choice == '6':
            if not controller.is_connected:
                print("\nNincs kapcsolat a robottal.")
                input("\nNyomj Enter-t a folytatáshoz...")
                continue
                
            safety_mode = controller.toggle_safety_mode()
            print(f"\nBiztonsági mód {'BEKAPCSOLVA' if safety_mode else 'KIKAPCSOLVA'}")
            if safety_mode:
                print(f"A mozgások {controller.safe_move_segments} szegmensre lesznek felosztva és megerősítést igényelnek.")
            else:
                print("A mozgások egyben lesznek végrehajtva megerősítés nélkül.")
                
            input("\nNyomj Enter-t a folytatáshoz...")
            
        elif choice == '7':
            if controller.is_connected:
                print("\nLekapcsolódás a robotról...")
                controller.disconnect()
                
            print("\nÚjrakapcsolódás a robothoz...")
            if controller.connect():
                print("Sikeresen kapcsolódva a robothoz!")
            else:
                print("Nem sikerült kapcsolódni a robothoz.")
                
            input("\nNyomj Enter-t a folytatáshoz...")
            
        else:
            print("\nÉrvénytelen választás. Próbáld újra.")
            input("\nNyomj Enter-t a folytatáshoz...")


def main():
    """Fő függvény az UR Rajzoló Vezérlő futtatásához"""
    # Bizonyosodjunk meg róla, hogy a mappák léteznek
    if not os.path.exists(DRAWINGS_FOLDER):
        try:
            os.makedirs(DRAWINGS_FOLDER)
            print(f"Létrehozva a drawings mappa: {DRAWINGS_FOLDER}")
        except:
            print(f"Nem sikerült létrehozni a drawings mappát: {DRAWINGS_FOLDER}")
    
    # Vezérlő inicializálása
    controller = URDrawingController(robot_ip=ROBOT_IP)
    
    # A GUI indítása
    create_gui(controller)

if __name__ == "__main__":
    main()