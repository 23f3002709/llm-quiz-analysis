"""
Azure Function App entry point
Wraps the FastAPI application for Azure Functions
"""
import logging
import azure.functions as func
from main import app

# Create the Azure Function App with ASGI support
app_func = func.AsgiFunctionApp(app=app, http_auth_level=func.AuthLevel.ANONYMOUS)

logging.info("Azure Function App initialized successfully")
