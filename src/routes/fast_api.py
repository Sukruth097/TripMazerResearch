import os
import sys
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import the trip optimization agent
from agents.worker.trip_optimization_agent.agent import (
    plan_complete_trip, 
    TripOptimizationAgent
)

# Import individual optimization tools
from tools.optimization import (
    search_accommodations,
    plan_itinerary,
    search_restaurants,
    optimize_travel
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="TripMazer Optimization API",
    description="Intelligent trip planning and optimization API for Azure Functions",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class TripPlanRequest(BaseModel):
    query: str = Field(..., description="Natural language trip planning query", min_length=5)

class ToolRequest(BaseModel):
    query: str = Field(..., description="Natural language query for the specific tool", min_length=5)

class RestaurantRequest(BaseModel):
    itinerary_details: str = Field(..., description="Itinerary details for restaurant planning")
    dates: str = Field(..., description="Travel dates")
    dietary_preferences: str = Field(default="", description="Dietary preferences (optional)")

class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime
    execution_time_ms: Optional[float] = None

# Global agent instance
trip_agent = TripOptimizationAgent()

# Utility functions
def create_success_response(data: Any, execution_time: float = None) -> Dict[str, Any]:
    """Create a standardized success response."""
    return {
        "success": True,
        "data": data,
        "error": None,
        "timestamp": datetime.utcnow().isoformat(),
        "execution_time_ms": execution_time
    }

def create_error_response(error_message: str, execution_time: float = None) -> Dict[str, Any]:
    """Create a standardized error response."""
    return {
        "success": False,
        "data": None,
        "error": error_message,
        "timestamp": datetime.utcnow().isoformat(),
        "execution_time_ms": execution_time
    }

def measure_execution_time(func):
    """Decorator to measure execution time."""
    def wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        return result, execution_time
    return wrapper

# Health check endpoint
@app.get("/health")
@app.get("/")
async def health_check():
    """Health check endpoint for Azure Functions."""
    logger.info("Health check requested")
    return create_success_response({
        "status": "healthy",
        "service": "TripMazer Optimization API",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    })

# Main trip planning endpoint
@app.post("/optimized_trip_planner")
async def plan_optimized_trip(request: TripPlanRequest):
    """
    Plan a complete optimized trip based on natural language query.
    
    This endpoint uses the intelligent trip optimization agent that:
    - Extracts preferences and routing from the query
    - Allocates budget intelligently across different categories
    - Routes through multiple optimization tools based on user priorities
    - Combines results into a comprehensive trip plan
    
    Args:
        request: TripPlanRequest containing the natural language query
        
    Returns:
        Complete trip planning results with budget allocation and recommendations
    """
    logger.info(f"Trip planning requested with query: {request.query[:100]}...")
    
    try:
        @measure_execution_time
        def execute_trip_planning():
            return plan_complete_trip(request.query)
        
        results, execution_time = execute_trip_planning()
        
        logger.info(f"Trip planning completed successfully in {execution_time:.2f}ms")
        return create_success_response(results, execution_time)
        
    except Exception as e:
        error_msg = f"Error in trip planning: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=create_error_response(error_msg)
        )

# Individual tool endpoints
@app.post("/tools/accommodation")
async def search_accommodation_tool(request: ToolRequest):
    """
    Search for accommodation options based on natural language query.
    
    This tool extracts accommodation requirements and provides detailed recommendations
    with pricing, amenities, and booking information.
    """
    logger.info(f"Accommodation search requested: {request.query[:100]}...")
    
    try:
        @measure_execution_time
        def execute_accommodation_search():
            return search_accommodations.invoke({"query": request.query})
        
        result, execution_time = execute_accommodation_search()
        
        logger.info(f"Accommodation search completed in {execution_time:.2f}ms")
        return create_success_response({
            "tool": "accommodation",
            "result": result
        }, execution_time)
        
    except Exception as e:
        error_msg = f"Error in accommodation search: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=create_error_response(error_msg)
        )

@app.post("/tools/itinerary")
async def plan_itinerary_tool(request: ToolRequest):
    """
    Plan detailed itinerary based on natural language query.
    
    This tool creates day-by-day itineraries with activities, timing,
    and budget considerations.
    """
    logger.info(f"Itinerary planning requested: {request.query[:100]}...")
    
    try:
        @measure_execution_time
        def execute_itinerary_planning():
            return plan_itinerary.invoke({"query": request.query})
        
        result, execution_time = execute_itinerary_planning()
        
        logger.info(f"Itinerary planning completed in {execution_time:.2f}ms")
        return create_success_response({
            "tool": "itinerary",
            "result": result
        }, execution_time)
        
    except Exception as e:
        error_msg = f"Error in itinerary planning: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=create_error_response(error_msg)
        )

