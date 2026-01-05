from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Device
from farms.models import Batch  # Changed from batches.models
from .serializers import DeviceSerializer, BatchSerializer

class BatchViewSet(viewsets.ModelViewSet):
    queryset = Batch.objects.all().select_related('farm')
    serializer_class = BatchSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['farm']
    search_fields = ['name', 'batch_number']

class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all().select_related('farm', 'batch', 'farm__farmer', 'farm__farmer__user')
    serializer_class = DeviceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['farm', 'batch', 'status', 'device_type']
    search_fields = ['device_name', 'serial_number']