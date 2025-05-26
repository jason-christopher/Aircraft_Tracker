import os
import time
from datetime import datetime
import csv
import requests
from geopy.distance import geodesic
from dotenv import load_dotenv
from mapping import TYPE_MAP

# --- LOAD .ENV ---
load_dotenv()

MY_LAT = float(os.getenv("MY_LAT"))
MY_LON = float(os.getenv("MY_LON"))
ADSB_KEY = os.getenv("ADSB_KEY")

# --- SETTINGS ---
DISTANCE_THRESHOLD_MILES = 3000
TYPES_TO_SEARCH = ['C17', 'E3TF']

# --- FUNCTIONS ---
def get_aircraft_ads_b():
  # Call API
  url = "https://adsbexchange-com1.p.rapidapi.com/v2/mil"
  headers = {
    "x-rapidapi-key": ADSB_KEY,
    "x-rapidapi-host": "adsbexchange-com1.p.rapidapi.com"
  }
  response = requests.get(url, headers=headers)
  if response.status_code != 200:
    return []
  
  # Get aircraft
  aircraft_list = response.json().get("ac", [])
  filtered_aircraft = []

  # Filter aircraft and add to final list
  for plane in aircraft_list:
    try:
      lat = float(plane.get('lat', 0) or 0)
      lon = float(plane.get('lon', 0) or 0)
      alt = plane.get('alt_baro')
      if lat and lon and alt != 'ground':
        distance = geodesic((MY_LAT, MY_LON), (lat, lon)).miles
        if distance <= DISTANCE_THRESHOLD_MILES:
          filtered_aircraft.append(plane)
    except:
      continue
  return filtered_aircraft


def collect_data():
  aircraft_list = get_aircraft_ads_b()
  aircraft_dict = {}

  for plane in aircraft_list:
    try:
      if plane.get('t', '').strip().upper() in TYPES_TO_SEARCH:
        unix_time = int(time.time())
        hex = str(plane.get('hex'))
        unique_key = str(unix_time) + '-' + hex
        callsign = plane.get('flight', '').strip().upper()

        if callsign == '0' or callsign == '00000000':
          callsign = 'Unknown Callsign'
        if not callsign:
          continue

        squawk = plane.get('squawk', 'Unavailable')
        altitude = plane.get('alt_baro', 'Unavailable')
        if isinstance(altitude, (int, float)):
          altitude = int(altitude)
        else:
          altitude = str(altitude)

        lat = float(plane['lat'])
        lon = float(plane['lon'])
        tail_number = str(plane.get('r', ''))
        aircraft_type = TYPE_MAP.get(plane.get('t', '').upper(), plane.get('t'))
        heading = int(plane.get('track')) if isinstance(plane.get('track'), (int, float)) else None
        ground_speed = int(plane.get('gs')) if isinstance(plane.get('gs'), (int, float)) else None

        # Add to dictionary
        aircraft_dict[unique_key] = {
          'hex': hex,
          'callsign': callsign,
          'datetime': str(datetime.now()),
          'tail number': tail_number,
          'squawk': squawk,
          'altitude': altitude,
          'latitude': lat,
          'longitude': lon,
          'type': aircraft_type,
          'heading': heading,
          'ground speed': ground_speed,
        }

    except Exception as e:
      print(f"Error processing aircraft: {e}")
  
  print(aircraft_dict)
  return aircraft_dict


# --- MAIN LOOP ---
if __name__ == "__main__":

  # Output file name
  output_file = "aircraft_data_my_api.csv"

  fieldnames = ['hex',
          'callsign',
          'datetime',
          'tail number',
          'squawk',
          'altitude',
          'latitude',
          'longitude',
          'type',
          'heading',
          'ground speed',
          ]
  
  MINUTES_TO_RUN = 180
  MINUTES_BETWEEN_RUNS = 1

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
