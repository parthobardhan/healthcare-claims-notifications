from mangum import Mangum
from .app import app

handler = Mangum(app, lifespan="off", api_gateway_base_path="/claims")


def lambda_handler(event, context):
    if "pathParameters" in event and event["pathParameters"]:
        path = event.get("path", "")
        if path.startswith("/dev/claims"):
            event["path"] = path.replace("/dev/claims", "")
        elif path.startswith("/prod/claims"):
            event["path"] = path.replace("/prod/claims", "")

    return handler(event, context)
