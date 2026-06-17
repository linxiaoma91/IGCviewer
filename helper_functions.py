import os
import numpy as np

def clear_folder(folder_path):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)  # Remove files and links
            # elif os.path.isdir(file_path):  # Uncomment to also remove subdirectories
            #     shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')

def get_minmax_values(igcs, map_padding):
    min_lon = np.min([np.min(arr.lons) for arr in igcs]) - map_padding
    max_lon = np.max([np.max(arr.lons) for arr in igcs]) + map_padding
    min_lat = np.min([np.min(arr.lats) for arr in igcs]) - map_padding
    max_lat = np.max([np.max(arr.lats) for arr in igcs]) + map_padding
    max_alt = np.max([np.max(arr.alts) for arr in igcs])
    min_time = np.min([np.min(arr.times) for arr in igcs])
    max_time = np.max([np.max(arr.times) for arr in igcs])
    return [min_lon, max_lon, min_lat, max_lat], max_alt, min_time, max_time