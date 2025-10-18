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
from src.services.perplexity_service import PerplexityService
from src.utils.service_initializer import get_perplexity_service, get_serp_api_service


def _search_hotels_with_serp(location: str, check_in_date: str, check_out_date: str,
                             adults: int = 2, children: int = 0, currency: str = "INR") -> str:
    """
    Search hotels using SERP API and return formatted results.
    
    Args:
        location: Destination city/location
        check_in_date: Check-in date in YYYY-MM-DD format
        check_out_date: Check-out date in YYYY-MM-DD format
        adults: Number of adults (default 2)
        children: Number of children (default 0)
        currency: Currency code - "INR" or "USD" (default "INR")
        
    Returns:
        Formatted markdown string with top 5 hotel results
    """
    try:
        # Get SERP service
        serp_service = get_serp_api_service()
        
        # Search hotels
        hotel_results = serp_service.search_hotels(
            location=location,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            currency=currency,
            country_code="in" if currency == "INR" else "us",
            adults=adults,
            children=children,
            language="en",
            vacation_rentals="true",
            sort_by=[13, 3, 8],  # Rating, Price, Distance
            no_cache="true"
        )
        
        # Format results
        if 'error' in hotel_results:
            return f"\n\n---\n\n## SERP Hotel Search Results\n\n**Error:** {hotel_results['error']}"
        
        if 'properties' not in hotel_results or not hotel_results['properties']:
            return "\n\n---\n\n## SERP Hotel Search Results\n\nNo hotels found."
        
        # Get top 5 hotels
        properties = hotel_results['properties'][:5]
        
        # Build markdown table
        currency_symbol = "₹" if currency == "INR" else "$"
        
        output = f"\n\n---\n\n## Top 5 SERP Hotel Recommendations\n\n"
        output += f"**Search Parameters:** {location} | Check-in: {check_in_date} | Check-out: {check_out_date} | Guests: {adults} adults"
        if children > 0:
            output += f", {children} children"
        output += "\n\n"
        
        # Create table header
        output += "| # | Hotel Name | Rating | Price/Night | Hotel Class | Key Amenities | Booking Link |\n"
        output += "|---|------------|--------|-------------|-------------|---------------|-------------|\n"
        
        # Add hotel rows
        for i, hotel in enumerate(properties, 1):
            name = hotel.get('name', 'N/A')
            rating = hotel.get('overall_rating', 'N/A')
            reviews = hotel.get('reviews', 0)
            
            # Get price
            price_info = hotel.get('total_rate', {})
            if isinstance(price_info, dict):
                price = price_info.get('lowest', 'N/A')
            else:
                price = 'N/A'
            
            price_str = f"{currency_symbol}{price}" if price != 'N/A' else 'N/A'
            
            hotel_class = hotel.get('hotel_class', 'N/A')
            hotel_class_str = f"{hotel_class}⭐" if hotel_class != 'N/A' else 'N/A'
            
            # Get amenities (first 3)
            amenities = hotel.get('amenities', [])
            amenities_str = ", ".join(amenities[:3]) if amenities else "N/A"
            
            # Get booking link
            link = hotel.get('link', '#')
            link_str = f"[View Details]({link})"
            
            # Format rating with reviews
            rating_str = f"{rating} ({reviews} reviews)" if rating != 'N/A' else 'N/A'
            
            output += f"| {i} | {name} | {rating_str} | {price_str} | {hotel_class_str} | {amenities_str} | {link_str} |\n"
        
        output += "\n*Prices shown are per night for the entire property. Data from Google Hotels via SERP API.*\n"
        
        return output
        
    except Exception as e:
        print(f"SERP hotel search error: {e}")
        import traceback
        traceback.print_exc()
        return f"\n\n---\n\n## SERP Hotel Search Results\n\n**Error:** {str(e)}"



