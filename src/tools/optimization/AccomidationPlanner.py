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


# Helper function to extract clean numeric price
def get_hotel_price(hotel):
    """Get clean numeric price from hotel data"""
    price_info = hotel.get('rate_per_night', {})
    
    if isinstance(price_info, dict):
        # Use extracted_lowest which is already a clean number
        price = price_info.get('extracted_lowest')
        if price is not None and isinstance(price, (int, float)):
            return float(price)
    
    return None


# Helper function to check if hotel has valid price
def has_valid_price(hotel):
    return get_hotel_price(hotel) is not None


def select_budget_hotels(hotels_with_prices, hotels_without_prices, budget_per_night, low_threshold, high_threshold):
    """Budget-focused hotel selection: prioritize affordable options with good ratings"""
    
    budget_hotels = []
    mid_range_hotels = []
    luxury_hotels = []
    
    # Categorize hotels by price thresholds
    for hotel in hotels_with_prices:
        price_val = get_hotel_price(hotel)
        
        if price_val is not None:
            rating = hotel.get('overall_rating', 0)
            rating_val = float(rating) if rating and rating != 'N/A' else 0
            
            if price_val <= low_threshold:
                budget_hotels.append((hotel, price_val, rating_val))
            elif price_val >= high_threshold:
                luxury_hotels.append((hotel, price_val, rating_val))
            else:
                mid_range_hotels.append((hotel, price_val, rating_val))
    
    # Budget strategy: cheapest first, then best rated within same price range
    budget_hotels.sort(key=lambda x: (x[1], -x[2]))  # Price ascending, rating descending
    mid_range_hotels.sort(key=lambda x: (x[1], -x[2]))
    luxury_hotels.sort(key=lambda x: (x[1], -x[2]))
    
    # Selection: prioritize budget hotels (4), fill with mid-range if needed
    selected = [h[0] for h in budget_hotels[:4]]
    if len(selected) < 5:
        selected.extend([h[0] for h in mid_range_hotels[:5-len(selected)]])
    if len(selected) < 5:
        selected.extend([h[0] for h in luxury_hotels[:5-len(selected)]])
    
    # Fill with non-priced hotels if still needed
    if len(selected) < 5:
        needed = 5 - len(selected)
        selected.extend(hotels_without_prices[:needed])
    
    print(f"✅ Budget-focused selection: {len(selected)} hotels chosen")
    return selected[:5]


def select_luxury_hotels(hotels_with_prices, hotels_without_prices, budget_per_night, low_threshold, high_threshold):
    """Luxury-focused hotel selection: prioritize high-end options with top ratings"""
    
    budget_hotels = []
    mid_range_hotels = []
    luxury_hotels = []
    
    # Categorize hotels by price thresholds
    for hotel in hotels_with_prices:
        price_val = get_hotel_price(hotel)
        
        if price_val is not None:
            rating = hotel.get('overall_rating', 0)
            rating_val = float(rating) if rating and rating != 'N/A' else 0
            
            if price_val <= low_threshold:
                budget_hotels.append((hotel, price_val, rating_val))
            elif price_val >= high_threshold:
                luxury_hotels.append((hotel, price_val, rating_val))
            else:
                mid_range_hotels.append((hotel, price_val, rating_val))
    
    # Luxury strategy: best rated first, regardless of price within luxury tier
    budget_hotels.sort(key=lambda x: x[2], reverse=True)  # Best rated first
    mid_range_hotels.sort(key=lambda x: x[2], reverse=True)
    luxury_hotels.sort(key=lambda x: x[2], reverse=True)
    
    print(f"🏨 Hotel categorization: {len(luxury_hotels)} luxury (≥₹{high_threshold:.0f}), {len(mid_range_hotels)} mid-range (₹{low_threshold:.0f}-₹{high_threshold:.0f}), {len(budget_hotels)} budget (≤₹{low_threshold:.0f})")
    
    # Selection: For luxury preference, prioritize highest-priced options regardless of threshold
    selected = [h[0] for h in luxury_hotels[:3]]  # Top 3 true luxury (if any)
    
    # If few luxury hotels, add highest-priced mid-range with top ratings
    if len(selected) < 5:
        # Sort mid-range by price descending for luxury preference (want most expensive)
        mid_range_luxury_sorted = sorted(mid_range_hotels, key=lambda x: (x[1], x[2]), reverse=True)
        selected.extend([h[0] for h in mid_range_luxury_sorted[:5-len(selected)]])
    
    # Only add budget as absolute last resort and only highest-rated ones
    if len(selected) < 5:
        selected.extend([h[0] for h in budget_hotels[:5-len(selected)]])
    
    print(f"✅ Luxury-focused selection: {len(selected)} hotels chosen")
    
    # Fill with non-priced hotels if still needed
    if len(selected) < 5:
        needed = 5 - len(selected)
        selected.extend(hotels_without_prices[:needed])
    
    print(f"✅ Luxury-focused selection: {len(selected)} hotels chosen")
    return selected[:5]


