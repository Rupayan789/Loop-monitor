from rest_framework.response import Response
import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import pytz
from .models import *
from django.db.models import Max
from datetime import timedelta
import csv

# to create JSON Response to send 
def create_generic_response(status, message, data=None, status_code=None):
    response_data = {
        'status': status,
        'message': message,
        'data': data
    }
    return Response(response_data, status=status_code)

# convert timestamp_utc to  timestamp based on local timezone and store it to STORE STATUS table
def convert_utc_to_local(timestamp,timezone):
    timestamp = timestamp.split('.')[0]
    timestamp_utc = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
    local_time = timestamp_utc.replace(tzinfo=pytz.UTC).astimezone(pytz.timezone(timezone))
    return local_time

# this function is to access the google drive api to download large file
def get_drive_credentials():
    creds = None
    SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds


def get_max_timestamp():
    max_timestamp = StoreStatus.objects.aggregate(max_timestamp=Max('timestamp_utc'))['max_timestamp']
    return max_timestamp

def get_business_hours(store_id,day):
    businessHrsLst = BusinessHours.objects.filter(store_id=store_id,day=day)
    return businessHrsLst


def is_store_active(store_id, interval_start, interval_end):
    marker = interval_end
    one_hour = timedelta(hours=1)
    active = 0
    inactive = 0
    # decrement the marker by each hour and check if the store is active or inactive depending on the maximum number of active or inactive counts within the hour 
    while marker >= interval_start + one_hour:
        statusDict = StoreStatus.objects.filter(store_id = store_id, timestamp_utc__range=(marker-one_hour,marker+one_hour))
        marker = marker - one_hour
        if statusDict.exists() is False: # consider the store active if it has no data for that hour (within the business hour)
            active += 1
            continue
        hr_active = 0
        hr_inactive = 0
        for item in statusDict:
            if item.status is 'active':
                hr_active += 1
            else:
                hr_inactive += 1
        if hr_active >= hr_inactive:
            active += 1
        else:
            inactive += 1
        

    return { 'active_count' : active, 'inactive_count' : inactive}

def minutes_store_active_last_hr(store_id, end_timestamp):
    marker = end_timestamp - timedelta(hours=1)
    one_min = timedelta(minutes=1)
    active_count = 0 
    inactive_count = 0
    # find the total uptime and downtime minutes by finding records for each minute and checking the status
    while marker < end_timestamp:
        statusDict = StoreStatus.objects.filter(store_id = store_id, timestamp_utc__range=(marker,marker+one_min)).last() 
        if statusDict is None or statusDict.status is 'active': # if record not present in timeinterval consider active
            active_count += 1
        else:
            inactive_count += 1

        marker = marker + one_min # increment marker by one min

    return { 'active_count' : active_count, 'inactive_count' : inactive_count}

def get_unique_store_ids():
    unique_store_ids = StoreStatus.objects.values_list('store_id', flat=True).distinct()
    return unique_store_ids

def update_store_uptime_downtime(row , file_path):
    # write each row to csv file
    with open(file_path, 'a', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(row)

    csv_file.close() # close file stream


def replaceTimeFromDatetime(datetime_obj,time_obj):
   
    # Get the current date
    current_date = datetime.date.today()

    # Create a new datetime.datetime object with the date and the time from business_hr.start_time_local
    new_datetime_obj = datetime.datetime.combine(current_date, time_obj)

    # Replace the time component of datetime_obj with the new time
    current_timestamp_with_new_time = datetime_obj.replace(hour=new_datetime_obj.hour, minute=new_datetime_obj.minute, second=new_datetime_obj.second)
    
    return current_timestamp_with_new_time