"""
Trip Optimization Tools

This module contains all the trip planning and optimization tools:
- AccommodationPlanner: Search and recommend accommodations
- ItineraryPlanner: Create detailed day-by-day itineraries  
- RestaurantsSearch: Find restaurants based on itinerary locations
- TravelOptimization: Optimize transportation routes and modes

All tools use LLM-based extraction and Perplexity AI for search capabilities.
They support currency detection (₹ for Indian regions, $ for international)
and provide comprehensive markdown outputs with Google Maps integration.
"""

# Import all optimization tools
from .AccomidationPlanner import search_accommodations
from .IternaryPlanning import plan_itinerary
from .RestaurantsSearch import search_restaurants
from .TravelOptimization import optimize_travel

# Export all tools for easy importing
__all__ = [
    "search_accommodations",
    "plan_itinerary", 
    "search_restaurants",
    "optimize_travel"
]

# Tool descriptions for documentation
TOOL_DESCRIPTIONS = {
    "search_accommodations": {
        "description": "Search for accommodation options based on natural language query",
        "input": "Natural language query with location, dates, budget, preferences",
        "output": "Markdown formatted accommodation recommendations with pricing",
        "example": "Find hotels in Paris for 2 people from 26-11-2025 to 30-11-2025 with budget $500"
    },
    
    "plan_itinerary": {
        "description": "Create comprehensive day-by-day itinerary plans",
        "input": "Natural language query with destination, dates, travel type, preferences",
        "output": "Daily tables with Time|Activity|Details|Maps columns",
        "example": "Plan a 3-day itinerary for Tokyo for couple with budget $1500, prefer temples and shopping"
    },
    
    "search_restaurants": {
        "description": "Find restaurants based on itinerary locations and dietary preferences",
        "input": "Itinerary details (from plan_itinerary), dates, dietary preferences",
        "output": "Restaurant tables with Time|Location|Restaurant|Cuisine|Price|Dietary|Maps",
        "example": "Search restaurants for Tokyo itinerary with veg and non-veg preferences"
    },
    
    "optimize_travel": {
        "description": "Optimize transportation routes, modes, and costs",
        "input": "Natural language query with from/to locations, dates, budget, transport preferences",
        "output": "Transportation options table with cost analysis and booking recommendations",
        "example": "Optimize travel from Mumbai to Goa for 4 people, prefer trains, budget ₹8000"
    }
}

def get_tool_info(tool_name: str = None) -> dict:
    """
    Get information about available tools.
    
    Args:
        tool_name: Specific tool name, or None for all tools
        
    Returns:
        Tool information dictionary
    """
    if tool_name:
        return TOOL_DESCRIPTIONS.get(tool_name, {})
    return TOOL_DESCRIPTIONS

def list_available_tools() -> list:
    """
    Get list of all available optimization tools.
    
    Returns:
        List of tool names
    """
    return list(__all__)

# Convenience function for complete trip planning workflow
def plan_complete_trip(
    itinerary_query: str,
    dietary_preferences: str = "",
    travel_optimization_query: str = ""
) -> dict:
    """
    Complete trip planning workflow using all tools.
    
    Args:
        itinerary_query: Query for itinerary planning
        dietary_preferences: Dietary preferences for restaurant search
        travel_optimization_query: Query for travel optimization
        
    Returns:
        Dictionary with results from all tools
        
    Example:
        >>> results = plan_complete_trip(
        ...     itinerary_query="Plan 3-day Tokyo trip for couple, budget $1500",
        ...     dietary_preferences="veg and non-veg",
        ...     travel_optimization_query="Optimize travel from Delhi to Tokyo for 2 people"
        ... )
        >>> print(results['itinerary'])
        >>> print(results['restaurants']) 
        >>> print(results['travel'])
    """
    results = {}
    
    try:
        # Step 1: Plan itinerary
        print("🗺️ Planning itinerary...")
        itinerary_result = plan_itinerary.invoke({"query": itinerary_query})
        results['itinerary'] = itinerary_result
        
        # Step 2: Find restaurants based on itinerary
        if dietary_preferences:
            print("🍽️ Finding restaurants...")
            # Extract dates from itinerary query (simple extraction)
            import re
            date_match = re.search(r'(\d{1,2}-\d{1,2}-\d{4})\s+to\s+(\d{1,2}-\d{1,2}-\d{4})', itinerary_query)
            dates = f"{date_match.group(1)} to {date_match.group(2)}" if date_match else "Dates not specified"
            
            restaurant_result = search_restaurants.invoke({
                "itinerary_details": itinerary_result,
                "dates": dates,
                "dietary_preferences": dietary_preferences
            })
            results['restaurants'] = restaurant_result
        
        # Step 3: Optimize travel
        if travel_optimization_query:
            print("🚌 Optimizing travel...")
            travel_result = optimize_travel.invoke({"query": travel_optimization_query})
            results['travel'] = travel_result
            
        print("✅ Complete trip planning finished!")
        return results
        
    except Exception as e:
        print(f"❌ Error in complete trip planning: {str(e)}")
        return {"error": str(e), **results}
