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
            "sort_by": 2
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
        # print("\n🌐 DEBUG - SERP API FLIGHT SEARCH:")
        # print(f"   Params: {params}")
        # print(f"   Results: {results}")
        # if 'error' in results:
        #     print(f"   SERP API ERROR: {results['error']}")
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
    
    def search_hotels(self, query: str, check_in_date: str, check_out_date: str,
                     currency: str, country_code: str = "in",
                     adults: Optional[int] = None, children: Optional[int] = None,
                     language: Optional[str] = None, vacation_rentals: Optional[str] = None,
                     sort_by: Optional[List[int]] = None, max_price: Optional[str] = None,
                     min_price: Optional[str] = None, property_types: Optional[str] = None,
                     rating: Optional[str] = None,
                     amenities: Optional[str] = None, hotel_class: Optional[str] = None,
                     free_cancellation: Optional[str] = None, no_cache: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for hotels and accommodations using SerpAPI Google Hotels engine.
        
        Mandatory Args:
            query (str): Search query for hotels (can be a city name like "Mumbai" or a full query like "hotels under 2000rs per night in Mumbai")
            check_in_date (str): Check-in date in YYYY-MM-DD format
            check_out_date (str): Check-out date in YYYY-MM-DD format
            currency (str): Currency code (e.g., "INR", "USD")
            country_code (str): Country code (default "in" for India)
            
        Optional Args:
            adults (Optional[int]): Number of adults - defaults to 2 if not provided
            children (Optional[int]): Number of children
            language (Optional[str]): Language code (e.g., "en") - defaults to 'en' if not provided
            vacation_rentals (Optional[str]): Include vacation rentals ("true"/"false") - defaults to "true"
            sort_by (Optional[List[int]]): Sort criteria list [13-Rating, 3-Price, 8-Distance, 9-Popularity] - defaults to [3] (Price)
            max_price (Optional[str]): Maximum price filter
            min_price (Optional[str]): Minimum price filter
            property_types (Optional[str]): Filter by property types - defaults to [12,13,14,17] (all types)
            amenities (Optional[str]): Filter by amenities (e.g., "wifi,pool,parking")
            hotel_class (Optional[str]): Filter by star rating (e.g., "2,3,4,5")
            free_cancellation (Optional[str]): Filter for free cancellation ("true"/"false")
            no_cache (Optional[str]): Force fresh results ("true"/"false") - defaults to "true"
            rating (Optional[str]): Filter by hotel rating (e.g., "2,3,4,5")

        Returns:
            Dict[str, Any]: Hotel search results with properties, prices, ratings, amenities
        """
        try:
            # Debug: Print what's being sent to SERP API
            print(f"\n🌐 DEBUG - SERP API Call:")
            print(f"   Query: '{query}'")
            
            # Build mandatory parameters with hardcoded defaults
            params = {
                "engine": "google_hotels",
                "q": query,
                "check_in_date": check_in_date,
                "check_out_date": check_out_date,
                "currency": currency,
                "gl": country_code,
                "api_key": self.api_key,
                # "property_types": ["12","13","14","17"],  # All property types
                "hl": language if language is not None else "en",  # Default to English
                "adults": adults if adults is not None else 2,  # Default to 2 adults
                # "vacation_rentals": vacation_rentals if vacation_rentals is not None else "true",  # Default to true
                "no_cache": "true",  # Default to true
                # "sort_by": sort_by if sort_by is not None else [3],  # Default to sort by price
            }
            
            # Add optional parameters if provided
            optional_params = {
                "children": str(children) if children is not None else None,
                "max_price": max_price,
                "min_price": min_price,
                "amenities": amenities,
                "rating": rating,
                "hotel_class": hotel_class,
                "free_cancellation": free_cancellation
            }
            
            # Filter out None values and merge with mandatory params
            filtered_optional = {k: v for k, v in optional_params.items() if v is not None}
            params.update(filtered_optional)
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            return results
            
        except Exception as e:
            print(f"Hotel search error: {e}")
            traceback.print_exc()
            return {"error": str(e)}


# Example usage
if __name__ == "__main__":
    # Initialize with API key (can be provided directly or loaded from environment)
    API_KEY = "eaa4969cb04c9844cd8700553f7cd5ce55f09c2ca32eda56a7e3b5dc776be386"
    serp_service = SerpAPIService(api_key=API_KEY)
    
    # Test location images search
    # location_name = "Mandalpatti Peak"
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
            for i, flight in enumerate(flight_results[:10]):
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

    # Test hotel search
    # print("\nTesting hotel search:")
    # try:
    #     hotel_results = serp_service.search_hotels(
    #         query="Budget hotels in Mumbai",
    #         check_in_date="2025-11-19",
    #         check_out_date="2025-11-22",
    #         currency="INR",
    #         country_code="in",  # Mandatory
    #         adults=1,           # Optional, defaults to 2
    #         language="en",      # Optional, defaults to 'en'
    #         rating="8",
    #         sort_by="3",
    #         no_cache="true"      # Optional, defaults to "true"
    #     )
        
    #     print("="*80)
    #     print("HOTEL SEARCH RESULTS")
    #     print("="*80)
        
    #     # Check if there's an error first
    #     if 'error' in hotel_results:
    #         print(f"\nERROR: {hotel_results['error']}")
    #     else:
    #         # Check what keys are actually in the results
    #         print(f"\nAvailable keys in results: {list(hotel_results.keys())}")
            
    #         # Extract properties (hotels)
    #         if 'properties' in hotel_results and hotel_results['properties']:
    #             properties = hotel_results['properties']  # Get top 5
    #             print(f"\nFOUND {len(hotel_results['properties'])} HOTELS")
    #             print(f"\nTOP 5 HOTELS:")
                
    #             for i, hotel in enumerate(properties, 1):
    #                 name = hotel.get('name', 'No name')
    #                 price = hotel.get('total_rate', {}).get('lowest', 'N/A')
    #                 rating = hotel.get('overall_rating', 'N/A')
    #                 reviews = hotel.get('reviews', 0)
    #                 hotel_class = hotel.get('hotel_class', 'N/A')
    #                 link = hotel.get('link', 'No link')
                    
    #                 print(f"\n{i}. {name}")
    #                 print(f"   Price: ₹{price}")
    #                 print(f"   Rating: {rating} ({reviews} reviews)")
    #                 print(f"   Class: {hotel_class} star")
    #                 print(f"   Link: {link}")
                    
    #                 # Show amenities if available
    #                 if 'amenities' in hotel:
    #                     amenities = hotel['amenities'][:5]  # First 5 amenities
    #                     print(f"   Amenities: {', '.join(amenities)}")
    #         else:
    #             print("\nNo properties found in results")
                
    #         # Check for search metadata
    #         if 'search_metadata' in hotel_results:
    #             metadata = hotel_results['search_metadata']
    #             print(f"\nSearch completed in: {metadata.get('total_time_taken', 'N/A')}s")
        
    #     print("\n" + "="*80)
    #     print("END OF HOTEL SEARCH")
    #     print("="*80)
                
    # except Exception as e:
    #     print(f"Hotel search error: {e}")
    #     print(f"Error details: {traceback.format_exc()}")