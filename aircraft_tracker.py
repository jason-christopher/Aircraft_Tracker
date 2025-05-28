import os
import requests
from geopy.distance import geodesic
from twilio.rest import Client
from dotenv import load_dotenv
from mapping import TYPE_MAP, DIRECTION_MAP

# --- LOAD .ENV ---
load_dotenv()

MY_LAT = float(os.getenv("MY_LAT"))
MY_LON = float(os.getenv("MY_LON"))
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM")
TWILIO_TO = os.getenv("TWILIO_TO")
ADSB_KEY = os.getenv("ADSB_KEY")

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

def check_nearby_aircraft(aircraft_list, NEARBY_DISTANCE_THRESHOLD_MILES):
  messages = []

  for plane in aircraft_list:
    try:
      lat = plane.get('lat', None)
      lon = plane.get('lon', None)

      # Back-up lat/lon
      if not lat:
        lat = plane.get('rr_lat', None)
      if not lon:
        lon = plane.get('rr_lon', None)
      
      distance = geodesic((MY_LAT, MY_LON), (lat, lon)).miles

      # check distance
      if distance <= NEARBY_DISTANCE_THRESHOLD_MILES:
        callsign = plane.get('flight', 'UNKNOWN CALLSIGN').strip().upper()

        if callsign == '0' or callsign == '00000000':
          callsign = 'UNKNOWN CALLSIGN'

        squawk = plane.get('squawk', '')
        altitude = plane.get('alt_baro', '')
        if isinstance(altitude, (int, float)):
          altitude_fmt = f"{int(altitude):,} ft"
        else:
          altitude_fmt = str(altitude)

        aircraft_type = TYPE_MAP.get(plane.get('t', '').upper(), plane.get('t'))
        heading = get_heading_label(plane.get('track', None))

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
