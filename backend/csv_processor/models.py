from django.db import models
import uuid
import os


class UploadedFile(models.Model):
    STATUS_CHOICES = [
        ('uploading', 'Uploading'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500, blank=True)  # Optional for memory-only processing
    file_size = models.BigIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploading')
    total_rows = models.BigIntegerField(null=True, blank=True)
    columns = models.JSONField(null=True, blank=True)
    dtypes = models.JSONField(null=True, blank=True)
    processing_progress = models.FloatField(default=0.0)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.filename} ({self.status})"
    
    def delete(self, *args, **kwargs):
        # Clean up the file when deleting the record (only if file exists on disk)
        if self.file_path and os.path.exists(self.file_path):
            os.remove(self.file_path)
        super().delete(*args, **kwargs)