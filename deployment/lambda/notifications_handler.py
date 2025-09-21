from mangum import Mangum
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from notify.app import app

def strip_stage_path(scope, receive, send):
    """Strip API Gateway stage path prefix from requests"""
    path = scope.get("path", "")
    
    if path.startswith("/dev/notifications"):
        scope["path"] = path[len("/dev/notifications"):] or "/"
    elif path.startswith("/notifications"):
        scope["path"] = path[len("/notifications"):] or "/"
    
    return app(scope, receive, send)

handler = Mangum(strip_stage_path)
