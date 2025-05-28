import os
import time
from datetime import datetime
import csv
import requests
from geopy.distance import geodesic
from dotenv import load_dotenv
from mapping import TYPE_MAP
from aircraft_tracker import check_nearby_aircraft

# --- LOAD .ENV ---
load_dotenv()

MY_LAT = float(os.getenv("MY_LAT"))
MY_LON = float(os.getenv("MY_LON"))

# --- SETTINGS ---
DISTANCE_THRESHOLD_MILES = 3000
NEARBY_DISTANCE_THRESHOLD_MILES = 10
TYPES_TO_SEARCH = ['C17', 'E3TF', 'B742', 'B52', 'F35', 'F18S', 'C5M', 'E6', 'R135', 'W135', 'E2', 'B752']
MINUTES_TO_RUN = 120
MINUTES_BETWEEN_RUNS = 1

# --- MISSING INFO DICTIONARY ---
missing_info_dict = {}

# --- FUNCTIONS ---
def contains_no_substring_from_list(main_string, substring_list):
  for sub in substring_list: 
    if sub.strip().lower() in main_string.strip().lower():
      return False
  return True


def get_aircraft_ads_b():
  # Call API
  url = "https://api.adsb.one/v2/mil"
  response = requests.get(url)
  if response.status_code != 200:
    return []
  
  # Get aircraft
  aircraft_list = response.json().get("ac", [])
  filtered_aircraft = []

  # Filter aircraft and add to final list
  for plane in aircraft_list:
    try:
      lat = plane.get('lat', None)
      lon = plane.get('lon', None)
      own_op = plane.get('ownOp', '')
      alt = plane.get('alt_baro', 'Unknown')

      # Back-up lat/lon
      if not lat:
        lat = plane.get('rr_lat', None)
      if not lon:
        lon = plane.get('rr_lon', None)

      if lat and lon and alt != 'ground':
        # Filter to only US aircraft
        if contains_no_substring_from_list(own_op, ['Canad', 'Israel', 'United Kingdom', 'Royal', 'Australia', 'Mexic', 'Qatar']):
          distance = geodesic((MY_LAT, MY_LON), (float(lat), float(lon))).miles
          if distance <= DISTANCE_THRESHOLD_MILES:
            filtered_aircraft.append(plane)
    except Exception as e:
      # print(f"Error processing aircraft: {e}")
      continue
  return filtered_aircraft


def collect_data():
  aircraft_list = get_aircraft_ads_b()
  aircraft_dict = {}

  for plane in aircraft_list:
    try:
      if plane.get('t', '').strip().upper() in TYPES_TO_SEARCH:
        degraded = False
        unix_time = int(time.time())
        hex = str(plane.get('hex'))
        unique_key = str(unix_time) + '-' + hex
        callsign = plane.get('flight', 'UNKNOWN CALLSIGN').strip().upper()
        if callsign == '0' or callsign == '00000000' or callsign == '':
          callsign = 'UNKNOWN CALLSIGN'
        squawk = plane.get('squawk', 'Unavailable')
        altitude = plane.get('alt_baro', 'Unavailable')
        if isinstance(altitude, (int, float)):
          altitude = int(altitude)
        else:
          altitude = str(altitude)
        lat = plane.get('lat', None)
        lon = plane.get('lon', None)
        # Back-up lat/lon
        if not lat:
          lat = plane.get('rr_lat', None)
          degraded = True
        if not lon:
          lon = plane.get('rr_lon', None)
          degraded = True
        tail_number = str(plane.get('r', ''))
        own_op = plane.get('ownOp', '')
        aircraft_type = TYPE_MAP.get(plane.get('t', '').upper(), plane.get('t'))
        desc = plane.get('desc', '')
        if 'VC-25' in desc:
          aircraft_type = 'AIR FORCE ONE'
        heading = int(plane.get('track')) if isinstance(plane.get('track'), (int, float)) else None
        ground_speed = int(plane.get('gs')) if isinstance(plane.get('gs'), (int, float)) else None

        # Update missing info dictionary
        if callsign != 'UNKNOWN CALLSIGN' and squawk != 'Unavailable':
          missing_info_dict[hex] = {
            'callsign': callsign,
            'squawk': squawk,
          }

        # Update missing info with dictionary info
        if hex in missing_info_dict:
          if callsign == 'UNKNOWN CALLSIGN':
            callsign = missing_info_dict[hex]['callsign']
          if squawk == 'Unavailable':
            squawk = missing_info_dict[hex]['squawk']

        # Add to dictionary
        aircraft_dict[unique_key] = {
          'hex': hex,
          'callsign': callsign,
          'datetime': str(datetime.now()),
          'operator': own_op,
          'tail number': tail_number,
          'squawk': squawk,
          'altitude': altitude,
          'latitude': float(lat) if lat else 'UNKNOWN LAT',
          'longitude': float(lon) if lon else 'UNKNOWN LON',
          'type': aircraft_type,
          'heading': heading,
          'ground speed': ground_speed,
          'degraded': degraded,
        }

    except Exception as e:
      print(f"Error processing aircraft: {e}")

  # Print nearby aircraft (and send SMS if enabled)
  check_nearby_aircraft(aircraft_list, MY_LAT, MY_LON, NEARBY_DISTANCE_THRESHOLD_MILES)
  
  # print(aircraft_dict)
  return aircraft_dict


# --- MAIN LOOP ---
if __name__ == "__main__":

  # Output file name
  output_file = "aircraft_data2.csv"

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

  # Write header only if file doesn't exist
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
      with open("error_log.txt", 'a') as err:
        err.write(f"[{datetime.now()}] Error: {str(e)}\n")

    time.sleep(MINUTES_BETWEEN_RUNS*60)
