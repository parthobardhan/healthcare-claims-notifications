from mangum import Mangum
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from claims.app import app

def strip_stage_path(scope, receive, send):
    """Strip API Gateway stage path prefix from requests"""
    path = scope.get("path", "")
    
    if path.startswith("/dev/claims"):
        scope["path"] = path[len("/dev/claims"):] or "/"
    elif path.startswith("/claims"):
        scope["path"] = path[len("/claims"):] or "/"
    
    return app(scope, receive, send)

handler = Mangum(strip_stage_path)
