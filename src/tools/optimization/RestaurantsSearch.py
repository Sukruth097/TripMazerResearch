import os
import sys
import json
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
# Add the src directory to Python path when running directly
if __name__ == "__main__":
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Add parent directories to path for proper importing
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '..', '..')
sys.path.insert(0, src_dir)

from langchain.tools import tool

# Handle relative imports for both direct execution and when imported from main.py
try:
    from src.services.perplexity_service import PerplexityService
except ImportError:
    try:
        from services.perplexity_service import PerplexityService
    except ImportError:
        # If still failing, try absolute path
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
        from services.perplexity_service import PerplexityService


def _get_perplexity_service() -> PerplexityService:
    """Get initialized Perplexity service instance."""
    # Get API key from environment variable
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY environment variable is required")
    return PerplexityService(api_key)
@tool
def search_restaurants(location: str, dates: str = "", dietary_preferences: str = "veg and non-veg", 
                      budget_hint: str = "", travelers: int = 2, itinerary_details: str = "") -> str:
    """
    Search for restaurants in a specific location with dietary preferences and budget.
    
    This tool works in TWO modes:
    1. **Independent Mode**: Search restaurants for a location directly
    2. **Itinerary Mode**: Get restaurants based on day-by-day itinerary (if provided)
    
    Args:
        location: City/region to search restaurants (e.g., "Mumbai", "Delhi", "Goa")
        dates: Travel dates in DD-MM-YYYY to DD-MM-YYYY format (optional)
        dietary_preferences: "veg only", "veg and non-veg", "non-veg only" (default: "veg and non-veg")
        budget_hint: Budget like "INR 5000 for 2 people for 3 days" (optional)
        travelers: Number of people (default: 2)
        itinerary_details: Optional itinerary for location-specific recommendations
    
    Returns:
        str: Restaurant recommendations in markdown table format with realistic pricing
    
    Example Independent Usage:
        # Find best seafood restaurants in Mumbai
        result = search_restaurants(
            location="Mumbai",
            dietary_preferences="non-veg only",
            budget_hint="INR 3000 per person",
            travelers=2
        )
        
    Example Itinerary-Based Usage:
        itinerary = "Day 1: Gateway of India (10 AM), Marine Drive (4 PM)"
        result = search_restaurants(
            location="Mumbai", 
            dates="25-12-2025 to 27-12-2025",
            dietary_preferences="veg and non-veg",
            itinerary_details=itinerary
        )
    """
    try:
        # Get Perplexity service from centralized utility
        from src.utils.service_initializer import get_perplexity_service
        perplexity_service = get_perplexity_service()
        
        # Determine mode: Independent or Itinerary-based
        search_mode = "itinerary-based" if itinerary_details else "independent"
        
        # Create comprehensive system prompt for restaurant recommendations
        system_prompt = f"""You are an expert restaurant consultant and food advisor with deep knowledge of local cuisines and dining options.

**SEARCH MODE:** {search_mode.upper()}
**LOCATION:** {location}
**DIETARY PREFERENCES:** {dietary_preferences if dietary_preferences else "No specific preferences"}
**BUDGET:** {budget_hint if budget_hint else "No specific budget - suggest varied price ranges"}
**TRAVELERS:** {travelers} person{'s' if travelers > 1 else ''}

{'**ITINERARY CONTEXT:** ' + itinerary_details if itinerary_details else '**INDEPENDENT SEARCH:** Find best restaurants in ' + location}

**TASK: Recommend restaurants based on mode**

**MODE 1 - INDEPENDENT SEARCH (No itinerary provided):**
- Recommend TOP restaurants in {location} for {dietary_preferences} preferences
- Categorize by meal types (Breakfast, Lunch, Dinner) and cuisine types
- Include must-visit local specialties and popular spots
- Provide diverse price ranges from budget to fine dining

**MODE 2 - ITINERARY-BASED (Itinerary provided):**
- Parse itinerary to extract locations and times
- Match restaurants near each activity location
- Align with meal times from itinerary schedule

**INPUT ANALYSIS:**
- Itinerary Details: {itinerary_details}
- Travel Dates: {dates}
- Dietary Preferences: {dietary_preferences if dietary_preferences else "No specific preferences mentioned"}
- Budget Guidance: {budget_hint if budget_hint else "No specific budget mentioned - suggest varied price ranges"}

**BUDGET CONSIDERATIONS:**
- If budget is provided, calculate realistic per-person per-meal costs
- For Indian destinations: Budget restaurants INR 150-300, Mid-range INR 300-800, Fine dining INR 800-2000 per person
- For international destinations: Budget $10-25, Mid-range $25-60, Fine dining $60-150 per person
- If budget seems insufficient, suggest budget-friendly options but mention realistic alternatives

**CURRENCY DETECTION RULES:**
- If locations in the itinerary are Indian regions/cities (Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad, Pune, Ahmedabad, Jaipur, Surat, Lucknow, Kanpur, Nagpur, Indore, Thane, Bhopal, Visakhapatnam, Patna, Vadodara, Ghaziabad, Ludhiana, Agra, Nashik, Faridabad, Meerut, Rajkot, Kalyan, Vasai-Virar, Varanasi, Srinagar, Aurangabad, Dhanbad, Amritsar, Navi Mumbai, Allahabad, Ranchi, Howrah, Coimbatore, Jabalpur, Gwalior, Vijayawanda, Jodhpur, Madurai, Raipur, Kota, Guwahati, Chandigarh, Solapur, Hubli-Dharwad, Bareilly, Moradabad, Mysore, Gurgaon, Aligarh, Jalandhar, Tiruchirappalli, Bhubaneswar, Salem, Warangal, Mira-Bhayandar, Thiruvananthapuram, Bhiwandi, Saharanpur, Guntur, Amravati, Bikaner, Noida, Jamshedpur, Bhilai Nagar, Cuttack, Firozabad, Kochi, Bhavnagar, Dehradun, Durgapur, Asansol, Nanded-Waghala, Kolhapur, Ajmer, Akola, Gulbarga, Jamnagar, Ujjain, Loni, Siliguri, Jhansi, Ulhasnagar, Nellore, Jammu, Sangli-Miraj & Kupwad, Belgaum, Mangalore, Ambattur, Tirunelveli, Malegaon, Gaya, Jalgaon, Udaipur, Maheshtala, or any other Indian city/state): Use INR (Indian Rupees)
- For ALL OTHER international destinations: Use $ (US Dollars)

**DIETARY PREFERENCE HANDLING:**
- "veg only" or "vegetarian": Recommend only pure vegetarian restaurants
- "veg and non-veg": Include both vegetarian and non-vegetarian options
- "non-veg only": Focus on non-vegetarian cuisine
- No preferences: Include diverse options with clear dietary indicators

**INSTRUCTIONS:**
1. Parse the itinerary to extract locations, times, and activities
2. For each day and location, suggest appropriate restaurants
3. Consider meal times: breakfast (7-10 AM), lunch (12-3 PM), dinner (6-9 PM), snacks/cafes (other times)
4. Match restaurant proximity to itinerary locations
5. Respect dietary preferences strictly
6. Include local cuisine specialties
7. Provide realistic price ranges in correct currency (consider INR 800-1500 per person per day for decent meals in India)
8. Add Google Maps links as clickable restaurant names
9. **BUDGET UTILIZATION**: Recommend restaurants that make good use of the available budget while respecting dietary preferences and user tastes. If budget seems low, suggest budget-friendly options but mention realistic alternatives.

**RESPONSE FORMAT (MANDATORY):**

# Restaurant Recommendations

## Extracted Information
- **Travel Dates:** [extracted dates]
- **Dietary Preferences:** [extracted preferences or "No specific preferences"]
- **Locations:** [list of locations from itinerary]
- **Currency:** INR (Indian Rupees)

---

## Day 1 - [Date] | [Location]

| Time | Location | Restaurant | Cuisine | Price Range | Dietary Options | Maps |
|------|----------|------------|---------|-------------|-----------------|------|
| [Time] | [Specific area/landmark] | [Restaurant Name] | [Cuisine type] | [Currency][Price range] | [Veg/Non-veg/Both] | [[Restaurant Name](https://maps.google.com/search/[Restaurant+Name+Location])] |
| [Time] | [Area] | [Restaurant] | [Cuisine] | [Price] | [Dietary] | [[Restaurant](link)] |

## Day 2 - [Date] | [Location]

| Time | Location | Restaurant | Cuisine | Price Range | Dietary Options | Maps |
|------|----------|------------|---------|-------------|-----------------|------|
| [Time] | [Area] | [Restaurant] | [Cuisine] | [Price] | [Dietary] | [[Restaurant](link)] |

[Continue for all days...]

## Restaurant Highlights
- **Best Breakfast Spot:** [Restaurant name and reason]
- **Must-Try Local Cuisine:** [Restaurant and signature dish]
- **Best Value for Money:** [Restaurant and why]
- **Dietary Preference Friendly:** [Best options for specified preferences]

## Dining Tips
- [Local dining customs and etiquette]
- [Best times to visit popular restaurants]
- [Reservation recommendations]
- [Payment methods and tipping culture]
- [Special dietary requirement handling]

**IMPORTANT:**
- Always use INR (Indian Rupees) currency throughout for all locations
- Ensure all restaurant suggestions align with specified dietary preferences
- Provide clickable Google Maps links for each restaurant
- Consider meal timing logically with itinerary activities (if provided)"""

        # Build search query based on mode
        if itinerary_details:
            # Itinerary-based search
            search_query = f"""Find restaurants based on this itinerary:
{itinerary_details}

Dates: {dates if dates else 'Not specified'}
Dietary Preferences: {dietary_preferences}
Travelers: {travelers}
Budget: {budget_hint if budget_hint else 'Flexible'}

Provide restaurant recommendations near each activity location with meal timings."""
        else:
            # Independent location-based search
            search_query = f"""Find the best restaurants in {location} for {travelers} person{'s' if travelers > 1 else ''}.

Dietary Preferences: {dietary_preferences}
Budget: {budget_hint if budget_hint else 'Varied price ranges from budget to fine dining'}
Dates: {dates if dates else 'General recommendations'}

Provide diverse restaurant options categorized by:
1. Breakfast spots
2. Lunch recommendations  
3. Dinner options
4. Local specialties and must-try cuisines
5. Different price ranges (budget, mid-range, fine dining)"""

        # Search using Perplexity
        results = perplexity_service.search(
            query=search_query,
            system_prompt=system_prompt,
            temperature=0.1
        )
        
        # Return results directly since the system prompt handles formatting
        if isinstance(results, dict) and 'error' in results:
            return f"## Error in Restaurant Search\n\n{results['error']}"
        
        return results
        
    except Exception as e:
        return f"## Error in Restaurant Search\n\nFailed to process restaurant search: {str(e)}"


