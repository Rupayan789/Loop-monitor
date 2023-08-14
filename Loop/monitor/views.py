from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view
import requests
from datetime import datetime
import csv
from . import models
from .utils import *
from .task import *
from celery.result import AsyncResult
from django_celery_results.models import TaskResult
from decouple import config




@api_view(['GET'])
def trigger_report(request):
    task = computeReport.delay()
    return create_generic_response(status="success",message=f'Data uploading started..',data={'task_id':task.id},status_code=200)




@api_view(['GET'])
def get_report(request,task_id):
    result = AsyncResult(task_id)
    # print(result.ready())
    if result.ready():
        task_result = TaskResult.objects.get(task_id=task_id)
        return create_generic_response(status="success",message=f'Process successfully completed',data=json.loads(task_result.result),status_code=200)
    else:
        return create_generic_response(status="success",message=f'Process still running',data=None,status_code=200)
    




@api_view(['GET'])
def get_store_timezone(request):

    try:
        url = f"https://drive.google.com/uc?export=download&id={config('STORE_TIMEZONE_FILE_ID')}"
        response = requests.get(url)

        if response.status_code == 200:
            csv_data = response.text
        else:
            return create_generic_response(status='error',message=f'Data fetch failed',status_code=response.status_code)
        csv_rows = csv.DictReader(csv_data.splitlines())
        batch_size = 1000
        batch = []

        for row in csv_rows:
            batch.append(models.StoreTimezone(store_id=row['store_id'], timezone_str=row['timezone_str']))
            
            if len(batch) >= batch_size:
                models.StoreTimezone.objects.bulk_create(batch)
                batch = []

        # Insert any remaining rows
        if batch:
            models.StoreTimezone.objects.bulk_create(batch)

        return create_generic_response(status="success",message=f'Data fetched successfully',status_code=200)
    
    except Exception as e:

        return create_generic_response(status="error",message=f'Request failed: {str(e)}',status_code=500)
    


    
@api_view(['GET'])
def get_business_hours(request):

    try:
        url = f"https://drive.google.com/uc?export=download&id={config('BUSINESS_HOURS_FILE_ID')}"
        response = requests.get(url)
        
        if response.status_code == 200:
            csv_data = response.text
        else:
            return create_generic_response(status='error',message=f'Data fetch failed',status_code=response.status_code,data=response)
        csv_rows = csv.DictReader(csv_data.splitlines())
        batch_size = 1000
        batch = []

        for row in csv_rows:
            timezone = models.StoreTimezone.objects.filter(store_id=row['store_id']).first();
            if timezone is None:
                timezone = models.StoreTimezone.objects.create(store_id=row['store_id'], timezone_str="America/Chicago")
            
            batch.append(models.BusinessHours(store_id=row['store_id'], day=row['day'],start_time_local=row['start_time_local'], end_time_local=row['end_time_local'],timezone=timezone))
            
            if len(batch) >= batch_size:
                models.BusinessHours.objects.bulk_create(batch)
                batch = []

        # Insert any remaining rows
        if batch:
            models.BusinessHours.objects.bulk_create(batch)

        return create_generic_response(status="success",message=f'Data fetched successfully',data=csv_rows,status_code=200)
    
    except Exception as e:
        
        return create_generic_response(status="error",message=f'Request failed: {str(e)}',status_code=500)
    


    
@api_view(['GET'])
def get_store_status(request):

    task = computeStoreDataEntry.delay()
    return create_generic_response(status="success",message=f'Data uploading started..',data={'task_id':task.id},status_code=200)



    
@api_view(['GET'])
def get_store_upload_status(request,task_id):
    result = AsyncResult(task_id)
    # print(result.ready())
    if result.ready():
        task_result = TaskResult.objects.get(task_id=task_id)
        return create_generic_response(status="success",message=f'Process successfully completed',data=json.loads(task_result.result),status_code=200)
    else:
        return create_generic_response(status="success",message=f'Process still running',data=None,status_code=200)
    
