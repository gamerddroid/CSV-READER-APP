import os
import django
from unittest import mock
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csv_reader_project.settings')
django.setup()

from csv_processor.file_processor import LargeCSVProcessor
# …


def generate_large_csv(num_rows=10000):
    lines = ['name','job']
    for i in range(num_rows):
        lines.append(f"{i},{i*2}")
    return "\n".join(lines).encode("utf-8")


def test_large_csv_processor_instantiation():
    process = LargeCSVProcessor()
    assert isinstance(process, LargeCSVProcessor)

class DummyUploadedFile:
    def __init__(self, content):
        self._content = content
    def chunks(self):
        yield self._content

def test_save_uploaded_file_creates_db_record(tmp_path):
    processor = LargeCSVProcessor()
    dummy_content = generate_large_csv(1000)
    dummy_file = DummyUploadedFile(dummy_content)
    filename = "test.csv"

    with mock.patch("csv_processor.file_processor.UploadedFile.objects.create") as mock_create:
        mock_create.return_value = mock.Mock(id=1, filename=filename)
        result = processor.save_uploaded_file(dummy_file, filename)
        print("The result of the dummy data is ", next(dummy_file.chunks()))
        assert mock_create.called
        assert result.filename == filename

