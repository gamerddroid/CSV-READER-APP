import pandas as pd
import io
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
import logging


logging.basicConfig(
    filename='logs/csv_debug.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

@api_view(['POST'])
@parser_classes([MultiPartParser])
def upload_csv(request):
    try:
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        csv_file = request.FILES['file']
        
        if not csv_file.name.endswith('.csv'):
            return Response(
                {'error': 'File must be a CSV'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Read CSV file into pandas DataFrame
        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        df = pd.read_csv(io_string)
        
        logging.info("DataFrame shape: %s", df.shape)
        logging.info("DataFrame columns: %s", df.columns.tolist())
        logging.info("DataFrame head:\n%s", df.head().to_string())
        # Get DataFrame information
        dataframe_info = {
            'shape': df.shape,
            'columns': df.columns.tolist(),
            'dtypes': df.dtypes.astype(str).to_dict(),
            'head': df.head().to_dict('records'),
            'info': {
                'memory_usage': df.memory_usage(deep=True).sum(),
                'null_counts': df.isnull().sum().to_dict(),
            }
        }
        
        return Response({
            'message': 'CSV file processed successfully',
            'filename': csv_file.name,
            'dataframe_info': dataframe_info
        }, status=status.HTTP_200_OK)
        
    except pd.errors.EmptyDataError:
        return Response(
            {'error': 'CSV file is empty'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except pd.errors.ParserError as e:
        return Response(
            {'error': f'Error parsing CSV: {str(e)}'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def health_check(request):
    return JsonResponse({'status': 'healthy'})