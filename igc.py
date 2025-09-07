from datetime import datetime
import numpy as np
import re
import pickle
import tqdm
import os


def file_loader(folder_paths=[]):
    file_list = []
    for folder in folder_paths:
        # List all files in the current folder
        for filename in os.listdir(folder):
            # Join the folder path with the filename
            file_path = os.path.join(folder, filename)
            # Only add files (not directories)
            if os.path.isfile(file_path):
                file_list.append(file_path)

    pickle_name = folder_paths[0].replace("/", "-") + '.pkl'

    try:
        with open(pickle_name, 'rb') as file:  # 'rb' = read binary
            igcs = pickle.load(file)
    except:
        igcs = []
        for file_name in tqdm.tqdm(file_list):
            igcs.append(IGC(file_name))
        with open(pickle_name, 'wb') as file:  # 'wb' = write binary
            pickle.dump(igcs, file)
    return igcs


class IGC:
    def __init__(self, filepath, start="000000"):
        #print("Loading:", filepath)
        self.filepath = filepath
        self.start = start
        self.lnavozn_data = {}  # Dictionary to store LNAVOZN data

        # Find pilot name
        match = re.search(r'_([a-zA-Z0-9]{1,})(?=\.\w+$)', self.filepath)

        if match:
            self.name = match.group(1)
        else:
            self.name = None

        num_entries = sum(1 for line in open(filepath) if line.startswith('B'))

        self.start_date = "None"

        self.times = np.ones(num_entries) * -65535
        self.lats = np.ones(num_entries) * -65535
        self.lons = np.ones(num_entries) * -65535
        self.alts = np.ones(num_entries) * -65535
        self.climb_rates = np.ones(num_entries) * -65535

        self._load_and_parse()

        if self.name == "PG":
            self._parse_lnavozn()  # Parse LNAVOZN data

        self.fill_gaps()

    def _parse_lnavozn(self):
        """Parse LNAVOZN entries from the IGC file with proper name filtering"""
        # First collect all valid point names in order
        point_names = []
        with open(self.filepath, 'r') as file:
            for line in file:
                line = line.strip()
                if line.startswith('C'):
                    # Skip lines that are just timestamps or null coordinates
                    if (line.startswith('C2') and len(line) == 25) or line.startswith('C0000000N00000000E'):
                        continue

                    parts = line.split()
                    if len(parts) >= 2:  # Has coordinates and name
                        # Verify it has proper coordinate structure (N and E in expected positions)
                        coord_part = parts[0][1:]  # Remove leading C
                        if len(coord_part) >= 17 and 'N' in coord_part and 'E' in coord_part:
                            point_names.append(' '.join(parts[1:]))
                    else:  # No name provided but has coordinates
                        point_names.append('')
        #print(point_names)

        # Now parse LNAVOZN entries and assign names by order
        name_index = 0
        with open(self.filepath, 'r') as file:
            current_group = None

            for line in file:
                line = line.strip()
                if line.startswith('LNAVOZN'):
                    parts = line.split(',')
                    group_id = parts[0].split('=')[1]

                    if group_id not in self.lnavozn_data:
                        self.lnavozn_data[group_id] = {
                            'Lat': None,
                            'Lon': None,
                            'R1': None,
                            'A12': None,
                            'Name': ''
                        }

                    current_group = self.lnavozn_data[group_id]

                    has_coords = False
                    for part in parts[1:]:
                        if '=' in part:
                            key, value = part.split('=')
                            if key == 'Lat':
                                current_group['Lat'] = self._parse_coordinate(value)
                                has_coords = True
                            elif key == 'Lon':
                                current_group['Lon'] = self._parse_coordinate(value)
                                has_coords = True
                            elif key == 'R1':
                                if 'km' in value:
                                    current_group['R1'] = float(value.replace('km', ''))
                                else:
                                    current_group['R1'] = float(value.replace('m', '')) / 1000
                            elif key == 'A12':
                                current_group['A12'] = float(value)

                    # Only assign name when we have coordinates (to avoid double assignment)
                    if has_coords and name_index < len(point_names):
                        current_group['Name'] = point_names[name_index]
                        #print(point_names[name_index], "assigned to", str(group_id))
                        name_index += 1

    def _parse_coordinate(self, coord_str):
        """Parse latitude or longitude string into decimal degrees"""
        if 'N' in coord_str or 'S' in coord_str:
            # Latitude format: DDMM.MMMN/S
            parts = re.split('([NS])', coord_str)
            deg_min = parts[0]
            hemisphere = parts[1]
        else:
            # Longitude format: DDDMM.MMME/W
            parts = re.split('([EW])', coord_str)
            deg_min = parts[0]
            hemisphere = parts[1]

        # Split into degrees and minutes
        if '.' in deg_min:
            deg_part = deg_min.split('.')[0]
            degrees = float(deg_part[:-2])
            minutes = float(deg_part[-2:] + '.' + deg_min.split('.')[1])
        else:
            degrees = float(deg_min[:-2])
            minutes = float(deg_min[-2:])

        decimal_degrees = degrees + minutes / 60.0
        if hemisphere in ['S', 'W']:
            decimal_degrees *= -1
        return decimal_degrees

    def _parse_b_record(self, line):
        time_str = line[1:7]
        time = datetime.strptime(time_str, "%H%M%S")

        lat_deg = int(line[7:9])
        lat_min = float(line[9:14]) / 1000.0
        lat_hem = line[14]
        lat = lat_deg + lat_min / 60.0
        if lat_hem == 'S':
            lat = -lat

        lon_deg = int(line[15:18])
        lon_min = float(line[18:23]) / 1000.0
        lon_hem = line[23]
        lon = lon_deg + lon_min / 60.0
        if lon_hem == 'W':
            lon = -lon


        if lat == 0 or lon == 0: print(self.name)
        altitude = int(line[30:35])
        return time, lat, lon, altitude

    def fill_gaps(self):

        #print(len(self.times), len(self.lats), len(self.lons), len(self.alts))
        unique_indices = np.unique(self.times, return_index=True)[1]
        self.times = self.times[unique_indices]
        self.lats = self.lats[unique_indices]
        self.lons = self.lons[unique_indices]
        self.alts = self.alts[unique_indices]

        last_i = 1
        times_fixed_count = 0
        #self.times = self.times
        while last_i < len(self.times) - 1:

            for i in range(last_i, len(self.times)):
                if self.times[0] + i == self.times[i]:
                    last_i = i
                else:
                    times_fixed_count += 1
                    self.times = np.insert(self.times, i, self.times[i - 1] + 1)
                    self.lats = np.insert(self.lats, i, self.lats[i - 1])
                    self.lons = np.insert(self.lons, i, self.lons[i - 1])
                    self.alts = np.insert(self.alts, i, self.alts[i - 1])
                    last_i = i
                    break
        #print(times_fixed_count)

        #Fill zero coordinates
        for i, val in enumerate(self.lats):
            if val == 0: self.lats[i] = self.lats[i-1]
        for i, val in enumerate(self.lons):
            if val == 0: self.lons[i] = self.lons[i-1]

        return

    def _load_and_parse(self):

        # cell_size=0.005
        with open(self.filepath, 'r') as file:
            last_time = None
            last_alt = None

            for line in file:
                if line.startswith('B'):
                    time, lat, lon, alt = self._parse_b_record(line)

                    self.times[np.argmax(self.times == -65535)] = time.hour * 3600 + time.minute * 60 + time.second
                    self.lats[np.argmax(self.lats == -65535)] = lat
                    self.lons[np.argmax(self.lons == -65535)] = lon
                    self.alts[np.argmax(self.alts == -65535)] = alt

                    # self.lats.append(lat)
                    # self.lons.append(lon)
                    # self.alts.append(alt)

                    if last_time is not None and last_alt is not None:
                        dt = (time - last_time).total_seconds()
                        dz = alt - last_alt
                        climb = dz / dt if dt > 0 else 0
                    else:
                        climb = 0

                    self.climb_rates[np.argmax(self.climb_rates == -65535)] = climb
                    last_time, last_alt = time, alt

                if line.startswith("LMCU::TKOFFLAND") or line.startswith("LXCM::TKOFFLAND"):
                    # Extract the date part using regex
                    match = re.search(r'^[A-Za-z]{4}::TKOFFLAND:\d+,(\d{8})', line)
                    if match:
                        date_str = match.group(1)
                        # Parse the datetime (YYYYMMDDHHMMSS)
                        self.start_date = datetime.strptime(date_str, '%Y%m%d')
                        # Format as YYYY-MM-DD
                        # print(str(self.start_date)[:10])

        start_idx = np.argmax(
            self.times == (int(self.start[0:2]) * 3600 + int(self.start[2:4]) * 60 + int(self.start[4:6]) - 7200))

        self.lats = self.lats[start_idx:]
        self.lons = self.lons[start_idx:]
        self.alts = self.alts[start_idx:]

    def get_lnavozn_data(self):
        """Return the parsed LNAVOZN data"""
        return self.lnavozn_data


