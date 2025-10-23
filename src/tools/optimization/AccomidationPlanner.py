import os
import sys
import json
import random
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
from src.utils.service_initializer import get_serp_api_service


@tool
def search_accommodations(location: str, check_in_date: str, check_out_date: str,
                         adults: int = 2, children: int = 0, currency: str = "INR",
                         query: str = None, rating: list = None) -> str:
    """
    Search for hotels and accommodations using SERP Google Hotels API.
    
    **CRITICAL QUERY GUIDELINES:**
    SERP API fails with detailed/long queries. Keep queries SIMPLE and use only 2 types:
    
    1. **Budget Travel** → query = "Budget hotels and hostels in {location}"
       - Use when: User mentions budget, cheap, affordable, backpacking, hostels, dormitory
       - Example: "Budget hotels and hostels in Mumbai"
    
    2. **Luxury/Comfort Travel** → query = "Luxury hotels in {location}"
       - Use when: User mentions luxury, premium, comfort, 4-star, 5-star, resort
       - Example: "Luxury hotels in Dubai"
    
    **Agent's Responsibility:**
    - Analyze user preferences (budget vs luxury)
    - Construct ONE of the two simple query formats above
    - Pass other parameters (dates, adults, currency) separately
    
    Args:
        location: Destination city/location (e.g., "Mumbai", "Dubai", "Paris")
        check_in_date: Check-in date in YYYY-MM-DD format (e.g., "2025-11-25")
        check_out_date: Check-out date in YYYY-MM-DD format (e.g., "2025-11-30")
        adults: Number of adults (default 2)
        children: Number of children (default 0)
        currency: Currency code - Always "INR" (Indian Rupees) for all destinations (default "INR")
        query: Simple search query - MUST be one of:
               - "Budget hotels and hostels in {location}" (for budget travel)
               - "Luxury hotels in {location}" (for luxury/comfort travel)
               If not provided, defaults to "Budget hotels and hostels in {location}"
        rating: List of rating values to filter hotels (e.g., [7,8,9] for ratings 7-9)
                Default: [7, 8, 9] if not provided (good quality hotels with 7+ rating)
                Can override based on preference: [8,9] for luxury (8+ rating only)
        
    Returns:
        str: Formatted markdown table with top 5 hotel results from Google Hotels
    
    Example Usage:
        >>> # Budget traveler
        >>> search_accommodations.invoke({
        ...     "location": "Goa",
        ...     "check_in_date": "2025-11-19",
        ...     "check_out_date": "2025-11-22",
        ...     "adults": 2,
        ...     "currency": "INR",
        ...     "rating": [7,8,9],
        ...     "query": "Budget hotels and hostels in Goa"
        ... })
        
        >>> # Luxury traveler
        >>> search_accommodations.invoke({
        ...     "location": "Dubai",
        ...     "check_in_date": "2025-12-01",
        ...     "check_out_date": "2025-12-05",
        ...     "adults": 2,
        ...     "currency": "INR",
        ...     "rating": [8,9],
        ...     "query": "Luxury hotels in Dubai"
        ... })
    """
    try:
        # Get SERP service
        serp_service = get_serp_api_service()
        
        # Use provided query or construct default budget query
        if query:
            search_query = query
        else:
            # Default to budget hotels if no query provided
            search_query = f"Budget hotels and hostels in {location}"
        
        # Default rating filter to [7, 8, 9] if not provided
        if rating is None:
            rating = [7, 8, 9]  # Default: Good ratings (7+)
        
        
        # Search hotels with SERP API (always use INR)
        hotel_results = serp_service.search_hotels(
            query=search_query,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            currency="INR",  # Always use INR regardless of destination
            country_code="in",  # Always use India country code
            adults=adults,
            children=children,
            language="en",
            rating=rating,  # Pass rating filter if provided
            # vacation_rentals="true",
            # sort_by=[13, 3, 8],  # Sort by: Rating, Price, Distance
            no_cache="true"
        )
        
        # Format results
        if 'error' in hotel_results:
            return f"## Hotel Search Results\n\n**Error:** {hotel_results['error']}"
        
        if 'properties' not in hotel_results or not hotel_results['properties']:
            return f"## Hotel Search Results\n\nNo hotels found for query: '{search_query}'"
        
        # Get first 15 hotels, then use hybrid selection for better balance
        all_properties = hotel_results['properties']
        
        # Take up to 15 properties (or all if less than 15)
        available_properties = all_properties[:15] if len(all_properties) >= 15 else all_properties
        
        # Hybrid selection: First 3 top-ranked + Random 2 from remaining for variety
        if len(available_properties) >= 5:
            # Take first 3 results (most relevant/highest ranked)
            top_3 = available_properties[:3]
            
            # Get random 2 from the remaining properties (positions 4-15)
            remaining = available_properties[3:]
            if len(remaining) >= 2:
                random_2 = random.sample(remaining, 2)
            else:
                random_2 = remaining
            
            # Combine top 3 + random 2
            properties = top_3 + random_2
        else:
            # If less than 5 properties available, use all
            properties = available_properties
        
        # Build markdown table (always use INR symbol)
        currency_symbol = "₹"  # Always use INR
        
        output = f"## 🏨 Top 5 Hotel Recommendations\n\n"
        output += f"**Search Query:** {search_query}\n"
        output += f"**Dates:** {check_in_date} to {check_out_date} | **Guests:** {adults} adults"
        if children > 0:
            output += f", {children} children"
        output += "\n\n"
        
        # Create table header
        output += "| # | Hotel Name | Rating | Price/Night | Check-in Time | Check-out Time | Key Amenities | Nearby Places |\n"
        output += "|---|------------|--------|-------------|---------------|----------------|---------------|---------------|\n"
        
        # Add hotel rows
        for i, hotel in enumerate(properties, 1):
            # Get name and clean it (remove pipe characters that break markdown tables)
            name = hotel.get('name', 'N/A')
            name = name.replace('|', '-')  # Replace pipe with dash to avoid table breaking
            
            rating = hotel.get('overall_rating', 'N/A')
            reviews = hotel.get('reviews', 0)
            
            # Get price
            price_info = hotel.get('rate_per_night', {})
            # print(f"Price Info---------->: {price_info}")
            if isinstance(price_info, dict):
                price = price_info.get('lowest', 'N/A')
            else:
                price = 'N/A'
            
            # Get check-in and check-out times
            check_in_time = hotel.get('check_in_time', 'N/A')
            check_out_time = hotel.get('check_out_time', 'N/A')
            
            price_str = f"{currency_symbol}{price}" if price != 'N/A' else 'N/A'
            
            # Get amenities (first 3) and clean them
            amenities = hotel.get('amenities', [])
            if amenities:
                # Clean amenities and join
                cleaned_amenities = [am.replace('|', '-') for am in amenities[:3]]
                amenities_str = ", ".join(cleaned_amenities)
            else:
                amenities_str = "N/A"

            # Get nearby places (first 3) and format them for the Nearby Places column
            nearby_places = hotel.get('nearby_places', [])
            if nearby_places:
                nearby_details = []
                for place in nearby_places[:3]:
                    place_name = place.get('name', 'Unknown').replace('|', '-')
                    transportations = place.get('transportations', [])

                    if transportations:
                        transport_strs = []
                        for transport in transportations:
                            t_type = transport.get('type', 'N/A')
                            t_duration = transport.get('duration', 'N/A')
                            transport_strs.append(f"{t_type}: {t_duration}")

                        transports_joined = "; ".join(transport_strs)
                        nearby_details.append(f"• {place_name} ({transports_joined})")
                    else:
                        nearby_details.append(f"• {place_name}")

                # Join multiple nearby places with line breaks for bullet point list
                nearby_str = "<br>".join(nearby_details) if nearby_details else "N/A"
            else:
                nearby_str = "N/A"
            
            # Format rating with reviews
            rating_str = f"{rating} ({reviews} reviews)" if rating != 'N/A' else 'N/A'
            
            output += f"| {i} | {name} | {rating_str} | {price_str} | {check_in_time} | {check_out_time} | {amenities_str} | {nearby_str} |\n"
        
        # output += "\n*Prices shown are per night for the entire property. Data from Google Hotels via SERP API.*\n"
        
        return output
        
    except Exception as e:
        print(f"❌ SERP hotel search error: {e}")
        import traceback
        traceback.print_exc()
        return f"## Hotel Search Results\n\n**Error:** {str(e)}"


