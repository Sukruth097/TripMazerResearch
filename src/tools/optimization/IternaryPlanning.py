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
def plan_itinerary(query: str) -> str:
    """
    Create a comprehensive itinerary plan based on natural language query.
    
    This tool extracts itinerary requirements from a natural language query and uses
    Perplexity AI to create detailed day-by-day travel plans with activities, timings, and maps.
    
    Args:
        query: Natural language query describing itinerary needs
    
    Returns:
        str: Detailed itinerary plan in markdown format with daily tables
    
    Example:
        >>> query = "Plan a 3-day itinerary for Tokyo from Delhi for couple from 25-12-2025 to 28-12-2025 with budget $1500. We prefer temples, shopping, and nightlife."
        >>> result = plan_itinerary(query)
        >>> print(result)
        
        # Itinerary Planning Results
        
        ## Extracted Requirements
        - **From:** Delhi
        - **Destination:** Tokyo
        - **Travel Type:** Couple
        - **Budget:** $1500 USD
        - **Dates:** 25-12-2025 to 28-12-2025
        - **Preferred Activities:** temples, shopping, nightlife
        
        ---
        
        ## Day 1 - December 25, 2025
        
        | Time | Activity | Details | Maps |
        |------|----------|---------|------|
        | 9:00 AM | Senso-ji Temple | Traditional Buddhist temple, perfect for couples seeking spiritual experience | [Senso-ji Temple](https://maps.google.com/search/Senso-ji+Temple+Tokyo) |
        | 12:00 PM | Nakamise Shopping Street | Traditional shopping street near temple | [Nakamise Street](https://maps.google.com/search/Nakamise+Shopping+Street+Tokyo) |
        | 7:00 PM | Shibuya Nightlife District | Perfect for couples' nightlife experience | [Shibuya](https://maps.google.com/search/Shibuya+Tokyo) |
        
        ## Day 2 - December 26, 2025
        
        | Time | Activity | Details | Maps |
        |------|----------|---------|------|
        | 10:00 AM | Meiji Shrine | Peaceful shrine in the heart of Tokyo | [Meiji Shrine](https://maps.google.com/search/Meiji+Shrine+Tokyo) |
        | 2:00 PM | Ginza Shopping | High-end shopping district | [Ginza](https://maps.google.com/search/Ginza+Tokyo) |
        
        ## Budget Breakdown
        - **Total Budget:** $1500 USD
        - **Per Day:** ~$500 USD
        - **Activities:** $200 per day
        - **Food:** $150 per day  
        - **Transportation:** $50 per day
        - **Shopping:** $100 per day
        
        ## Travel Tips
        - Book temple visits early during peak season
        - Carry cash for traditional shopping areas
        - Download Google Translate for easier navigation
    """
    try:
        # Get Perplexity service
        perplexity_service = _get_perplexity_service()
        
        # Create comprehensive system prompt that extracts AND plans itinerary
        system_prompt = """You are an expert travel itinerary planner and advisor with data extraction capabilities.

**STEP 1: Extract itinerary requirements from the user query**
First, identify and extract these parameters from the user's natural language query:
- From Location: Origin/departure location
- Destination: Where they want to travel
- Travel Type: solo/group/couple (if mentioned)
- Budget: Budget amount with appropriate currency (see currency rules below)
- Travel Dates: When they're traveling (extract any date mentions)
- Preferred Activities: Any activities mentioned (beach, mountains, nightclub, pubs, temples, shopping, etc.)

**CURRENCY DETECTION RULES:**
- If BOTH from location AND destination are Indian regions/cities (Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad, Pune, Ahmedabad, Jaipur, Surat, Lucknow, Kanpur, Nagpur, Indore, Thane, Bhopal, Visakhapatnam, Patna, Vadodara, Ghaziabad, Ludhiana, Agra, Nashik, Faridabad, Meerut, Rajkot, Kalyan, Vasai-Virar, Varanasi, Srinagar, Aurangabad, Dhanbad, Amritsar, Navi Mumbai, Allahabad, Ranchi, Howrah, Coimbatore, Jabalpur, Gwalior, Vijayawanda, Jodhpur, Madurai, Raipur, Kota, Guwahati, Chandigarh, Solapur, Hubli-Dharwad, Bareilly, Moradabad, Mysore, Gurgaon, Aligarh, Jalandhar, ...iruchirappalli, Bhubaneswar, Salem, Warangal, Mira-Bhayandar, Thiruvananthapuram, Bhiwandi, Saharanpur, Guntur, Amravati, Bikaner, Noida, Jamshedpur, Bhilai Nagar, Cuttack, Firozabad, Kochi, Bhavnagar, Dehradun, Durgapur, Asansol, Nanded-Waghala, Kolhapur, Ajmer, Akola, Gulbarga, Jamnagar, Ujjain, Loni, Siliguri, Jhansi, Ulhasnagar, Nellore, Jammu, Sangli-Miraj & Kupwad, Belgaum, Mangalore, Ambattur, Tirunelveli, Malegaon, Gaya, Jalgaon, Udaipur, Maheshtala, or any other Indian city/state): Use INR (Indian Rupees)
- For ALL OTHER destinations or international travel: Use $ (US Dollars)

**STEP 2: Create comprehensive day-by-day itinerary**
Based on the extracted requirements, create a detailed itinerary plan.

**Instructions for itinerary planning:**
1. Calculate the number of days from the dates provided
2. Create day-by-day plans considering travel type (solo/group/couple preferences)
3. Include preferred activities if mentioned, otherwise suggest popular activities
4. Provide optimal timing for each activity based on local conditions
5. Include realistic travel times between activities
6. Consider budget constraints for activity selection
7. Use the CORRECT CURRENCY throughout all pricing
8. Provide Google Maps links as clickable place names
9. **BUDGET UTILIZATION**: Aim to use most of the available budget to create comprehensive and engaging itineraries that match user preferences

**Response Format (MANDATORY):**

# Itinerary Planning Results

## Extracted Requirements
- **From:** [extracted from location]
- **Destination:** [extracted destination]
- **Travel Type:** [solo/group/couple or "Not specified"]
- **Budget:** [INR for Indian regions or USD for international][extracted budget] [INR for Indian regions or USD for international]
- **Dates:** [extracted dates]
- **Preferred Activities:** [list extracted activities or "None specified"]

---

## Day 1 - [Date]

| Time | Activity | Details | Maps |
|------|----------|---------|------|
| [Time] | [Activity Name] | [Comprehensive details including why it's good for travel type, cost estimates, duration, tips] | [[Activity Name](https://maps.google.com/search/[Activity+Name+Location])] |
| [Time] | [Activity Name] | [Details] | [[Activity Name](https://maps.google.com/search/[Activity+Name+Location])] |

## Day 2 - [Date]

| Time | Activity | Details | Maps |
|------|----------|---------|------|
| [Time] | [Activity Name] | [Details] | [[Activity Name](https://maps.google.com/search/[Activity+Name+Location])] |

[Continue for all days...]

## Budget Breakdown
- **Total Budget:** [Currency][Amount] [Currency Code]
- **Per Day:** ~[Currency][Amount per day] [Currency Code]
- **Activities:** [Currency][Amount] per day
- **Food:** [Currency][Amount] per day
- **Transportation:** [Currency][Amount] per day
- **Shopping/Misc:** [Currency][Amount] per day

## Travel Tips for [Travel Type]
- [Specific tips based on travel type and destination]
- [Local customs and etiquette]
- [Best times to visit attractions]
- [Transportation recommendations]
- [Safety and practical advice]

**IMPORTANT FORMATTING RULES:**
1. Use the correct currency symbol (INR for India, USD for international) throughout
2. Make Google Maps links clickable with format: [[Place Name](https://maps.google.com/search/Place+Name+City)]
3. Include comprehensive activity details considering travel type preferences
4. Provide realistic timing and logical activity flow
5. Consider local opening hours, peak times, and seasonal factors
6. If preferred activities are mentioned, prioritize them in the itinerary"""

        # Search using Perplexity with the combined extraction and planning prompt
        results = perplexity_service.search(
            query=query,
            system_prompt=system_prompt,
            temperature=0.1
        )
        
        # Return results directly since the system prompt handles formatting
        if isinstance(results, dict) and 'error' in results:
            return f"## Error in Itinerary Planning\n\n{results['error']}"
        
        return results
        
    except Exception as e:
        return f"## Error in Itinerary Planning\n\nFailed to process itinerary planning: {str(e)}"


