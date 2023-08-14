from django.urls import path
from . import views


urlpatterns = [
    path('trigger-report',views.trigger_report,name='trigger_report'),
    path('get-report/<str:task_id>',views.get_report,name='get_report'),
    path('get-store-timezone',views.get_store_timezone,name="get_store_timezone"),
    path('get-business-hour',views.get_business_hours,name='get_business_hours'),
    path('get-store-status',views.get_store_status,name='get_store_status'),
    path('get-store-upload-status/<str:task_id>',views.get_store_upload_status,name='get_store_upload-status')
]