def select_midrange_hotels(hotels_with_prices, hotels_without_prices, budget_per_night, low_threshold, high_threshold):
    """Mid-range hotel selection: balanced approach across all categories"""
    
    budget_hotels = []
    mid_range_hotels = []
    luxury_hotels = []
    
    # Categorize hotels by price thresholds
    for hotel in hotels_with_prices:
        price_val = get_hotel_price(hotel)
        
        if price_val is not None:
            rating = hotel.get('overall_rating', 0)
            rating_val = float(rating) if rating and rating != 'N/A' else 0
            
            if price_val <= low_threshold:
                budget_hotels.append((hotel, price_val, rating_val))
            elif price_val >= high_threshold:
                luxury_hotels.append((hotel, price_val, rating_val))
            else:
                mid_range_hotels.append((hotel, price_val, rating_val))
    
    # Calculate max price for balanced scoring
    all_prices = [get_hotel_price(h) for h in hotels_with_prices if get_hotel_price(h) is not None]
    max_price = max(all_prices) if all_prices else 1
    
    # Mid-range strategy: balanced approach
    budget_hotels.sort(key=lambda x: x[2], reverse=True)  # Best rated budget
    luxury_hotels.sort(key=lambda x: x[2], reverse=True)  # Best rated luxury
    mid_range_hotels.sort(key=lambda x: (x[2] * 0.7 + (1 - x[1]/max_price) * 0.3), reverse=True)  # Balanced score
    
    # Mid-range: truly balanced selection
    selected = []
    selected.extend([h[0] for h in mid_range_hotels[:2]])  # 2 mid-range
    selected.extend([h[0] for h in budget_hotels[:2]])     # 2 budget
    selected.extend([h[0] for h in luxury_hotels[:1]])     # 1 luxury
    if len(selected) < 5:
        # Fill remaining with best available from any category
        all_remaining = []
        all_remaining.extend([h[0] for h in budget_hotels[2:]])
        all_remaining.extend([h[0] for h in mid_range_hotels[2:]])
        all_remaining.extend([h[0] for h in luxury_hotels[1:]])
        selected.extend(all_remaining[:5-len(selected)])
    
    selection_type = "Balanced mix"
    
    # Fill with non-priced hotels if still needed
    if len(selected) < 5:
        needed = 5 - len(selected)
        selected.extend(hotels_without_prices[:needed])
    
    print(f"✅ {selection_type} selection: {len(selected)} hotels chosen")
    return selected[:5]