# Test code
if __name__ == "__main__":
    # print("="*80)
    # print("TEST: SERP Hotel Search Tool")
    # print("="*80)
    
    # # Test 1: Budget hotels with rating filter
    # print("\n" + "="*60)
    # print("TEST 1: Budget Hotels in Goa (Rating 7+)")
    # print("="*60)
    
    # try:
    #     result = search_accommodations.invoke({
    #         "location": "Goa",
    #         "check_in_date": "2025-11-19",
    #         "check_out_date": "2025-11-22",
    #         "adults": 2,
    #         "children": 0,
    #         "currency": "INR",
    #         "rating": [7, 8, 9],  # Filter for ratings 7-9
    #         "query": "Budget hotels and hostels in Goa"
    #     })
    #     print(result)
    #     print("\n✅ Test 1 completed successfully!")
    # except Exception as e:
    #     print(f"❌ Error occurred: {str(e)}")
    #     import traceback
    #     traceback.print_exc()
    
    # Test 2: Luxury hotels with higher rating filter (INR for international)
    print("\n" + "="*60)
    print("TEST 2: Luxury Hotels in Dubai (Rating 8+) - Prices in INR")
    print("="*60)
    
    try:
        result = search_accommodations.invoke({
            "location": "Dubai",
            "check_in_date": "2025-12-01",
            "check_out_date": "2025-12-05",
            "adults": 2,
            "children": 0,
            "currency": "INR",  # Changed to INR for all destinations
            "rating": [8, 9],  # Filter for ratings 8-9 (high-end)
            "query": "Luxury hotels in Dubai"
        })
        print(result)
        print("\n✅ Test 2 completed successfully!")
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()

