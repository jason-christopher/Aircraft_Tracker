import os
import sys
import time
from datetime import datetime
import csv
import requests
from geopy.distance import geodesic
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from mapping import TYPE_MAP
from alerts.aircraft_tracker import check_nearby_aircraft

# --- LOAD .ENV ---
load_dotenv()

MY_LAT = float(os.getenv("MY_LAT"))
MY_LON = float(os.getenv("MY_LON"))

print(MY_LAT, MY_LON)

# --- SETTINGS ---
DISTANCE_THRESHOLD_MILES = 3000
NEARBY_DISTANCE_THRESHOLD_MILES = 5
MINUTES_TO_RUN = 120
MINUTES_BETWEEN_RUNS = 1

# --- MISSING INFO DICTIONARY ---
missing_info_dict = {}

# --- FUNCTIONS ---
def is_us_military(icao24):
    try:
        return 0xAE0000 <= int(icao24, 16) <= 0xAFFFFF
    except:
        return False


def state_to_adsb_dict(state):
    # Convert OpenSky state array to adsb.one-style dict for check_nearby_aircraft compatibility
    baro_alt_m = state[7]
    alt_ft = int(baro_alt_m * 3.28084) if isinstance(baro_alt_m, (int, float)) else 'ground'
    return {
        'lat': state[6],
        'lon': state[5],
        'flight': state[1] or '',
        'squawk': state[14] or 'Unavailable',
        'alt_baro': alt_ft,
        't': '',
        'track': state[10],
    }


def get_aircraft_opensky():
    url = "https://opensky-network.org/api/states/all"
    response = requests.get(url)
    if response.status_code != 200:
        print(f'API Error: {response.status_code}')
        return []

    states = response.json().get("states", [])
    filtered_aircraft = []

    count_total = len(states)
    count_mil = 0
    count_airborne = 0
    count_has_pos = 0
    count_in_range = 0

    for state in states:
        try:
            icao24 = state[0]
            lon = state[5]
            lat = state[6]
            on_ground = state[8]

            if not is_us_military(icao24):
                continue
            count_mil += 1

            if lat is None or lon is None:
                continue
            count_has_pos += 1

            if on_ground:
                continue
            count_airborne += 1

            distance = geodesic((MY_LAT, MY_LON), (float(lat), float(lon))).miles
            if distance <= DISTANCE_THRESHOLD_MILES:
                count_in_range += 1
                filtered_aircraft.append(state)
        except Exception as e:
            continue

    print(f"  OpenSky total states: {count_total}")
    print(f"  US military hex (AE0000-AFFFFF): {count_mil}")
    print(f"  Has position: {count_has_pos}")
    print(f"  Airborne: {count_airborne}")
    print(f"  Within {DISTANCE_THRESHOLD_MILES} miles: {count_in_range}")

    return filtered_aircraft


def collect_data():
    aircraft_list = get_aircraft_opensky()
    aircraft_dict = {}

    for state in aircraft_list:
        try:
            unix_time = int(time.time())
            hex_id = str(state[0])
            unique_key = str(unix_time) + '-' + hex_id

            callsign = (state[1] or '').strip().upper()
            if callsign in ('', '0', '00000000'):
                callsign = 'UNKNOWN CALLSIGN'

            squawk = state[14] or 'Unavailable'

            baro_alt_m = state[7]
            altitude = int(baro_alt_m * 3.28084) if isinstance(baro_alt_m, (int, float)) else 'Unavailable'

            lat = state[6]
            lon = state[5]
            velocity_ms = state[9]
            ground_speed = int(velocity_ms * 1.94384) if isinstance(velocity_ms, (int, float)) else None
            heading = int(state[10]) if isinstance(state[10], (int, float)) else None
            origin_country = state[2] or ''

            # Update missing info dictionary
            if callsign != 'UNKNOWN CALLSIGN' and squawk != 'Unavailable':
                missing_info_dict[hex_id] = {
                    'callsign': callsign,
                    'squawk': squawk,
                }

            # Fill in from memory if currently missing
            if hex_id in missing_info_dict:
                if callsign == 'UNKNOWN CALLSIGN':
                    callsign = missing_info_dict[hex_id]['callsign']
                if squawk == 'Unavailable':
                    squawk = missing_info_dict[hex_id]['squawk']

            aircraft_dict[unique_key] = {
                'hex': hex_id,
                'callsign': callsign,
                'datetime': str(datetime.now()),
                'operator': origin_country,
                'tail number': '',
                'squawk': squawk,
                'altitude': altitude,
                'latitude': float(lat),
                'longitude': float(lon),
                'type': '',
                'heading': heading,
                'ground speed': ground_speed,
                'degraded': False,
            }

        except Exception as e:
            print(f"Error processing aircraft: {e}")

    # Convert to adsb.one-compatible format for nearby aircraft check
    adsb_compat = [state_to_adsb_dict(s) for s in aircraft_list]
    check_nearby_aircraft(adsb_compat, MY_LAT, MY_LON, NEARBY_DISTANCE_THRESHOLD_MILES)

    return aircraft_dict


# --- MAIN LOOP ---
if __name__ == "__main__":

    output_file = os.path.join(BASE_DIR, 'data', 'aircraft_data_opensky.csv')

    fieldnames = ['hex',
                  'callsign',
                  'datetime',
                  'operator',
                  'tail number',
                  'squawk',
                  'altitude',
                  'latitude',
                  'longitude',
                  'type',
                  'heading',
                  'ground speed',
                  'degraded',
                  ]

    if not os.path.exists(output_file):
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

    for i in range(MINUTES_TO_RUN):
        try:
            nested_dict = collect_data()
            aircraft_data = list(nested_dict.values())

            with open(output_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerows(aircraft_data)

            print(f"Run {i+1}/{MINUTES_TO_RUN}: Saved {len(aircraft_data)} aircraft.")

        except Exception as e:
            with open(os.path.join(BASE_DIR, 'logs', 'error_log.txt'), 'a') as err:
                err.write(f"[{datetime.now()}] Error: {str(e)}\n")

        time.sleep(MINUTES_BETWEEN_RUNS * 60)
