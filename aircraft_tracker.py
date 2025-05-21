
import os
import requests
from geopy.distance import geodesic
from twilio.rest import Client
from dotenv import load_dotenv

# --- LOAD .ENV ---

load_dotenv()

MY_LAT = float(os.getenv("MY_LAT"))
MY_LON = float(os.getenv("MY_LON"))
TWILIO_SID = str(os.getenv("TWILIO_SID"))
TWILIO_AUTH_TOKEN = str(os.getenv("TWILIO_AUTH_TOKEN"))
TWILIO_FROM = str(os.getenv("TWILIO_FROM"))
TWILIO_TO = str(os.getenv("TWILIO_TO"))
ADSB_KEY = str(os.getenv("ADSB_KEY"))

# --- SETTINGS ---

distance_check = 50

# --- FUNCTIONS ---

def get_aircraft_open_sky():
  url = "https://opensky-network.org/api/states/all?lamin=34.0000&lomin=-99.0000&lamax=37.0000&lomax=-96.0000"
  response = requests.get(url)
  if response.status_code == 200:
    return response.json().get('states', [])
  else:
    return []
  
def get_aircraft_ads_b():
  url = "https://adsbexchange-com1.p.rapidapi.com/v2/mil"
  headers = {
    "x-rapidapi-key": ADSB_KEY,
    "x-rapidapi-host": "adsbexchange-com1.p.rapidapi.com"
  }
  response = requests.get(url, headers=headers)
  if response.status_code == 200:
    aircraft_list = response.json()["ac"]

    # Create list of filtered aircraft based on location
    filtered_aircraft_list = []

    # Iterate through each aircraft to filter by location
    for plane in aircraft_list:
      # Some aircraft may not have a 'lat' or 'lon' key
      try: 
        lat = float(plane['lat']) if plane['lat'] else None
        lon = float(plane['lon']) if plane['lon'] else None
        alt = int(plane['alt_baro']) if plane['alt_baro']!='ground' else 'ground'

        if lat and lon and alt!='ground':
          distance = geodesic((MY_LAT, MY_LON), (lat, lon)).miles
          if distance <= distance_check:
            filtered_aircraft_list.append(plane)
      except:
        continue
    
    # print(filtered_aircraft_list)
    return filtered_aircraft_list
  else:
    return []

def send_sms(message):
  client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
  client.messages.create(body=message, from_=TWILIO_FROM, to=TWILIO_TO)

def check_nearby_aircraft():
  aircraft_list = get_aircraft_ads_b()
  msg = ''

  # Iterate through planes
  for plane in aircraft_list:
    try:
      callsign = plane['flight'].strip().upper()
      squawk = int(plane['squawk']) if plane['squawk'] else None
      altitude = int(plane['alt_baro']) if plane['alt_baro'] else 'Unavailable'
      lat = float(plane['lat'])
      lon = float(plane['lon'])
      type = str(plane['t']) if plane['t'] else None
      if type:
        if type == 'TEX2':
          type = 'T-6 Texan II'
        elif type == 'R135':
          type = 'RC-135 Rivet Joint'
        elif type == 'E3TF':
          type = 'E-3G AWACS'
        elif type == 'H47':
          type = 'H-47 Chinook'
      heading_raw = float(plane['track']) if plane['track'] else None
      if heading_raw:
        if heading_raw <=22.5:
          heading = 'N'
        elif heading_raw <=67.5:
          heading = 'NE'
        elif heading_raw <=112.5:
          heading = 'E'
        elif heading_raw <=157.5:
          heading = 'SE'
        elif heading_raw <=202.5:
          heading = 'S'
        elif heading_raw <=247.5:
          heading = 'SW'
        elif heading_raw <=292.5:
          heading = 'W'
        elif heading_raw <=337.5:
          heading = 'NW'
        else:
          heading = None
      distance = geodesic((MY_LAT, MY_LON), (lat, lon)).miles

      # Check criteria
      if callsign and callsign != '0':
        msg += f"{callsign} ({type}) detected {distance:.1f} miles away at {altitude:,} ft{', heading ' + heading if heading else ''}.\n"
        
        # Check for emergency
        if squawk in [7500, 7600, 7700]:
          msg += f"'{callsign}' squawking {squawk} {distance:.2f} miles away at {altitude:,} ft.\n"

    except Exception as e:
      print(f"Error processing {callsign}: {e}")
  print(msg)
  # # if msg:
  #   # send_sms(msg)

# --- MAIN LOOP ---

if __name__ == "__main__":
  check_nearby_aircraft()
