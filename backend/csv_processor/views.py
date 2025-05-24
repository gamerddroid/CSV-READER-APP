import pandas as pd
import os
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator
from .models import UploadedFile
from .file_processor import LargeCSVProcessor
from .tasks import process_large_csv
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@parser_classes([MultiPartParser])
def upload_large_csv(request):
    """
    Upload and process large CSV files.
    Files are saved to disk and processed asynchronously.
    """
    try:
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        uploaded_file = request.FILES['file']
        
        if not uploaded_file.name.endswith('.csv'):
            return Response(
                {'error': 'File must be a CSV'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check file size (optional limit for very large files)
        max_size = 50 * 1024 * 1024 * 1024  # 50GB limit
        if uploaded_file.size > max_size:
            return Response(
                {'error': f'File too large. Maximum size is {max_size // (1024**3)}GB'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        processor = LargeCSVProcessor()
        
        # For files > 1GB, handle copying in background
        large_file_threshold = 1 * 1024 * 1024 * 1024  # 1GB
        if uploaded_file.size > large_file_threshold:
            # Save to temporary location first
            db_file = processor.save_uploaded_file_temp(uploaded_file, uploaded_file.name)
            # Process everything (copy + analysis) in background
            process_large_csv.delay(str(db_file.id), move_from_temp=True)
        else:
            # Small files: immediate copy, background analysis
            db_file = processor.save_uploaded_file(uploaded_file, uploaded_file.name)
            process_large_csv.delay(str(db_file.id))
        
        return Response({
            'message': 'File uploaded successfully. Processing started.',
            'file_id': str(db_file.id),
            'filename': db_file.filename,
            'file_size': db_file.file_size,
            'status': db_file.status
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return Response(
            {'error': f'An error occurred: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_file_status(request, file_id):
    """
    Get the processing status and metadata of an uploaded file.
    """
    try:
        db_file = UploadedFile.objects.get(id=file_id)
        
        return Response({
            'file_id': str(db_file.id),
            'filename': db_file.filename,
            'file_size': db_file.file_size,
            'status': db_file.status,
            'total_rows': db_file.total_rows,
            'columns': db_file.columns,
            'dtypes': db_file.dtypes,
            'processing_progress': db_file.processing_progress,
            'error_message': db_file.error_message,
            'created_at': db_file.created_at,
            'updated_at': db_file.updated_at
        })
        
    except UploadedFile.DoesNotExist:
        raise Http404("File not found")


@api_view(['GET'])
def get_file_data(request, file_id):
    """
    Get paginated data from a processed CSV file.
    Supports efficient pagination for very large files.
    """
    try:
        db_file = UploadedFile.objects.get(id=file_id)
        
        if db_file.status != 'completed':
            return Response(
                {'error': f'File processing not completed. Current status: {db_file.status}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get pagination parameters
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 100))
        
        # Validate pagination parameters
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 10000:  # Limit max page size
            page_size = 100
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Check if offset is beyond file
        if db_file.total_rows and offset >= db_file.total_rows:
            return Response({
                'data': [],
                'page': page,
                'page_size': page_size,
                'total_rows': db_file.total_rows,
                'total_pages': (db_file.total_rows + page_size - 1) // page_size,
                'has_next': False,
                'has_previous': page > 1
            })
        
        processor = LargeCSVProcessor()
        
        # Get the requested chunk of data
        df_chunk = processor.get_data_chunk(db_file.file_path, offset, page_size)
        
        # Replace NaN values with None for JSON compatibility
        import numpy as np
        df_chunk = df_chunk.replace({np.nan: None})
        
        # Convert to records
        data = df_chunk.to_dict('records')
        
        # Calculate pagination info
        total_pages = (db_file.total_rows + page_size - 1) // page_size if db_file.total_rows else 1
        has_next = page < total_pages
        has_previous = page > 1
        
        return Response({
            'data': data,
            'page': page,
            'page_size': page_size,
            'total_rows': db_file.total_rows,
            'total_pages': total_pages,
            'has_next': has_next,
            'has_previous': has_previous,
            'columns': db_file.columns,
            'dtypes': db_file.dtypes
        })
        
    except UploadedFile.DoesNotExist:
        raise Http404("File not found")
    except Exception as e:
        logger.error(f"Error getting file data: {e}")
        return Response(
            {'error': f'An error occurred: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def list_files(request):
    """
    List all uploaded files with their status.
    """
    files = UploadedFile.objects.all().order_by('-created_at')
    
    file_list = []
    for file_obj in files:
        file_list.append({
            'file_id': str(file_obj.id),
            'filename': file_obj.filename,
            'file_size': file_obj.file_size,
            'status': file_obj.status,
            'total_rows': file_obj.total_rows,
            'processing_progress': file_obj.processing_progress,
            'created_at': file_obj.created_at,
            'updated_at': file_obj.updated_at
        })
    
    return Response({'files': file_list})


@api_view(['DELETE'])
def delete_file(request, file_id):
    """
    Delete an uploaded file and its data.
    """
    try:
        db_file = UploadedFile.objects.get(id=file_id)
        filename = db_file.filename
        db_file.delete()  # This will also delete the physical file
        
        return Response({
            'message': f'File {filename} deleted successfully'
        })
        
    except UploadedFile.DoesNotExist:
        raise Http404("File not found")


@api_view(['GET'])
def get_file_stats(request, file_id):
    """
    Get detailed statistics about a processed file.
    """
    try:
        db_file = UploadedFile.objects.get(id=file_id)
        
        if db_file.status != 'completed':
            return Response(
                {'error': f'File processing not completed. Current status: {db_file.status}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        processor = LargeCSVProcessor()
        stats = processor.get_file_statistics(db_file.file_path)
        
        return Response({
            'file_id': str(db_file.id),
            'filename': db_file.filename,
            'statistics': stats
        })
        
    except UploadedFile.DoesNotExist:
        raise Http404("File not found")


@api_view(['GET'])
def health_check(request):
    """Health check endpoint."""
    return JsonResponse({'status': 'healthy'})