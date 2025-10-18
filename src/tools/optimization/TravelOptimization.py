import os
import json
import sys
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

# Add project root to path for standalone execution
if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from src.entity.travel_search_params import TravelSearchParams
from src.utils.service_initializer import get_perplexity_service, get_serp_api_service
from langchain.tools import tool


def _extract_flight_details(flight_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract clean, structured flight details for easy table formatting.
    
    Returns:
        Dict with: airline, departure_time, arrival_time, duration_minutes, price, carbon_grams
    """
    try:
        main_flight = flight_data.get('flights', [{}])[0]
        
        # Extract airline names from all flight segments
        airline_names = ', '.join([
            f.get('airline', 'Unknown') 
            for f in flight_data.get('flights', [])
        ])
        
        # Extract departure time (multiple fallback options)
        departure_time = (
            main_flight.get('departure_airport', {}).get('time')
            or main_flight.get('departure_time')
            or main_flight.get('departure_time_utc')
            or "N/A"
        )
        
        # Extract arrival time (multiple fallback options)
        arrival_time = (
            main_flight.get('arrival_airport', {}).get('time')
            or main_flight.get('arrival_time')
            or main_flight.get('arrival_time_utc')
            or "N/A"
        )
        
        # Extract duration in minutes
        duration_minutes = (
            main_flight.get('duration')
            or flight_data.get('total_duration')
            or 0
        )
        
        # Extract price (per person)
        price = flight_data.get('price', 0)
        
        # Extract carbon emissions in grams
        carbon_grams = flight_data.get('carbon_emissions', {}).get('this_flight', 0)
        
        return {
            'airline': airline_names,
            'departure_time': departure_time,
            'arrival_time': arrival_time,
            'duration_minutes': duration_minutes,
            'price_per_person': price,
            'carbon_grams': carbon_grams
        }
    except Exception as e:
        return {
            'airline': 'Unknown',
            'departure_time': 'N/A',
            'arrival_time': 'N/A',
            'duration_minutes': 0,
            'price_per_person': 0,
            'carbon_grams': 0,
            'parse_error': str(e)
        }


def _search_flights_with_serp(params: TravelSearchParams) -> Dict[str, Any]:
    """
    Search flights using SERP API for both outbound and return journeys.
    Returns structured, table-ready flight data for easy agent formatting.
    """
    try:
        serp_service = get_serp_api_service()
        
        # Use airport codes from params (agent should provide these)
        origin_airport = params.origin_airport or params.origin
        dest_airport = params.destination_airport or params.destination
        
        results = {
            'provider': 'serp_api',
            'transport_mode': 'flight',
            'success': True,
            'outbound_flights': [],
            'return_flights': [],
            'error': None,
            'route_info': {
                'origin': params.origin,
                'destination': params.destination,
                'origin_airport': origin_airport,
                'destination_airport': dest_airport
            }
        }
        
        # Search outbound flights
        print(f"Searching flights: {params.origin}({origin_airport}) -> {params.destination}({dest_airport})")
        outbound_results = serp_service.search_flights(
            departure_id=origin_airport,
            arrival_id=dest_airport,
            outbound_date=params.departure_date,
            country_code="in" if params.is_domestic else "us",
            currency=params.currency,
            adults=params.travelers
        )
        
        # Extract structured outbound flight details (top 5 options)
        if isinstance(outbound_results, dict) and 'best_flights' in outbound_results:
            for flight in outbound_results['best_flights'][:5]:
                flight_details = _extract_flight_details(flight)
                results['outbound_flights'].append(flight_details)
        
        # Search return flights if needed
        if params.trip_type == "round_trip" and params.return_date:
            print(f"Searching return flights: {params.destination}({dest_airport}) -> {params.origin}({origin_airport})")
            return_results = serp_service.search_flights(
                departure_id=dest_airport,
                arrival_id=origin_airport,
                outbound_date=params.return_date,
                country_code="in" if params.is_domestic else "us",
                currency=params.currency,
                adults=params.travelers
            )
            
            # Extract structured return flight details (top 5 options)
            if isinstance(return_results, dict) and 'best_flights' in return_results:
                for flight in return_results['best_flights'][:5]:
                    flight_details = _extract_flight_details(flight)
                    results['return_flights'].append(flight_details)
        
        return results
        
    except Exception as e:
        return {
            'provider': 'serp_api',
            'transport_mode': 'flight', 
            'success': False,
            'error': str(e),
            'outbound_flights': [],
            'return_flights': []
        }


def _extract_ground_transport_details_with_ai(raw_text: str, transport_type: str, travelers: int, currency: str) -> List[Dict[str, Any]]:
    """
    Extract structured ground transport details from Perplexity raw text using Gemini.
    
    Returns:
        List of dicts with: operator, service_type, departure_time, arrival_time, duration_minutes, price_per_person, platform
    """
    try:
        from src.utils.service_initializer import get_gemini_client
        client = get_gemini_client()
        
        extraction_prompt = f"""
        TASK: Extract {transport_type} information from the text into structured JSON array.
        
        RAW TEXT:
        {raw_text[:3000]}
        
        Extract each {transport_type} option into this exact format:
        [
          {{
            "operator": "Train Name/Number OR Bus Operator Name",
            "service_type": "Class (1A/2A/3A/Sleeper) OR Bus Type (AC/Non-AC/Sleeper/Volvo)",
            "departure_time": "HH:MM (24-hour format)",
            "arrival_time": "HH:MM (24-hour format)",
            "duration_minutes": 920,
            "price_per_person": 2500.0,
            "platform": "IRCTC/RedBus/etc"
          }}
        ]
        
        RULES:
        - Extract 5-8 best options
        - Convert duration to total minutes (e.g., "15h 20m" → 920)
        - Use mid-range class pricing for trains (2A or 3A)
        - For buses, use typical AC sleeper pricing
        - Times in 24-hour format (e.g., "17:00", "08:30")
        - If price range given, use middle value
        - Currency: {currency}
        
        Return ONLY the JSON array, no other text.
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=extraction_prompt
        )
        
        response_text = response.text.strip()
        
        # Clean JSON response
        if response_text.startswith('```json'):
            response_text = response_text.replace('```json', '').replace('```', '').strip()
        elif response_text.startswith('```'):
            response_text = response_text.replace('```', '').strip()
        
        # Parse JSON
        extracted_data = json.loads(response_text)
        
        return extracted_data if isinstance(extracted_data, list) else []
        
    except Exception as e:
        print(f"⚠️ AI extraction failed for {transport_type}: {e}")
        return []


