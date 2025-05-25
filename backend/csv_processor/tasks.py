from celery import shared_task
from .file_processor import LargeCSVProcessor
import logging 
import base64

logger = logging.getLogger(__name__)

@shared_task
def process_large_csv(file_id, move_from_temp=False, file_content_b64=None):
    """
    Celery task to process large CSV files asynchronously.
    
    Args:
        file_id: UUID of the UploadedFile record
        move_from_temp: If True, move file from temp to permanent location first
        file_content_b64: For large files, base64 encoded file content for serialization
    """
    logger.info(f"CELERY TASK STARTED: {file_id}")
    logger.info(f"Move from temp: {move_from_temp}")
    logger.info(f"File content provided: {file_content_b64 is not None}")
    
    try:
        # Decode file content if provided
        file_content = None
        if file_content_b64:
            logger.info(f"Decoding base64 content, size: {len(file_content_b64)}")
            file_content = base64.b64decode(file_content_b64)
            logger.info(f"Decoded file content size: {len(file_content)} bytes")
        
        logger.info(f"Starting file processor for {file_id}")
        processor = LargeCSVProcessor()
        processor.process_file_async(file_id, move_from_temp, file_content)
        
        logger.info(f"CELERY TASK COMPLETED SUCCESSFULLY: {file_id}")
        
    except Exception as e:
        logger.error(f"CELERY TASK FAILED: {file_id} - Error: {str(e)}")
        logger.exception("Full traceback:")
        
        # Update database record to failed status
        try:
            from .models import UploadedFile
            db_file = UploadedFile.objects.get(id=file_id)
            db_file.status = 'failed'
            db_file.error_message = str(e)
            db_file.save()
            logger.info(f"Updated file {file_id} status to failed")
        except Exception as db_error:
            logger.error(f"Failed to update database status: {db_error}")
        
        raise