if __name__ == "__main__":
    print("Testing Restaurant Search with Itinerary Integration...")
    
    # First, we need to import and run the itinerary planner
    try:
        from IternaryPlanning import plan_itinerary
        
        # Test itinerary query
        itinerary_query = """
        Plan a 2-day itinerary for Tokyo from Delhi for a couple 
        from 25-12-2025 to 27-12-2025 with budget $1000. 
        We prefer temples, shopping, and traditional experiences.
        """
        
        print("STEP 1: Generating Itinerary...")
        print(f"Query: {itinerary_query.strip()}")
        print("\n" + "="*60)
        
        # Get itinerary from itinerary planner
        itinerary_result = plan_itinerary.invoke({"query": itinerary_query})
        print("ITINERARY GENERATED:")
        print("="*60)
        print(itinerary_result)
        
        print("\n" + "="*80 + "\n")
        
        # Test restaurant search with the generated itinerary
        print("STEP 2: Finding Restaurants...")
        print("Dietary Preferences: veg and non-veg")
        print("\n" + "="*60)
        print("RESTAURANT RECOMMENDATIONS:")
        print("="*60)
        
        # Search restaurants based on the itinerary
        restaurant_result = search_restaurants.invoke({
            "itinerary_details": itinerary_result,
            "dates": "25-12-2025 to 27-12-2025",
            "dietary_preferences": "veg and non-veg"
        })
        
        print(restaurant_result)
        
        print("\n" + "="*80)
        print("Restaurant search integration test completed!")
        print(" Check restaurant recommendations aligned with itinerary locations and times.")
        
    except ImportError:
        print("Could not import itinerary planner. Testing restaurant search independently...")
    except Exception as e:
        print(f"Error in restaurant search test: {str(e)}")
     
