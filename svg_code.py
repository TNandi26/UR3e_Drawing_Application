#!/usr/bin/env python3
# SVG to Trajectory Converter for UR3e Robot - SVG konvertáló a UR3e robothoz

import os
import math
import json
import xml.etree.ElementTree as ET
import logging

# Naplózás beállítása
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("svg_converter.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Konfigurációs változók (ezeket kell módosítani szükség szerint)
INPUT_SVG_FILE = "drawings/zigzag.svg"  # Az SVG fájl elérési útja - ezt kell módosítani minden új rajzhoz
OUTPUT_TRAJECTORY_FILE = None  # Ha None, akkor az input nevét használja .json kiterjesztéssel
CENTER_X = 0.0  # Az A4-es papír középpontjának X koordinátája a robot koordináta rendszerében - KALIBRÁLÁSNÁL ÁLLÍTANDÓ!
CENTER_Y = 0.0  # Az A4-es papír középpontjának Y koordinátája a robot koordináta rendszerében - KALIBRÁLÁSNÁL ÁLLÍTANDÓ!
Z_SURFACE = 0.0  # A papír felületének Z koordinátája a robot koordináta rendszerében - KALIBRÁLÁSNÁL ÁLLÍTANDÓ!
PEN_UP_Z = 0.07  # Mennyire emelje fel a tollat amikor nem rajzol (7cm) - lehet állítani ha túl magasra emeli
PEN_DOWN_Z = 0.0  # Tollal a papíron (általában 0, de lehet hogy kicsit nagyobbra kell állítani)
RX = 0.0  # Forgatás az X tengely körül - ne változtasd, ha a toll függőlegesen áll
RY = 3.14159  # Forgatás az Y tengely körül (általában π a függőleges tollhoz) - ne változtasd, ha a toll függőlegesen áll
RZ = 0.0  # Forgatás a Z tengely körül - ne változtasd, ha a toll függőlegesen áll

# A4 papír méretei méterben
A4_WIDTH = 0.210
A4_HEIGHT = 0.297

def ensure_directory_exists(file_path):
    """Ellenőrzi, hogy a könyvtár létezik-e, ha nem, létrehozza."""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        try:
            os.makedirs(directory)
            print(f"Létrehozott könyvtár: {directory}")
        except Exception as e:
            print(f"Figyelmeztetés: Nem sikerült létrehozni a könyvtárat {directory}: {str(e)}")

class SVGToTrajectoryConverter:
    def __init__(self, center_x, center_y, z_surface, pen_up_z, pen_down_z, rx, ry, rz):
        """
        Konverter inicializálása a robot pozícióparamétereivel.
        """
        self.center_x = center_x
        self.center_y = center_y
        self.z_surface = z_surface
        self.pen_up_z = pen_up_z
        self.pen_down_z = pen_down_z
        self.rx = rx
        self.ry = ry
        self.rz = rz
    
    def create_svg_files(self):
        """Alapértelmezett SVG fájlok létrehozása, ha nem léteznek."""
        # Drawings könyvtár létrehozása, ha nem létezik
        drawings_dir = os.path.dirname(INPUT_SVG_FILE)
        if not drawings_dir:
            drawings_dir = "drawings"
        os.makedirs(drawings_dir, exist_ok=True)
        
        # SVG fájlok létrehozása, ha nem léteznek
        self.create_square_svg(os.path.join(drawings_dir, "square.svg"))
        self.create_circle_svg(os.path.join(drawings_dir, "circle.svg")) 
        self.create_spiral_svg(os.path.join(drawings_dir, "spiral.svg"))
        self.create_star_svg(os.path.join(drawings_dir, "star.svg"))
        self.create_diamond_svg(os.path.join(drawings_dir, "diamond.svg"))
        self.create_proper_diamond_svg(os.path.join(drawings_dir, "proper_diamond.svg"))
        self.create_triangle_svg(os.path.join(drawings_dir, "triangle.svg"))
        self.create_grid_svg(os.path.join(drawings_dir, "grid.svg"))
        self.create_zigzag_svg(os.path.join(drawings_dir, "zigzag.svg"))
        self.create_starburst_svg(os.path.join(drawings_dir, "starburst.svg"))
        self.create_temple_svg(os.path.join(drawings_dir, "temple.svg"))
        self.create_temple1_svg(os.path.join(drawings_dir, "temple1.svg"))
        
        print("Alapértelmezett SVG fájlok létrehozva a drawings könyvtárban.")
    
    def create_square_svg(self, filename):
        """Négyzet SVG fájl létrehozása."""
        svg_content = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <path style="fill:none;stroke:#000000;stroke-width:1px;" d="M 50,50 L 150,50 L 150,150 L 50,150 Z" />
</svg>"""
        
        with open(filename, 'w') as f:
            f.write(svg_content)
    
    def create_circle_svg(self, filename):
        """Kör SVG fájl létrehozása."""
        svg_content = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <circle style="fill:none;stroke:#000000;stroke-width:1px;" cx="105" cy="148.5" r="50" />
</svg>"""
        
        with open(filename, 'w') as f:
            f.write(svg_content)
    
    def create_spiral_svg(self, filename):
        """Spirál SVG fájl létrehozása."""
        # Spirál útvonal generálása
        spiral_path = "M 105,148.5 "
        radius = 5
        for angle in range(0, 1080, 5):
            rad = math.radians(angle)
            radius += 0.2
            x = 105 + radius * math.cos(rad)
            y = 148.5 + radius * math.sin(rad)
            spiral_path += f"L {x},{y} "
        
        svg_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <path style="fill:none;stroke:#000000;stroke-width:1px;" d="{spiral_path}" />
</svg>"""
        
        with open(filename, 'w') as f:
            f.write(svg_content)
    
    def create_star_svg(self, filename):
        """Csillag SVG fájl létrehozása."""
        svg_content = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <path style="fill:none;stroke:#000000;stroke-width:1px;" d="M 105,98.5 L 120,133.5 L 155,133.5 L 130,153.5 L 140,188.5 L 105,168.5 L 70,188.5 L 80,153.5 L 55,133.5 L 90,133.5 Z" />
</svg>"""
        
        with open(filename, 'w') as f:
            f.write(svg_content)
    
    def create_diamond_svg(self, filename):
        """Gyémánt SVG fájl létrehozása a megadott kép alapján."""
        # Gyémánt design a képről
        diamond_path = """M 50,100 L 105,50 L 160,100 L 105,150 Z
        M 50,100 L 30,120 L 105,180 L 180,120 L 160,100
        M 30,120 L 20,130 L 105,200 L 190,130 L 180,120
        M 50,100 L 70,80 L 105,50
        M 160,100 L 140,80 L 105,50
        M 105,150 L 85,130 L 50,100
        M 105,150 L 125,130 L 160,100
        M 105,180 L 85,160 L 50,100
        M 105,180 L 125,160 L 160,100
        M 105,200 L 85,180 L 30,120
        M 105,200 L 125,180 L 180,120"""
        
        svg_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <path style="fill:none;stroke:#000000;stroke-width:1px;" d="{diamond_path}" />
</svg>"""
        
        with open(filename, 'w') as f:
            f.write(svg_content)
    
    def create_proper_diamond_svg(self, filename):
        """Egyszerű gyémánt alakzat létrehozása."""
        svg_content = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <path style="fill:none;stroke:#000000;stroke-width:1px;" d="M 105,80 L 140,148.5 L 105,217 L 70,148.5 Z" />
</svg>"""
        
        with open(filename, 'w') as f:
            f.write(svg_content)
    
    def create_triangle_svg(self, filename):
        """Háromszög SVG fájl létrehozása."""
        svg_content = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <path style="fill:none;stroke:#000000;stroke-width:1px;" d="M 55,180 L 105,80 L 155,180 Z" />
</svg>"""
        
        with open(filename, 'w') as f:
            f.write(svg_content)
    
    def create_grid_svg(self, filename):
        """Rács minta SVG fájl létrehozása."""
        # Rács útvonal generálása
        grid_path = ""
        # Vízszintes vonalak
        for y in range(60, 201, 20):
            grid_path += f"M 40,{y} L 170,{y} "
        
        # Függőleges vonalak
        for x in range(40, 171, 20):
            grid_path += f"M {x},60 L {x},200 "
        
        svg_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <path style="fill:none;stroke:#000000;stroke-width:1px;" d="{grid_path}" />
</svg>"""
        
        with open(filename, 'w') as f:
            f.write(svg_content)
    
    def create_zigzag_svg(self, filename):
        """Cikk-cakk minta SVG fájl létrehozása."""
        zigzag_path = "M 40,130 "
        
        for i in range(6):
            zigzag_path += f"L {60 + i*20},100 L {80 + i*20},160 "
        
        svg_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <path style="fill:none;stroke:#000000;stroke-width:1px;" d="{zigzag_path}" />
</svg>"""
        
        with open(filename, 'w') as f:
            f.write(svg_content)
    
    def create_starburst_svg(self, filename):
        """Csillagrobbanás minta SVG fájl létrehozása."""
        starburst_path = ""
        center_x, center_y = 105, 148.5
        
        # Sugarak létrehozása a középpontból
        for angle in range(0, 360, 15):
            rad = math.radians(angle)
            outer_x = center_x + 70 * math.cos(rad)
            outer_y = center_y + 70 * math.sin(rad)
            starburst_path += f"M {center_x},{center_y} L {outer_x},{outer_y} "
        
        svg_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <path style="fill:none;stroke:#000000;stroke-width:1px;" d="{starburst_path}" />
</svg>"""
        
        with open(filename, 'w') as f:
            f.write(svg_content)
    
    def create_temple_svg(self, filename):
        """Egyszerű templom körvonal SVG fájl létrehozása."""
        temple_path = """M 70,180 L 70,120 L 90,100 L 120,100 L 140,120 L 140,180 Z
        M 70,120 L 140,120
        M 105,120 L 105,180
        M 60,180 L 150,180
        M 80,100 L 80,80 L 130,80 L 130,100
        M 90,80 L 90,70 L 120,70 L 120,80"""
        
        svg_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <path style="fill:none;stroke:#000000;stroke-width:1px;" d="{temple_path}" />
</svg>"""
        
        with open(filename, 'w') as f:
            f.write(svg_content)
    
    def create_temple1_svg(self, filename):
        """Részletesebb templom körvonal SVG fájl létrehozása."""
        temple1_path = """M 65,180 L 65,110 L 80,95 L 130,95 L 145,110 L 145,180 Z
        M 65,110 L 145,110
        M 105,110 L 105,180
        M 55,180 L 155,180
        M 75,95 L 75,75 L 135,75 L 135,95
        M 85,75 L 85,65 L 125,65 L 125,75
        M 95,65 L 95,55 L 115,55 L 115,65
        M 105,55 L 105,40
        M 95,110 L 95,140 L 115,140 L 115,110
        M 75,150 L 95,150
        M 115,150 L 135,150
        M 75,160 L 95,160
        M 115,160 L 135,160"""
        
        svg_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <path style="fill:none;stroke:#000000;stroke-width:1px;" d="{temple1_path}" />
</svg>"""
        
        with open(filename, 'w') as f:
            f.write(svg_content)
    
    def parse_svg_path(self, svg_file):
        """SVG fájl elemzése és útvonal adatok kinyerése."""
        try:
            # Először ellenőrizzük, hogy létezik-e a fájl
            if not os.path.exists(svg_file):
                logger.error(f"Az SVG fájl {svg_file} nem található.")
                return []
                
            # Próbáljuk elemezni a fájlt
            with open(svg_file, 'r') as f:
                svg_content = f.read()
                print(f"SVG fájl mérete: {len(svg_content)} bájt")
                
            tree = ET.parse(svg_file)
            root = tree.getroot()
            
            # FIXME: Ha itt hiba van, lehet hogy a file encoding más, vagy az ET.parse nem támogatja
            
            # Útvonal elemek keresése
            paths = []
            
            # Szabványos útvonalak kezelése
            for path in root.findall('.//{http://www.w3.org/2000/svg}path'):
                d = path.get('d')
                if d:
                    print(f"Útvonal találva d attribútummal: {d[:50]}...")  # Az első 50 karakter kiírása
                    paths.append(d)
                else:
                    print("Útvonal elem találva 'd' attribútum nélkül")
            
            # Körök kezelése (útvonallá konvertálás)
            for circle in root.findall('.//{http://www.w3.org/2000/svg}circle'):
                cx = float(circle.get('cx', 0))
                cy = float(circle.get('cy', 0))
                r = float(circle.get('r', 0))
                
                print(f"Kör találva: cx={cx}, cy={cy}, r={r}")
                
                # Útvonal létrehozása a körhöz
                # TODO: Ezt lehet hogy finomítani kellene, mert sok pontot generál
                circle_path = f"M {cx-r},{cy} "
                for angle in range(0, 361, 5):  # 5 fokos lépések
                    rad = math.radians(angle)
                    x = cx + r * math.cos(rad)
                    y = cy + r * math.sin(rad)
                    circle_path += f"L {x},{y} "
                
                paths.append(circle_path)
            
            # Téglalapok kezelése (útvonallá konvertálás)
            for rect in root.findall('.//{http://www.w3.org/2000/svg}rect'):
                x = float(rect.get('x', 0))
                y = float(rect.get('y', 0))
                width = float(rect.get('width', 0))
                height = float(rect.get('height', 0))
                
                print(f"Téglalap találva: x={x}, y={y}, width={width}, height={height}")
                
                # Útvonal létrehozása a téglalaphoz
                rect_path = f"M {x},{y} L {x+width},{y} L {x+width},{y+height} L {x},{y+height} Z"
                paths.append(rect_path)
            
            # Ellenőrizzük, hogy találtunk-e útvonalakat
            if not paths:
                logger.error("Nem találhatók útvonalak az SVG fájlban.")
                return []
            
            print(f"Összesen {len(paths)} útvonal található.")
            
            # Útvonalak parancsokká alakítása
            return self.parse_path_commands(paths)
            
        except ET.ParseError as e:
            logger.error(f"XML elemzési hiba az SVG fájlban: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Hiba az SVG fájl elemzésekor: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def parse_path_commands(self, paths):
        """SVG útvonal parancsok értelmezése rajzolási parancsok listájává."""
        # HACK: Ez a függvény elég komplex, nem a legszebb, de működik...
        drawing_commands = []
        
        for path_index, path_d in enumerate(paths):
            print(f"#{path_index+1}. útvonal elemzése")
            
            # Útvonal adatok elemzése
            try:
                commands = path_d.replace(',', ' ').split()
                i = 0
                current_cmd = None
                absolute_position = [0, 0]  # Aktuális pozíció SVG koordinátákban
                
                while i < len(commands):
                    if i < len(commands) and commands[i] in 'MLmlHhVvZzCcSsQqTtAa':
                        current_cmd = commands[i]
                        i += 1
                        
                    # Move parancsok
                    elif current_cmd in 'Mm' and i+1 < len(commands):
                        try:
                            x = float(commands[i])
                            y = float(commands[i+1])
                            
                            # Relatív koordináták korrigálása
                            if current_cmd == 'm':
                                x += absolute_position[0]
                                y += absolute_position[1]
                            
                            absolute_position = [x, y]
                            drawing_commands.append(('move', x, y))
                            i += 2
                        except ValueError:
                            i += 1
                            
                    # Line parancsok
                    elif current_cmd in 'Ll' and i+1 < len(commands):
                        try:
                            x = float(commands[i])
                            y = float(commands[i+1])
                            
                            # Relatív koordináták korrigálása
                            if current_cmd == 'l':
                                x += absolute_position[0]
                                y += absolute_position[1]
                            
                            absolute_position = [x, y]
                            drawing_commands.append(('line', x, y))
                            i += 2
                        except ValueError:
                            i += 1
                            
                    # Vízszintes vonal parancsok
                    elif current_cmd in 'Hh' and i < len(commands):
                        try:
                            x = float(commands[i])
                            # Vízszintes vonal - csak az X változik
                            if current_cmd == 'h':
                                x += absolute_position[0]
                            
                            absolute_position = [x, absolute_position[1]]
                            drawing_commands.append(('line', x, absolute_position[1]))
                            i += 1
                        except ValueError:
                            i += 1
                            
                    # Függőleges vonal parancsok
                    elif current_cmd in 'Vv' and i < len(commands):
                        try:
                            y = float(commands[i])
                            # Függőleges vonal - csak az Y változik
                            if current_cmd == 'v':
                                y += absolute_position[1]
                            
                            absolute_position = [absolute_position[0], y]
                            drawing_commands.append(('line', absolute_position[0], y))
                            i += 1
                        except ValueError:
                            i += 1
                            
                    # Útvonal lezárása parancsok
                    elif current_cmd in 'Zz':
                        # Útvonal lezárása - visszatérés az első ponthoz
                        # Keressük meg az első move parancsot ebben a szegmensben
                        segment_start = 0
                        for j, cmd in enumerate(drawing_commands):
                            if cmd[0] == 'move' and j >= segment_start:
                                segment_start = j
                                break
                        
                        if segment_start < len(drawing_commands):
                            first_move = drawing_commands[segment_start]
                            drawing_commands.append(('line', first_move[1], first_move[2]))
                            absolute_position = [first_move[1], first_move[2]]
                        
                        i += 1
                        
                    # Görbe parancsok kezelése (egyszerűsítve vonalakként)
                    # FIXME: Ezt lehetne jobban implementálni több köztes ponttal
                    elif current_cmd in 'CcSs' and i+5 < len(commands):
                        try:
                            # Cubic Bézier görbe - vezérlőpontok és végpont
                            ctrl1_x = float(commands[i])
                            ctrl1_y = float(commands[i+1])
                            ctrl2_x = float(commands[i+2])
                            ctrl2_y = float(commands[i+3])
                            end_x = float(commands[i+4])
                            end_y = float(commands[i+5])
                            
                            # Relatív koordináták korrigálása
                            if current_cmd == 'c' or current_cmd == 's':
                                ctrl1_x += absolute_position[0]
                                ctrl1_y += absolute_position[1]
                                ctrl2_x += absolute_position[0]
                                ctrl2_y += absolute_position[1]
                                end_x += absolute_position[0]
                                end_y += absolute_position[1]
                            
                            # Köztes pontok hozzáadása a simább görbéhez
                            # TODO: Lehet, hogy túl sok pontot generál, ez sok munkát adhat a robotnak
                            steps = 10
                            for t in range(1, steps+1):
                                t_norm = t / steps
                                # Cubic Bézier formula
                                bx = (1-t_norm)**3 * absolute_position[0] + \
                                     3 * (1-t_norm)**2 * t_norm * ctrl1_x + \
                                     3 * (1-t_norm) * t_norm**2 * ctrl2_x + \
                                     t_norm**3 * end_x
                                by = (1-t_norm)**3 * absolute_position[1] + \
                                     3 * (1-t_norm)**2 * t_norm * ctrl1_y + \
                                     3 * (1-t_norm) * t_norm**2 * ctrl2_y + \
                                     t_norm**3 * end_y
                                
                                drawing_commands.append(('line', bx, by))
                            
                            absolute_position = [end_x, end_y]
                            i += 6
                        except (ValueError, IndexError):
                            i += 1
                            
                    # Quadratic görbe parancsok kezelése (egyszerűsítve vonalakként)
                    elif current_cmd in 'QqTt' and i+3 < len(commands):
                        try:
                            # Quadratic Bézier görbe - vezérlőpont és végpont
                            ctrl_x = float(commands[i])
                            ctrl_y = float(commands[i+1])
                            end_x = float(commands[i+2])
                            end_y = float(commands[i+3])
                            
                            # Relatív koordináták korrigálása
                            if current_cmd == 'q' or current_cmd == 't':
                                ctrl_x += absolute_position[0]
                                ctrl_y += absolute_position[1]
                                end_x += absolute_position[0]
                                end_y += absolute_position[1]
                            
                            # Köztes pontok hozzáadása a simább görbéhez
                            steps = 10
                            for t in range(1, steps+1):
                                t_norm = t / steps
                                # Quadratic Bézier formula
                                bx = (1-t_norm)**2 * absolute_position[0] + \
                                     2 * (1-t_norm) * t_norm * ctrl_x + \
                                     t_norm**2 * end_x
                                by = (1-t_norm)**2 * absolute_position[1] + \
                                     2 * (1-t_norm) * t_norm * ctrl_y + \
                                     t_norm**2 * end_y
                                
                                drawing_commands.append(('line', bx, by))
                            
                            absolute_position = [end_x, end_y]
                            i += 4
                        except (ValueError, IndexError):
                            i += 1
                            
                    # Ív parancsok kezelése (egyszerűsítve vonalakként)
                    elif current_cmd in 'Aa' and i+6 < len(commands):
                        try:
                            rx = float(commands[i])
                            ry = float(commands[i+1])
                            x_axis_rotation = float(commands[i+2])
                            large_arc_flag = int(commands[i+3])
                            sweep_flag = int(commands[i+4])
                            end_x = float(commands[i+5])
                            end_y = float(commands[i+6])
                            
                            # Relatív koordináták korrigálása
                            if current_cmd == 'a':
                                end_x += absolute_position[0]
                                end_y += absolute_position[1]
                            
                            # Íveket egyszerű vonalakként kezeljük egyelőre
                            # TODO: Ezt lehetne javítani több pont használatával
                            drawing_commands.append(('line', end_x, end_y))
                            absolute_position = [end_x, end_y]
                            i += 7
                        except (ValueError, IndexError):
                            i += 1
                            
                    else:
                        # Nem támogatott vagy érvénytelen parancsok kihagyása
                        i += 1
                
                print(f"#{path_index+1}. útvonal sikeresen értelmezve")
                
            except Exception as e:
                logger.error(f"Hiba a(z) #{path_index+1}. útvonal értelmezésekor: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        
        return drawing_commands
    
    def scale_to_a4(self, drawing_commands):
        """Rajzolási parancsok méretezése, hogy illeszkedjenek az A4-es papírra."""
        if not drawing_commands:
            return []
            
        # Megkeressük a rajz határait SVG koordinátákban
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for cmd in drawing_commands:
            if cmd[0] in ('move', 'line'):
                x, y = cmd[1], cmd[2]
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
        
        # Méretezési tényezők számítása az A4-es papírhoz (90%-át használjuk, margókat hagyva)
        svg_width = max_x - min_x
        svg_height = max_y - min_y
        
        print(f"Rajz határai: X={min_x}-tól {max_x}-ig, Y={min_y}-tól {max_y}-ig")
        print(f"Rajz méretei: Szélesség={svg_width}, Magasság={svg_height}")
        
        # SVG általában 210x297 egységet használ A4-hez, de ellenőrizzük a határokat
        scale_x = (A4_WIDTH * 0.9) / svg_width if svg_width > 0 else 1
        scale_y = (A4_HEIGHT * 0.9) / svg_height if svg_height > 0 else 1
        
        # A kisebb méretezési tényezőt használjuk a méretarány megtartásához
        scale = min(scale_x, scale_y)
        print(f"Méretezési tényezők: X={scale_x}, Y={scale_y}, Használva={scale}")
        
        # Átalakítjuk és méretezzük a rajzolási parancsokat, hogy középre kerüljenek az A4-es papíron
        scaled_commands = []
        
        for cmd in drawing_commands:
            if cmd[0] == 'move' or cmd[0] == 'line':
                # Normalizáljuk a koordinátákat a rajz középpontjához viszonyítva
                x_norm = cmd[1] - (min_x + svg_width/2)
                y_norm = cmd[2] - (min_y + svg_height/2)
                
                # Méretezzük, hogy illeszkedjen az A4-re és középre a robot középpontjánál
                x = self.center_x + x_norm * scale
                y = self.center_y + y_norm * scale
                
                scaled_commands.append((cmd[0], x, y))
        
        print(f"{len(drawing_commands)} parancs átméretezve, hogy illeszkedjen az A4-es papírra.")
        return scaled_commands
    
    def generate_trajectory(self, scaled_commands):
        """Átméretezett parancsok konvertálása 6D robot trajektóriává."""
        if not scaled_commands:
            return []
            
        trajectory = []
        
        for cmd in scaled_commands:
            if cmd[0] == 'move':
                # Move esetén a toll fent van
                x, y = cmd[1], cmd[2]
                z = self.z_surface + self.pen_up_z
                pose = [x, y, z, self.rx, self.ry, self.rz]
                trajectory.append(('move', pose))
                
            elif cmd[0] == 'line':
                # Line esetén a toll lent van
                x, y = cmd[1], cmd[2]
                z = self.z_surface + self.pen_down_z
                pose = [x, y, z, self.rx, self.ry, self.rz]
                trajectory.append(('line', pose))
        
        print(f"Trajektória generálva {len(trajectory)} ponttal.")
        return trajectory
    
    def convert_svg_to_trajectory(self, svg_file):
        """SVG fájl konvertálása robot trajektóriává."""
        # SVG fájl elemzése
        print(f"SVG fájl elemzése: {svg_file}")
        drawing_commands = self.parse_svg_path(svg_file)
        if not drawing_commands:
            print("Nem találhatók rajzolási parancsok az SVG fájlban.")
            return []
        
        print(f"{len(drawing_commands)} rajzolási parancs elemzése az SVG-ből.")
            
        # Méretezés A4 papírra
        print("Parancsok átméretezése A4 papírra...")
        scaled_commands = self.scale_to_a4(drawing_commands)
        if not scaled_commands:
            print("Nem sikerült átméretezni a rajzolási parancsokat.")
            return []
            
        # Trajektória generálása
        print("Robot trajektória generálása...")
        trajectory = self.generate_trajectory(scaled_commands)
        
        return trajectory
    
    def save_trajectory(self, trajectory, output_file):
        """Trajektória mentése JSON fájlba."""
        if not trajectory:
            logger.error("Nincs trajektória a mentéshez.")
            return False
            
        try:
            # Ellenőrizzük, hogy a kimeneti könyvtár létezik-e
            ensure_directory_exists(output_file)
            
            # NumPy tömbök vagy egyéb nem-szerializálható típusok átalakítása listákká
            serializable_trajectory = []
            for cmd, pose in trajectory:
                serializable_pose = [float(p) for p in pose]
                serializable_trajectory.append((cmd, serializable_pose))
                
            with open(output_file, 'w') as f:
                json.dump(serializable_trajectory, f, indent=4)
                
            logger.info(f"Trajektória mentve {output_file} fájlba {len(trajectory)} ponttal.")
            print(f"Trajektória mentve {output_file} fájlba {len(trajectory)} ponttal.")
            return True
        except Exception as e:
            logger.error(f"Hiba a trajektória mentésekor: {str(e)}")
            # Próbáljuk menteni a jelenlegi könyvtárba tartalékként
            try:
                fallback_file = os.path.basename(output_file)
                print(f"Kísérlet a jelenlegi könyvtárba mentésre: {fallback_file}")
                with open(fallback_file, 'w') as f:
                    json.dump(serializable_trajectory, f, indent=4)
                logger.info(f"Trajektória mentve tartalék helyre: {fallback_file}")
                print(f"Trajektória mentve: {fallback_file}")
                return True
            except Exception as e2:
                logger.error(f"A tartalék mentés is sikertelen: {str(e2)}")
                return False

def main():
    # A konfigurált változók használata
    global OUTPUT_TRAJECTORY_FILE
    
    print(f"SVG konvertálása: {INPUT_SVG_FILE}")
    
    # Konvertáló létrehozása a konfigurált paraméterekkel
    converter = SVGToTrajectoryConverter(
        center_x=CENTER_X,
        center_y=CENTER_Y,
        z_surface=Z_SURFACE,
        pen_up_z=PEN_UP_Z,
        pen_down_z=PEN_DOWN_Z,
        rx=RX,
        ry=RY,
        rz=RZ
    )
    
    # Először létrehozzuk a minta SVG fájlokat, ha nem léteznek
    print("Minta SVG fájlok ellenőrzése/létrehozása...")
    converter.create_svg_files()
    
    # Ellenőrizzük, hogy létezik-e a bemeneti fájl
    if not os.path.exists(INPUT_SVG_FILE):
        print(f"Hiba: Az SVG fájl {INPUT_SVG_FILE} nem található.")
        return
    
    # Ha nincs megadva kimeneti fájl, használjuk ugyanazt a nevet .json kiterjesztéssel
    if OUTPUT_TRAJECTORY_FILE is None:
        base_name = os.path.splitext(INPUT_SVG_FILE)[0]
        OUTPUT_TRAJECTORY_FILE = base_name + '.json'
    
    # SVG konvertálása trajektóriává
    print(f"Feldolgozás...")
    trajectory = converter.convert_svg_to_trajectory(INPUT_SVG_FILE)
    
    if not trajectory:
        print("Hiba: Nem sikerült konvertálni az SVG-t trajektóriává.")
        return
    
    print(f"Trajektória generálva {len(trajectory)} ponttal.")
    
    # Trajektória mentése
    if converter.save_trajectory(trajectory, OUTPUT_TRAJECTORY_FILE):
        print(f"Trajektória mentve {OUTPUT_TRAJECTORY_FILE} fájlba")
    else:
        print("Hiba: Nem sikerült menteni a trajektóriát.")

if __name__ == "__main__":
    main()