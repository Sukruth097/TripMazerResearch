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

from langchain.tools import tool
from src.services.perplexity_service import PerplexityService


def _get_perplexity_service() -> PerplexityService:
    """Get initialized Perplexity service instance."""
    # Get API key from environment variable
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY environment variable is required")
    return PerplexityService(api_key)
@tool
def search_restaurants(itinerary_details: str, dates: str, dietary_preferences: str = "", budget_hint: str = "") -> str:
    """
    Search for restaurants based on itinerary details and dietary preferences.
    
    This tool analyzes an itinerary plan and suggests restaurants for each location and time,
    considering dietary preferences, budget constraints, and local cuisine options.
    
    Args:
        itinerary_details: Complete itinerary in JSON/Markdown format from itinerary planner
        dates: Travel dates in DD-MM-YYYY to DD-MM-YYYY format
        dietary_preferences: Dietary preferences like "veg only", "veg and non-veg", "non-veg only", etc.
        budget_hint: Optional budget guidance like "INR 6250 for 2 people for 3 days" to suggest appropriate price ranges
    
    Returns:
        str: Restaurant recommendations in markdown table format with realistic pricing
    
    Example:
        itinerary = "Day 1 - Tokyo: Visit Senso-ji Temple (9:00 AM), Nakamise Shopping (12:00 PM)"
        dates = "25-12-2025 to 28-12-2025"
        preferences = "veg and non-veg"
        result = search_restaurants(itinerary, dates, preferences)
      
        
        # Restaurant Recommendations
        
        ## Extracted Information
        - **Travel Dates:** 25-12-2025 to 28-12-2025
        - **Dietary Preferences:** veg and non-veg
        - **Locations:** Tokyo (Senso-ji Temple, Nakamise Shopping)
        
        ---
        
        ## Day 1 - December 25, 2025 | Tokyo
        
        | Time | Location | Restaurant | Cuisine | Price Range | Dietary Options | Maps |
        |------|----------|------------|---------|-------------|-----------------|------|
        | 8:00 AM | Near Senso-ji Temple | Temple Breakfast Cafe | Japanese | $15-25 | Veg & Non-veg | [Temple Breakfast Cafe](https://maps.google.com/search/Temple+Breakfast+Cafe+Senso-ji+Tokyo) |
        | 1:00 PM | Nakamise Shopping Area | Traditional Ramen House | Japanese Ramen | $10-20 | Veg & Non-veg options | [Traditional Ramen House](https://maps.google.com/search/Ramen+House+Nakamise+Tokyo) |
        | 7:00 PM | Asakusa District | Sushi Master | Sushi | $30-50 | Fresh seafood & veg options | [Sushi Master](https://maps.google.com/search/Sushi+Master+Asakusa+Tokyo) |
    """
    try:
        # Get Perplexity service
        perplexity_service = _get_perplexity_service()
        
        # Create comprehensive system prompt for restaurant recommendations
        system_prompt = f"""You are an expert restaurant consultant and food advisor with deep knowledge of local cuisines and dining options.

**TASK: Analyze the provided itinerary and recommend restaurants for each location and time**

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
- **Currency:** [INR or USD based on location]

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
- Use correct currency throughout (INR for Indian locations, USD for international)
- Ensure all restaurant suggestions align with specified dietary preferences
- Provide clickable Google Maps links for each restaurant
- Consider meal timing logically with itinerary activities"""

        # Search using Perplexity
        results = perplexity_service.search(
            query=f"Recommend restaurants based on this itinerary: {itinerary_details}. Dates: {dates}. Dietary preferences: {dietary_preferences}",
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
     