def _search_ground_transport_with_perplexity(params: TravelSearchParams, modes: List[str]) -> Dict[str, Any]:
    """
    Search buses and trains using Perplexity, then extract structured data.
    Returns table-ready format like flights.
    """
    try:
        perplexity_service = get_perplexity_service()
        
        results = {
            'provider': 'perplexity',
            'transport_modes': modes,
            'success': True,
            'outbound_trains': [],
            'return_trains': [],
            'outbound_buses': [],
            'return_buses': [],
            'error': None,
            'route_info': {
                'origin': params.origin,
                'destination': params.destination
            }
        }
        
        # Search trains if requested
        if 'train' in modes:
            train_query = f"""
            Find train options from {params.origin} to {params.destination} 
            on {params.departure_date} for {params.travelers} travelers.
            Budget: {params.currency} {params.budget_limit if params.budget_limit else 'flexible'}.
            
            {"Also find return train options from " + params.destination + " to " + params.origin + " on " + params.return_date + "." if params.trip_type == "round_trip" and params.return_date else ""}
            
            Provide 5-8 best train options with:
            - Train name and number
            - Departure and arrival times (with stations)
            - Journey duration
            - Available classes with prices (1A, 2A, 3A, Sleeper)
            - Booking platforms
            
            Be specific with actual train numbers and realistic pricing.
            """
            
            train_system_prompt = """
            You are a train search assistant for Indian Railways. Provide detailed train information:
            
            1. Train name and number (e.g., "Rajdhani Express 12951")
            2. Departure station and time (e.g., "Mumbai Central - 17:00")
            3. Arrival station and time (e.g., "New Delhi - 08:35 next day")
            4. Journey duration (e.g., "15h 35m")
            5. Class-wise pricing: 1A, 2A, 3A, Sleeper
            6. Booking platforms
            
            List actual trains with real train numbers. Be specific and detailed.
            """
            
            train_raw = perplexity_service.search(
                query=train_query,
                system_prompt=train_system_prompt,
                temperature=0.1
            )
            
            # Extract structured data from raw text
            trains_structured = _extract_ground_transport_details_with_ai(
                train_raw, 'train', params.travelers, params.currency
            )
            
            # Split into outbound and return based on count
            if trains_structured:
                mid_point = len(trains_structured) // 2
                results['outbound_trains'] = trains_structured[:mid_point] if params.trip_type == "round_trip" else trains_structured
                results['return_trains'] = trains_structured[mid_point:] if params.trip_type == "round_trip" and mid_point > 0 else []
        
        # Search buses if requested
        if 'bus' in modes:
            bus_query = f"""
            Find bus options from {params.origin} to {params.destination} 
            on {params.departure_date} for {params.travelers} travelers.
            Budget: {params.currency} {params.budget_limit if params.budget_limit else 'flexible'}.
            
            {"Also find return bus options from " + params.destination + " to " + params.origin + " on " + params.return_date + "." if params.trip_type == "round_trip" and params.return_date else ""}
            
            Provide 5-8 best bus options with:
            - Operator names (KSRTC, MSRTC, VRL, SRS, RedBus partners)
            - Bus types (AC Sleeper, Non-AC Sleeper, Volvo, Semi-Sleeper)
            - Departure and arrival times
            - Journey duration
            - Pricing per seat
            - Booking platforms
            
            For long routes, include overnight sleeper buses. Be specific with actual operators.
            """
            
            bus_system_prompt = """
            You are a bus travel search assistant for India. Provide detailed bus information:
            
            1. Operator name (e.g., "VRL Travels", "MSRTC", "SRS Travels")
            2. Bus type (e.g., "AC Sleeper", "Volvo Multi-axle", "Non-AC Seater")
            3. Departure time and point (e.g., "20:00 from Dadar")
            4. Arrival time and point (e.g., "08:00 at Kashmere Gate")
            5. Journey duration (e.g., "24h 30m")
            6. Price per seat
            7. Booking platform (RedBus, AbhiBus, etc.)
            
            List actual operators with realistic pricing. Be specific and detailed.
            """
            
            bus_raw = perplexity_service.search(
                query=bus_query,
                system_prompt=bus_system_prompt,
                temperature=0.1
            )
            
            # Extract structured data from raw text
            buses_structured = _extract_ground_transport_details_with_ai(
                bus_raw, 'bus', params.travelers, params.currency
            )
            
            # Split into outbound and return
            if buses_structured:
                mid_point = len(buses_structured) // 2
                results['outbound_buses'] = buses_structured[:mid_point] if params.trip_type == "round_trip" else buses_structured
                results['return_buses'] = buses_structured[mid_point:] if params.trip_type == "round_trip" and mid_point > 0 else []
        
        return results
        
    except Exception as e:
        return {
            'provider': 'perplexity',
            'transport_modes': modes,
            'success': False,
            'error': str(e),
            'outbound_trains': [],
            'return_trains': [],
            'outbound_buses': [],
            'return_buses': []
        }


