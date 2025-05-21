
import os
import requests
from geopy.distance import geodesic
from twilio.rest import Client
import time
import re
from dotenv import load_dotenv

# --- LOAD .ENV ---

load_dotenv()

MY_LAT = float(os.getenv("MY_LAT"))
MY_LON = float(os.getenv("MY_LON"))

# --- SETTINGS ---

NON_MIL_CALLSIGN_PREFIXES = [
  # Commercial and cargo airline prefixes
  "AAL", "DAL", "UAL", "SKW", "ASA", "SWA", "JBU", "FFT", "NKS",
  "ENY", "ASH", "RPA", "PDT", "EDV", "AWI", "QXE",
  "FDX", "UPS", "GTI", "ABX",
  "BAW", "AFR", "KLM", "DLH", "ACA", "QFA", "JAL", "ANA", "UAE", "THY", 
  "CXK", "SCU", "SKU", "JIA",
]

# --- FUNCTIONS ---

def get_aircraft():
  url = "https://opensky-network.org/api/states/all?lamin=35.0000&lomin=-98.0000&lamax=36.0000&lomax=-97.0000"
  response = requests.get(url)
  if response.status_code == 200:
    return response.json().get('states', [])
  else:
    return []

def is_military(callsign):
  # Match known commercial/cargo airline prefixes
  for prefix in NON_MIL_CALLSIGN_PREFIXES:
    if callsign.startswith(prefix):
      return False
  # Match FAA-style general aviation N-numbers
  if re.fullmatch(r"N\d{1,5}[A-Z]{0,2}", callsign):
    return False
  return True

def send_sms(message):
    client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
    client.messages.create(body=message, from_=TWILIO_FROM, to=TWILIO_TO)

def check_nearby_aircraft():
  aircraft_list = get_aircraft()

  # Set desired distance
  distance_check = 90

  # Iterate through planes
  for plane in aircraft_list:
    try:
      callsign = plane[1].strip().upper()
      origin_country = plane[2]
      lat = plane[6]
      lon = plane[5]
      squawk = int(plane[14]) if plane[14] else None
      on_ground = plane[8]
      altitude = plane[7]*3.281 if plane[7] else 'Unavailable'

      # Check criteria
      if origin_country == "United States" and lat and lon and not on_ground and callsign:
        # Check for military aircraft
        if is_military(callsign):
          distance = geodesic((MY_LAT, MY_LON), (lat, lon)).miles
          if distance <= distance_check:
            msg = f"Military aircraft '{callsign}' detected {distance:.2f} miles away at {altitude} feet."
            print(msg)
            # send_sms(msg)
        
        # Check for emergency
        if squawk in [7500, 7600, 7700]:
          distance = geodesic((MY_LAT, MY_LON), (lat, lon)).miles
          if distance <= distance_check:
            msg = f"'{callsign}' squawking {squawk} {distance:.2f} miles away at {altitude} feet."
            print(msg)
    except Exception as e:
      print(f"Error processing aircraft: {e}")

# --- MAIN LOOP ---

if __name__ == "__main__":
  check_nearby_aircraft()
