from celery import shared_task
from .file_processor import LargeCSVProcessor

@shared_task
def process_large_csv(file_id, move_from_temp=False, file_content=None):
    """
    Celery task to process large CSV files asynchronously.
    
    Args:
        file_id: UUID of the UploadedFile record
        move_from_temp: If True, move file from temp to permanent location first
        file_content: For large files, process directly from memory content
    """
    processor = LargeCSVProcessor()
    processor.process_file_async(file_id, move_from_temp, file_content)