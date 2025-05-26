from django.urls import path
from . import views

urlpatterns = [
    # Large file endpoints
    path('upload-large-csv/', views.upload_large_csv, name='upload_large_csv'),
    path('files/', views.list_files, name='list_files'),
    path('files/<uuid:file_id>/', views.get_file_status, name='get_file_status'),
    path('files/<uuid:file_id>/data/', views.get_file_data, name='get_file_data'),
    path('files/<uuid:file_id>/stats/', views.get_file_stats, name='get_file_stats'),
    path('files/<uuid:file_id>/delete/', views.delete_file, name='delete_file'),
    
    # Health check
    path('health/', views.health_check, name='health_check'),
    
    # Disk space
    path('disk-space/', views.get_disk_space, name='get_disk_space'),
]