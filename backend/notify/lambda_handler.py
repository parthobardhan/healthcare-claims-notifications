from mangum import Mangum
from .app import app

handler = Mangum(app, lifespan="off", api_gateway_base_path="/notify")


def lambda_handler(event, context):
    if "pathParameters" in event and event["pathParameters"]:
        path = event.get("path", "")
        if path.startswith("/dev/notify"):
            event["path"] = path.replace("/dev/notify", "")
        elif path.startswith("/prod/notify"):
            event["path"] = path.replace("/prod/notify", "")

    return handler(event, context)
