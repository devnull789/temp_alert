from urllib.parse import quote
import time, threading, json, requests, os, logging, base64, http.client
from datetime import datetime
import pytz

#http.client.HTTPConnection.debuglevel = 1
logging.basicConfig(level=logging.WARN)

client_id = os.getenv('SENSOR_PUSH_ID')
client_secret = os.getenv('SENSOR_PUSH_KEY')

temp_frzr_id = '8726354'
temp_frig_id = '8716253'
temp_frzr_g_id = '8751243'
temp_frzr_c_id = '8792651'

def monitor_temps():

    url = "https://api.sensorpush.com/api/v1/oauth/authorize"

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }

    data = { "email": f"{client_id}", "password": f"{client_secret}" }


    logging.info("Prep Authorize...")
    logging.debug(f"URL: {url}")
    logging.debug(f"Headers: {headers}")
    logging.debug(f"Data: {data}")

    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 200:
        logging.error("Error in Authorization: %s %s", response.status_code, response.text)
        exit()

    #logging.info("Authorization response: %s", response.json())

    # Assuming 'response' is a Response object from a requests call
    response_dict = response.json()

    # Extract the 'authorization' value
    authorization_value = response_dict.get('authorization')

    # Print the extracted 'authorization' value
    logging.debug("SUCCESS: Authorization value:", authorization_value)


    #-----------------------------------------------------------

    url = "https://api.sensorpush.com/api/v1/oauth/accesstoken"

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }

    data = { "authorization": f"{authorization_value}" }


    logging.info("Prep Access Token...")
    logging.debug(f"URL: {url}")
    logging.debug(f"Headers: {headers}")
    logging.debug(f"Data: {data}")

    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 200:
        logging.error("Error in Access Token: %s %s", response.status_code, response.text)
        exit()

    response_dict = response.json()

    # Extract the 'access_token' value
    access_token = response_dict.get('accesstoken')

    logging.debug("SUCCESS: Access Token value:", access_token)

    #-----------------------------------------------------------

    url = "https://api.sensorpush.com/api/v1/samples"

    headers = {
        "accept": "application/json",
        "Authorization": f"{access_token}"
    }

    data = { "limit": 1 }


    logging.info("Prep Samples...")
    logging.debug(f"URL: {url}")
    logging.debug(f"Headers: {headers}")
    logging.debug(f"Data: {data}")

    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 200:
        logging.error("Error in Samples: %s %s", response.status_code, response.text)
        exit()

    response_dict = response.json()

    last_time = response_dict.get('last_time')

    # Get the current date and time in UTC
    current_datetime = datetime.utcnow()
    day_of_week = current_datetime.strftime("%A")


    utc_zone = pytz.timezone('UTC')
    utc_time = utc_zone.localize(current_datetime)

    pacific_zone = pytz.timezone('US/Pacific')
    current_datetime_pacific = utc_time.astimezone(pacific_zone)
    

    # convert 'last_time' provided by sensor gateway'
    datetime_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    provided_datetime = datetime.strptime(last_time, datetime_format)

    # Calculate the difference
    time_difference = current_datetime - provided_datetime

    # Get the difference in days, hours, minutes, and seconds
    diff_total_seconds  = time_difference.total_seconds()
    days = time_difference.days
    hours, remainder = divmod(time_difference.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)


    temp_frzr = response_dict['sensors'][temp_frzr_id][0]['temperature']
    temp_frig = response_dict['sensors'][temp_frig_id][0]['temperature']
    temp_frzr_g = response_dict['sensors'][temp_frzr_g_id][0]['temperature']
    temp_frzr_c = response_dict['sensors'][temp_frzr_c_id][0]['temperature']

    log_file_date_today = datetime.today().strftime('%Y-%m-%d')   # system timezone (UTC)
    filename = f"{log_file_date_today}.log"
    with open(filename, 'a') as logfile:
    
        logfile.write(f"{current_datetime_pacific}, Age {diff_total_seconds:.0f}s  {temp_frzr}, {temp_frig}, {temp_frzr_g}, {temp_frzr_c}\n")

        if (current_datetime_pacific.hour >= 11 and current_datetime_pacific.hour <= 22):       
            if (temp_frzr > 22.0
                or temp_frig > 49.0
                or temp_frzr_g > 13.0
                or temp_frzr_c > 10.0):
                logfile.write("ALERT temp out of range - open hours!!\n")
        

        if diff_total_seconds > 360:    # if more than 6 minutes since last sensor push update !
            logfile.write(f"ALERT!  last_time is stale!\n")
            logfile.write(f"last_time   : {last_time}\n")
            logfile.write(f"provided_datetime: {provided_datetime}\n")
            logfile.write(f"current_datetime: {current_datetime}\n")
            logfile.write(f"time diff: {time_difference}\n")
            
            logfile.write(json.dumps(response.json(), indent=4) + "\n")

        # TODO:  migrate to 'test_temps' only and setup unit tests
        test_result = test_temps(current_datetime_pacific.hour, diff_total_seconds, day_of_week, temp_frzr, temp_frig, temp_frzr_g, temp_frzr_c)
        if test_result == "":
            pass    # logfile.write("Test okay\n")
        else:
            logfile.write(f"ALERT: {test_result}\n")


def test_temps(hour_pst, diff_seconds, day_of_week, temp_frzr, temp_frig, temp_frzr_g, temp_frzr_c):

        test_response = ""
        if (hour_pst >= 11 and hour_pst <= 22):       # open hours
            if (temp_frzr > 22.0
                or temp_frig > 49.0
                or temp_frzr_g > 13.0
                or temp_frzr_c > 10.0):
                test_response = test_response + "function:  temp out of range - open hours!! "
        
        if diff_seconds > 360:
            test_response = test_response + "function:  last_time is stale! "

        return test_response


while True:
    monitor_temps()  
    time.sleep(60)  # check @ 60 seconds