@tool
def travel_search_tool(origin: str, destination: str, departure_date: str, 
                      transport_modes: List[str], travelers: int = 1,
                      return_date: str = None, budget_limit: float = None, 
                      currency: str = "INR", origin_airport: str = None,
                      destination_airport: str = None, is_domestic: bool = True,
                      trip_type: str = "round_trip") -> str:
    """
    Unified travel search tool with direct parameters.
    
    Works for both:
    - Agent usage: Agent passes extracted parameters directly
    - Direct testing: Simple parameter interface for testing
    
    Args:
        origin: Origin city/location
        destination: Destination city/location
        departure_date: Departure date (YYYY-MM-DD)
        transport_modes: List of transport modes ["flight", "bus", "train"]
        travelers: Number of travelers
        return_date: Return date for round trips
        budget_limit: Budget limit
        currency: Currency code (USD, INR, etc.)
        origin_airport: Airport code resolved by agent (optional)
        destination_airport: Airport code resolved by agent (optional) 
        is_domestic: Whether route is domestic
        trip_type: "round_trip" or "one_way"
        
    Returns:
        JSON string with search results
        
    Example Agent Usage:
        results = travel_search_tool(
            origin="Mumbai", destination="Delhi", 
            departure_date="2024-12-01", return_date="2024-12-05",
            transport_modes=["flight", "train"], travelers=2,
            budget_limit=15000, currency="INR", 
            origin_airport="BOM", destination_airport="DEL",
            is_domestic=True
        )
        
    Example Direct Testing:
        results = travel_search_tool(
            origin="Mumbai", destination="Delhi",
            departure_date="2024-12-01", 
            transport_modes=["flight"], travelers=1
        )
    """
    try:
        # Create TravelSearchParams from direct parameters
        params = TravelSearchParams(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            travelers=travelers,
            budget_limit=budget_limit,
            currency=currency,
            transport_modes=transport_modes,
            trip_type=trip_type,
            is_domestic=is_domestic,
            is_international=not is_domestic,
            origin_airport=origin_airport,
            destination_airport=destination_airport
        )
        
        # Validate parameters
        validation_errors = params.validate()
        if validation_errors:
            raise ValueError(f"Invalid parameters: {', '.join(validation_errors)}")
        
        # Initialize results container
        search_results = {
            'search_params': params.__dict__,
            'results': {},
            'summary': {
                'providers_used': [],
                'transport_modes_searched': [],
                'search_success': True
            }
        }
        
        # Search flights with SERP if requested
        if "flight" in params.transport_modes and params.use_serp_for_flights:
            print("Searching flights with SERP API...")
            flight_results = _search_flights_with_serp(params)
            search_results['results']['flights'] = flight_results
            search_results['summary']['providers_used'].append('serp_api')
            search_results['summary']['transport_modes_searched'].append('flight')
            
            if not flight_results['success']:
                print(f"Flight search failed: {flight_results['error']}")
        
        # Search ground transport with Perplexity if requested
        ground_modes = [mode for mode in params.transport_modes if mode in ['bus', 'train']]
        if ground_modes and params.use_perplexity_for_ground:
            print(f"Searching {', '.join(ground_modes)} with Perplexity...")
            ground_results = _search_ground_transport_with_perplexity(params, ground_modes)
            search_results['results']['ground_transport'] = ground_results
            search_results['summary']['providers_used'].append('perplexity')
            search_results['summary']['transport_modes_searched'].extend(ground_modes)
            
            if not ground_results['success']:
                print(f"Ground transport search failed: {ground_results['error']}")
        
        return json.dumps(search_results, indent=2, default=str)
        
    except Exception as e:
        # Simple error handling as requested
        raise Exception(f"Travel search failed: {str(e)}")


