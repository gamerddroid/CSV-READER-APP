# Generated by Django 4.2.7 on 2025-05-24 16:40

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='UploadedFile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('filename', models.CharField(max_length=255)),
                ('file_path', models.CharField(max_length=500)),
                ('file_size', models.BigIntegerField()),
                ('status', models.CharField(choices=[('uploading', 'Uploading'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')], default='uploading', max_length=20)),
                ('total_rows', models.BigIntegerField(blank=True, null=True)),
                ('columns', models.JSONField(blank=True, null=True)),
                ('dtypes', models.JSONField(blank=True, null=True)),
                ('processing_progress', models.FloatField(default=0.0)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
