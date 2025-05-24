import pandas as pd
import os
import tempfile
import uuid
from typing import Generator, Dict, Any, Tuple
from .models import UploadedFile
import logging

logger = logging.getLogger(__name__)

class LargeCSVProcessor:
    def __init__(self, chunk_size: int = 10000):
        """
        Initialize the processor with configurable chunk size.
        
        Args:
            chunk_size: Number of rows to process at a time
        """
        self.chunk_size = chunk_size
        
    def save_uploaded_file(self, uploaded_file, filename: str) -> UploadedFile:
        """
        Save uploaded file to disk and create database record.
        """
        # Create uploads directory if it doesn't exist
        uploads_dir = '/tmp/csv_uploads'
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(filename)[1]
        unique_filename = f"{file_id}{file_extension}"
        file_path = os.path.join(uploads_dir, unique_filename)
        
        # Save file to disk
        with open(file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Create database record
        db_file = UploadedFile.objects.create(
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            status='uploading'
        )
        
        logger.info(f"Saved file {filename} with ID {db_file.id}")
        return db_file
    
    def save_uploaded_file_temp(self, uploaded_file, filename: str) -> UploadedFile:
        """
        Save uploaded file to temporary location for large files.
        """
        # Create temp directory
        temp_dir = '/tmp/csv_temp_uploads'
        os.makedirs(temp_dir, exist_ok=True)
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(filename)[1]
        unique_filename = f"{file_id}{file_extension}"
        temp_file_path = os.path.join(temp_dir, unique_filename)
        
        # Save file to temp location
        with open(temp_file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        
        # Get file size
        file_size = os.path.getsize(temp_file_path)
        
        # Create database record with temp path
        db_file = UploadedFile.objects.create(
            filename=filename,
            file_path=temp_file_path,  # Will be moved later
            file_size=file_size,
            status='uploading'
        )
        
        logger.info(f"Saved large file {filename} to temp location with ID {db_file.id}")
        return db_file
    
    def analyze_file_structure(self, file_path: str) -> Tuple[list, dict, int]:
        """
        Analyze CSV file structure without loading entire file into memory.
        
        Returns:
            Tuple of (columns, dtypes, estimated_rows)
        """
        # Read just the first few chunks to determine structure
        chunk_iter = pd.read_csv(file_path, chunksize=self.chunk_size)
        
        first_chunk = next(chunk_iter)
        columns = first_chunk.columns.tolist()
        dtypes = first_chunk.dtypes.astype(str).to_dict()
        
        # Estimate total rows by file size
        file_size = os.path.getsize(file_path)
        avg_row_size = len(first_chunk.to_csv()) / len(first_chunk)
        estimated_rows = int(file_size / avg_row_size)
        
        return columns, dtypes, estimated_rows
    
    def get_data_chunk(self, file_path: str, offset: int, limit: int) -> pd.DataFrame:
        """
        Get a specific chunk of data from the CSV file.
        
        Args:
            file_path: Path to the CSV file
            offset: Starting row number
            limit: Number of rows to return
            
        Returns:
            DataFrame with the requested rows
        """
        try:
            # Skip rows before offset and read only the required number
            if offset == 0:
                df = pd.read_csv(file_path, nrows=limit)
            else:
                df = pd.read_csv(file_path, skiprows=range(1, offset + 1), nrows=limit)
            
            return df
        except Exception as e:
            logger.error(f"Error reading chunk from {file_path}: {e}")
            raise
    
    def stream_csv_chunks(self, file_path: str) -> Generator[pd.DataFrame, None, None]:
        """
        Generator that yields chunks of the CSV file.
        
        Args:
            file_path: Path to the CSV file
            
        Yields:
            DataFrame chunks
        """
        try:
            chunk_iter = pd.read_csv(file_path, chunksize=self.chunk_size)
            for chunk in chunk_iter:
                yield chunk
        except Exception as e:
            logger.error(f"Error streaming chunks from {file_path}: {e}")
            raise
    
    def get_file_statistics(self, file_path: str) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the CSV file.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            Dictionary with file statistics
        """
        stats = {
            'total_rows': 0,
            'columns': [],
            'dtypes': {},
            'null_counts': {},
            'memory_usage': 0,
            'file_size': os.path.getsize(file_path)
        }
        
        chunk_count = 0
        null_counts = {}
        
        try:
            for chunk in self.stream_csv_chunks(file_path):
                if chunk_count == 0:
                    # First chunk - initialize structure
                    stats['columns'] = chunk.columns.tolist()
                    stats['dtypes'] = chunk.dtypes.astype(str).to_dict()
                    null_counts = chunk.isnull().sum().to_dict()
                else:
                    # Accumulate null counts
                    chunk_nulls = chunk.isnull().sum().to_dict()
                    for col, count in chunk_nulls.items():
                        null_counts[col] += count
                
                stats['total_rows'] += len(chunk)
                stats['memory_usage'] += chunk.memory_usage(deep=True).sum()
                chunk_count += 1
            
            stats['null_counts'] = null_counts
            
        except Exception as e:
            logger.error(f"Error calculating statistics for {file_path}: {e}")
            raise
        
        return stats
    
    def process_file_async(self, file_id: str, move_from_temp: bool = False):
        """
        Process file asynchronously (to be used with Celery).
        
        Args:
            file_id: UUID of the UploadedFile record
            move_from_temp: If True, move file from temp to permanent location first
        """
        try:
            db_file = UploadedFile.objects.get(id=file_id)
            db_file.status = 'processing'
            db_file.save()
            
            # Move from temp to permanent location if needed
            if move_from_temp:
                uploads_dir = '/tmp/csv_uploads'
                os.makedirs(uploads_dir, exist_ok=True)
                
                temp_path = db_file.file_path
                permanent_path = temp_path.replace('/csv_temp_uploads/', '/csv_uploads/')
                
                # Move file
                import shutil
                shutil.move(temp_path, permanent_path)
                
                # Update database path
                db_file.file_path = permanent_path
                db_file.save()
                
                logger.info(f"Moved large file from temp to permanent location: {permanent_path}")
            
            # Analyze file structure
            columns, dtypes, estimated_rows = self.analyze_file_structure(db_file.file_path)
            
            # Update database with initial analysis
            db_file.columns = columns
            db_file.dtypes = dtypes
            db_file.total_rows = estimated_rows
            db_file.processing_progress = 50.0
            db_file.save()
            
            # Get detailed statistics
            stats = self.get_file_statistics(db_file.file_path)
            
            # Update with final results
            db_file.total_rows = stats['total_rows']
            db_file.status = 'completed'
            db_file.processing_progress = 100.0
            db_file.save()
            
            logger.info(f"Successfully processed file {db_file.filename}")
            
        except Exception as e:
            logger.error(f"Error processing file {file_id}: {e}")
            db_file = UploadedFile.objects.get(id=file_id)
            db_file.status = 'failed'
            db_file.error_message = str(e)
            db_file.save()