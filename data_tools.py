from bs4 import BeautifulSoup
import requests
from datetime import datetime, timezone
import constants
import pytz
from google.cloud import datastore
from twilio.rest import Client
import pickle

# Function to convert date and time string to datetime object
def string_to_datetime(date_string):
    # Convert the date to a datetime object
    date = datetime.strptime(date_string, '%m/%d %H:%M')
    date = date.replace(year=datetime.now(timezone.utc).year)
    date = date.replace(tzinfo=timezone.utc)
    return date

# Function to send a text message
def send_text_message(alerts, to_number=constants.MY_PHONE_NUMBER, time_zone='US/Pacific'):

    client = Client(constants.TWILIO_ACCOUNT_SID, constants.TWILIO_AUTH_TOKEN)

    ############################ Need to make this users for local time ############################
    ############################ Should this be done elsewhere? ############################


    # Create the message to send to user
    message_body = 'Still N Fork Alert: \n'
    for alert in alerts:
        local_date = alert['date'].astimezone(pytz.timezone(time_zone))
        message_body += f'{alert["type"]} {alert["height"]}ft\n{local_date.strftime("%A %m-%d %I:%M %p")}\n'
    message_body += constants.ARGW1_GRAPH_URL

    print("Number: ", to_number)
    print("Message: ", message_body)

    #Send the message
    message = client.messages.create(
        to=to_number,
        from_=constants.TWILIO_PHONE_NUMBER,
        body=message_body
    )



# Function to convert web data to a list
def web_to_list(web_page):

    # Collect all the rows containing river points from the prediction table in the raw html
    data_list = []
    soup = BeautifulSoup(web_page, 'html.parser')
    prediction_table = soup.find_all('table')[2]
    rows = prediction_table.find_all('tr')[2:]  # Ignore the first two header rows

    # Parse and convert each river point to a datetime and height, then add to data_list
    for row in rows:
        date = row.find_all('td')[0].text
        date = string_to_datetime(date)
        height = row.find_all('td')[1].text
        height = float(height[:-2])

        data_list.append((date, height))

    return data_list


# Declaration of the task as a function.
def get_river_data(url):
    web_page = requests.get(url).content
    return web_to_list(web_page)

# Store each data point from the list in the datastore
def store_data(data_list, datastore_client):

    # Delete all ARGW1 data from the datastore
    query = datastore_client.query(kind=constants.ARGW1)
    results = list(query.fetch())
    for entity in results:
        datastore_client.delete(entity.key)

    # Loop through the data list
    for data_point in data_list:
        # Create a key
        key = datastore_client.key(constants.ARGW1)

        # Create an entity
        entity = datastore.Entity(key=key)

        # Set the entity properties
        entity['date'] = data_point[0]
        entity['height'] = data_point[1]

        # Save the entity
        datastore_client.put(entity)


# Function to get the max height from the datastore
def get_max_point(datastore_client):
    query = datastore_client.query(kind=constants.ARGW1)
    results = list(query.fetch())

    # Get the data_point with the max height
    max_point = max(results, key=lambda x: x['height'])

    return max_point


def create_alert(user, max_height, datastore_client):
    # Create a key
    key = datastore_client.key(constants.ALERTS)

    # Create an entity
    peak = datastore.Entity(key=key)

    # Set the entity properties
    peak['user'] = user.key
    peak['date'] = max_height['date']
    peak['height'] = max_height['height']
    peak['type'] = 'Peak'

    # Save the entity
    datastore_client.put(peak)

    return peak

def below_base_height(user, max_point):
    # Check if the max height is below the users base height
    if max_point['height'] < user['height_base']:
        return True
    else:
        return False

def outside_user_hours(user, current_time):
    # Check if the current time is outside the user's hours

    local_time = current_time.astimezone(pytz.timezone(user["time_zone"]))
    local_hour = local_time.hour + local_time.minute / 60

    start_hour = user["start_hour"]
    end_hour = user["end_hour"]

    if start_hour <= end_hour:
        if local_hour < start_hour or local_hour > end_hour:
            return True
        else:
            return False

    else:
        if local_hour < start_hour and local_hour > end_hour:
            return True
        else:
            return False

def get_latest_peak(user, datastore_client):
    # Get the user's latest peak from Alerts in datastore
    query = datastore_client.query(kind=constants.ALERTS)
    query.add_filter('user', '=',  user.key)
    query.add_filter('type', '=', 'Peak')
    peaks = list(query.fetch())
    if len(peaks) > 0:
        max_peak = peaks[0]
        for peak in peaks:
            if peak['height'] > max_peak['height']:
                max_peak = peak
        return max_peak
    else:
        return None

def calc_height_time_diff(current_time, max_point, latest_peak):

    # If no previous peak or more than 6 hours in the past then set both time and height difference to max to trigger an alert
    if latest_peak is None or (current_time - latest_peak['date']).days > 0.25:
        return float('inf'), float('inf')
    
    # Calculate the time and height difference 
    time_diff = (latest_peak['date'] - max_point["date"]).days
    height_diff = max_point['height'] - latest_peak['height']

    return height_diff, time_diff

def no_alert_needed(user, current_time, max_point, latest_peak):

    height_diff, time_diff = calc_height_time_diff(current_time, max_point, latest_peak)
    
    # Calculate the minimum time difference for an alert
    min_time_diff = max((max_point["date"] - current_time).days * user["time_slope"], user["time_diff_min"])
    min_height_diff = max(user["height_diff_start"] - (max_point["height"] - user["height_base"]) * user["height_slope"], user["height_diff_min"])

    if height_diff < min_height_diff and time_diff < min_time_diff:
        return True
    else:
        return False


# Function to issue alerts based on the max height
def issue_alerts(datastore_client):
    # Get the max height
    max_point = get_max_point(datastore_client)


    # Get all the users in datastore
    query = datastore_client.query(kind=constants.USERS)
    users = list(query.fetch())


    # Loop through the users
    for user in users:

        current_time = datetime.now(timezone.utc)

        if below_base_height(user, max_point):
            continue

        if outside_user_hours(user, current_time):
            continue     

        latest_peak = get_latest_peak(user, datastore_client)

        if no_alert_needed(user, current_time, max_point, latest_peak):
            continue

        peak = create_alert(user, max_point, datastore_client)

        send_text_message([peak], user['phone_number'], user['time_zone'])