if __name__ == "__main__":
    # Test queries with different scenarios
    
    # Test 1: International travel with preferences (should use USD)
    test_query_international = """
    Plan a 4-day itinerary for Tokyo from Delhi for a couple 
    from 25-12-2025 to 29-12-2025 with budget $2000. 
    We prefer temples, shopping, nightlife, and traditional experiences.
    """
    
    # Test 2: Indian domestic travel (should use INR)
    test_query_indian = """
    Plan a 3-day itinerary for Goa from Mumbai for group travel
    from 20-01-2026 to 23-01-2026 with budget INR 15000.
    We prefer beaches, water sports, and local cuisine.
    """
    
    print("Testing Itinerary Planner with Currency Detection...")
    
    # Test international query
    print(f"\nTEST 1 - International Travel (Should use USD):")
    print(f"Query: {test_query_international.strip()}")
    print("\n" + "="*70)
    print("ITINERARY RESULTS:")
    print("="*70 + "\n")
    
    try:
        result1 = plan_itinerary.invoke({"query": test_query_international})
        print(result1)
        print("\n" + "="*70)
        print("International itinerary test completed!")
    except Exception as e:
        print(f"Error in international test: {str(e)}")
    
    print("\n" + "="*80 + "\n")
    
    # Test Indian domestic query
    print(f"TEST 2 - Indian Domestic Travel (Should use INR):")
    print(f"Query: {test_query_indian.strip()}")
    print("\n" + "="*70)
    print("ITINERARY RESULTS:")
    print("="*70 + "\n")
    
    try:
        result2 = plan_itinerary.invoke({"query": test_query_indian})
        print(result2)
        print("\n" + "="*70)
        print("Indian domestic itinerary test completed!")
    except Exception as e:
        print(f"Error in Indian test: {str(e)}")
        
    print("\n" + "="*80)
    print("🎉 All itinerary tests completed!")
    print("💡 Check the daily tables with Time|Activity|Details|Maps columns above.")
    print("🔗 Maps should appear as clickable place names linking to Google Maps.")
    print("Check currency symbols (INR vs USD) in budget sections.")
