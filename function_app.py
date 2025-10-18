import azure.functions as func
from fastapi import FastAPI
from azure.functions import AsgiFunctionApp, AuthLevel
import sys
import os

# Add src to path for imports
# current_dir = os.path.dirname(os.path.abspath(__file__))
# src_path = os.path.join(current_dir, 'src')
# sys.path.insert(0, src_path)

# Import the FastAPI app
from src.routes.fast_api import app 

# This exposes your FastAPI app to Azure Functions
app = AsgiFunctionApp(app=app, http_auth_level=AuthLevel.ANONYMOUS)

@app.route(route="AiTripPlanner", auth_level=func.AuthLevel.ANONYMOUS)
def AiTripPlanner(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )