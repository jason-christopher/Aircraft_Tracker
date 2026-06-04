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

# --- LOAD .ENV ---
load_dotenv()

MY_LAT = float(os.getenv("MY_LAT"))
MY_LON = float(os.getenv("MY_LON"))
ADSB_KEY = os.getenv("ADSB_KEY")

# --- SETTINGS ---
DISTANCE_THRESHOLD_MILES = 15000
TYPES_TO_SEARCH = ['C17', 'E3TF', 'B742', 'B52', 'F35', 'F18S', 'C5M', 'E6', 'R135', 'W135', 'E2', 'B752', 'B762', 'K35R']
MINUTES_TO_RUN = 180
MINUTES_BETWEEN_RUNS = 1

# --- MISSING INFO DICTIONARY ---
missing_info_dict = {}
unknown_callsign_hexes = set()  # hex_ids written to CSV with UNK C/S

# --- FUNCTIONS ---
def get_aircraft_ads_b():
  url = "https://adsbexchange-com1.p.rapidapi.com/v2/mil"
  headers = {
    "x-rapidapi-key": ADSB_KEY,
    "x-rapidapi-host": "adsbexchange-com1.p.rapidapi.com"
  }
  response = requests.get(url, headers=headers)
  if response.status_code != 200:
    return []

  aircraft_list = response.json().get("ac", [])
  filtered_aircraft = []

  for plane in aircraft_list:
    try:
      alt = plane.get('alt_baro', 'Unknown')

      # adsb_icao / mlat / adsr_icao carry lat/lon directly; mode_s falls back to rr_lat/rr_lon
      lat = plane.get('lat') or plane.get('rr_lat', None)
      lon = plane.get('lon') or plane.get('rr_lon', None)

      if lat and lon and alt != 'ground':
        distance = geodesic((MY_LAT, MY_LON), (float(lat), float(lon))).miles
        if distance <= DISTANCE_THRESHOLD_MILES:
          filtered_aircraft.append(plane)
    except Exception as e:
      print(f"Error filtering aircraft: {e}")
      continue
  return filtered_aircraft


def collect_data():
  aircraft_list = get_aircraft_ads_b()
  aircraft_dict = {}

  unix_time = int(time.time())

  for plane in aircraft_list:
    try:
      if plane.get('t', '').strip().upper() in TYPES_TO_SEARCH:
        hex_id = str(plane.get('hex'))
        unique_key = str(unix_time) + '-' + hex_id
        callsign = plane.get('flight', 'UNK C/S').strip().upper()
        if callsign == '0' or callsign == '00000000' or callsign == '':
          callsign = 'UNK C/S'
        squawk = plane.get('squawk', 'Unavailable')
        altitude = plane.get('alt_baro', 'Unavailable')
        if isinstance(altitude, (int, float)):
          altitude = int(altitude)
        else:
          altitude = str(altitude)

        # adsb_icao / mlat / adsr_icao → use lat/lon; mode_s → fall back to rr_lat/rr_lon
        lat = plane.get('lat', None)
        lon = plane.get('lon', None)
        if lat and lon:
          source = plane.get('type', 'unknown')
        else:
          lat = plane.get('rr_lat', None)
          lon = plane.get('rr_lon', None)
          source = 'mode_s'

        tail_number = str(plane.get('r', ''))
        aircraft_type = TYPE_MAP.get(plane.get('t', '').upper(), plane.get('t'))
        if plane.get('t', '').upper() == 'B742' and tail_number in ('92-9000', '86-8800'):
          aircraft_type = 'AIR FORCE ONE'
        heading = int(plane.get('track')) if isinstance(plane.get('track'), (int, float)) else None
        ground_speed = int(plane.get('gs')) if isinstance(plane.get('gs'), (int, float)) else None
        vertical_rate = int(plane.get('baro_rate')) if isinstance(plane.get('baro_rate'), (int, float)) else None
        emergency = plane.get('emergency', 'none') not in ('none', '', None)

        # Update missing info dictionary — callsign and squawk tracked independently
        if callsign != 'UNK C/S':
          missing_info_dict.setdefault(hex_id, {})['callsign'] = callsign
        if squawk != 'Unavailable':
          missing_info_dict.setdefault(hex_id, {})['squawk'] = squawk

        # Fill in from memory if currently missing
        if hex_id in missing_info_dict:
          if callsign == 'UNK C/S' and 'callsign' in missing_info_dict[hex_id]:
            callsign = missing_info_dict[hex_id]['callsign']
          if squawk == 'Unavailable' and 'squawk' in missing_info_dict[hex_id]:
            squawk = missing_info_dict[hex_id]['squawk']

        aircraft_dict[unique_key] = {
          'hex': hex_id,
          'callsign': callsign,
          'datetime': str(datetime.now()),
          'tail number': tail_number,
          'squawk': squawk,
          'altitude': altitude,
          'latitude': float(lat) if lat else 'UNKNOWN LAT',
          'longitude': float(lon) if lon else 'UNKNOWN LON',
          'type': aircraft_type,
          'heading': heading,
          'ground speed': ground_speed,
          'vertical rate': vertical_rate,
          'emergency': emergency,
          'source': source,
        }

    except Exception as e:
      print(f"Error processing aircraft: {e}")

  return aircraft_dict


