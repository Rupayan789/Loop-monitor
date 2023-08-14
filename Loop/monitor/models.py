# monitor/models.py
from django.db import models

class StoreTimezone(models.Model):
    store_id = models.CharField(max_length=50, primary_key=True)
    timezone_str = models.CharField(max_length=100)  

class BusinessHours(models.Model):
    store_id = models.CharField(max_length=50,db_index=True)
    day = models.IntegerField()  # 0=Monday, 6=Sunday
    start_time_local = models.TimeField()
    end_time_local = models.TimeField()
    timezone = models.ForeignKey(StoreTimezone, on_delete=models.SET_NULL, null=True)  # ForeignKey to StoreTimezone

    class Meta:
        indexes = [
            models.Index(fields=['store_id'])  # Create an index on the store_id field
        ]

    def __str__(self):
        return f"{self.store_id} - {self.day}: {self.start_time_local} - {self.end_time_local})"

class StoreStatus(models.Model):
    id = models.AutoField(primary_key=True)
    store_id = models.CharField(max_length=50, db_index=True)
    timestamp_utc = models.DateTimeField()
    status = models.CharField(max_length=10)  # 'active' or 'inactive'

    class Meta:
        indexes = [
            models.Index(fields=['store_id'])  # Create an index on the store_id field
        ]