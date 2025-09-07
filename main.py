import igc
from GifGenerator import generate_gif_imageio, clear_folder, pngs_to_video
import numpy as np
import cv2
from tqdm import tqdm
import painter
import dicts
from painter import draw_circle

import texter

igcs = igc.file_loader(folder_paths=["IGC/t5"])

#load task data from PG
index = next((i for i, obj in enumerate(igcs) if obj.name == "PG"), None)
checkpoints_dict = igcs[index].get_lnavozn_data()

zoom_buffer = 0.05
fasl = 3317

min_lon = np.min([np.min(arr.lons) for arr in igcs]) - zoom_buffer
max_lon = np.max([np.max(arr.lons) for arr in igcs]) + zoom_buffer
min_lat = np.min([np.min(arr.lats) for arr in igcs]) - zoom_buffer
max_lat = np.max([np.max(arr.lats) for arr in igcs]) + zoom_buffer
max_alt = np.max([np.max(arr.alts) for arr in igcs])
min_time = np.min([np.min(arr.times) for arr in igcs])
max_time = np.max([np.max(arr.times) for arr in igcs])

print(min_lon,max_lon,min_lat,max_lat)

clear_folder("frames/")

basemap = painter.get_basemap(min_lon, max_lon, min_lat, max_lat)

img_size_x = basemap.shape[1]
img_size_y = basemap.shape[0]

# plot task markers
for marker_id, marker_data in checkpoints_dict.items():
    print(marker_id)
    lat = marker_data['Lat']
    lon = marker_data['Lon']
    radius = marker_data['R1']
    name = marker_data['Name']
    #print(checkpoints_dict)

    radius_px = int(img_size_y/(max_lat - min_lat) * radius/111) # 1° = 111km)

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    font_thickness = 1
    text_color = (0, 0, 0)

    # Call your drawing function with the extracted parameters
    x_loc, y_loc = painter.latlon2px(lat, lon, min_lat, max_lat, min_lon, max_lon, img_size_x, img_size_y)
    draw_circle(basemap, x_loc, y_loc, [radius_px], [(128,128,128)], 0.3)
    cv2.putText(basemap, str(marker_id)+ ": " + str(name), (x_loc-5, y_loc+5), font, font_scale, text_color, font_thickness,
                cv2.LINE_AA)


#get dicts for roundels
nations_dict = dicts.nations_dict()
colors_dict = dicts.colors_dict()
angles_dict = dicts.angles_dict()




start_dict_t2 = {"HV":"142119", "HG":"142052", "FOX":"142013", "SH":"142614", "CK":"142025",
              "IX":"141422", "311":"142845", "6L":"141420", "FLS":"143018", "PG":"142016",
              "J":"142847", "40":"141845", "NW":"141425", "AG":"142104", "B8":"144602",
              "JM":"142856", "100":"142051", "QT":"144610", "1X":"141814", "RI":"144720",
              "FP":"142617", "680":"145721", "AN":"142832", "W4":"144617"}

start_dict_t3 = {"HV":"124935", "HG":"124950", "FOX":"123513",
              "IX":"124812", "311":"123636", "6L":"124804", "FLS":"123630", "PG":"123512",
              "J":"124459", "40":"124318", "NW":"124818", "AG":"124929", "B8":"125039",
              "100":"122937", "QT":"130433", "1X":"124600", "RI":"124726",
              "680":"123037", "AN":"123649", "W4":"123302", "CK":"123516", "FP":"123013",
              "SH":"123005", "JM":"124531", "LS4":"122732"}

start_dict_t5 = {"HV":"131156", "HG":"131247", "FOX":"123326",
              "IX":"130557", "311":"125619", "6L":"130554", "FLS":"125620", "PG":"123321",
              "J":"124709", "40":"130727", "NW":"130606", "AG":"130825", "B8":"132926",
              "100":"122059", "QT":"131313", "1X":"124326", "RI":"125638",
              "680":"125950", "AN":"125630", "W4":"131137", "CK":"124711",
              "SH":"131735", "LS4":"123807"}

start_dict_t6 = {"IX":"122841", "6L":"122845", "HV":"123655",
              "CK":"123437", "FOX":"123423", "PG":"123442",
              "NW":"122845", "J":"122621", "40":"123932",
              "HG":"125241", "JM":"122603", "W4":"120557",
              "AN":"123950", "AG":"124010", "680":"114210",
              "SH":"114216", "FLS":"123947", "FP":"114210",
              "311":"123955","LS4":"115416", "B8":"115602",
              "QT":"121933", "100":"121453", "RI":"115157",
              "1X":"115553"}

