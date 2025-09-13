from mangum import Mangum
from .app import app

handler = Mangum(app, lifespan="off")

def lambda_handler(event, context):
    if 'path' in event and event['path'].startswith('/notify'):
        event['path'] = event['path'][7:]  # Remove '/notify' prefix
        if not event['path']:
            event['path'] = '/'
    
    if 'pathParameters' in event and event['pathParameters'] and 'proxy' in event['pathParameters']:
        proxy_path = event['pathParameters']['proxy']
        event['path'] = '/' + proxy_path if proxy_path else '/'
    
    return handler(event, context)