@app.post("/tools/restaurants")
async def search_restaurants_tool(request: RestaurantRequest):
    """
    Search for restaurant recommendations based on itinerary and preferences.
    
    This tool provides restaurant suggestions aligned with the travel itinerary,
    including timing, cuisine types, and budget considerations.
    """
    logger.info(f"Restaurant search requested for dates: {request.dates}")
    
    try:
        @measure_execution_time
        def execute_restaurant_search():
            return search_restaurants.invoke({
                "itinerary_details": request.itinerary_details,
                "dates": request.dates,
                "dietary_preferences": request.dietary_preferences
            })
        
        result, execution_time = execute_restaurant_search()
        
        logger.info(f"Restaurant search completed in {execution_time:.2f}ms")
        return create_success_response({
            "tool": "restaurants",
            "result": result
        }, execution_time)
        
    except Exception as e:
        error_msg = f"Error in restaurant search: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=create_error_response(error_msg)
        )

@app.post("/tools/travel")
async def optimize_travel_tool(request: ToolRequest):
    """
    Optimize travel routes and transportation based on query.
    
    This tool provides transportation recommendations with route optimization,
    cost analysis, and timing considerations.
    """
    logger.info(f"Travel optimization requested: {request.query[:100]}...")
    
    try:
        @measure_execution_time
        def execute_travel_optimization():
            return optimize_travel.invoke({"query": request.query})
        
        result, execution_time = execute_travel_optimization()
        
        logger.info(f"Travel optimization completed in {execution_time:.2f}ms")
        return create_success_response({
            "tool": "travel",
            "result": result
        }, execution_time)
        
    except Exception as e:
        error_msg = f"Error in travel optimization: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=create_error_response(error_msg)
        )

# Agent information endpoint
@app.get("/agent/info")
async def get_agent_info():
    """
    Get information about the trip optimization agent and available tools.
    """
    logger.info("Agent info requested")
    
    try:
        agent_info = {
            "agent_name": "TripOptimizationAgent",
            "version": "1.0.0",
            "available_tools": [
                {
                    "name": "accommodation",
                    "description": "Search for accommodation options with detailed recommendations",
                    "endpoint": "/tools/accommodation"
                },
                {
                    "name": "itinerary",
                    "description": "Plan detailed day-by-day itineraries",
                    "endpoint": "/tools/itinerary"
                },
                {
                    "name": "restaurants",
                    "description": "Find restaurant recommendations aligned with itinerary",
                    "endpoint": "/tools/restaurants"
                },
                {
                    "name": "travel",
                    "description": "Optimize travel routes and transportation",
                    "endpoint": "/tools/travel"
                }
            ],
            "main_endpoint": "/optimized_trip_planner",
            "features": [
                "Intelligent preference extraction",
                "Dynamic budget allocation",
                "Tool routing based on user priorities",
                "Comprehensive result combination",
                "Multi-currency support (₹ and $)"
            ]
        }
        
        return create_success_response(agent_info)
        
    except Exception as e:
        error_msg = f"Error getting agent info: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=create_error_response(error_msg)
        )

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    error_msg = f"Unhandled error: {str(exc)}"
    logger.error(error_msg, exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content=create_error_response(error_msg)
    )

# Azure Functions compatibility
def main(req):
    """Azure Functions entry point."""
    import azure.functions as func
    from fastapi import Request
    from fastapi.responses import JSONResponse
    
    # Convert Azure Functions request to FastAPI request
    # This is a simplified conversion - you may need to adjust based on your Azure setup
    
    try:
        # Extract route and method
        route = req.route_params.get('route', '')
        method = req.method.lower()
        
        # Handle routing
        if route == 'health' or route == '':
            return func.HttpResponse(
                json.dumps(create_success_response({
                    "status": "healthy",
                    "service": "TripMazer Optimization API"
                })),
                mimetype="application/json",
                status_code=200
            )
        
        # For other routes, return a generic response
        # In production, you'd want to properly route to FastAPI
        return func.HttpResponse(
            json.dumps(create_success_response({
                "message": "TripMazer API is running",
                "route": route,
                "method": method
            })),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"Azure Functions error: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps(create_error_response(str(e))),
            mimetype="application/json",
            status_code=500
        )

# For local development
if __name__ == "__main__":
    import uvicorn
    
    # Check if required environment variables are set
    required_env_vars = ["PERPLEXITY_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please set these in your .env file")
        sys.exit(1)
    
    logger.info("Starting TripMazer Optimization API...")
    logger.info("Available endpoints:")
    logger.info("  - GET  /health - Health check")
    logger.info("  - POST /optimized_trip_planner - Main trip planning")
    logger.info("  - POST /tools/accommodation - Accommodation search")
    logger.info("  - POST /tools/itinerary - Itinerary planning")
    logger.info("  - POST /tools/restaurants - Restaurant search")
    logger.info("  - POST /tools/travel - Travel optimization")
    logger.info("  - GET  /agent/info - Agent information")
    logger.info("  - GET  /docs - API documentation")
    
    uvicorn.run(
        "fast_api:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
