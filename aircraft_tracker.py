import os
import requests
from geopy.distance import geodesic
from twilio.rest import Client
from dotenv import load_dotenv

# --- LOAD .ENV ---
load_dotenv()

MY_LAT = float(os.getenv("MY_LAT"))
MY_LON = float(os.getenv("MY_LON"))
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM")
TWILIO_TO = os.getenv("TWILIO_TO")
ADSB_KEY = os.getenv("ADSB_KEY")

# --- SETTINGS ---
DISTANCE_THRESHOLD_MILES = 75

# --- TYPE TRANSLATION MAP ---
TYPE_MAP = {
  'TEX2': 'T-6 Texan II',
  'R135': 'RC-135 Rivet Joint',
  'W135': 'WC-135R',
  'E3TF': 'E-3G AWACS',
  'H47': 'H-47 Chinook',
  'T38': 'T-38 Talon',
  'C17': 'C-17A Globemaster',
  'H64': 'AH-64 Apache',
  'K35R': 'KC-135R Stratotanker',
  'H60': 'H-60 Black Hawk',
  'C130': 'C-130 Hercules',
  'V22': 'V-22 Osprey',
  'H53S': 'H-53 Sea Stallion',
  'E2': 'E-2 Hawkeye',
  'EC45': 'EC-145',
  'B737': 'C-40A Clipper',
  'C27J': 'HC-27J Spartan',
  'BE20': 'C-12 Huron',
  'P8': 'P-8 Poseidon',
  'P8 ?': 'P-8 Poseidon',
  'C30J': 'C-130J Super Hercules',
  'A119': 'TH-73A Thrasher',
  'HAWK': 'T-45 Goshawk',
  'B762': 'KC-46A Pegasus',
  'C5M': 'C-5M Galaxy',
  'C560': 'C-35 Citation',
  'SW4': 'C-26 Metro III',
  'Q1': 'RQ-1 Predator',
  'GLF5': 'C-37',
  'F5': 'F-5 Tiger II',
  'E6': 'E-6B TACAMO',
  'B52': 'B-52H Stratofortress',
}

DIRECTION_MAP = [
  (22.5, 'N'), (67.5, 'NE'), (112.5, 'E'), (157.5, 'SE'),
  (202.5, 'S'), (247.5, 'SW'), (292.5, 'W'), (337.5, 'NW')
]

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

def get_heading_label(track):
  if track is None:
    return None
  for angle, label in DIRECTION_MAP:
    if track <= angle:
      return label
  return 'N'

def send_sms(message):
  client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
  client.messages.create(body=message, from_=TWILIO_FROM, to=TWILIO_TO)

def check_nearby_aircraft():
  aircraft_list = get_aircraft_ads_b()
  messages = []

  for plane in aircraft_list:
    try:
      callsign = plane.get('flight', '').strip().upper()
      if callsign == '0' or callsign == '00000000':
        callsign = 'Unknown Callsign'
      if not callsign:
        continue

      squawk = int(plane['squawk']) if plane.get('squawk') else None
      altitude = plane.get('alt_baro', 'Unavailable')
      if isinstance(altitude, (int, float)):
        altitude_fmt = f"{int(altitude):,} ft"
      else:
        altitude_fmt = str(altitude)

      lat = float(plane['lat'])
      lon = float(plane['lon'])
      distance = geodesic((MY_LAT, MY_LON), (lat, lon)).miles

      aircraft_type = TYPE_MAP.get(plane.get('t', '').upper(), plane.get('t'))
      heading = get_heading_label(plane.get('track'))

      description = f"{callsign} ({aircraft_type}) detected {distance:.1f} miles away at {altitude_fmt}"
      if heading:
        description += f", heading {heading}"
      messages.append(description + ".")

      if squawk in [7500, 7600, 7700]:
        messages.append(f"'{callsign}' squawking {squawk} at {altitude_fmt}, {distance:.2f} miles away.")

    except Exception as e:
      print(f"Error processing aircraft: {e}")

  if messages:
    console_msg = "\n".join(messages)
    sms_msg = "  ".join(messages)
    print(console_msg)
    # send_sms(sms_msg)

# --- MAIN LOOP ---
if __name__ == "__main__":
  check_nearby_aircraft()
