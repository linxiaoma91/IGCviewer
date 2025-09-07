import numpy as np
import cv2
import os
import matplotlib.pyplot as plt
import contextily as ctx

def get_basemap(min_lon, max_lon, min_lat, max_lat):
    if os.path.exists("basemap.png"):
        image_path = "basemap.png"  # Replace with your image path
        basemap = cv2.imread(image_path)
        # basemap = cv2.cvtColor(basemap, cv2.COLOR_RGB2BGR)
    else:
        fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100, layout='constrained')
        ax.set_aspect('equal')
        ax.set_xlim(min_lon, max_lon)
        ax.set_ylim(min_lat, max_lat)
        ax.set_xticks([])
        ax.set_yticks([])
        ctx.add_basemap(ax, source=ctx.providers.Esri.WorldImagery, crs='EPSG:4326', attribution=False)
        plt.savefig("basemap.png", dpi=100, bbox_inches='tight', pad_inches=0)
        plt.close()

        image_path = "basemap.png"  # Replace with your image path
        basemap = cv2.imread(image_path)
        # basemap = cv2.cvtColor(basemap, cv2.COLOR_RGB2BGR)

    return basemap

def latlon2px(lat, lon, min_lat, max_lat, min_lon, max_lon, img_size_x, img_size_y):
    x = (lon - min_lon) * img_size_x / (max_lon - min_lon)
    y = -(lat - max_lat) * img_size_y / (max_lat - min_lat)
    return int(x), int(y) #Vorher runden!


def draw_circle(img, x, y, r_list, color_list, alpha, angle_list=None):
    """
    Draw circles or circle segments on an image with alpha blending.

    Parameters:
    - img: Input image
    - x, y: Center coordinates
    - r_list: List of radii
    - color_list: List of colors (BGR tuples)
    - alpha: Transparency level (0-1)
    - angle_list: List of (start_angle, end_angle) tuples in degrees (optional)
                  If None, full circles are drawn
                  Angles are measured clockwise from the positive x-axis
    """
    overlay = np.zeros_like(img)
    mask = np.zeros_like(img[:, :, 0])  # Single-channel mask

    img_size_x = img.shape[1]
    img_size_y = img.shape[0]

    # Initialize bounding box to cover all circles/segments
    x1, y1 = img_size_x, img_size_y  # Start with max possible
    x2, y2 = 0, 0  # Start with min possible

    # Find the overall bounding box that contains all circles/segments
    for r in r_list:
        x1 = min(x1, max(0, x - r))
        y1 = min(y1, max(0, y - r))
        x2 = max(x2, min(img_size_x, x + r))
        y2 = max(y2, min(img_size_y, y + r))

    # Skip if no valid region
    if x1 >= x2 or y1 >= y2:
        return img

    # Initialize small_mask and small_overlay for the combined region
    small_mask = np.zeros((y2 - y1, x2 - x1), dtype=np.uint8)
    small_overlay = np.zeros((y2 - y1, x2 - x1, 3), dtype=np.uint8)

    # If angle_list is None, create default full circles (0-360)
    if angle_list is None:
        angle_list = [(0, 360)] * len(r_list)
    elif len(angle_list) != len(r_list):
        raise ValueError("angle_list must have same length as r_list")

    # Draw all circles/segments into the small_mask and small_overlay
    for r, color, (start_angle, end_angle) in zip(r_list, color_list, angle_list):
        # Draw the segment (if start != end, otherwise full circle)
        if start_angle != end_angle:
            cv2.ellipse(small_mask, (x - x1, y - y1), (r, r), 0,
                        start_angle, end_angle, 255, -1)
            cv2.ellipse(small_overlay, (x - x1, y - y1), (r, r), 0,
                        start_angle, end_angle, color, -1)
        else:
            cv2.circle(small_mask, (x - x1, y - y1), r, 255, -1)
            cv2.circle(small_overlay, (x - x1, y - y1), r, color, -1)

    # Blend the entire region at once
    blended_roi = img[y1:y2, x1:x2]
    mask_float = small_mask.astype(float)[:, :, None] / 255.0  # Normalize to [0,1]

    # Apply alpha blending
    img[y1:y2, x1:x2] = (
            blended_roi * (1 - mask_float * alpha) +
            small_overlay * (mask_float * alpha)
    )

    return img