start_dict_t8 = {"680":"132400", "FP":"132358", "B8":"135543",
                 "HV":"140035", "40":"135412", "IX":"135818",
                 "AN":"135454", "J":"135942", "JM":"135919",
                 "6L":"135827", "NW":"135833", "FLS":"135456",
                 "HG":"135621", "FOX":"135259", "CK":"135304",
                 "PG":"135302", "W4":"13406", "1X":"133041",
                 "SH":"132418", "QT":"133050", "100":"133656",
                 "LS4":"130507", "AG":"135525", "311":"135443",
                 "RI":"132337"}

start_dict = start_dict_t5
time_mode = "synced" # "abs" or "synced" ("synced" needs start_dict)
time_offset = -7200 # -7200 for Garray
time_step = 3 # seconds
total_length = max(len(arr.lats[::time_step]) for arr in igcs)

label_manager = texter.TextLabelManager(repulsion_radius=75, attraction_force=0.1, repulsion_force=0.3, damping=0.1)

if time_mode == "synced":
    min_time = min(int(t[0:2])*3600 + int(t[2:4])*60 + int(t[4:6]) for t in start_dict.values()) + time_offset
elif time_mode == "abs":
    min_time = min_time

for step in tqdm(range(0, int((max_time - min_time) / time_step))):

    if time_mode == "abs": abs_time = int(min_time + step * time_step)
    step_image = basemap.copy()

    # Create a transparent overlay for paths
    path_overlay = np.zeros_like(step_image, dtype=np.uint8)

    text_dict = {}

    #grid = TextPlacementGrid(img_size_x, img_size_y, grid_rows=80, grid_cols=80)



    for igc in igcs[0:]:

        if time_mode == "synced":
            #abs_time = min(min_time + step * time_step, np.max(igc.times))
            start_time = int(start_dict[igc.name][0:2])*3600 + int(start_dict[igc.name][2:4])*60 + int(start_dict[igc.name][4:6])
            abs_time = min(start_time + step * time_step + time_offset, np.max(igc.times))

        # Get current position
        if len(igc.lats[np.where(igc.times == abs_time)[0]]) > 0:
            lats = igc.lats[np.where(igc.times == abs_time)[0]][0]
            lons = igc.lons[np.where(igc.times == abs_time)[0]][0]
            alts = igc.alts[np.where(igc.times == abs_time)[0]][0]
            x_loc, y_loc = painter.latlon2px(lats, lons, min_lat, max_lat, min_lon, max_lon, img_size_x, img_size_y)
        else:
            continue

        try:
            nation = nations_dict[igc.name]
        except KeyError:
            nation = None

        try:
            color = colors_dict[nation]
        except KeyError:
            color = [(127, 127, 127), (127, 127, 127), (127, 127, 127)]

        # Get all positions up to current time
        prev_indices = np.where((igc.times >= min_time) & (igc.times <= abs_time))[0]

        path_downsampling = 30
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
            x, y = painter.latlon2px(lat, lon, min_lat, max_lat, min_lon, max_lon, img_size_x, img_size_y)
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
            cv2.polylines(path_overlay, [pts], isClosed=False, color=(255,255,255) if igc.name =="PG" else path_color, thickness=3 if igc.name=="PG" else 1, lineType=cv2.LINE_AA)

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
                r_list = [radius, radius // 2]
        else:
            r_list = [radius] * len(color)

        step_image = painter.draw_circle(step_image, x_loc, y_loc, r_list, color, 0.4, angle_list)

        # Draw label
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        font_thickness = 1
        text_color = (0, 0, 0)

        #step_image = grid.place_text(step_image, igc.name, x_loc, y_loc)

        #if igc.name == "PG": y_loc = y_loc - 40

        text_dict[igc.name] = {'pos': (x_loc, y_loc), 'text': igc.name}


        #cv2.putText(step_image, igc.name, (x_loc - 10, y_loc + 30), font, font_scale, text_color, font_thickness,
        #            cv2.LINE_AA)

    # Blend the path overlay with the main image with transparency
    alpha = 0.3  # Adjust this value (0.0 to 1.0) for desired transparency
    step_image = cv2.addWeighted(step_image, 1, path_overlay, alpha, 0)

    for obj_id, obj_data in text_dict.items():
        label_manager.add_or_update_object(obj_id, obj_data['pos'], obj_data['text'])
        #cv2.circle(frame, obj_data['pos'], 5, (0, 0, 255), -1)

    # Draw labels
    label_manager.draw_labels(step_image)

    # Draw time (your existing code)
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






