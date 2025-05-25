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
    
    def create_file_record_memory(self, filename: str, file_size: int) -> UploadedFile:
        """
        Create database record for large files processed in memory.
        """
        # Create database record without file_path for memory processing
        db_file = UploadedFile.objects.create(
            filename=filename,
            file_path='',  # No physical file path for memory processing
            file_size=file_size,
            status='uploading'
        )
        
        logger.info(f"Created memory record for large file {filename} with ID {db_file.id}")
        return db_file
    
    def analyze_file_structure_from_content(self, file_content: bytes) -> Tuple[list, dict, int]:
        """
        Analyze CSV file structure from file content bytes.
        """
        import io
        
        # Convert bytes to string IO
        content_str = file_content.decode('utf-8')
        file_io = io.StringIO(content_str)
        
        # Read first chunk to determine structure
        chunk_iter = pd.read_csv(file_io, chunksize=self.chunk_size)
        first_chunk = next(chunk_iter)
        
        columns = first_chunk.columns.tolist()
        dtypes = first_chunk.dtypes.astype(str).to_dict()
        
        # Estimate total rows by content size
        avg_row_size = len(content_str) / len(first_chunk) if len(first_chunk) > 0 else 1
        estimated_rows = int(len(content_str) / avg_row_size)
        
        return columns, dtypes, estimated_rows
    
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
    
    def process_file_async(self, file_id: str, move_from_temp: bool = False, file_content: bytes = None):
        """
        Process file asynchronously (to be used with Celery).
        
        Args:
            file_id: UUID of the UploadedFile record
            move_from_temp: If True, move file from temp to permanent location first
            file_content: For large files, process directly from memory content
        """
        try:
            logger.info(f"PROCESSOR: Starting async processing for file {file_id}")
            db_file = UploadedFile.objects.get(id=file_id)
            logger.info(f"PROCESSOR: Found file record: {db_file.filename}")
            
            db_file.status = 'processing'
            db_file.save()
            logger.info(f"PROCESSOR: Updated status to processing")
            
            # Handle different processing modes
            if file_content:
                # Large file: process from memory content
                logger.info(f"PROCESSOR: Processing large file {db_file.filename} from memory content, size: {len(file_content)} bytes")
                columns, dtypes, estimated_rows = self.analyze_file_structure_from_content(file_content)
                logger.info(f"PROCESSOR: Analysis complete - columns: {len(columns)}, estimated rows: {estimated_rows}")
            elif move_from_temp:
                # Move from temp to permanent location if needed
                logger.info(f"PROCESSOR: Moving file from temp location")
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
                
                logger.info(f"PROCESSOR: Moved large file from temp to permanent location: {permanent_path}")
                columns, dtypes, estimated_rows = self.analyze_file_structure(db_file.file_path)
            else:
                # Small file: analyze from file path
                logger.info(f"PROCESSOR: Analyzing small file from path: {db_file.file_path}")
                columns, dtypes, estimated_rows = self.analyze_file_structure(db_file.file_path)
                logger.info(f"PROCESSOR: Small file analysis complete")
            
            # Update database with initial analysis
            logger.info(f"PROCESSOR: Updating database with analysis results")
            db_file.columns = columns
            db_file.dtypes = dtypes
            db_file.total_rows = estimated_rows
            db_file.processing_progress = 50.0
            db_file.save()
            
            # Get detailed statistics only for files with physical paths
            if db_file.file_path:
                logger.info(f"PROCESSOR: Getting detailed statistics for file with path")
                stats = self.get_file_statistics(db_file.file_path)
                # Update with final results
                db_file.total_rows = stats['total_rows']
                logger.info(f"PROCESSOR: Statistics complete, final row count: {stats['total_rows']}")
            else:
                logger.info(f"PROCESSOR: Skipping detailed statistics for memory-processed file")
            
            db_file.status = 'completed'
            db_file.processing_progress = 100.0
            db_file.save()
            
            logger.info(f"PROCESSOR: Successfully processed file {db_file.filename}")
            
        except Exception as e:
            logger.error(f"PROCESSOR: Error processing file {file_id}: {e}")
            logger.exception("PROCESSOR: Full traceback:")
            try:
                db_file = UploadedFile.objects.get(id=file_id)
                db_file.status = 'failed'
                db_file.error_message = str(e)
                db_file.save()
                logger.info(f"PROCESSOR: Updated file {file_id} status to failed")
            except Exception as db_error:
                logger.error(f"PROCESSOR: Failed to update database status: {db_error}")
            raise