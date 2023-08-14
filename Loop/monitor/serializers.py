from rest_framework import serializers

class GenericResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    data = serializers.JSONField(required=False)

