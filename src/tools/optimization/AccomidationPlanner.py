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
def search_accommodations(query: str) -> str:
    """
    Search for accommodation options based on natural language query.
    
    This tool extracts accommodation requirements from a natural language query and uses
    Perplexity AI to find the best accommodation options with detailed recommendations.
    
    Args:
        query: Natural language query describing accommodation needs
    
    Returns:
        str: Detailed accommodation recommendations in markdown format
    
    Example:
        >>> query = "Find hotels in Paris for 2 people from 26-11-2025 to 30-11-2025 with budget $500 and prefer wifi and breakfast"
        >>> result = search_accommodations(query)
        >>> print(result)
        
        # Accommodation Search Results
        
        ## Extracted Requirements
        - **From:** Not specified
        - **Destination:** Paris
        - **Guests:** 2 people
        - **Budget:** $500 USD
        - **Dates:** 26-11-2025 to 30-11-2025
        - **Preferences:** wifi, breakfast
        
        ---
        
        ## Recommended Accommodations
        
        ### 1. Hotel Malte Opera
        - **Type:** Boutique Hotel
        - **Price Range:** $180-220 per night
        - **Location:** 2nd Arrondissement, near Opera
        - **Amenities:**
          - Free WiFi
          - Continental breakfast included
          - 24/7 reception
        - **Booking:** Booking.com, Hotels.com
        - **Why recommended:** Perfect match for budget and preferences
        
        ### 2. Ibis Styles Paris Republique
        - **Type:** Modern Hotel
        - **Price Range:** $150-190 per night
        - **Location:** République area, metro access
        - **Amenities:**
          - Complimentary WiFi
          - Breakfast buffet available
          - Air conditioning
        - **Booking:** Direct booking, Expedia
        - **Why recommended:** Great value with preferred amenities
        
        ## Summary & Top Recommendation
        Hotel Malte Opera offers the best combination of location, amenities, and value for your Paris stay.
        
        ## Booking Tips
        - Book early for November dates as it's peak tourist season
        - Check cancellation policies for flexibility
    """
    try:
        # Get Perplexity service
        perplexity_service = _get_perplexity_service()
        
        # Create comprehensive system prompt that extracts AND searches
        system_prompt = """You are an expert accommodation planner and travel advisor with data extraction capabilities.

**STEP 1: Extract accommodation requirements from the user query**
First, identify and extract these parameters from the user's natural language query:
- From Location: Origin/departure location
- Destination: Where accommodation is needed
- Number of People: How many guests (default to 1 if not specified)
- Budget: Budget amount with appropriate currency (see currency rules below)
- Travel Dates: When they're traveling (extract any date mentions)
- Preferences: Any amenities or features mentioned (wifi, pool, breakfast, 3star ,hostels,dormitory, 5 star hotels etc.)

**CURRENCY DETECTION RULES:**
- If BOTH from location AND destination are Indian regions/cities (Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad, Pune, Ahmedabad, Jaipur, Surat, Lucknow, Kanpur, Nagpur, Indore, Thane, Bhopal, Visakhapatnam, Patna, Vadodara, Ghaziabad, Ludhiana, Agra, Nashik, Faridabad, Meerut, Rajkot, Kalyan, Vasai-Virar, Varanasi, Srinagar, Aurangabad, Dhanbad, Amritsar, Navi Mumbai, Allahabad, Ranchi, Howrah, Coimbatore, Jabalpur, Gwalior, Vijayawanda, Jodhpur, Madurai, Raipur, Kota, Guwahati, Chandigarh, Solapur, Hubli-Dharwad, Bareilly, Moradabad, Mysore, Gurgaon, Aligarh, Jalandhar, Tiruchirappalli, Bhubaneswar, Salem, Warangal, Mira-Bhayandar, Thiruvananthapuram, Bhiwandi, Saharanpur, Guntur, Amravati, Bikaner, Noida, Jamshedpur, Bhilai Nagar, Cuttack, Firozabad, Kochi, Bhavnagar, Dehradun, Durgapur, Asansol, Nanded-Waghala, Kolhapur, Ajmer, Akola, Gulbarga, Jamnagar, Ujjain, Loni, Siliguri, Jhansi, Ulhasnagar, Nellore, Jammu, Sangli-Miraj & Kupwad, Belgaum, Mangalore, Ambattur, Tirunelveli, Malegaon, Gaya, Jalgaon, Udaipur, Maheshtala, or any other Indian city/state): Use ₹ (Indian Rupees)
- For ALL OTHER destinations or international travel: Use $ (US Dollars)

**STEP 2: Provide comprehensive accommodation recommendations**
Based on the extracted requirements, search for and recommend accommodation options that match the criteria.

**Instructions for recommendations:**
1. Search for accommodation options that match the extracted criteria
2. Consider hotels, hostels/dormitory, and other accommodation types
3. Include price ranges, amenities, and location details using the CORRECT CURRENCY
4. Provide at max 3-4 different options with varying price points
5. Consider all specified preferences when making recommendations
6. Include booking tips and best practices
7. Mention any seasonal considerations or local events that might affect pricing
8. **BUDGET UTILIZATION**: Aim to use most of the available budget to recommend the best possible accommodations within user preferences
8. **IMPORTANT**: Use the correct currency symbol (₹ for India, $ for international) throughout all pricing

**Response Format (MANDATORY):**
Start with a clear extraction summary, then provide recommendations in table format for easy comparison:

# Accommodation Search Results

## Extracted Requirements
- **From:** [extracted from location]
- **Destination:** [extracted destination]
- **Guests:** [extracted number] people
- **Budget:** [₹ for Indian regions or $ for international][extracted budget] [INR for Indian regions or USD for international]
- **Dates:** [extracted dates]
- **Preferences:** [list extracted preferences or "None specified"]

---

## Recommended Accommodations

| # | Property Name | Type | Price/Night/Person | Location | Coordinates | Key Amenities | Booking Links |
|---|---------------|------|-------------------|----------|-------------|---------------|---------------|
| 1 | [Hotel Name] | Hotel/Hostel | ₹[price] per person | [Area/District] | [Lat, Long] | WiFi, Breakfast, Pool | [Booking.com](https://booking.com) • [Agoda](https://agoda.com) |
| 2 | [Hotel Name] | Apartment | ₹[price] per person | [Area/District] | [Lat, Long] | Kitchen, WiFi, AC | [Airbnb](https://airbnb.com) • [MakeMyTrip](https://makemytrip.com) |
| 3 | [Hotel Name] | Hostel | ₹[price] per person | [Area/District] | [Lat, Long] | Dorm, WiFi, Common Area | [Hostelworld](https://hostelworld.com) • [Goibibo](https://goibibo.com) |

### Additional Information
**Budget Option:** Brief note on value for money option with any trade-offs.
**Luxury Option:** Brief note on premium choice and why it's worth the extra cost.
**Seasonal Notes:** December is peak season - book early for better rates and availability.

## Booking Tips
Book early for peak season/holidays for better rates. All guests need valid ID at check-in.

Always provide current, accurate information with specific details about availability and pricing where possible.

**CRITICAL INSTRUCTIONS FOR COORDINATES AND BOOKING LINKS:**
1. Include GPS coordinates (latitude, longitude) for each property in decimal format (e.g., 28.6139, 77.2090)
2. Coordinates help users navigate and check exact locations on maps
3. In Booking Links column, include multiple real booking platforms separated by • symbol
4. Try to provide actual hotel booking links when possible (Booking.com, Agoda, Airbnb, Hotels.com, etc.)
5. Format as [Platform Name](URL) for proper markdown rendering
6. Popular platforms: Booking.com, Agoda, Hotels.com, Expedia, Airbnb, MakeMyTrip, Goibibo, Hostelworld
7. Include official hotel websites when available
8. Ensure links are current and functional

**CRITICAL PRICING INSTRUCTIONS:**
- ALWAYS calculate and show price per night per person
- If hotel room accommodates multiple guests, divide total room price by number of guests
- For example: If room costs ₹3,000/night for 3 people, show ₹1,000 per person
- For dormitory/hostel beds, show individual bed price
- Make pricing calculations clear and accurate for the specified number of guests

**EXAMPLE FORMAT:**
- Coordinates column: 28.6139, 77.2090 (decimal degrees format)
- Price column: ₹1,500 per person (if room for 3 people costs ₹4,500 total)
- Booking Links: [Booking.com](https://booking.com/hotel/link) • [Agoda](https://agoda.com/hotel/link)"""

        # Search using Perplexity with the combined extraction and recommendation prompt
        results = perplexity_service.search(
            query=query,
            system_prompt=system_prompt,
            temperature=0
        )
        
        # Return results directly since the system prompt handles formatting
        if isinstance(results, dict) and 'error' in results:
            return f"## Error in Accommodation Search\n\n{results['error']}"
        
        return results
        
    except Exception as e:
        return f"## Error in Accommodation Planning\n\nFailed to process accommodation search: {str(e)}"


if __name__ == "__main__":
    test_query = """
    I need accommodation in bangalore to Delhi  for 3 people 
    from 15-12-2025 to 22-12-2025 with a budget of 30000 rupees overall. 
    I prefer hotels with wifi, breakfast included, and near to transport.
    """
    
    print("Testing Accommodation Planner...")
    print(f"\nQuery: {test_query.strip()}")
    print("\n" + "="*60)
    print("ACCOMMODATION SEARCH RESULTS")
    print("="*60 + "\n")
    
    try:
        # Use invoke method instead of direct call to avoid deprecation warning
        result = search_accommodations.invoke({"query": test_query})
        print(result)
        print("\n" + "="*60)
        print("Test completed successfully!")
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        print("\nTroubleshooting:")
        print("- Replace the placeholder API key with your actual Perplexity API key")
        print("- Check your internet connection")
        print("- Verify your Perplexity API key is valid")
        print("- Ensure you have sufficient API credits")