# For testing
if __name__ == "__main__":
    print("Testing Unified Travel Search Tool...")
    
    try:
        test_result = travel_search_tool.invoke({
            "origin": "Mumbai",
            "destination": "Delhi",
            "origin_airport": "BOM",
            "destination_airport": "DEL",
            "departure_date": "2025-12-01",
            "transport_modes": ["flight", "train", "bus"],
            "travelers": 2,
            "return_date": "2025-12-05",
            "budget_limit": 35000,
            "currency": "INR",
            "is_domestic": True
        })
        
        print("✅ Test successful!")
        print("\n" + "="*80)
        print("SEARCH RESULTS (Structured Format)")
        print("="*80)
        
        results = json.loads(test_result)

        # ------------------ FLIGHT RESULTS ------------------
        if 'flights' in results.get('results', {}):
            flights = results['results']['flights']
            print("\n🛫 FLIGHT OPTIONS:")
            print("-"*80)
            
            if flights.get('success'):
                route_info = flights.get('route_info', {})
                departure_date = results.get('search_params', {}).get('departure_date', '')
                return_date = results.get('search_params', {}).get('return_date', '')
                
                # Outbound flights (now pre-structured)
                if flights.get('outbound_flights'):
                    print(f"\n📤 Outbound Journey: {route_info.get('origin')} → {route_info.get('destination')} ({departure_date})")
                    print(f"{'#':<4} {'Airline':<20} {'Departure':<12} {'Arrival':<12} {'Duration':<10} {'Price':<12}")
                    print("-"*80)
                    
                    for idx, flight in enumerate(flights['outbound_flights'], 1):
                        airline = flight.get('airline', 'Unknown')[:19]
                        departure = flight.get('departure_time', 'N/A')
                        arrival = flight.get('arrival_time', 'N/A')
                        duration_min = flight.get('duration_minutes', 0)
                        duration = f"{duration_min//60}h {duration_min%60}m" if duration_min else "N/A"
                        price = flight.get('price_per_person', 0)
                        
                        print(f"{idx:<4} {airline:<20} {departure:<12} {arrival:<12} {duration:<10} ₹{price:>9,.0f}")
                
                # Return flights (now pre-structured)
                if flights.get('return_flights'):
                    print(f"\n📥 Return Journey: {route_info.get('destination')} → {route_info.get('origin')} ({return_date})")
                    print(f"{'#':<4} {'Airline':<20} {'Departure':<12} {'Arrival':<12} {'Duration':<10} {'Price':<12}")
                    print("-"*80)
                    
                    for idx, flight in enumerate(flights['return_flights'], 1):
                        airline = flight.get('airline', 'Unknown')[:19]
                        departure = flight.get('departure_time', 'N/A')
                        arrival = flight.get('arrival_time', 'N/A')
                        duration_min = flight.get('duration_minutes', 0)
                        duration = f"{duration_min//60}h {duration_min%60}m" if duration_min else "N/A"
                        price = flight.get('price_per_person', 0)
                        
                        print(f"{idx:<4} {airline:<20} {departure:<12} {arrival:<12} {duration:<10} ₹{price:>9,.0f}")
            else:
                print(f"    ❌ Flight search failed: {flights.get('error')}")

        # ------------------ GROUND TRANSPORT RESULTS ------------------
        if 'ground_transport' in results.get('results', {}):
            ground = results['results']['ground_transport']
            
            if ground.get('success'):
                route_info = ground.get('route_info', {})
                departure_date = results.get('search_params', {}).get('departure_date', '')
                return_date = results.get('search_params', {}).get('return_date', '')
                
                # Train results (outbound)
                if ground.get('outbound_trains'):
                    print(f"\n\n🚆 TRAIN OPTIONS:")
                    print("-"*80)
                    print(f"\n📤 Outbound Journey: {route_info.get('origin')} → {route_info.get('destination')} ({departure_date})")
                    print(f"{'#':<4} {'Train/Class':<25} {'Departure':<12} {'Arrival':<12} {'Duration':<10} {'Price':<12} {'Platform':<15}")
                    print("-"*80)
                    
                    for idx, train in enumerate(ground['outbound_trains'], 1):
                        operator = train.get('operator', 'Unknown')[:24]
                        service = train.get('service_type', 'N/A')
                        full_name = f"{operator} ({service})" if service != 'N/A' else operator
                        departure = train.get('departure_time', 'N/A')
                        arrival = train.get('arrival_time', 'N/A')
                        duration_min = train.get('duration_minutes', 0)
                        duration = f"{duration_min//60}h {duration_min%60}m" if duration_min else "N/A"
                        price = train.get('price_per_person', 0)
                        platform = train.get('platform', 'N/A')[:14]
                        
                        print(f"{idx:<4} {full_name[:25]:<25} {departure:<12} {arrival:<12} {duration:<10} ₹{price:>9,.0f} {platform:<15}")
                
                # Train results (return)
                if ground.get('return_trains'):
                    print(f"\n📥 Return Journey: {route_info.get('destination')} → {route_info.get('origin')} ({return_date})")
                    print(f"{'#':<4} {'Train/Class':<25} {'Departure':<12} {'Arrival':<12} {'Duration':<10} {'Price':<12} {'Platform':<15}")
                    print("-"*80)
                    
                    for idx, train in enumerate(ground['return_trains'], 1):
                        operator = train.get('operator', 'Unknown')[:24]
                        service = train.get('service_type', 'N/A')
                        full_name = f"{operator} ({service})" if service != 'N/A' else operator
                        departure = train.get('departure_time', 'N/A')
                        arrival = train.get('arrival_time', 'N/A')
                        duration_min = train.get('duration_minutes', 0)
                        duration = f"{duration_min//60}h {duration_min%60}m" if duration_min else "N/A"
                        price = train.get('price_per_person', 0)
                        platform = train.get('platform', 'N/A')[:14]
                        
                        print(f"{idx:<4} {full_name[:25]:<25} {departure:<12} {arrival:<12} {duration:<10} ₹{price:>9,.0f} {platform:<15}")
                
                # Bus results (outbound)
                if ground.get('outbound_buses'):
                    print(f"\n\n🚌 BUS OPTIONS:")
                    print("-"*80)
                    print(f"\n📤 Outbound Journey: {route_info.get('origin')} → {route_info.get('destination')} ({departure_date})")
                    print(f"{'#':<4} {'Operator/Type':<25} {'Departure':<12} {'Arrival':<12} {'Duration':<10} {'Price':<12} {'Platform':<15}")
                    print("-"*80)
                    
                    for idx, bus in enumerate(ground['outbound_buses'], 1):
                        operator = bus.get('operator', 'Unknown')[:24]
                        service = bus.get('service_type', 'N/A')
                        full_name = f"{operator} ({service})" if service != 'N/A' else operator
                        departure = bus.get('departure_time', 'N/A')
                        arrival = bus.get('arrival_time', 'N/A')
                        duration_min = bus.get('duration_minutes', 0)
                        duration = f"{duration_min//60}h {duration_min%60}m" if duration_min else "N/A"
                        price = bus.get('price_per_person', 0)
                        platform = bus.get('platform', 'N/A')[:14]
                        
                        print(f"{idx:<4} {full_name[:25]:<25} {departure:<12} {arrival:<12} {duration:<10} ₹{price:>9,.0f} {platform:<15}")
                
                # Bus results (return)
                if ground.get('return_buses'):
                    print(f"\n📥 Return Journey: {route_info.get('destination')} → {route_info.get('origin')} ({return_date})")
                    print(f"{'#':<4} {'Operator/Type':<25} {'Departure':<12} {'Arrival':<12} {'Duration':<10} {'Price':<12} {'Platform':<15}")
                    print("-"*80)
                    
                    for idx, bus in enumerate(ground['return_buses'], 1):
                        operator = bus.get('operator', 'Unknown')[:24]
                        service = bus.get('service_type', 'N/A')
                        full_name = f"{operator} ({service})" if service != 'N/A' else operator
                        departure = bus.get('departure_time', 'N/A')
                        arrival = bus.get('arrival_time', 'N/A')
                        duration_min = bus.get('duration_minutes', 0)
                        duration = f"{duration_min//60}h {duration_min%60}m" if duration_min else "N/A"
                        price = bus.get('price_per_person', 0)
                        platform = bus.get('platform', 'N/A')[:14]
                        
                        print(f"{idx:<4} {full_name[:25]:<25} {departure:<12} {arrival:<12} {duration:<10} ₹{price:>9,.0f} {platform:<15}")
            else:
                print(f"\n\n    ❌ Ground transport search failed: {ground.get('error')}")
        
        print("\n" + "="*80)
        print(f"Search completed using: {', '.join(results.get('summary', {}).get('providers_used', []))}")
        print("="*80)
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()