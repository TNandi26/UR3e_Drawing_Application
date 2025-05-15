#!/usr/bin/env python3
# SVG to Trajectory Converter for UR3e Robot

import os
import math
import json
import xml.etree.ElementTree as ET
import logging
import sys
from pathlib import Path

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("svg_converter.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Configuration variables - EDIT THESE AS NEEDED
# Input and output files
file_to_convert = "abstract_koch"
INPUT_SVG_FILE = f"svg/{file_to_convert}.svg"  # Path to SVG file
OUTPUT_TRAJECTORY_FILE = f"drawings/{file_to_convert}.json"  # If None, uses input name with .json extension

# Drawing configuration
DRAWING_SCALE = 0.35  # Scale factor reduced to make drawings smaller (circle radius ~4cm, square ~6cm per side)
PRESERVE_ASPECT_RATIO = True  # Keep the aspect ratio when scaling
DRAWING_OFFSET_X = 0.0  # Additional X offset in mm
DRAWING_OFFSET_Y = 0.0  # Additional Y offset in mm

# Robot position settings (based on provided trajectory files)
CENTER_X = -37.0  # Center X position (from the trajectory files)
CENTER_Y = -295.0  # Center Y position (from the trajectory files)
Z_SURFACE = -145  # Drawing surface height from the trajectory files

# Robot Z positions
PEN_UP_Z = 20.0  # How high to lift the pen when not drawing (mm)
PEN_DOWN_Z = 0.0  # Pen on paper (may need slight adjustment)

# Robot orientation (from the trajectory files)
RX = 2.2  # Rotation around X axis
RY = 2.2  # Rotation around Y axis
RZ = 0.0  # Rotation around Z axis


# Load calibration data
CALIBRATION_FILE = "calibration.json"  # Path to calibration file

# A4 paper dimensions in mm
A4_WIDTH = 210.0
A4_HEIGHT = 297.0

# Path optimization settings
PATH_OPTIMIZATION = True  # Whether to optimize paths
PATH_TOLERANCE = 0.5  # Maximum distance (mm) to consider points connected
MAX_SEGMENTS_PER_PATH = 1000  # Maximum number of segments in a single path


class RobotConfig:
    """Class to handle robot configuration including calibration data"""
    def __init__(self, calibration_file=CALIBRATION_FILE):
        self.calibration_file = calibration_file
        # Default values in case calibration file is not found
        self.center_x = 0.0
        self.center_y = 0.0
        self.z_surface = 0.0
        self.rx = RX
        self.ry = RY
        self.rz = RZ
        self.home_position = [-37, -295, -42, 2.2, 2.2, 0]
        self.default_speed = 0.1
        self.default_acc = 0.5
        self.robot_ip = "10.150.0.1"
        self.robot_port = 30002
        
        # Load calibration data
        self.load_calibration()
    
    def load_calibration(self):
        """Load calibration data from JSON file"""
        try:
            if os.path.exists(self.calibration_file):
                with open(self.calibration_file, 'r') as f:
                    calibration = json.load(f)
                
                self.z_surface = calibration.get('drawing_surface', self.z_surface)
                self.home_position = calibration.get('home_position', self.home_position)
                self.default_speed = calibration.get('default_speed', self.default_speed)
                self.default_acc = calibration.get('default_acc', self.default_acc)
                self.robot_ip = calibration.get('robot_ip', self.robot_ip)
                self.robot_port = calibration.get('robot_port', self.robot_port)
                
                # Extract center position from home position (assuming X and Y from home position)
                self.center_x = self.home_position[0]
                self.center_y = self.home_position[1]
                
                # Extract rotation values if present in home position
                if len(self.home_position) >= 6:
                    self.rx = self.home_position[3]
                    self.ry = self.home_position[4]
                    self.rz = self.home_position[5]
                
                logger.info(f"Calibration data loaded from {self.calibration_file}")
                logger.info(f"Drawing surface Z: {self.z_surface}")
                logger.info(f"Center position: X={self.center_x}, Y={self.center_y}")
            else:
                logger.warning(f"Calibration file {self.calibration_file} not found, using defaults")
        except Exception as e:
            logger.error(f"Error loading calibration data: {str(e)}")
            logger.error("Using default values")


def ensure_directory_exists(file_path):
    """Ensure the directory exists for the given file path"""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        try:
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")
        except Exception as e:
            logger.warning(f"Warning: Could not create directory {directory}: {str(e)}")


class SVGToTrajectoryConverter:
    def __init__(self, robot_config):
        """
        Initialize converter with robot configuration
        """
        self.robot_config = robot_config
        self.scale_factor = DRAWING_SCALE
        self.preserve_aspect_ratio = PRESERVE_ASPECT_RATIO
        self.offset_x = DRAWING_OFFSET_X
        self.offset_y = DRAWING_OFFSET_Y
        self.pen_up_z = PEN_UP_Z
        self.pen_down_z = PEN_DOWN_Z
    
    def create_svg_files(self):
        """Create default SVG samples if they don't exist"""
        # Create drawings directory if it doesn't exist
        drawings_dir = os.path.dirname(INPUT_SVG_FILE)
        if not drawings_dir:
            drawings_dir = "svg"
        os.makedirs(drawings_dir, exist_ok=True)
        
        # Create sample SVG files
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
        
        logger.info(f"Default SVG files created in the {drawings_dir} directory")
    
    def create_square_svg(self, filename):
        """Create a square SVG file"""
        svg_content = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <path style="fill:none;stroke:#000000;stroke-width:1px;" d="M 50,50 L 150,50 L 150,150 L 50,150 Z" />
</svg>"""
        
        with open(filename, 'w') as f:
            f.write(svg_content)
    
    def create_circle_svg(self, filename):
        """Create a circle SVG file"""
        svg_content = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <circle style="fill:none;stroke:#000000;stroke-width:1px;" cx="105" cy="148.5" r="50" />
</svg>"""
        
        with open(filename, 'w') as f:
            f.write(svg_content)
    
    def create_spiral_svg(self, filename):
        """Create a spiral SVG file"""
        # Generate spiral path
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
        """Create a star SVG file"""
        svg_content = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <path style="fill:none;stroke:#000000;stroke-width:1px;" d="M 105,98.5 L 120,133.5 L 155,133.5 L 130,153.5 L 140,188.5 L 105,168.5 L 70,188.5 L 80,153.5 L 55,133.5 L 90,133.5 Z" />
</svg>"""
        
        with open(filename, 'w') as f:
            f.write(svg_content)
    
    def create_diamond_svg(self, filename):
        """Create a diamond SVG file"""
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
        """Create a simple diamond shape"""
        svg_content = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <path style="fill:none;stroke:#000000;stroke-width:1px;" d="M 105,80 L 140,148.5 L 105,217 L 70,148.5 Z" />
</svg>"""
        
        with open(filename, 'w') as f:
            f.write(svg_content)
    
    def create_triangle_svg(self, filename):
        """Create a triangle SVG file"""
        svg_content = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <path style="fill:none;stroke:#000000;stroke-width:1px;" d="M 55,180 L 105,80 L 155,180 Z" />
</svg>"""
        
        with open(filename, 'w') as f:
            f.write(svg_content)
    
    def create_grid_svg(self, filename):
        """Create a grid SVG file"""
        # Generate grid path
        grid_path = ""
        # Horizontal lines
        for y in range(60, 201, 20):
            grid_path += f"M 40,{y} L 170,{y} "
        
        # Vertical lines
        for x in range(40, 171, 20):
            grid_path += f"M {x},60 L {x},200 "
        
        svg_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <path style="fill:none;stroke:#000000;stroke-width:1px;" d="{grid_path}" />
</svg>"""
        
        with open(filename, 'w') as f:
            f.write(svg_content)
    
    def create_zigzag_svg(self, filename):
        """Create a zigzag SVG file"""
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
        """Create a starburst pattern SVG file"""
        starburst_path = ""
        center_x, center_y = 105, 148.5
        
        # Create rays from center
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
        """Create a simple temple outline SVG file"""
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
    
    def parse_svg_path(self, svg_file):
        """Parse SVG file and extract path data"""
        try:
            # Check if file exists
            if not os.path.exists(svg_file):
                logger.error(f"SVG file {svg_file} not found")
                return []
                
            # Parse SVG file
            tree = ET.parse(svg_file)
            root = tree.getroot()
            
            # Find SVG namespace
            namespace = '{http://www.w3.org/2000/svg}'
            if root.tag.startswith('{'):
                namespace = '{' + root.tag.split('}')[0][1:] + '}'
            
            # Extract paths
            drawing_commands = []
            
            # Process <path> elements
            for path in root.findall(f'.//{namespace}path'):
                d = path.get('d')
                if d:
                    logger.info(f"Found path with d attribute: {d[:50]}...")
                    drawing_commands.extend(self.parse_path_data(d))
            
            # Process <circle> elements
            for circle in root.findall(f'.//{namespace}circle'):
                cx = float(circle.get('cx', 0))
                cy = float(circle.get('cy', 0))
                r = float(circle.get('r', 0))
                
                logger.info(f"Found circle: cx={cx}, cy={cy}, r={r}")
                
                # Create path commands for circle
                circle_cmds = self.circle_to_commands(cx, cy, r)
                drawing_commands.extend(circle_cmds)
            
            # Process <rect> elements
            for rect in root.findall(f'.//{namespace}rect'):
                x = float(rect.get('x', 0))
                y = float(rect.get('y', 0))
                width = float(rect.get('width', 0))
                height = float(rect.get('height', 0))
                
                logger.info(f"Found rectangle: x={x}, y={y}, width={width}, height={height}")
                
                # Create path commands for rectangle (ensuring it's closed)
                rect_cmds = [
                    ('move', x, y),
                    ('line', x + width, y),
                    ('line', x + width, y + height),
                    ('line', x, y + height),
                    ('line', x, y)  # Close the rectangle by returning to starting point
                ]
                drawing_commands.extend(rect_cmds)
            
            # Process <line> elements
            for line in root.findall(f'.//{namespace}line'):
                x1 = float(line.get('x1', 0))
                y1 = float(line.get('y1', 0))
                x2 = float(line.get('x2', 0))
                y2 = float(line.get('y2', 0))
                
                logger.info(f"Found line: ({x1},{y1}) to ({x2},{y2})")
                
                # Create path commands for line
                line_cmds = [
                    ('move', x1, y1),
                    ('line', x2, y2)
                ]
                drawing_commands.extend(line_cmds)
            
            # Process <polyline> elements
            for polyline in root.findall(f'.//{namespace}polyline'):
                points = polyline.get('points', '')
                if points:
                    logger.info(f"Found polyline: points={points[:50]}...")
                    
                    # Parse points and create commands
                    point_list = []
                    for point_pair in points.replace(',', ' ').strip().split():
                        if ' ' in point_pair:
                            x, y = point_pair.split()
                        else:
                            # Try to split it into pairs
                            coords = points.replace(',', ' ').strip().split()
                            if len(coords) % 2 == 0:
                                point_list = [(float(coords[i]), float(coords[i+1])) for i in range(0, len(coords), 2)]
                                break
                    
                    if point_list:
                        # First point is a move, rest are lines
                        x, y = point_list[0]
                        poly_cmds = [('move', x, y)]
                        for x, y in point_list[1:]:
                            poly_cmds.append(('line', x, y))
                        drawing_commands.extend(poly_cmds)
            
            # Process <polygon> elements (like polyline but closed)
            for polygon in root.findall(f'.//{namespace}polygon'):
                points = polygon.get('points', '')
                if points:
                    logger.info(f"Found polygon: points={points[:50]}...")
                    
                    # Parse points and create commands
                    point_list = []
                    for point_pair in points.replace(',', ' ').strip().split():
                        if ' ' in point_pair:
                            x, y = point_pair.split()
                            point_list.append((float(x), float(y)))
                        else:
                            # Try to split it into pairs
                            coords = points.replace(',', ' ').strip().split()
                            if len(coords) % 2 == 0:
                                point_list = [(float(coords[i]), float(coords[i+1])) for i in range(0, len(coords), 2)]
                                break
                    
                    if point_list:
                        # First point is a move, rest are lines, close with a line back to first point
                        x, y = point_list[0]
                        poly_cmds = [('move', x, y)]
                        for x, y in point_list[1:]:
                            poly_cmds.append(('line', x, y))
                        # Close the polygon
                        poly_cmds.append(('line', point_list[0][0], point_list[0][1]))
                        drawing_commands.extend(poly_cmds)
            
            # Check if we found any drawing commands
            if not drawing_commands:
                logger.warning("No path elements found in SVG file")
            else:
                logger.info(f"Found {len(drawing_commands)} drawing commands")
            
            return drawing_commands
            
        except ET.ParseError as e:
            logger.error(f"XML parsing error in SVG file: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error parsing SVG file: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def circle_to_commands(self, cx, cy, r, num_segments=36):
        """Convert circle to a series of drawing commands"""
        commands = []
        
        # Add initial move to first point
        angle = 0
        x = cx + r * math.cos(math.radians(angle))
        y = cy + r * math.sin(math.radians(angle))
        commands.append(('move', x, y))
        
        # Add line commands for each segment
        for i in range(1, num_segments + 1):
            angle = (i * 360) / num_segments
            x = cx + r * math.cos(math.radians(angle))
            y = cy + r * math.sin(math.radians(angle))
            commands.append(('line', x, y))
        
        return commands
    
    def parse_path_data(self, path_d):
        """Parse SVG path data into drawing commands"""
        drawing_commands = []
        
        # Normalize path data - add spaces around command letters
        for cmd in "MLHVCSQTAZmlhvcsqtaz":
            path_d = path_d.replace(cmd, f" {cmd} ")
        
        # Split path data into tokens
        tokens = path_d.replace(',', ' ').split()
        
        current_cmd = None
        abs_position = [0, 0]  # Current absolute position
        start_position = [0, 0]  # Starting position of the current subpath
        first_position = [0, 0]  # First point in the path (for Z commands)
        
        i = 0
        while i < len(tokens):
            # Check if token is a command letter
            if tokens[i] in "MLHVCSQTAZmlhvcsqtaz":
                current_cmd = tokens[i]
                i += 1
                continue
            
            # Process commands
            if current_cmd in "Mm":  # Move commands
                if i + 1 < len(tokens):
                    try:
                        x = float(tokens[i])
                        y = float(tokens[i+1])
                        
                        # Adjust relative coordinates
                        if current_cmd == 'm':
                            x += abs_position[0]
                            y += abs_position[1]
                        
                        # First move in the path
                        if len(drawing_commands) == 0 or drawing_commands[-1][0] == 'move':
                            first_position = [x, y]
                        
                        abs_position = [x, y]
                        start_position = [x, y]  # Update start position
                        drawing_commands.append(('move', x, y))
                        i += 2
                    except ValueError:
                        i += 1
                else:
                    i += 1
            
            elif current_cmd in "Ll":  # Line commands
                if i + 1 < len(tokens):
                    try:
                        x = float(tokens[i])
                        y = float(tokens[i+1])
                        
                        # Adjust relative coordinates
                        if current_cmd == 'l':
                            x += abs_position[0]
                            y += abs_position[1]
                        
                        abs_position = [x, y]
                        drawing_commands.append(('line', x, y))
                        i += 2
                    except ValueError:
                        i += 1
                else:
                    i += 1
            
            elif current_cmd in "Hh":  # Horizontal line commands
                if i < len(tokens):
                    try:
                        x = float(tokens[i])
                        
                        # Adjust relative coordinates
                        if current_cmd == 'h':
                            x += abs_position[0]
                        
                        abs_position = [x, abs_position[1]]
                        drawing_commands.append(('line', x, abs_position[1]))
                        i += 1
                    except ValueError:
                        i += 1
                else:
                    i += 1
            
            elif current_cmd in "Vv":  # Vertical line commands
                if i < len(tokens):
                    try:
                        y = float(tokens[i])
                        
                        # Adjust relative coordinates
                        if current_cmd == 'v':
                            y += abs_position[1]
                        
                        abs_position = [abs_position[0], y]
                        drawing_commands.append(('line', abs_position[0], y))
                        i += 1
                    except ValueError:
                        i += 1
                else:
                    i += 1
            
            elif current_cmd in "Zz":  # Close path commands
                # Draw line back to the starting point of current subpath
                # Use 'line' to ensure path is closed properly
                if abs_position != first_position and len(drawing_commands) > 0:
                    drawing_commands.append(('line', first_position[0], first_position[1]))
                    abs_position = list(first_position)
                i += 1
            
            # Bezier curve commands - simplified as linear segments
            elif current_cmd in "Cc" and i + 5 < len(tokens):  # Cubic Bezier
                try:
                    x1 = float(tokens[i])
                    y1 = float(tokens[i+1])
                    x2 = float(tokens[i+2])
                    y2 = float(tokens[i+3])
                    x = float(tokens[i+4])
                    y = float(tokens[i+5])
                    
                    # Adjust relative coordinates
                    if current_cmd == 'c':
                        x1 += abs_position[0]
                        y1 += abs_position[1]
                        x2 += abs_position[0]
                        y2 += abs_position[1]
                        x += abs_position[0]
                        y += abs_position[1]
                    
                    # Approximate Bezier curve with line segments
                    self.approximate_bezier_curve(drawing_commands, abs_position[0], abs_position[1], 
                                                 x1, y1, x2, y2, x, y)
                    
                    abs_position = [x, y]
                    i += 6
                except ValueError:
                    i += 1
            
            elif current_cmd in "Ss" and i + 3 < len(tokens):  # Smooth cubic Bezier
                try:
                    # Calculate reflection of second control point
                    x1 = abs_position[0] + (abs_position[0] - float(tokens[i-2]) if i >= 2 else 0)
                    y1 = abs_position[1] + (abs_position[1] - float(tokens[i-1]) if i >= 2 else 0)
                    
                    x2 = float(tokens[i])
                    y2 = float(tokens[i+1])
                    x = float(tokens[i+2])
                    y = float(tokens[i+3])
                    
                    # Adjust relative coordinates
                    if current_cmd == 's':
                        x2 += abs_position[0]
                        y2 += abs_position[1]
                        x += abs_position[0]
                        y += abs_position[1]
                    
                    # Approximate Bezier curve with line segments
                    self.approximate_bezier_curve(drawing_commands, abs_position[0], abs_position[1], 
                                                 x1, y1, x2, y2, x, y)
                    
                    abs_position = [x, y]
                    i += 4
                except ValueError:
                    i += 1
            
            elif current_cmd in "Qq" and i + 3 < len(tokens):  # Quadratic Bezier
                try:
                    x1 = float(tokens[i])
                    y1 = float(tokens[i+1])
                    x = float(tokens[i+2])
                    y = float(tokens[i+3])
                    
                    # Adjust relative coordinates
                    if current_cmd == 'q':
                        x1 += abs_position[0]
                        y1 += abs_position[1]
                        x += abs_position[0]
                        y += abs_position[1]
                    
                    # Convert quadratic to cubic Bezier for consistent handling
                    cx1 = abs_position[0] + 2/3 * (x1 - abs_position[0])
                    cy1 = abs_position[1] + 2/3 * (y1 - abs_position[1])
                    cx2 = x + 2/3 * (x1 - x)
                    cy2 = y + 2/3 * (y1 - y)
                    
                    # Approximate Bezier curve with line segments
                    self.approximate_bezier_curve(drawing_commands, abs_position[0], abs_position[1], 
                                                 cx1, cy1, cx2, cy2, x, y)
                    
                    abs_position = [x, y]
                    i += 4
                except ValueError:
                    i += 1
            
            elif current_cmd in "Tt" and i + 1 < len(tokens):  # Smooth quadratic Bezier
                try:
                    # Calculate reflection of control point
                    x1 = 2 * abs_position[0] - x1 if 'x1' in locals() else abs_position[0]
                    y1 = 2 * abs_position[1] - y1 if 'y1' in locals() else abs_position[1]
                    
                    x = float(tokens[i])
                    y = float(tokens[i+1])
                    
                    # Adjust relative coordinates
                    if current_cmd == 't':
                        x += abs_position[0]
                        y += abs_position[1]
                    
                    # Convert quadratic to cubic Bezier for consistent handling
                    cx1 = abs_position[0] + 2/3 * (x1 - abs_position[0])
                    cy1 = abs_position[1] + 2/3 * (y1 - abs_position[1])
                    cx2 = x + 2/3 * (x1 - x)
                    cy2 = y + 2/3 * (y1 - y)
                    
                    # Approximate Bezier curve with line segments
                    self.approximate_bezier_curve(drawing_commands, abs_position[0], abs_position[1], 
                                                 cx1, cy1, cx2, cy2, x, y)
                    
                    abs_position = [x, y]
                    i += 2
                except ValueError:
                    i += 1
                    
            elif current_cmd in "Aa" and i + 6 < len(tokens):  # Arc commands
                try:
                    rx = float(tokens[i])
                    ry = float(tokens[i+1])
                    angle = float(tokens[i+2])
                    large_arc = int(float(tokens[i+3]))
                    sweep = int(float(tokens[i+4]))
                    x = float(tokens[i+5])
                    y = float(tokens[i+6])
                    
                    # Adjust relative coordinates
                    if current_cmd == 'a':
                        x += abs_position[0]
                        y += abs_position[1]
                    
                    # Approximate arc with line segments
                    self.approximate_arc(drawing_commands, abs_position[0], abs_position[1], 
                                       rx, ry, angle, large_arc, sweep, x, y)
                    
                    abs_position = [x, y]
                    i += 7
                except ValueError:
                    i += 1
            
            else:
                # Skip unknown or incomplete commands
                i += 1
        
        return drawing_commands
    
    def approximate_bezier_curve(self, commands, x0, y0, x1, y1, x2, y2, x3, y3, steps=10):
        """Approximate cubic Bezier curve with line segments"""
        for i in range(1, steps + 1):
            t = i / steps
            # Cubic Bezier formula
            x = (1-t)**3 * x0 + 3*(1-t)**2*t * x1 + 3*(1-t)*t**2 * x2 + t**3 * x3
            y = (1-t)**3 * y0 + 3*(1-t)**2*t * y1 + 3*(1-t)*t**2 * y2 + t**3 * y3
            commands.append(('line', x, y))
    
    def approximate_arc(self, commands, x0, y0, rx, ry, angle, large_arc, sweep, x, y, steps=20):
        """Approximate elliptical arc with line segments"""
        # Implementation based on SVG spec conversion to center parameterization
        # See: https://www.w3.org/TR/SVG/implnote.html#ArcConversionEndpointToCenter
        
        # Handle degenerate case
        if x0 == x and y0 == y:
            return
            
        # Ensure radii are positive
        rx = abs(rx)
        ry = abs(ry)
        
        # If rx or ry is 0, treat as a straight line
        if rx == 0 or ry == 0:
            commands.append(('line', x, y))
            return
            
        # Convert angle from degrees to radians
        angle_rad = math.radians(angle)
        cos_angle = math.cos(angle_rad)
        sin_angle = math.sin(angle_rad)
        
        # Step 1: Compute transformed coordinates
        dx = (x0 - x) / 2
        dy = (y0 - y) / 2
        x1d = cos_angle * dx + sin_angle * dy
        y1d = -sin_angle * dx + cos_angle * dy
        
        # Step 2: Ensure radii are large enough
        radii_check = (x1d**2 / rx**2) + (y1d**2 / ry**2)
        if radii_check > 1:
            # Scale up rx and ry
            rx *= math.sqrt(radii_check)
            ry *= math.sqrt(radii_check)
        
        # Step 3: Compute center
        sq = ((rx**2 * ry**2) - (rx**2 * y1d**2) - (ry**2 * x1d**2)) / ((rx**2 * y1d**2) + (ry**2 * x1d**2))
        sq = max(0, sq)  # Ensure non-negative
        coef = math.sqrt(sq)
        if large_arc == sweep:
            coef = -coef
        cxd = coef * rx * y1d / ry
        cyd = -coef * ry * x1d / rx
        
        # Transform center back
        cx = cos_angle * cxd - sin_angle * cyd + (x0 + x) / 2
        cy = sin_angle * cxd + cos_angle * cyd + (y0 + y) / 2
        
        # Step 4: Compute start and end angles
        ux = (x1d - cxd) / rx
        uy = (y1d - cyd) / ry
        vx = (-x1d - cxd) / rx
        vy = (-y1d - cyd) / ry
        
        # Compute start angle
        start_angle = math.atan2(uy, ux)
        
        # Compute angle extent
        n = math.sqrt((ux**2 + uy**2) * (vx**2 + vy**2))
        p = ux * vx + uy * vy
        d = p / n
        d = max(-1, min(1, d))  # Ensure -1 <= d <= 1
        
        angle_extent = math.acos(d)
        if ux * vy - uy * vx < 0:
            angle_extent = -angle_extent
            
        if sweep == 0 and angle_extent > 0:
            angle_extent -= 2 * math.pi
        elif sweep == 1 and angle_extent < 0:
            angle_extent += 2 * math.pi
            
        # Create line segments to approximate the arc
        for i in range(1, steps + 1):
            t = i / steps
            angle = start_angle + t * angle_extent
            
            # Compute point on ellipse
            px = cx + rx * math.cos(angle) * cos_angle - ry * math.sin(angle) * sin_angle
            py = cy + rx * math.cos(angle) * sin_angle + ry * math.sin(angle) * cos_angle
            
            commands.append(('line', px, py))
    
    def optimize_paths(self, drawing_commands):
        """
        Optimize drawing commands by converting unnecessary 'move' to 'line'
        when points are close enough to be considered continuous
        """
        if not PATH_OPTIMIZATION or not drawing_commands:
            return drawing_commands
            
        optimized = []
        current_path = []
        
        for i, cmd in enumerate(drawing_commands):
            cmd_type, x, y = cmd
            
            # Start a new path with a move command
            if cmd_type == 'move':
                # If we have a current path, add it to the optimized list
                if current_path:
                    optimized.extend(current_path)
                    current_path = []
                
                # Check if we should connect to the previous point
                if (i > 0 and len(optimized) > 0 and 
                    self.distance(optimized[-1][1], optimized[-1][2], x, y) <= PATH_TOLERANCE):
                    # Convert to line if it's close enough to the last point
                    optimized.append(('line', x, y))
                else:
                    # Otherwise use a move command
                    current_path.append(('move', x, y))
            else:  # Line command
                # Add to current path
                current_path.append((cmd_type, x, y))
                
                # Check if we reached the maximum segments in a path
                if len(current_path) >= MAX_SEGMENTS_PER_PATH:
                    optimized.extend(current_path)
                    current_path = []
        
        # Add any remaining path
        if current_path:
            optimized.extend(current_path)
        
        logger.info(f"Path optimization: {len(drawing_commands)} -> {len(optimized)} commands")
        return optimized
    
    def distance(self, x1, y1, x2, y2):
        """Calculate Euclidean distance between two points"""
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    
    def detect_closed_paths(self, drawing_commands):
        """
        Detect closed paths and ensure they are properly closed
        by converting final move to line if needed
        """
        if not drawing_commands:
            return drawing_commands
            
        result = []
        path_start = None
        
        for cmd in drawing_commands:
            cmd_type, x, y = cmd
            
            if cmd_type == 'move':
                # If we have a path start and the current command is a move
                if path_start is not None:
                    # Check if the last point is close to the path start
                    last_cmd = result[-1]
                    last_x, last_y = last_cmd[1], last_cmd[2]
                    
                    # If the last point is close to the path start but not exactly at it
                    if (self.distance(last_x, last_y, path_start[0], path_start[1]) < PATH_TOLERANCE and
                        (last_x != path_start[0] or last_y != path_start[1])):
                        # Add a line to close the path properly
                        result.append(('line', path_start[0], path_start[1]))
                
                # Start a new path
                path_start = (x, y)
            
            result.append(cmd)
        
        # Check if the last path should be closed
        if path_start is not None and len(result) > 0:
            last_cmd = result[-1]
            last_x, last_y = last_cmd[1], last_cmd[2]
            
            if (self.distance(last_x, last_y, path_start[0], path_start[1]) < PATH_TOLERANCE and
                (last_x != path_start[0] or last_y != path_start[1])):
                # Add a line to close the path properly
                result.append(('line', path_start[0], path_start[1]))
        
        return result
    
    def scale_to_robot_coordinates(self, drawing_commands):
        """Scale and convert SVG drawing commands to robot coordinates"""
        if not drawing_commands:
            return []
            
        # Find the bounding box of the drawing
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for cmd in drawing_commands:
            if cmd[0] in ('move', 'line'):
                x, y = cmd[1], cmd[2]
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
        
        # Calculate sizes and centers
        svg_width = max_x - min_x
        svg_height = max_y - min_y
        svg_center_x = min_x + svg_width / 2
        svg_center_y = min_y + svg_height / 2
        
        logger.info(f"Drawing bounds: X=[{min_x}, {max_x}], Y=[{min_y}, {max_y}]")
        logger.info(f"Drawing size: {svg_width} x {svg_height}")
        
        # Calculate scaling factors
        # Default to maintaining aspect ratio unless specified otherwise
        if self.preserve_aspect_ratio:
            # Use the smaller scaling factor to maintain aspect ratio
            scale_x = scale_y = min(A4_WIDTH / svg_width, A4_HEIGHT / svg_height) * self.scale_factor
        else:
            # Scale X and Y independently
            scale_x = A4_WIDTH / svg_width * self.scale_factor
            scale_y = A4_HEIGHT / svg_height * self.scale_factor
        
        logger.info(f"Scaling factors: X={scale_x}, Y={scale_y}")
        
        # Transform drawing commands to robot coordinates
        robot_commands = []
        
        for cmd in drawing_commands:
            if cmd[0] in ('move', 'line'):
                # Center the drawing on the robot's drawing surface
                x_centered = (cmd[1] - svg_center_x) * scale_x
                y_centered = (cmd[2] - svg_center_y) * scale_y
                
                # Apply robot coordinate system transformation
                # Note: The robot coordinate system has Z pointing up
                robot_x = self.robot_config.center_x + x_centered + self.offset_x
                robot_y = self.robot_config.center_y + y_centered + self.offset_y
                
                robot_commands.append((cmd[0], robot_x, robot_y))
        
        logger.info(f"Transformed {len(robot_commands)} commands to robot coordinates")
        return robot_commands
    
    def generate_trajectory(self, robot_commands):
        """Generate robot trajectory from scaled commands"""
        if not robot_commands:
            return []
        
        trajectory = []
        pen_state = "up"  # Track pen state to avoid unnecessary moves
        current_x = current_y = None  # Track current position
        
        for cmd in robot_commands:
            cmd_type, x, y = cmd
            
            if cmd_type == 'move':
                # If pen is down, lift it first
                if pen_state == "down" and current_x is not None and current_y is not None:
                    # Add a point to lift the pen at the current position
                    lift_pose = [
                        current_x, 
                        current_y, 
                        self.robot_config.z_surface + self.pen_up_z,
                        self.robot_config.rx,
                        self.robot_config.ry,
                        self.robot_config.rz
                    ]
                    trajectory.append(('move', lift_pose))
                    pen_state = "up"
                
                # Move to the new position with pen up
                pose = [
                    x,  # X
                    y,  # Y
                    self.robot_config.z_surface + self.pen_up_z,  # Z (pen up)
                    self.robot_config.rx,
                    self.robot_config.ry,
                    self.robot_config.rz
                ]
                trajectory.append(('move', pose))
                current_x, current_y = x, y
                
            elif cmd_type == 'line':
                # If pen is up, lower it at the current position before drawing line
                if pen_state == "up" and current_x is not None and current_y is not None:
                    lower_pose = [
                        current_x, 
                        current_y, 
                        self.robot_config.z_surface + self.pen_down_z,
                        self.robot_config.rx,
                        self.robot_config.ry,
                        self.robot_config.rz
                    ]
                    trajectory.append(('line', lower_pose))
                    pen_state = "down"
                
                # Draw line to the new position
                pose = [
                    x,  # X
                    y,  # Y
                    self.robot_config.z_surface + self.pen_down_z,  # Z (pen down)
                    self.robot_config.rx,
                    self.robot_config.ry,
                    self.robot_config.rz
                ]
                trajectory.append(('line', pose))
                current_x, current_y = x, y
                pen_state = "down"
        
        # Always end with pen up
        if pen_state == "down" and current_x is not None and current_y is not None:
            final_pose = [
                current_x, 
                current_y, 
                self.robot_config.z_surface + self.pen_up_z,
                self.robot_config.rx,
                self.robot_config.ry,
                self.robot_config.rz
            ]
            trajectory.append(('move', final_pose))
        
        # Add a final move to a safe position above the drawing
        if trajectory:
            safe_x = self.robot_config.home_position[0]
            safe_y = self.robot_config.home_position[1]
            safe_z = self.robot_config.home_position[2]
            safe_pose = [
                safe_x,
                safe_y,
                safe_z,
                self.robot_config.rx,
                self.robot_config.ry,
                self.robot_config.rz
            ]
            trajectory.append(('move', safe_pose))
        
        logger.info(f"Generated trajectory with {len(trajectory)} points")
        return trajectory
    
    def convert_svg_to_trajectory(self, svg_file):
        """Convert SVG file to robot trajectory"""
        # Parse SVG file
        logger.info(f"Parsing SVG file: {svg_file}")
        drawing_commands = self.parse_svg_path(svg_file)
        
        if not drawing_commands:
            logger.error("No drawing commands found in SVG file")
            return []
        
        logger.info(f"Extracted {len(drawing_commands)} drawing commands")
        
        # Detect and fix closed paths
        drawing_commands = self.detect_closed_paths(drawing_commands)
        logger.info(f"After closing paths: {len(drawing_commands)} commands")
        
        # Optimize paths by converting unnecessary moves to lines
        if PATH_OPTIMIZATION:
            drawing_commands = self.optimize_paths(drawing_commands)
            logger.info(f"After path optimization: {len(drawing_commands)} commands")
        
        # Scale commands to robot coordinates
        logger.info("Scaling to robot coordinates...")
        robot_commands = self.scale_to_robot_coordinates(drawing_commands)
        
        if not robot_commands:
            logger.error("Failed to scale drawing commands")
            return []
        
        # Generate robot trajectory
        logger.info("Generating robot trajectory...")
        trajectory = self.generate_trajectory(robot_commands)
        
        logger.info(f"Conversion complete. Trajectory has {len(trajectory)} points")
        return trajectory
    
    def save_trajectory(self, trajectory, output_file):
        """Save trajectory to JSON file"""
        if not trajectory:
            logger.error("No trajectory to save")
            return False
        
        try:
            # Ensure output directory exists
            ensure_directory_exists(output_file)
            
            # Convert trajectory to serializable format
            # Format matches the expected format from the provided example JSON files
            serializable_trajectory = []
            for _, pose in trajectory:
                # Format all values to clean floats with 2 decimal places
                formatted_pose = [float(f"{p:.2f}") for p in pose]
                serializable_trajectory.append([formatted_pose])
            
            with open(output_file, 'w') as f:
                json.dump(serializable_trajectory, f, indent=4)
            
            logger.info(f"Trajectory saved to {output_file}")
            print(f"Saved {len(serializable_trajectory)} points to trajectory file")
            return True
            
        except Exception as e:
            logger.error(f"Error saving trajectory: {str(e)}")
            # Try to save to a fallback location
            try:
                fallback_file = os.path.basename(output_file)
                with open(fallback_file, 'w') as f:
                    json.dump(serializable_trajectory, f, indent=4)
                logger.info(f"Trajectory saved to fallback location: {fallback_file}")
                print(f"Saved {len(serializable_trajectory)} points to fallback file: {fallback_file}")
                return True
            except Exception as e2:
                logger.error(f"Fallback save also failed: {str(e2)}")
                return False


def main():
    """Main function to run the SVG to trajectory converter"""
    global OUTPUT_TRAJECTORY_FILE
    
    # Banner
    print("=" * 70)
    print("SVG to Robot Trajectory Converter for UR3e")
    print("=" * 70)
    
    # Load robot configuration
    print("Loading robot configuration...")
    robot_config = RobotConfig(CALIBRATION_FILE)
    
    # Create converter
    converter = SVGToTrajectoryConverter(robot_config)
    
    # Create sample SVG files if they don't exist
    print("Checking for sample SVG files...")
    converter.create_svg_files()
    
    # Check if input file exists
    if not os.path.exists(INPUT_SVG_FILE):
        print(f"Error: SVG file {INPUT_SVG_FILE} not found.")
        # Try to list available SVG files
        try:
            drawings_dir = os.path.dirname(INPUT_SVG_FILE)
            if not drawings_dir:
                drawings_dir = "svg"
            if os.path.exists(drawings_dir):
                print(f"\nAvailable SVG files in {drawings_dir}:")
                for file in os.listdir(drawings_dir):
                    if file.endswith(".svg"):
                        print(f"  - {os.path.join(drawings_dir, file)}")
            else:
                print(f"\nThe directory {drawings_dir} does not exist. Run the script first to create it with samples.")
        except Exception:
            pass
        return
    
    # Set output file if not specified
    if OUTPUT_TRAJECTORY_FILE is None:
        base_name = os.path.splitext(INPUT_SVG_FILE)[0]
        OUTPUT_TRAJECTORY_FILE = base_name + '.json'
    
    print(f"Input SVG: {INPUT_SVG_FILE}")
    print(f"Output JSON: {OUTPUT_TRAJECTORY_FILE}")
    print(f"Drawing scale: {DRAWING_SCALE}")
    print(f"Preserve aspect ratio: {PRESERVE_ASPECT_RATIO}")
    print(f"Path optimization: {PATH_OPTIMIZATION}")
    
    # Convert SVG to trajectory
    print("\nConverting SVG to robot trajectory...")
    trajectory = converter.convert_svg_to_trajectory(INPUT_SVG_FILE)
    
    if not trajectory:
        print("Error: Failed to convert SVG to trajectory.")
        return
    
    print(f"Generated trajectory with {len(trajectory)} points.")
    
    # Save trajectory
    print("Saving trajectory...")
    if converter.save_trajectory(trajectory, OUTPUT_TRAJECTORY_FILE):
        print(f"Trajectory saved to {OUTPUT_TRAJECTORY_FILE}")
        print("\nSuccess! You can now use this trajectory with your UR3e robot.")
    else:
        print("Error: Failed to save trajectory.")


if __name__ == "__main__":
    main()