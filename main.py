import numpy as np
import cv2
from tqdm import tqdm
import random

import igc
import helper_functions
import painter
import dicts
import texter

# load list with all igc files in given folder
igcs = igc.file_loader(folder_paths=["IGC/t6"], use_saved=True )

#load task data dict from a single given igc file
name = "SG"
index = next((i for i, obj in enumerate(igcs) if obj.name == name), None)
checkpoints_dict = igcs[index].get_navdata()

print(checkpoints_dict)

for igc in igcs:
    igc.get_start_time(checkpoints_dict)

map_padding = 0.1 # umlaufender Rand auf der Karte in Winkel-Grad
fasl = 1618 # Referenzhöhe für Berechnung der Marker-Durchmesser

time_mode = "synced" # "abs" = absolute Zeit  or "synced" = synchronisiert auf Start ("synced" needs start_dict)
time_offset = -7200 # UTC auf Ortszeit in Sekunden
time_step = 10 # Zeitschritt in Sekunden zwischen einzelnen Bildern
path_downsampling = 30 # Schritte überspringen beim Zeichnen des zurückgelegten Weges -> spart Rechenzeit

minmax_coords, max_alt, min_time, max_time = helper_functions.get_minmax_values(igcs, map_padding) # suche min und max Werte aus allen igcs

# Clear output folder for images
helper_functions.clear_folder("frames/")

# Kartenansicht erstellen
basemap = painter.get_basemap(minmax_coords)
img_size_y, img_size_x, _ = basemap.shape
print(basemap.shape)

# plot task markers
basemap = painter.draw_taskmarkers(basemap, checkpoints_dict, minmax_coords, img_size_x, img_size_y)

#get dicts for national roundels (fancy für Weltmeisterschaften!)
nations_dict = dicts.nations_dict()
#colors_dict = dicts.colors_dict()
angles_dict = dicts.angles_dict()

start_dict = dicts.start_dict_feuerst_t4()

# Zufällige Farben, falls erforderlich
random.seed(42)
colors_dict = {igc.name: (random.randint(0,256),random.randint(0,256),random.randint(0,256)) for igc in igcs}

total_length = max(len(igc.lats[::time_step]) for igc in igcs)

# Objekte für dynamische Labels, falls zu zittrig, Variablen SANFT verändern
label_manager = texter.TextLabelManager(repulsion_radius=75, attraction_force=0.1, repulsion_force=0.2, damping=0.1)

if time_mode == "synced":
    #min_time = min(int(t[0:2])*3600 + int(t[2:4])*60 + int(t[4:6]) for t in start_dict.values()) + time_offset
    min_time = min(igc.start_time for igc in igcs)
    print("MIN", min_time/3600
          )
elif time_mode == "abs":
    min_time = min_time



### Main Loop ###
for step in tqdm(range(0, int((max_time - min_time) / time_step))):

    if time_mode == "abs": abs_time = int(min_time + step * time_step)
    step_image = basemap.copy()

    # Create a transparent overlay for paths
    path_overlay = np.zeros_like(step_image, dtype=np.uint8)

    text_dict = {}

    for igc in igcs[0:]:

        if time_mode == "synced":


            #start_time = int(start_dict[igc.name][0:2])*3600 + int(start_dict[igc.name][2:4])*60 + int(start_dict[igc.name][4:6])

            start_time = igc.start_time - time_offset

            abs_time = min(start_time + step * time_step + time_offset, np.max(igc.times))

        # Get current position
        if len(igc.lats[np.where(igc.times == abs_time)[0]]) > 0:
            lats = igc.lats[np.where(igc.times == abs_time)[0]][0]
            lons = igc.lons[np.where(igc.times == abs_time)[0]][0]
            alts = igc.alts[np.where(igc.times == abs_time)[0]][0]
            x_loc, y_loc = painter.latlon2px(lats, lons, minmax_coords, img_size_x, img_size_y)
        else:
            continue

        try:
            nation = nations_dict[igc.name]
        except KeyError:
            nation = None

        try:
            color = [(0,0,0), colors_dict[igc.name]] # use nation or name as index
        except KeyError:
            color = [(127,127,127)]*2

        # Get all positions up to current time
        prev_indices = np.where((igc.times >= min_time) & (igc.times <= abs_time))[0]

        if path_downsampling > 1:
            prev_indices = prev_indices[::path_downsampling]
            # Ensure we include the last point (current position)
            if len(prev_indices) == 0 or prev_indices[-1] != np.where(igc.times == abs_time)[0][0]:
                prev_indices = np.append(prev_indices, np.where(igc.times == abs_time)[0][0])


        prev_lats = igc.lats[prev_indices]
        prev_lons = igc.lons[prev_indices]

        # Convert all positions to image coordinates
        path_points = []
        for lat, lon in zip(prev_lats, prev_lons):
            x, y = painter.latlon2px(lat, lon, minmax_coords, img_size_x, img_size_y)
            path_points.append((x, y))

        # Draw the path on the overlay
        if len(path_points) > 1:
            # Use the first color in the list for the path
            path_color = color[0] if isinstance(color[0], tuple) else (127, 127, 127)
            if path_color == (0,0,0): path_color = (127,127,127)

            # Convert points to numpy array in the correct format for polylines
            pts = np.array(path_points, np.int32)
            pts = pts.reshape((-1, 1, 2))

            # Draw the path with anti-aliased line on the overlay
            cv2.polylines(path_overlay, [pts], isClosed=False, color=path_color, thickness=1, lineType=cv2.LINE_AA)

        try:
            angle_list = angles_dict[nation]
        except KeyError:
            angle_list = None

        alts_norm = ((alts - 1000) / (max_alt - 1000))
        radius = 5 + max(0, int(alts_norm * 30))

        if angle_list == None:
            if len(color) == 3:
                r_list = [radius, int(radius * 0.66), int(radius * 0.33)]
            elif len(color) == 2:
                r_list = [radius, radius -2]
        else:
            r_list = [radius] * len(color)

        step_image = painter.draw_circle(step_image, x_loc, y_loc, r_list, color, 0.4, angle_list)

        # Draw label
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        font_thickness = 1
        text_color = (0, 0, 0)

        text_dict[igc.name] = {'pos': (x_loc, y_loc), 'text': igc.name}

    # Blend the path overlay with the main image with transparency
    alpha = 0.3  # Transparenz der Pfade
    step_image = cv2.addWeighted(step_image, 1, path_overlay, alpha, 0)

    for obj_id, obj_data in text_dict.items():
        label_manager.add_or_update_object(obj_id, obj_data['pos'], obj_data['text'])
        #cv2.circle(frame, obj_data['pos'], 5, (0, 0, 255), -1)

    # Draw labels
    label_manager.draw_labels(step_image)

    # Draw time
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    font_thickness = 2
    text_color = (0, 0, 0)
    abs_time = step * time_step
    hours = abs_time // 3600
    remaining_seconds = abs_time % 3600
    minutes = remaining_seconds // 60
    seconds = remaining_seconds % 60
    str_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    cv2.putText(step_image, str_time, (100, 100), font, font_scale, text_color, font_thickness, cv2.LINE_AA)

    cv2.imwrite('frames/' + str(step).zfill(4) + '.png', step_image)