@tool
def search_accommodations(query: str, location: str = None, check_in_date: str = None, 
                         check_out_date: str = None, adults: int = 2, 
                         children: int = 0, currency: str = "INR") -> str:
    """
    Search for accommodation options based on natural language query.
    
    This tool extracts accommodation requirements from a natural language query and uses
    Perplexity AI to find the best accommodation options with detailed recommendations.
    Additionally, it searches SERP API for structured hotel data when parameters are provided.
    
    Args:
        query: Natural language query describing accommodation needs
        location: Destination city/location for SERP search (optional)
        check_in_date: Check-in date in YYYY-MM-DD format for SERP search (optional)
        check_out_date: Check-out date in YYYY-MM-DD format for SERP search (optional)
        adults: Number of adults for SERP search (default 2)
        children: Number of children for SERP search (default 0)
        currency: Currency code for SERP search - "INR" or "USD" (default "INR")
    
    Returns:
        str: Detailed accommodation recommendations in markdown format (Perplexity + SERP results)
    
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
        perplexity_service = get_perplexity_service()
        
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
- If BOTH from location AND destination are Indian regions/cities (Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad, Pune, Ahmedabad, Jaipur, Surat, Lucknow, Kanpur, Nagpur, Indore, Thane, Bhopal, Visakhapatnam, Patna, Vadodara, Ghaziabad, Ludhiana, Agra, Nashik, Faridabad, Meerut, Rajkot, Kalyan, Vasai-Virar, Varanasi, Srinagar, Aurangabad, Dhanbad, Amritsar, Navi Mumbai, Allahabad, Ranchi, Howrah, Coimbatore, Jabalpur, Gwalior, Vijayawanda, Jodhpur, Madurai, Raipur, Kota, Guwahati, Chandigarh, Solapur, Hubli-Dharwad, Bareilly, Moradabad, Mysore, Gurgaon, Aligarh, Jalandhar, ...iruchirappalli, Bhubaneswar, Salem, Warangal, Mira-Bhayandar, Thiruvananthapuram, Bhiwandi, Saharanpur, Guntur, Amravati, Bikaner, Noida, Jamshedpur, Bhilai Nagar, Cuttack, Firozabad, Kochi, Bhavnagar, Dehradun, Durgapur, Asansol, Nanded-Waghala, Kolhapur, Ajmer, Akola, Gulbarga, Jamnagar, Ujjain, Loni, Siliguri, Jhansi, Ulhasnagar, Nellore, Jammu, Sangli-Miraj & Kupwad, Belgaum, Mangalore, Ambattur, Tirunelveli, Malegaon, Gaya, Jalgaon, Udaipur, Maheshtala, or any other Indian city/state): Use INR (Indian Rupees)
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
8. **IMPORTANT**: Use the correct currency symbol (INR for India, USD for international) throughout all pricing

**Response Format (MANDATORY):**
Start with a clear extraction summary, then provide recommendations in table format for easy comparison:

# Accommodation Search Results

## Extracted Requirements
- **From:** [extracted from location]
- **Destination:** [extracted destination]
- **Guests:** [extracted number] people
- **Budget:** [INR for Indian regions or USD for international][extracted budget] [INR for Indian regions or USD for international]
- **Dates:** [extracted dates]
- **Preferences:** [list extracted preferences or "None specified"]

---

## Recommended Accommodations

| # | Property Name | Type | Price/Night/Person | Location | Coordinates | Key Amenities | Booking Links |
|---|---------------|------|-------------------|----------|-------------|---------------|---------------|
| 1 | [Hotel Name] | Hotel/Hostel | INR [price] per person | [Area/District] | [Lat, Long] | WiFi, Breakfast, Pool | [Booking.com](https://booking.com) - [Agoda](https://agoda.com) |
| 2 | [Hotel Name] | Apartment | INR [price] per person | [Area/District] | [Lat, Long] | Kitchen, WiFi, AC | [Airbnb](https://airbnb.com) - [MakeMyTrip](https://makemytrip.com) |
| 3 | [Hotel Name] | Hostel | INR [price] per person | [Area/District] | [Lat, Long] | Dorm, WiFi, Common Area | [Hostelworld](https://hostelworld.com) - [Goibibo](https://goibibo.com) |

### Additional Information
**Budget Option:** Value for money with basic amenities.
**Luxury Option:** Premium choice worth the extra cost.

## Booking Tips
Book early for better rates. Valid ID required at check-in.

Always provide current, accurate information with specific details about availability and pricing where possible.

**CRITICAL INSTRUCTIONS FOR COORDINATES AND BOOKING LINKS:**
1. Include GPS coordinates (latitude, longitude) for each property in decimal format (e.g., 28.6139, 77.2090)
2. Coordinates help users navigate and check exact locations on maps
3. In Booking Links column, include multiple real booking platforms separated by - symbol
4. Try to provide actual hotel booking links when possible (Booking.com, Agoda, Airbnb, Hotels.com, etc.)
5. Format as [Platform Name](URL) for proper markdown rendering
6. Popular platforms: Booking.com, Agoda, Hotels.com, Expedia, Airbnb, MakeMyTrip, Goibibo, Hostelworld
7. Include official hotel websites when available
8. Ensure links are current and functional

**CRITICAL PRICING INSTRUCTIONS:**
- ALWAYS calculate and show price per night per person
- If hotel room accommodates multiple guests, divide total room price by number of guests
- For example: If room costs INR 3,000/night for 3 people, show INR 1,000 per person
- For dormitory/hostel beds, show individual bed price
- Make pricing calculations clear and accurate for the specified number of guests

**EXAMPLE FORMAT:**
- Coordinates column: 28.6139, 77.2090 (decimal degrees format)
- Price column: INR 1,500 per person (if room for 3 people costs INR 4,500 total)
- Booking Links: [Booking.com](https://booking.com/hotel/link) - [Agoda](https://agoda.com/hotel/link)"""

        # Search using Perplexity with the combined extraction and recommendation prompt
        results = perplexity_service.search(
            query=query,
            system_prompt=system_prompt,
            temperature=0
        )
        
        # Return results directly since the system prompt handles formatting
        if isinstance(results, dict) and 'error' in results:
            return f"## Error in Accommodation Search\n\n{results['error']}"
        
        # Add SERP hotel results if parameters are provided
        if location and check_in_date and check_out_date:
            serp_results = _search_hotels_with_serp(
                location=location,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                adults=adults,
                children=children,
                currency=currency
            )
            return results + serp_results
        
        return results
        
    except Exception as e:
        return f"## Error in Accommodation Planning\n\nFailed to process accommodation search: {str(e)}"


