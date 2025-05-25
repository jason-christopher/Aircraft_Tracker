import os
import time
from datetime import datetime
import csv
from mapping import TYPE_MAP
from aircraft_tracker import get_aircraft_ads_b

# --- SETTINGS ---
DISTANCE_THRESHOLD_MILES = 3000

# --- FUNCTIONS ---

def collect_data():
  aircraft_list = get_aircraft_ads_b()
  aircraft_dict = {}

  for plane in aircraft_list:
    try:
      if plane.get('t', '').upper() == 'C17':
        unix_time = int(time.time())
        hex = str(plane.get('hex'))
        unique_key = str(unix_time) + '-' + hex
        callsign = plane.get('flight', '').strip().upper()
        if callsign == '0' or callsign == '00000000':
          callsign = 'Unknown Callsign'
        if not callsign:
          continue

        squawk = int(plane['squawk']) if plane.get('squawk') else None
        altitude = plane.get('alt_baro', 'Unavailable')
        if isinstance(altitude, (int, float)):
          altitude = int(altitude)
        else:
          altitude = str(altitude)

        lat = float(plane['lat'])
        lon = float(plane['lon'])
        aircraft_type = TYPE_MAP.get(plane.get('t', '').upper(), plane.get('t'))
        heading = int(plane.get('track')) if isinstance(plane.get('track'), (int, float)) else None
        ground_speed = int(plane.get('gs')) if isinstance(plane.get('gs'), (int, float)) else None
        indicated_airspeed = int(plane.get('ias')) if isinstance(plane.get('ias'), (int, float)) else None

        # Add to dictionary
        aircraft_dict[unique_key] = {
          'hex': hex,
          'callsign': callsign,
          'datetime': str(datetime.now()),
          'squawk': squawk,
          'altitude': altitude,
          'latitude': lat,
          'longitude': lon,
          'type': aircraft_type,
          'heading': heading,
          'ground speed': ground_speed,
          'indicated airspeed': indicated_airspeed,
        }

    except Exception as e:
      print(f"Error processing aircraft: {e}")
  
  print(aircraft_dict)
  return aircraft_dict


# --- MAIN LOOP ---
if __name__ == "__main__":

  # Output file name
  output_file = "aircraft_data.csv"

  fieldnames = ['hex',
          'callsign',
          'datetime',
          'squawk',
          'altitude',
          'latitude',
          'longitude',
          'type',
          'heading',
          'ground speed',
          'indicated airspeed',
          ]

  # Write header only if file doesn't exist
  if not os.path.exists(output_file):
    with open(output_file, 'w', newline='') as f:
      writer = csv.DictWriter(f, fieldnames=fieldnames)
      writer.writeheader()

  for i in range(60):
    try:
      nested_dict = collect_data()
      aircraft_data = list(nested_dict.values())  # ✅ flatten to list of dicts

      with open(output_file, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerows(aircraft_data)

      print(f"Run {i+1}/60: Saved {len(aircraft_data)} aircraft.")

    except Exception as e:
      with open("error_log.txt", 'a') as err:
        err.write(f"[{datetime.now()}] Error: {str(e)}\n")

    time.sleep(60)
