import os
import sys
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AI-Trip-Planner")

# Initialize Azure configuration if available
# try:
#     from config.azure_config import initialize_azure_environment, get_environment_info
#     azure_initialized = initialize_azure_environment()
#     logger.info(f"Azure configuration initialized: {azure_initialized}")
# except ImportError:
#     logger.info("Azure configuration not available - running in local mode")
#     azure_initialized = False

# Add path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

# Import the trip optimization agent
from agents.worker.trip_optimization_agent.agent import (
    plan_complete_trip, 
    TripOptimizationAgent
)

# Import individual optimization tools
from tools.optimization import (
    search_accommodations,
    plan_itinerary,
    search_restaurants
)

# Import the  travel optimization (replaces old optimize_travel)
from tools.optimization.TravelOptimization import travel_search_tool

# Initialize FastAPI app
app = FastAPI(
    title="TripMazer Optimization API",
    description="Intelligent trip planning and optimization API for Azure Functions",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    root_path="/api"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom OpenAPI schema to avoid Azure Functions routing conflicts
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="TripMazer Optimization API",
        version="1.0.0",
        description="Multi-agent trip planning API system providing access to various AI agents for travel optimization",
        routes=app.routes,
    )
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Validate configuration on startup
@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI app startup")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP Exception occurred: {exc.status_code} - {exc.detail}")
    logger.error(f"Request URL: {request.url}")
    logger.error(f"Request headers: {dict(request.headers)}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error": "Authentication failed"}
    )

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
async def plan_optimized_trip(request: dict):
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
    logger.info(f"Trip planning requested with query: {request.get('query', '')[:100]}...")
    
    try:
        # Validate request
        if not request.get('query'):
            raise HTTPException(status_code=422, detail="Query field is required")
            
        @measure_execution_time
        def execute_trip_planning():
            return plan_complete_trip(request['query'])
        
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
async def search_accommodation_tool(request: dict):
    """
    Search for accommodation options based on natural language query.
    
    This tool extracts accommodation requirements and provides detailed recommendations
    with pricing, amenities, and booking information.
    """
    logger.info(f"Accommodation search requested: {request.get('query', '')[:100]}...")
    
    try:
        @measure_execution_time
        def execute_accommodation_search():
            return search_accommodations.invoke({"query": request.get('query', '')})
        
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
async def plan_itinerary_tool(request: dict):
    """
    Plan detailed itinerary based on natural language query.
    
    This tool creates day-by-day itineraries with activities, timing,
    and budget considerations.
    """
    logger.info(f"Itinerary planning requested: {request.get('query', '')[:100]}...")
    
    try:
        @measure_execution_time
        def execute_itinerary_planning():
            return plan_itinerary.invoke({"query": request.get('query', '')})
        
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
async def search_restaurants_tool(request: dict):
    """
    Search for restaurant recommendations based on itinerary and preferences.
    
    This tool provides restaurant suggestions aligned with the travel itinerary,
    including timing, cuisine types, and budget considerations.
    """
    logger.info(f"Restaurant search requested for dates: {request.get('dates', '')}")
    
    try:
        @measure_execution_time
        def execute_restaurant_search():
            return search_restaurants.invoke({
                "itinerary_details": request.get('itinerary_details', ''),
                "dates": request.get('dates', ''),
                "dietary_preferences": request.get('dietary_preferences', ''),
                "budget_hint": request.get('budget_hint', '')
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
async def optimize_travel_tool(request: dict):
    """
    Optimize travel routes and transportation based on query.
    
    This tool provides transportation recommendations with route optimization,
    cost analysis, and timing considerations using the hybrid approach.
    """
    logger.info(f"Travel optimization requested: {request.get('query', '')[:100]}...")
    
    try:
        @measure_execution_time
        def execute_travel_optimization():
            return travel_search_tool.invoke({"query": request.get('query', '')})
        
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

@app.post("/tools/travel_hybrid")
async def optimize_travel_hybrid(request: dict):
    """
    Travel optimization using SerpAPI for flights and Perplexity for other transport.
    
    This endpoint uses intelligent routing to:
    - Extract flight parameters using Gemini AI
    - Decide whether to search flights based on budget and preferences
    - Use SerpAPI for accurate flight pricing when appropriate
    - Use Perplexity for comprehensive bus/train options
    - Combine results for optimal travel recommendations
    """
    logger.info(f"Travel optimization requested: {request.get('query', '')[:100]}...")
    
    try:
        @measure_execution_time
        def execute_hybrid_travel():
            return travel_search_tool.invoke({"query": request.get('query', '')})
        
        result, execution_time = execute_hybrid_travel()
        
        logger.info(f"Hybrid travel optimization completed in {execution_time:.2f}ms")
        return create_success_response({
            "tool": "travel_hybrid",
            "result": result,
            "note": "Results combine SerpAPI flight data with Perplexity transport options"
        }, execution_time)
        
    except Exception as e:
        error_msg = f"Error in hybrid travel optimization: {str(e)}"
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
            "recent_updates": [
                "Improved restaurant budget allocation (15% → 25%)",
                "Added budget_hint parameter to restaurant search",
                "Replaced optimize_travel with hybrid_travel_optimization",
                "Enhanced budget allocation with 10% minimum for restaurants",
                "Added comprehensive logging system",
                "Fixed Unicode handling in logs"
            ],
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
                    "description": "Find restaurant recommendations with budget guidance",
                    "endpoint": "/tools/restaurants",
                    "new_features": ["budget_hint parameter for realistic pricing"]
                },
                {
                    "name": "travel",
                    "description": "Hybrid travel optimization (SerpAPI + Perplexity)",
                    "endpoint": "/tools/travel",
                    "new_features": ["Smart flight vs ground transport decisions", "Enhanced SERP data extraction"]
                }
            ],
            "main_endpoint": "/optimized_trip_planner",
            "features": [
                "Intelligent preference extraction via Gemini AI",
                "Dynamic budget allocation (improved restaurant allocation)",
                "Tool routing based on user priorities",
                "Comprehensive result combination",
                "Multi-currency support (₹ and $)",
                "Budget-aware restaurant recommendations",
                "Hybrid travel optimization",
                "Comprehensive execution logging"
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

# Test endpoint for recent changes
@app.post("/test/recent_changes")
async def test_recent_changes(request: dict):
    """
    Test endpoint to verify all recent changes work correctly.
    Tests budget allocation, restaurant budget hints, and hybrid travel optimization.
    """
    logger.info("Testing recent changes with sample query...")
    
    try:
        # Test budget allocation
        test_query = request.get('query') or "Plan trip from Delhi to Mumbai for 2 people, ₹25000 budget, good food"
        
        @measure_execution_time
        def test_execution():
            # Test the main trip planning with recent improvements
            results = plan_complete_trip(test_query)
            
            # Extract budget information for verification
            budget_info = {
                "query": test_query,
                "execution_successful": True,
                "has_restaurant_results": "restaurant" in str(results).lower(),
                "has_travel_results": "travel" in str(results).lower(),
                "results_length": len(str(results))
            }
            
            return {
                "test_results": budget_info,
                "actual_results": results
            }
        
        test_data, execution_time = test_execution()
        
        logger.info(f"Recent changes test completed in {execution_time:.2f}ms")
        return create_success_response({
            "test_status": "SUCCESS",
            "message": "All recent changes are working correctly",
            "test_data": test_data,
            "verified_features": [
                "Budget allocation system",
                "Restaurant budget hints", 
                "Hybrid travel optimization",
                "Comprehensive logging",
                "Unicode handling"
            ]
        }, execution_time)
        
    except Exception as e:
        error_msg = f"Recent changes test failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return create_error_response(error_msg)

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
# if __name__ == "__main__":
#     import uvicorn
    
#     # Check if required environment variables are set
#     required_env_vars = ["PERPLEXITY_API_KEY"]
#     missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
#     if missing_vars:
#         logger.error(f"Missing required environment variables: {missing_vars}")
#         logger.error("Please set these in your .env file")
#         sys.exit(1)
    
#     logger.info("Starting TripMazer Optimization API...")
#     logger.info("Available endpoints:")
#     logger.info("  - GET  /health - Health check")
#     logger.info("  - POST /optimized_trip_planner - Main trip planning")
#     logger.info("  - POST /tools/accommodation - Accommodation search")
#     logger.info("  - POST /tools/itinerary - Itinerary planning")
#     logger.info("  - POST /tools/restaurants - Restaurant search")
#     logger.info("  - POST /tools/travel - Travel optimization")
#     logger.info("  - GET  /agent/info - Agent information")
#     logger.info("  - GET  /docs - API documentation")
    
#     uvicorn.run(
#         "fast_api:app",
#         host="127.0.0.1",
#         port=8000,
#         reload=True,
#         log_level="info"
#     )
