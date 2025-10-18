"""
Azure Functions entry point for TripMazer API
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import azure.functions as func
from azure.functions import FunctionApp, AuthLevel

# Import the FastAPI app
from routes.fast_api import app as fastapi_app

# Create Azure Functions app
app = FunctionApp(http_auth_level=AuthLevel.ANONYMOUS)

@app.route(route="{*route}", auth_level=AuthLevel.ANONYMOUS)
async def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
    return await func.AsgiMiddleware(fastapi_app).handle_async(req)
