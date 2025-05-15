#!/usr/bin/env python3
# Create an abstract Koch-inspired fractal with ~1000 points

import os
import math
import random

def generate_koch_points(start_x, start_y, end_x, end_y, depth, randomize=False, rand_factor=0.2):
    """
    Generate points for a Koch curve with the given depth.
    Returns a list of points (x,y coordinates).
    
    If randomize is True, adds some randomness to make it more abstract.
    """
    if depth == 0:
        return [(start_x, start_y), (end_x, end_y)]
    
    # Calculate the coordinates of the 4 new points to create from the line segment
    vector_x = end_x - start_x
    vector_y = end_y - start_y
    
    # Calculate 1/3 and 2/3 points along the line
    one_third_x = start_x + vector_x / 3
    one_third_y = start_y + vector_y / 3
    two_thirds_x = start_x + 2 * vector_x / 3
    two_thirds_y = start_y + 2 * vector_y / 3
    
    # Calculate the peak point
    segment_length = math.sqrt(vector_x**2 + vector_y**2) / 3
    
    # Original angle of the line
    original_angle = math.atan2(vector_y, vector_x)
    
    # Add randomness to angle if requested
    peak_angle_offset = math.pi / 3  # Default 60 degrees
    if randomize:
        # Randomize the angle between 40 and 80 degrees
        peak_angle_offset = math.radians(random.uniform(40, 80))
        
        # Also randomize the segment length
        segment_length = segment_length * random.uniform(0.8, 1.2)
    
    # Coordinates of the peak point (rotate vector)
    peak_angle = original_angle - peak_angle_offset
    peak_x = one_third_x + segment_length * math.cos(peak_angle)
    peak_y = one_third_y + segment_length * math.sin(peak_angle)
    
    # Apply randomness to the point positions if requested
    if randomize and random.random() < rand_factor:
        # Randomly adjust points by up to 5% of the segment length
        max_offset = segment_length * 0.05
        one_third_x += random.uniform(-max_offset, max_offset)
        one_third_y += random.uniform(-max_offset, max_offset)
        two_thirds_x += random.uniform(-max_offset, max_offset)
        two_thirds_y += random.uniform(-max_offset, max_offset)
        peak_x += random.uniform(-max_offset, max_offset)
        peak_y += random.uniform(-max_offset, max_offset)
    
    # Recursively generate points for each of the 4 new line segments
    points = []
    points.extend(generate_koch_points(start_x, start_y, one_third_x, one_third_y, depth - 1, randomize, rand_factor)[:-1])
    points.extend(generate_koch_points(one_third_x, one_third_y, peak_x, peak_y, depth - 1, randomize, rand_factor)[:-1])
    points.extend(generate_koch_points(peak_x, peak_y, two_thirds_x, two_thirds_y, depth - 1, randomize, rand_factor)[:-1])
    points.extend(generate_koch_points(two_thirds_x, two_thirds_y, end_x, end_y, depth - 1, randomize, rand_factor))
    
    return points

def create_abstract_koch():
    """Create an abstract Koch-inspired fractal with approximately 1000 points"""
    os.makedirs("svg", exist_ok=True)
    
    # Set SVG viewBox dimensions - standard A4 paper (210x297mm)
    svg_width = 210
    svg_height = 297
    
    # Center position
    center_x = svg_width / 2
    center_y = svg_height / 2
    
    # Create an abstract design based on a hexagon with Koch-like edges
    # The hexagon will have a diameter of about 10cm
    radius = 50  # 5cm radius = 10cm diameter
    num_sides = 6
    
    # Calculate the vertices of the regular hexagon
    vertices = []
    for i in range(num_sides):
        angle = 2 * math.pi * i / num_sides
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        vertices.append((x, y))
    
    # Generate the Koch-like curves for each side of the hexagon
    # We'll use 4 iterations to get approximately 256 points per side
    # With 6 sides, that's around 1500 points in total
    all_points = []
    
    for i in range(num_sides):
        start_x, start_y = vertices[i]
        end_x, end_y = vertices[(i + 1) % num_sides]
        
        # Alternate between regular and randomized Koch curves
        # This creates a more abstract, interesting pattern
        if i % 2 == 0:
            # Regular Koch curve
            points = generate_koch_points(start_x, start_y, end_x, end_y, 4, False)
        else:
            # Randomized Koch curve
            points = generate_koch_points(start_x, start_y, end_x, end_y, 4, True, 0.3)
        
        # Add all points except the last (to avoid duplicates)
        all_points.extend(points[:-1])
    
    # Close the shape
    all_points.append(all_points[0])
    
    # Calculate the number of points for information
    num_points = len(all_points)
    
    # Convert points to SVG path
    path_data = f"M {all_points[0][0]},{all_points[0][1]} "
    for x, y in all_points[1:]:
        path_data += f"L {x},{y} "
    
    # Create SVG content
    svg_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <path style="fill:none;stroke:#000000;stroke-width:0.75px;" d="{path_data}" />
</svg>"""
    
    # Save the SVG file
    with open("svg/abstract_koch.svg", 'w') as f:
        f.write(svg_content)
    
    print(f"Abstract Koch fractal SVG saved to svg/abstract_koch.svg")
    print(f"This design has {num_points} points and is approximately 10cm in diameter")
    print("You can now run your svg_code.py script with this file")

if __name__ == "__main__":
    # Set random seed for reproducibility
    random.seed(42)
    create_abstract_koch()