def backfill_unknown_callsigns(output_file, fieldnames):
  global unknown_callsign_hexes
  hexes_to_update = {h for h in unknown_callsign_hexes if h in missing_info_dict}
  if not hexes_to_update:
    return 0, 0

  rows = []
  updated_records = 0
  updated_hexes = set()
  with open(output_file, 'r', newline='') as f:
    for row in csv.DictReader(f):
      if row['hex'] in hexes_to_update and row['callsign'] == 'UNK C/S':
        new_cs = missing_info_dict[row['hex']].get('callsign', '')
        if new_cs and new_cs != 'UNK C/S':
          row['callsign'] = new_cs
          updated_records += 1
          updated_hexes.add(row['hex'])
      rows.append(row)

  if updated_records:
    with open(output_file, 'w', newline='') as f:
      writer = csv.DictWriter(f, fieldnames=fieldnames)
      writer.writeheader()
      writer.writerows(rows)
    unknown_callsign_hexes -= hexes_to_update

  return len(updated_hexes), updated_records


def get_output_file():
  """Return today's CSV path (data/YYYY-MM/YYYY-MM-DD.csv), creating the folder if needed."""
  today = datetime.now().strftime('%Y-%m-%d')
  month = today[:7]
  month_dir = os.path.join(BASE_DIR, 'data', month)
  os.makedirs(month_dir, exist_ok=True)
  return os.path.join(month_dir, f'{today}.csv')


def preload_known_aircraft():
  """Scan all daily CSVs and populate missing_info_dict so callsigns survive restarts."""
  data_dir = os.path.join(BASE_DIR, 'data')
  records_scanned = 0
  for month_folder in sorted(os.listdir(data_dir)):
    month_path = os.path.join(data_dir, month_folder)
    if not os.path.isdir(month_path) or month_folder == 'Archive':
      continue
    for fname in sorted(os.listdir(month_path)):
      if not fname.endswith('.csv'):
        continue
      with open(os.path.join(month_path, fname), 'r', newline='') as f:
        for row in csv.DictReader(f):
          h  = row.get('hex', '').strip()
          cs = row.get('callsign', '').strip()
          sq = row.get('squawk', '').strip()
          if h and cs and cs != 'UNK C/S':
            missing_info_dict.setdefault(h, {})['callsign'] = cs
          if h and sq and sq != 'Unavailable':
            missing_info_dict.setdefault(h, {})['squawk'] = sq
          if h:
            records_scanned += 1
  return records_scanned


# --- MAIN LOOP ---
if __name__ == "__main__":

  print(MY_LAT, MY_LON)

  fieldnames = ['hex',
          'datetime',
          'callsign',
          'tail number',
          'squawk',
          'altitude',
          'latitude',
          'longitude',
          'type',
          'heading',
          'ground speed',
          'vertical rate',
          'emergency',
          'source',
          ]

  for i in range(MINUTES_TO_RUN):
    try:
      # Recalculate each run so the file rolls over at midnight automatically
      output_file = get_output_file()

      if not os.path.exists(output_file):
        with open(output_file, 'w', newline='') as f:
          writer = csv.DictWriter(f, fieldnames=fieldnames)
          writer.writeheader()

      nested_dict = collect_data()
      aircraft_data = list(nested_dict.values())

      with open(output_file, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerows(aircraft_data)

      for record in aircraft_data:
        if record['callsign'] == 'UNK C/S':
          unknown_callsign_hexes.add(record['hex'])

      aircraft_backfilled, records_backfilled = backfill_unknown_callsigns(output_file, fieldnames)
      backfill_str = f" | Backfilled {aircraft_backfilled} aircraft ({records_backfilled} records)" if aircraft_backfilled else ""
      print(f"Run {i+1}/{MINUTES_TO_RUN}: Saved {len(aircraft_data)} aircraft.{backfill_str}")

    except Exception as e:
      print(f"Run {i+1}/{MINUTES_TO_RUN}: ERROR — {e}")
      with open(os.path.join(BASE_DIR, 'logs', 'error_log.txt'), 'a') as err:
        err.write(f"[{datetime.now()}] Error: {str(e)}\n")

    time.sleep(MINUTES_BETWEEN_RUNS * 60)