if __name__ == "__main__":
    # Test 1: Perplexity only (no SERP parameters)
    test_query = """
    I need accommodation in Goa for 2 people 
    from 19-11-2025 to 22-11-2025 with a budget of 15000 rupees. 
    I prefer hotels with wifi, breakfast included, and beach view.
    """
    
    print("="*80)
    print("TEST 1: PERPLEXITY SEARCH ONLY (No SERP parameters)")
    print("="*80)
    print(f"\nQuery: {test_query.strip()}")
    print("\n" + "="*60)
    
    try:
        # Test without SERP parameters - only Perplexity
        result = search_accommodations.invoke({"query": test_query})
        print(result)
        print("\n" + "="*60)
        print("Test 1 completed successfully!")
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n\n")
    
    # Test 2: Full search with both Perplexity and SERP (with parameters)
    print("="*80)
    print("TEST 2: PERPLEXITY + SERP SEARCH (With manual parameters)")
    print("="*80)
    print(f"\nQuery: {test_query.strip()}")
    print("\nSERP Parameters:")
    print("  - location: Goa")
    print("  - check_in_date: 2025-11-19")
    print("  - check_out_date: 2025-11-22")
    print("  - adults: 2")
    print("  - children: 0")
    print("  - currency: INR")
    print("\n" + "="*60)
    
    try:
        # Test with SERP parameters - Perplexity + SERP
        result = search_accommodations.invoke({
            "query": test_query,
            "location": "Goa",
            "check_in_date": "2025-11-19",
            "check_out_date": "2025-11-22",
            "adults": 2,
            "children": 0,
            "currency": "INR"
        })
        print(result)
        print("\n" + "="*60)
        print("Test 2 completed successfully!")
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n\nTroubleshooting:")
    print("- Ensure PERPLEXITY_API_KEY and SERP_API_KEY are set in your .env file")
    print("- Check your internet connection")
    print("- Verify API keys are valid and have sufficient credits")