def calculate_price_thresholds(prices, budget_per_night):
    """Calculate price thresholds based on budget or data percentiles"""
    
    if budget_per_night:
        # Budget-based thresholds
        low_threshold = budget_per_night * 0.8      # 80% of budget
        high_threshold = budget_per_night * 1.5     # 150% of budget
        print(f"💰 Budget-based thresholds: Low ≤₹{low_threshold:.0f} | Mid ₹{low_threshold:.0f}-₹{high_threshold:.0f} | High ≥₹{high_threshold:.0f}")
    else:
        # Data-driven percentile thresholds
        prices_sorted = sorted(prices)
        low_threshold = prices_sorted[len(prices_sorted)//3] if len(prices_sorted) > 2 else min(prices)
        high_threshold = prices_sorted[2*len(prices_sorted)//3] if len(prices_sorted) > 2 else max(prices)
        print(f"💰 Data-driven thresholds: Low ≤₹{low_threshold:.0f} | Mid ₹{low_threshold:.0f}-₹{high_threshold:.0f} | High ≥₹{high_threshold:.0f}")
    
    return low_threshold, high_threshold


@tool
def search_accommodations(location: str, check_in_date: str, check_out_date: str,
                         adults: int = 2, children: int = 0, currency: str = "INR",
                         budget_per_night: int = None, preference_type: str = "mid-range",
                         query: str = None, rating: list = None, max_search_results: int = 20) -> str:
    """
    Search for hotels and accommodations using SERP Google Hotels API with budget-aware and preference-based selection.
    
    **ENHANCED PARAMETERS:**
    - budget_per_night: User's budget per night (INR) - automatically calculates price thresholds
    - preference_type: User's accommodation preference - determines search strategy and selection logic
    
    **PREFERENCE TYPES:**
    1. **"budget"** → Focuses on affordability, hostels, budget hotels
       - Uses all available SERP ratings (7, 8, 9) to maximize options
       - Query: "Budget hotels and hostels in {location}"
       
    2. **"mid-range"** → Balanced comfort and value
       - Balanced selection across price ranges
       - Query: "Hotels in {location}"
       
    3. **"luxury"** → Premium experience, 4-5 star hotels
       - Prioritizes high ratings and luxury amenities
       - Query: "Luxury hotels in {location}"
    
    **BUDGET-BASED LOGIC:**
    - If budget_per_night provided: Uses budget to calculate dynamic price thresholds
      - Budget tier: ≤ budget_per_night * 0.8
      - Mid tier: budget_per_night * 0.8 to budget_per_night * 1.5  
      - Luxury tier: ≥ budget_per_night * 1.5
    - If no budget: Uses data-driven percentile thresholds from search results
    
    **CRITICAL QUERY GUIDELINES:**
    SERP API fails with detailed/long queries. Queries are auto-generated based on preference_type.
    
    Args:
        location: Destination city/location (e.g., "Mumbai", "Dubai", "Paris")
        check_in_date: Check-in date in YYYY-MM-DD format (e.g., "2025-11-25")
        check_out_date: Check-out date in YYYY-MM-DD format (e.g., "2025-11-30")
        adults: Number of adults (default 2)
        children: Number of children (default 0)
        currency: Currency code - Always "INR" (Indian Rupees) for all destinations (default "INR")
        budget_per_night: User's budget per night in INR (e.g., 5000, 10000, 20000)
                         If provided, overrides automatic price threshold calculation
        preference_type: Accommodation preference type (default "mid-range")
                        Options: "budget", "mid-range", "luxury"
        query: Custom search query (optional) - overrides auto-generated query from preference_type
        rating: List of rating values to filter hotels (e.g., [7,8,9] for ratings 7-9)
                Auto-adjusted based on preference_type if not provided:
                - budget: [7,8,9] (good quality, accepts all available ratings)
                - mid-range: [7,8,9] (good quality)
                - luxury: [8,9] (high-end only)
        max_search_results: Maximum number of hotels to examine for selection (default 20)
        
    Returns:
        str: Formatted markdown table with top 5 hotel results optimized for user's budget and preferences
    
    Example Usage:
        >>> # Budget traveler with specific budget
        >>> search_accommodations.invoke({
        ...     "location": "Goa",
        ...     "check_in_date": "2025-11-19", 
        ...     "check_out_date": "2025-11-22",
        ...     "adults": 2,
        ...     "budget_per_night": 3000,
        ...     "preference_type": "budget"
        ... })
        
        >>> # Luxury traveler with high budget
        >>> search_accommodations.invoke({
        ...     "location": "Dubai",
        ...     "check_in_date": "2025-12-01",
        ...     "check_out_date": "2025-12-05", 
        ...     "adults": 2,
        ...     "budget_per_night": 25000,
        ...     "preference_type": "luxury"
        ... })
        
        >>> # Mid-range traveler without specific budget
        >>> search_accommodations.invoke({
        ...     "location": "Bangkok",
        ...     "check_in_date": "2025-12-10",
        ...     "check_out_date": "2025-12-15",
        ...     "adults": 2, 
        ...     "preference_type": "mid-range"
        ... })
    """
    try:
        # Get SERP service
        serp_service = get_serp_api_service()
        
        # Auto-generate query based on preference_type (unless custom query provided)
        if query:
            search_query = query
        else:
            query_mapping = {
                "budget": f"Budget hotels and hostels in {location}",
                "mid-range": f"Hotels in {location}",
                "luxury": f"Luxury hotels in {location}"
            }
            search_query = query_mapping.get(preference_type, f"Hotels in {location}")
        
        # Auto-adjust rating filter based on preference_type (unless custom rating provided)
        if rating is None:
            rating_mapping = {
                "budget": [7, 8, 9],         # All available SERP ratings
                "mid-range": [7, 8, 9],      # Good quality
                "luxury": [8, 9]             # High-end only
            }
            rating = rating_mapping.get(preference_type, [7, 8, 9])
        
        
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
        
        # Get more hotels to examine for better price coverage
        all_properties = hotel_results['properties']
        available_properties = all_properties[:max_search_results] if len(all_properties) >= max_search_results else all_properties
        
        # Separate hotels with and without valid prices
        hotels_with_prices = [hotel for hotel in available_properties if has_valid_price(hotel)]
        hotels_without_prices = [hotel for hotel in available_properties if not has_valid_price(hotel)]
        
        print(f"🏨 Found {len(hotels_with_prices)} hotels with prices, {len(hotels_without_prices)} without prices")
        
        # Extract prices for threshold calculation
        prices = []
        for hotel in hotels_with_prices:
            price_val = get_hotel_price(hotel)
            if price_val is not None:
                prices.append(price_val)
        
        if not prices:
            # No valid pricing data - fallback to rating-based selection
            properties = available_properties[:5]
            print("⚠️ No pricing data - selecting by ratings only")
        else:
            # Calculate price thresholds
            low_threshold, high_threshold = calculate_price_thresholds(prices, budget_per_night)
            
            # Select hotels based on preference type
            if preference_type == "budget":
                properties = select_budget_hotels(hotels_with_prices, hotels_without_prices, budget_per_night, low_threshold, high_threshold)
            elif preference_type == "luxury":
                properties = select_luxury_hotels(hotels_with_prices, hotels_without_prices, budget_per_night, low_threshold, high_threshold)
            else:  # mid-range
                properties = select_midrange_hotels(hotels_with_prices, hotels_without_prices, budget_per_night, low_threshold, high_threshold)
        
        # Build markdown table (always use INR symbol)
        currency_symbol = "₹"  # Always use INR
        
        # Sort final results by price (lowest to highest)
        properties_with_prices = []
        properties_without_prices = []
        
        for hotel in properties:
            price = get_hotel_price(hotel)
            if price is not None:
                properties_with_prices.append((hotel, price))
            else:
                properties_without_prices.append(hotel)
        
        # Sort hotels with prices by price ascending (lowest first)
        properties_with_prices.sort(key=lambda x: x[1])
        
        # Combine: sorted hotels with prices first, then hotels without prices
        sorted_properties = [hotel[0] for hotel in properties_with_prices] + properties_without_prices
        
        output = f"## 🏨 Top 5 Hotel Recommendations\n\n"
        output += f"**Search Query:** {search_query}\n"
        output += f"**Preference:** {preference_type.title()}"
        if budget_per_night:
            output += f" | **Budget:** ₹{budget_per_night:,}/night"
        output += f"\n**Dates:** {check_in_date} to {check_out_date} | **Guests:** {adults} adults"
        if children > 0:
            output += f", {children} children"
        output += "\n\n"
        
        # Create table header
        output += "| # | Hotel Name | Rating | Price/Night | Check-in | Check-out | Amenities | Nearby Places |\n"
        output += "|---|------------|--------|-------------|----------|-----------|-----------|---------------|\n"
        
        # Add hotel rows (exactly 5) - now sorted by price
        for i, hotel in enumerate(sorted_properties, 1):
            # Extract hotel data inline
            name = hotel.get('name', 'N/A').replace('|', '-')
            rating = hotel.get('overall_rating', 'N/A')
            reviews = hotel.get('reviews', 0)
            rating_str = f"{rating} ({reviews} reviews)" if rating != 'N/A' else 'N/A'
            
            # Price (use clean price extraction)
            price_val = get_hotel_price(hotel)
            price_str = f"{currency_symbol}{price_val:,.0f}" if price_val is not None else 'N/A'
            
            # Times and amenities
            check_in_time = hotel.get('check_in_time', 'N/A')
            check_out_time = hotel.get('check_out_time', 'N/A')
            amenities = hotel.get('amenities', [])
            amenities_str = ", ".join([am.replace('|', '-') for am in amenities[:3]]) if amenities else "N/A"
            
            # Nearby places (simplified)
            nearby_places = hotel.get('nearby_places', [])
            if nearby_places:
                nearby_details = []
                for place in nearby_places[:3]:
                    place_name = place.get('name', 'Unknown').replace('|', '-')
                    nearby_details.append(f"• {place_name}")
                nearby_str = "<br>".join(nearby_details)
            else:
                nearby_str = "N/A"
            
            output += f"| {i} | {name} | {rating_str} | {price_str} | {check_in_time} | {check_out_time} | {amenities_str} | {nearby_str} |\n"
        
        # Add simple pricing summary
        properties_with_prices = sum(1 for hotel in properties if has_valid_price(hotel))
        properties_without_prices = len(properties) - properties_with_prices
        
        if properties_without_prices > 0:
            output += f"\n**💡 Pricing Note:** {properties_with_prices} of 5 hotels show prices. {properties_without_prices} hotels have 'N/A' prices - check hotel websites directly.\n"
        else:
            output += f"\n**✅ All 5 hotels show current pricing information.**\n"
        
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
    
    # Test 2: Luxury hotels with budget parameter (INR for international)
    print("\n" + "="*60)
    print("TEST 2: Luxury Hotels in Dubai with Budget (₹25,000/night)")
    print("="*60)
    
    try:
        result = search_accommodations.invoke({
            "location": "Dubai",
            "check_in_date": "2025-12-01",
            "check_out_date": "2025-12-05",
            "adults": 2,
            "children": 0,
            "budget_per_night": 25000,  # ₹25,000 budget
            "preference_type": "luxury"  # Luxury preference
        })
        print(result)
        print("\n✅ Test 2 completed successfully!")
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Budget hotels with specific budget
    print("\n" + "="*60)
    print("TEST 3: Budget Hotels in Goa (₹3,000/night budget)")
    print("="*60)
    
    try:
        result = search_accommodations.invoke({
            "location": "Goa",
            "check_in_date": "2025-11-19",
            "check_out_date": "2025-11-22",
            "adults": 2,
            "children": 0,
            "budget_per_night": 3000,   # ₹3,000 budget
            "preference_type": "budget"  # Budget preference
        })
        print(result)
        print("\n✅ Test 3 completed successfully!")
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Comfort preference without budget
    # print("\n" + "="*60)
    # print("TEST 4: Comfort Hotels in Bangkok (No specific budget)")
    # print("="*60)
    
    # try:
    #     result = search_accommodations.invoke({
    #         "location": "Bangkok",
    #         "check_in_date": "2025-12-20",
    #         "check_out_date": "2025-12-25",
    #         "adults": 2,
    #         "children": 0,
    #         "preference_type": "comfort"  # Comfort preference
    #     })
    #     print(result)
    #     print("\n✅ Test 4 completed successfully!")
    # except Exception as e:
    #     print(f"❌ Error occurred: {str(e)}")
    #     import traceback
    #     traceback.print_exc()

