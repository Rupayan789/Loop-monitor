from celery import shared_task
import time
from . import models
import csv
from .utils import *
from django_celery_results.models import TaskResult
import json
from datetime import timedelta

@shared_task(bind=True,ignore_result=False)
def computeStoreDataEntry(self):
    #operations 
    
    try:
 
        file_path = 'store status2.csv'

        # Define batch size for processing
        batch_size = 1000

        # Process and insert data in batches
        batch = []
        count = 0
        with open(file_path, 'r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            
            for row in csv_reader:
                store_id = row['store_id']
                
                status = row['status']

                # Get StoreTimezone for the store_id
                try:
                    store_timezone = models.StoreTimezone.objects.get(store_id=store_id).timezone_str;
                except models.StoreTimezone.DoesNotExist:
                    store_timezone = "America/Chicago"

                timestamp_local = convert_utc_to_local(row['timestamp_utc'],store_timezone)
                count+=1
                
                

                batch.append(models.StoreStatus(store_id=store_id, timestamp_utc=timestamp_local, status=status))

                # Insert batch into database when it reaches the batch size
                if len(batch) >= batch_size:
                    models.StoreStatus.objects.bulk_create(batch)
                    batch = []

            # Insert any remaining records in the batch
            if batch:
                models.StoreStatus.objects.bulk_create(batch)
            
       
        
        return 'Completed'
    
    except Exception as e:
            return str(e)

@shared_task(bind=True,ignore_result=False)
def computeReport(self):
    # Retrieve the maximum timestamp from observations CSV (reference timestamp)
    reference_timestamp = get_max_timestamp() 

    # Define time intervals
    one_hour = timedelta(hours=1)
    one_day = timedelta(days=1)
    one_week = timedelta(weeks=1)

    file_path = f'report.csv' # the report file created

    header = [ 'store_id', 'uptime_last_hour(in minutes)', 'uptime_last_day(in hours)', 'update_last_week(in hours)', 'downtime_last_hour(in minutes)', 'downtime_last_day(in hours)', 'downtime_last_week(in hours)' ]

    update_store_uptime_downtime(row=header, file_path=file_path) # adds the header to the csv file

    unique_store_ids = get_unique_store_ids() # get all the unique store ids 

    # Iterate through each store
    for store_id in unique_store_ids:  

        last_hr_activity_count = None # the dict that would contains the uptime minutes and downtime minutes in last hour
        last_day_activity_count = None # the dict that would contains the uptime minutes and downtime minutes in last day

        active_count = 0 # aggregator that would sum up all uptime hours over the week
        inactive_count = 0 # aggregator that would sum up all downtime hours over the week

        current_timestamp = reference_timestamp 

        flag = 0 # a flag value to be set after last hour activity time is computed

        while current_timestamp >= reference_timestamp - one_week: # iterate until the current timestamp within a week
           
            # Get the day of the week (0=Monday, 6=Sunday)
            dayOfWeek = current_timestamp.weekday()

        
            business_hours = get_business_hours(store_id, dayOfWeek)  # Get business hours for the store and day  

            # if no business hour record exists ,then consider it to be open 24 * 7
            if business_hours.exists() is False:
                business_hours = [] 
                obj = BusinessHours(store_id = store_id, day = dayOfWeek, start_time_local= datetime.time(0, 0, 0), end_time_local= datetime.time(23, 59, 59))
                business_hours.append(obj)
            
           # iterate over each business hour object .i.e a day can have multiple business hours obj  6 AM - 10 AM , 3 PM - 10 PM
            for business_hr in business_hours:

                # converts current timestamp date and time to new timestamp .i.e 23-09-2023 12:23:12  and  10:00:00  -> 23-09-2023 10:00:00
                start_time_local = replaceTimeFromDatetime(current_timestamp, business_hr.start_time_local) 
                end_time_local = replaceTimeFromDatetime(current_timestamp,business_hr.end_time_local)

                # calculate last hour uptime and downtime in minutes for once
                if flag is 0:
                    last_hr_activity_count = minutes_store_active_last_hr(store_id = store_id, end_timestamp = min(end_time_local,reference_timestamp))
                    flag = 1

                # Determine if the store is active or inactive during this interval
                activity_count = is_store_active(store_id, start_time_local, end_time_local)  # Implement this

                active_count += activity_count['active_count']


                inactive_count += activity_count['inactive_count']

            # compute last day uptime and downtime only once
            if last_day_activity_count is None:
                last_day_activity_count = activity_count

            current_timestamp = current_timestamp - one_day # decrement current timestamp by a day until the start of the week

        last_week_activity_count = { 'active_count':active_count , 'inactive_count':inactive_count }

        # Finally write the record to the csv
        
        row = [store_id, last_hr_activity_count['active_count'], last_day_activity_count['active_count'], last_week_activity_count['active_count'],last_hr_activity_count['inactive_count'],last_day_activity_count['inactive_count'], last_week_activity_count['inactive_count']]
        
        update_store_uptime_downtime(row , file_path) 

    