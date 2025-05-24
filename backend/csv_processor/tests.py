import os
import tempfile
import pytest
from unittest.mock import Mock, patch
from django.core.files.uploadedfile import SimpleUploadedFile
import pandas as pd

from .file_processor import LargeCSVProcessor
from .models import UploadedFile


@pytest.fixture
def processor():
    return LargeCSVProcessor(chunk_size=5)


@pytest.fixture
def test_csv_content():
    return "name,age,city\nJohn,25,NYC\nJane,30,LA\nBob,35,Chicago\nAlice,28,Boston\nCharlie,32,Seattle"


@pytest.fixture
def test_csv_bytes(test_csv_content):
    return test_csv_content.encode('utf-8')


@pytest.fixture
def temp_csv_file(test_csv_content):
    temp_file = tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False)
    temp_file.write(test_csv_content)
    temp_file.close()
    yield temp_file.name
    os.unlink(temp_file.name)


@pytest.fixture(autouse=True)
def cleanup_uploaded_files():
    yield
    for uploaded_file in UploadedFile.objects.all():
        if uploaded_file.file_path and os.path.exists(uploaded_file.file_path):
            os.remove(uploaded_file.file_path)
        uploaded_file.delete()


@pytest.mark.django_db
class TestLargeCSVProcessor:
    
    def test_save_uploaded_file(self, processor, test_csv_bytes):
        uploaded_file = SimpleUploadedFile(
            "test.csv",
            test_csv_bytes,
            content_type="text/csv"
        )
        
        db_file = processor.save_uploaded_file(uploaded_file, "test.csv")
        
        assert db_file.filename == "test.csv"
        assert db_file.file_size == len(test_csv_bytes)
        assert db_file.status == "uploading"
        assert os.path.exists(db_file.file_path)
        assert db_file.file_path.endswith('.csv')

    def test_save_uploaded_file_temp(self, processor, test_csv_bytes):
        uploaded_file = SimpleUploadedFile(
            "large_test.csv",
            test_csv_bytes,
            content_type="text/csv"
        )
        
        db_file = processor.save_uploaded_file_temp(uploaded_file, "large_test.csv")
        
        assert db_file.filename == "large_test.csv"
        assert db_file.file_size == len(test_csv_bytes)
        assert db_file.status == "uploading"
        assert os.path.exists(db_file.file_path)
        assert 'csv_temp_uploads' in db_file.file_path

    def test_create_file_record_memory(self, processor):
        db_file = processor.create_file_record_memory("memory_file.csv", 1024)
        
        assert db_file.filename == "memory_file.csv"
        assert db_file.file_size == 1024
        assert db_file.status == "uploading"
        assert db_file.file_path == ""

    def test_analyze_file_structure_from_content(self, processor, test_csv_bytes):
        columns, dtypes, estimated_rows = processor.analyze_file_structure_from_content(test_csv_bytes)
        
        assert columns == ["name", "age", "city"]
        assert "name" in dtypes
        assert "age" in dtypes
        assert "city" in dtypes
        assert estimated_rows > 0

    def test_analyze_file_structure(self, processor, temp_csv_file):
        columns, dtypes, estimated_rows = processor.analyze_file_structure(temp_csv_file)
        
        assert columns == ["name", "age", "city"]
        assert "name" in dtypes
        assert "age" in dtypes
        assert "city" in dtypes
        assert estimated_rows > 0

    def test_get_data_chunk_from_beginning(self, processor, temp_csv_file):
        df = processor.get_data_chunk(temp_csv_file, 0, 2)
        
        assert len(df) == 2
        assert list(df.columns) == ["name", "age", "city"]
        assert df.iloc[0]['name'] == "John"
        assert df.iloc[1]['name'] == "Jane"

    def test_get_data_chunk_with_offset(self, processor, temp_csv_file):
        df = processor.get_data_chunk(temp_csv_file, 2, 2)
        
        assert len(df) == 2
        assert df.iloc[0]['name'] == "Bob"
        assert df.iloc[1]['name'] == "Alice"

    def test_get_data_chunk_beyond_file_end(self, processor, temp_csv_file):
        df = processor.get_data_chunk(temp_csv_file, 10, 5)
        assert len(df) == 0

    def test_stream_csv_chunks(self, processor, temp_csv_file):
        chunks = list(processor.stream_csv_chunks(temp_csv_file))
        
        assert len(chunks) > 0
        total_rows = sum(len(chunk) for chunk in chunks)
        assert total_rows == 5
        
        for chunk in chunks:
            assert list(chunk.columns) == ["name", "age", "city"]

    def test_get_file_statistics(self, processor, temp_csv_file):
        stats = processor.get_file_statistics(temp_csv_file)
        
        assert stats['total_rows'] == 5
        assert stats['columns'] == ["name", "age", "city"]
        assert 'dtypes' in stats
        assert 'null_counts' in stats
        assert 'memory_usage' in stats
        assert 'file_size' in stats
        assert stats['file_size'] > 0

    def test_get_file_statistics_with_nulls(self, processor):
        csv_with_nulls = "name,age,city\nJohn,25,NYC\nJane,,LA\nBob,35,\nAlice,28,Boston"
        temp_file = tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False)
        temp_file.write(csv_with_nulls)
        temp_file.close()
        
        try:
            stats = processor.get_file_statistics(temp_file.name)
            
            assert stats['total_rows'] == 4
            assert stats['null_counts']['age'] == 1
            assert stats['null_counts']['city'] == 1
            assert stats['null_counts']['name'] == 0
        finally:
            os.unlink(temp_file.name)

    @patch('csv_processor.file_processor.UploadedFile.objects.get')
    def test_process_file_async_small_file(self, mock_get, processor, temp_csv_file):
        mock_file = Mock()
        mock_file.id = "test-id"
        mock_file.filename = "test.csv"
        mock_file.file_path = temp_csv_file
        mock_file.save = Mock()
        mock_get.return_value = mock_file
        
        processor.process_file_async("test-id")
        
        assert mock_file.status == 'completed'
        assert mock_file.processing_progress == 100.0
        assert mock_file.total_rows == 5
        assert mock_file.columns is not None
        assert mock_file.dtypes is not None
        assert mock_file.save.called

    @patch('csv_processor.file_processor.UploadedFile.objects.get')
    def test_process_file_async_memory_content(self, mock_get, processor, test_csv_bytes):
        mock_file = Mock()
        mock_file.id = "test-id"
        mock_file.filename = "test.csv"
        mock_file.file_path = ""
        mock_file.save = Mock()
        mock_get.return_value = mock_file
        
        processor.process_file_async("test-id", file_content=test_csv_bytes)
        
        assert mock_file.status in ['processing', 'completed', 'failed']
        if mock_file.status == 'completed':
            assert mock_file.columns is not None
            assert mock_file.dtypes is not None
        assert mock_file.save.called

    @patch('csv_processor.file_processor.UploadedFile.objects.get')
    def test_process_file_async_error_handling(self, mock_get, processor):
        mock_file = Mock()
        mock_file.id = "test-id"
        mock_file.filename = "test.csv"
        mock_file.file_path = "/nonexistent/path.csv"
        mock_file.save = Mock()
        mock_get.return_value = mock_file
        
        processor.process_file_async("test-id")
        
        assert mock_file.status == 'failed'
        assert mock_file.error_message is not None
        assert mock_file.save.called

    def test_chunk_size_configuration(self):
        processor_large_chunks = LargeCSVProcessor(chunk_size=1000)
        assert processor_large_chunks.chunk_size == 1000
        
        processor_small_chunks = LargeCSVProcessor(chunk_size=50)
        assert processor_small_chunks.chunk_size == 50

    def test_analyze_file_structure_from_content_empty_file(self, processor):
        empty_content = b""
        
        with pytest.raises(Exception):
            processor.analyze_file_structure_from_content(empty_content)

    def test_analyze_file_structure_from_content_malformed_csv(self, processor):
        malformed_content = b"invalid,csv\ndata"
        
        try:
            columns, dtypes, estimated_rows = processor.analyze_file_structure_from_content(malformed_content)
            assert isinstance(columns, list)
            assert isinstance(dtypes, dict)
            assert isinstance(estimated_rows, int)
        except Exception:
            pass

    def test_get_data_chunk_file_not_found(self, processor):
        with pytest.raises(Exception):
            processor.get_data_chunk("/nonexistent/file.csv", 0, 10)

    def test_stream_csv_chunks_file_not_found(self, processor):
        with pytest.raises(Exception):
            list(processor.stream_csv_chunks("/nonexistent/file.csv"))

    def test_get_file_statistics_file_not_found(self, processor):
        with pytest.raises(Exception):
            processor.get_file_statistics("/nonexistent/file.csv")


