import os
import traceback
from typing import List, Dict, Any, Optional
from serpapi import GoogleSearch
from dotenv import load_dotenv
load_dotenv()

class SerpAPIService:
    """
    A service class for interacting with SerpAPI for various search operations.
    
    This class provides methods for searching flights, location images, and other
    search functionalities using the SerpAPI service.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the SerpAPI service with an API key.
        
        Args:
            api_key (str): The SerpAPI key. If not provided, will try to load from environment variable.
        """
        self.api_key = api_key 
        if not self.api_key:
            raise ValueError("SerpAPI key is required. Provide it as parameter or set SERP_API_KEY environment variable.")
    
    def search_flights(self, departure_id: str, arrival_id: str, outbound_date: str,
                      country_code: str, currency: str, return_date: Optional[str] = None, 
                      language: Optional[str] = None, type: Optional[str] = None,gl: Optional[str] = None,
                      multi_city_json: Optional[str] = None, travel_class: Optional[str] = None,
                      adults: Optional[int] = None, children: Optional[int] = None, 
                      infants_in_seat: Optional[int] = None, infants_on_lap: Optional[int] = None, 
                      sort_by: Optional[str] = None, stops: Optional[str] = None, 
                      exclude_airlines: Optional[str] = None, include_airlines: Optional[str] = None, 
                      bags: Optional[int] = None, max_price: Optional[str] = None, 
                      outbound_times: Optional[str] = None, return_times: Optional[str] = None, 
                      emissions: Optional[str] = None, layover_duration: Optional[str] = None, 
                      exclude_conns: Optional[str] = None, max_duration: Optional[str] = None,
                      departure_token: Optional[str] = None, booking_token: Optional[str] = None, 
                      show_hidden: Optional[str] = None, exclude_basic: Optional[str] = None, 
                      deep_search: Optional[str] = None, no_cache: Optional[str] = None, 
                      async_search: Optional[str] = None, zero_trace: Optional[str] = None, 
                      output: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for flights using Google Flights engine.
        
        Mandatory Args:
            departure_id (str): Departure airport code or location kgmid
            arrival_id (str): Arrival airport code or location kgmid  
            outbound_date (str): Outbound date in YYYY-MM-DD format
            country_code (str): Country code for search ('in' for Indian flights, 'us' for International flights)
            currency (str): Currency code (e.g., "USD", "INR")
            
        Optional Args:
            return_date (Optional[str]): Return date in YYYY-MM-DD format for round trips
            language (Optional[str]): Language code (e.g., "en") - defaults to 'en' if not provided
            type (Optional[str]): Flight type: 1-Round trip, 2-One way, 3-Multi-city - defaults to 2 (One way)
            multi_city_json (Optional[str]): JSON string for multi-city flights
            travel_class (Optional[str]): 1-Economy, 2-Premium economy, 3-Business, 4-First
            adults (Optional[int]): Number of adults
            children (Optional[int]): Number of children
            infants_in_seat (Optional[int]): Number of infants in seat
            infants_on_lap (Optional[int]): Number of infants on lap
            sort_by (Optional[str]): 1-Top flights, 2-Price, 3-Departure, etc.
            stops (Optional[str]): 0-Any, 1-Nonstop, 2-One stop or fewer, 3-Two stops or fewer
            exclude_airlines (Optional[str]): Comma-separated airline codes to exclude
            include_airlines (Optional[str]): Comma-separated airline codes to include
            bags (Optional[int]): Number of carry-on bags
            max_price (Optional[str]): Maximum ticket price
            outbound_times (Optional[str]): Outbound time range (HH format)
            return_times (Optional[str]): Return time range (HH format)
            emissions (Optional[str]): 1-Less emissions only
            layover_duration (Optional[str]): Min,max layover in minutes
            exclude_conns (Optional[str]): Exclude specific connecting airports
            max_duration (Optional[str]): Max flight duration in minutes
            departure_token (Optional[str]): Token for next leg or return flights
            booking_token (Optional[str]): Token to get booking options
            show_hidden (Optional[str]): Include hidden results
            exclude_basic (Optional[str]): Exclude basic fares (US only)
            deep_search (Optional[str]): Enable deep search
            no_cache (Optional[str]): Force fresh results
            async_search (Optional[str]): Async search
            zero_trace (Optional[str]): Enterprise mode, no trace
            output (Optional[str]): Output format: json or html
            
        Returns:
            Dict[str, Any]: Flight search results
        """
        # Build mandatory parameters with hardcoded defaults
        params = {
            "engine": "google_flights",
            "departure_id": departure_id,
            "arrival_id": arrival_id,
            "outbound_date": outbound_date,
            "api_key": self.api_key,
            "type": type if type is not None else "2",  # Default to one-way (2)
            "hl": language if language is not None else "en",  # Default to English
            "gl": country_code,  # 'in' for Indian flights, 'us' for International flights
            "currency": currency,
        }
        
        # Add optional parameters if provided
        optional_params = {
            "return_date": return_date,            
            "multi_city_json": multi_city_json,
            "travel_class": travel_class,
            "adults": adults,
            "children": children,
            "infants_in_seat": infants_in_seat,
            "infants_on_lap": infants_on_lap,
            "sort_by": sort_by,
            "stops": stops,
            "exclude_airlines": exclude_airlines,
            "include_airlines": include_airlines,
            "bags": bags,
            "max_price": max_price,
            "outbound_times": outbound_times,
            "return_times": return_times,
            "emissions": emissions,
            "layover_duration": layover_duration,
            "exclude_conns": exclude_conns,
            "max_duration": max_duration,
            "departure_token": departure_token,
            "booking_token": booking_token,
            "show_hidden": show_hidden,
            "exclude_basic": exclude_basic,
            "deep_search": deep_search,
            "no_cache": no_cache,
            "async": async_search,
            "zero_trace": zero_trace,
            "output": output
        }
        
        # Filter out None values and merge with mandatory params
        filtered_optional = {k: v for k, v in optional_params.items() if v is not None}
        params.update(filtered_optional)
        
        search = GoogleSearch(params)
        results = search.get_dict()
        return results
    
    def search_location_images(self, location: str, image_type: str = "photo", 
                             safe: str = "active", no_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Search Google Images for a given location or itinerary, excluding social media sites.

        Args:
            location (str): The location or itinerary to search for.
            image_type (str, optional): Type of image to search. Defaults to "photo".
            safe (str, optional): Safe search mode ("active" or "off"). Defaults to "active".
            no_cache (bool, optional): Disable cache for fresh results. Defaults to True.

        Returns:
            List[Dict[str, Any]]: List of image result dictionaries.
        """
        # Construct the query string with social media exclusions
        query = f"{location} -site:instagram.com -site:facebook.com -site:twitter.com -site:threads.com"

        params = {
            "q": query,
            "engine": "google_images",
            "ijn": "0",
            "api_key": self.api_key,
            "safe": safe,
            "image_type": image_type,
            "no_cache": str(no_cache).lower()
        }

        search = GoogleSearch(params)
        results = search.get_dict()
        return results.get("images_results", [])
    
    def search_buses(self, from_location: str, to_location: str, departure_date: str,
                    country_code: str = "in", language: str = "en") -> Dict[str, Any]:
        """
        Search for bus routes and schedules using SerpAPI Google Search.
        
        Args:
            from_location: Departure city/location
            to_location: Destination city/location  
            departure_date: Date in YYYY-MM-DD format
            country_code: Country code (default "in" for India)
            language: Language code (default "en")
            
        Returns:
            Dict containing bus search results
        """
        try:
            # Format the search query for bus booking websites
            query = f"{from_location} to {to_location} bus {departure_date} redbus makemytrip abhibus"
            
            params = {
                "engine": "google",
                "q": query,
                "api_key": self.api_key,
                "gl": country_code,
                "hl": language,
                "num": 3  # Get more results to find bus booking sites
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            return results
            
        except Exception as e:
            print(f"Bus search error: {e}")
            return {"error": str(e)}


# Example usage
if __name__ == "__main__":
    # Initialize with API key (can be provided directly or loaded from environment)
    API_KEY = "81a7d4fd3ef75f706da83b81e981e8eaeb9831453cb5ec0e4d1de003314fd7f3"
    serp_service = SerpAPIService(api_key=API_KEY)
    
    # Test location images search
    location_name = "Mandalpatti Peak"
    # images = serp_service.search_location_images(location_name)
    
    # print(f"Found {len(images)} images for {location_name}:")
    # for idx, img in enumerate(images[:5]):  # Print first 5 images
    #     print(f"{idx+1}. {img.get('title', 'No title')}: {img.get('original', 'No URL')}")
    
    # # Test flight search with basic parameters
    # print("\nTesting basic flight search:")
    # try:
    #     flights = serp_service.search_flights(
    #         departure_id="BOM",  # Mumbai
    #         arrival_id="DEL",    # Delhi
    #         outbound_date="2025-12-15",
    #         return_date="2025-12-18",
    #         currency="INR",
    #         language="en"
    #     )
    #     print(f"Basic flight search completed. Found results: {len(flights.get('best_flights', []))}")
    # except Exception as e:
    #     print(f"Basic flight search error: {e}")
    
    # Test flight search with advanced parameters
    print("\nTesting advanced flight search:")
    try:
        advanced_flights = serp_service.search_flights(
            departure_id="BLR",  # Goa
            arrival_id="HYD",    # Mumbai
            outbound_date="2025-10-30",
            country_code="in",   # India (mandatory)
            currency="INR",      # Currency (mandatory)
            language="en",       # Optional, defaults to 'en'
            type="2",            # One way
            # travel_class="1",    # Economy
            adults=1,            # 1 adult
            # sort_by="2",         # Sort by price     # Force fresh results
            no_cache="true"      # Force fresh results  
        )
        print(advanced_flights.keys())
        # Check for flight results in different possible keys
        flight_results = []
        result_source = ""
        
        if 'best_flights' in advanced_flights and advanced_flights['best_flights']:
            flight_results = advanced_flights['best_flights']
            result_source = "best_flights"
        elif 'other_flights' in advanced_flights and advanced_flights['other_flights']:
            flight_results = advanced_flights['other_flights']
            result_source = "other_flights"
        elif 'flights' in advanced_flights and advanced_flights['flights']:
            flight_results = advanced_flights['flights']
            result_source = "flights"
        
        print(f"Advanced flight search completed.")
        print(f"Found {len(flight_results)} results in '{result_source}'")
        
        # Display first 3 results with key information
        if flight_results:
            print(f"\nFirst 3 flight options:")
            for i, flight in enumerate(flight_results[:3]):
                if 'flights' in flight and len(flight['flights']) > 0:
                    main_flight = flight['flights'][0]
                    departure_time = main_flight['departure_airport']['time']
                    arrival_time = main_flight['arrival_airport']['time']
                    airline = main_flight['airline']
                    flight_num = main_flight['flight_number']
                    duration = flight['total_duration']
                    price = flight['price']
                    
                    print(f"{i+1}. {airline} {flight_num}")
                    print(f"   {departure_time} → {arrival_time} ({duration} min)")
                    print(f"   Price: ₹{price}")
        else:
            print("No flight results found")
            print(f"Available response keys: {list(advanced_flights.keys())}")
            
    except Exception as e:
        print(f"Advanced flight search error: {e}")

    