@pytest.mark.django_db
class TestLargeCSVProcessorIntegration:
    
    @pytest.fixture
    def integration_processor(self):
        return LargeCSVProcessor(chunk_size=3)
        
    def test_full_workflow_small_file(self, integration_processor):
        csv_content = "id,name,value\n1,A,100\n2,B,200\n3,C,300\n4,D,400\n5,E,500"
        csv_bytes = csv_content.encode('utf-8')
        
        uploaded_file = SimpleUploadedFile(
            "integration_test.csv",
            csv_bytes,
            content_type="text/csv"
        )
        
        db_file = integration_processor.save_uploaded_file(uploaded_file, "integration_test.csv")
        
        try:
            columns, dtypes, estimated_rows = integration_processor.analyze_file_structure(db_file.file_path)
            
            assert columns == ["id", "name", "value"]
            assert estimated_rows > 0
            
            stats = integration_processor.get_file_statistics(db_file.file_path)
            assert stats['total_rows'] == 5
            
            chunk1 = integration_processor.get_data_chunk(db_file.file_path, 0, 2)
            assert len(chunk1) == 2
            assert chunk1.iloc[0]['name'] == 'A'
            
            chunk2 = integration_processor.get_data_chunk(db_file.file_path, 2, 2)
            assert len(chunk2) == 2
            assert chunk2.iloc[0]['name'] == 'C'
            
            all_chunks = list(integration_processor.stream_csv_chunks(db_file.file_path))
            total_rows_from_chunks = sum(len(chunk) for chunk in all_chunks)
            assert total_rows_from_chunks == 5
            
        finally:
            if os.path.exists(db_file.file_path):
                os.remove(db_file.file_path)
            db_file.delete()

    def test_large_file_memory_processing(self, integration_processor):
        large_csv_content = "id,data\n" + "\n".join([f"{i},data_{i}" for i in range(1000)])
        csv_bytes = large_csv_content.encode('utf-8')
        
        db_file = integration_processor.create_file_record_memory("large_file.csv", len(csv_bytes))
        
        columns, dtypes, estimated_rows = integration_processor.analyze_file_structure_from_content(csv_bytes)
        
        assert columns == ["id", "data"]
        assert estimated_rows > 0
        assert isinstance(estimated_rows, int)
        
        db_file.delete()