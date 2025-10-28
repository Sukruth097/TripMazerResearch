import os
import json
import sys
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

# Add project root to path for standalone execution
if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from src.entity.travel_search_params import TravelSearchParams
from src.utils.service_initializer import get_perplexity_service, get_serp_api_service, get_gemini_client
from langchain.tools import tool


def _extract_flight_details(flight_data: Dict[str, Any], adults: int) -> Dict[str, Any]:
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
        
        airplane_names = ', '.join([
            f.get('airplane', 'Unknown')
            for f in flight_data.get('flights', [])
        ])
        
        # Create route flow showing departure → arrival for each segment
        flight_segments = flight_data.get('flights', [])
        route_segments = []
        
        for f in flight_segments:
            dep_name = f.get('departure_airport', {}).get('name', 'N/A')
            dep_time = f.get('departure_airport', {}).get('time', 'N/A')
            arr_name = f.get('arrival_airport', {}).get('name', 'N/A')
            arr_time = f.get('arrival_airport', {}).get('time', 'N/A')
            
            # Extract just time (HH:MM) from full datetime if present
            if dep_time and len(dep_time) > 5:
                dep_time = dep_time.split(' ')[-1] if ' ' in dep_time else dep_time[-5:]
            if arr_time and len(arr_time) > 5:
                arr_time = arr_time.split(' ')[-1] if ' ' in arr_time else arr_time[-5:]
            
            route_segments.append(f"{dep_name} ({dep_time})")
            # Add arrival for the last segment
            if f == flight_segments[-1]:
                route_segments.append(f"{arr_name} ({arr_time})")
        
        route_flow = ' → '.join(route_segments)
        
        layovers = flight_data.get("layovers")
        if layovers:
            for layover in layovers:
                print(f" - {layover['name']} ({layover['id']}) | Duration: {layover['duration']} minutes")
            # Format layover information for display
            layover_details = []
            for layover in layovers:
                duration_hours = layover.get('duration', 0) // 60
                duration_mins = layover.get('duration', 0) % 60
                if duration_hours > 0:
                    duration_str = f"{duration_hours}h {duration_mins}m"
                else:
                    duration_str = f"{duration_mins}m"
                # Include full airport name along with code and duration
                airport_name = layover.get('name', 'Unknown Airport')
                airport_code = layover.get('id', 'N/A')
                layover_details.append(f"{airport_name} ({airport_code}) - Duration: {duration_str}")
            layover_info = ", ".join(layover_details)
        else:
            layover_info = "Direct"
            
        travel_class = ', '.join([
            f.get('travel_class', 'Unknown')
            for f in flight_data.get('flights', [])
        ])
        
        flight_number = ', '.join([
            f.get('flight_number', 'Unknown')
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
        duration_minutes = flight_data.get('total_duration') or flight_data.get('duration') or 0
        
        price = int(flight_data.get('price', 0)/adults)
        
        # Extract carbon emissions in grams
        # carbon_grams = flight_data.get('carbon_emissions', {}).get('this_flight', 0)
        
        return {
            'airline': airline_names,
            'departure_time': departure_time,
            'arrival_time': arrival_time,
            'duration_minutes': duration_minutes,
            'price_per_person': price,
            'airplane_names': airplane_names,
            'travel_class': travel_class,
            'flight_number': flight_number,
            'layovers': layover_info,
            'route_flow': route_flow,
            # 'carbon_grams': carbon_grams
        }
    except Exception as e:
        return {
            'airline': 'Unknown',
            'departure_time': 'N/A',
            'arrival_time': 'N/A',
            'duration_minutes': 0,
            'price_per_person': 0,
            'carbon_grams': 0,
            'layovers': 'N/A',
            'route_flow': 'N/A',
            'parse_error': str(e)
        }


def _search_flights_with_serp(params: TravelSearchParams) -> Dict[str, Any]:
    """
    Search flights using SERP API for both outbound and return journeys.
    Returns structured, table-ready flight data for easy agent formatting.
    """
    try:
        serp_service = get_serp_api_service()
        
        # Require airport codes from agent - no fallback to city names
        origin_airport = params.origin_airport
        dest_airport = params.destination_airport
        
        # Validate that airport codes are provided
        if not origin_airport or len(origin_airport) != 3:
            return {
                'provider': 'serp_api',
                'transport_mode': 'flight',
                'success': False,
                'outbound_flights': [],
                'return_flights': [],
                'error': f'Invalid origin airport code: "{origin_airport}". Agent must provide valid 3-letter IATA codes.',
                'route_info': {
                    'origin': params.origin,
                    'destination': params.destination,
                    'origin_airport': origin_airport,
                    'destination_airport': dest_airport
                }
            }
        
        if not dest_airport or len(dest_airport) != 3:
            return {
                'provider': 'serp_api',
                'transport_mode': 'flight',
                'success': False,
                'outbound_flights': [],
                'return_flights': [],
                'error': f'Invalid destination airport code: "{dest_airport}". Agent must provide valid 3-letter IATA codes.',
                'route_info': {
                    'origin': params.origin,
                    'destination': params.destination,
                    'origin_airport': origin_airport,
                    'destination_airport': dest_airport
                }
            }
        
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
        print(f"🔍 DEBUG - Searching flights: {origin_airport} → {dest_airport} on {params.departure_date}")
        outbound_results = serp_service.search_flights(
            departure_id=origin_airport,
            arrival_id=dest_airport,
            outbound_date=params.departure_date,
            country_code="in" if params.is_domestic else "us",
            currency=params.currency,
            adults=params.travelers
        )
        
        print(f"🔍 DEBUG - Outbound results type: {type(outbound_results)}")
        if isinstance(outbound_results, dict):
            print(f"🔍 DEBUG - Outbound result keys: {list(outbound_results.keys())}")
            if 'error' in outbound_results:
                print(f"🔍 DEBUG - SERP API Error: {outbound_results['error']}")
        
        # Extract structured outbound flight details (top 3 options)
        if isinstance(outbound_results, dict):
            adults = outbound_results.get('search_parameters', {}).get('adults', 1)
            # print(f"   Outbound Adults: {adults}")
            flights_list = []
            if 'best_flights' in outbound_results and outbound_results['best_flights']:
                flights_list = outbound_results['best_flights']
            elif 'other_flights' in outbound_results and outbound_results['other_flights']:
                flights_list = outbound_results['other_flights']
            elif 'flights' in outbound_results and outbound_results['flights']:
                flights_list = outbound_results['flights']
            for flight in flights_list[:3]:  # Limit to top 3
                flight_details = _extract_flight_details(flight, adults)
                results['outbound_flights'].append(flight_details)
        
        # Search return flights if needed
        if params.trip_type == "round_trip" and params.return_date:
            return_results = serp_service.search_flights(
                departure_id=dest_airport,
                arrival_id=origin_airport,
                outbound_date=params.return_date,
                country_code="in" if params.is_domestic else "us",
                currency=params.currency,
                adults=params.travelers
            )
            # Extract structured return flight details (top 3 options)
            if isinstance(return_results, dict):
                adults = return_results.get('search_parameters', {}).get('adults', 1)
                
                flights_list = []
                if 'best_flights' in return_results and return_results['best_flights']:
                    flights_list = return_results['best_flights']
                elif 'other_flights' in return_results and return_results['other_flights']:
                    flights_list = return_results['other_flights']
                elif 'flights' in return_results and return_results['flights']:
                    flights_list = return_results['flights']
                for flight in flights_list[:10]:  # Limit to top 3
                    flight_details = _extract_flight_details(flight, adults)
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


def _search_ground_transport_with_perplexity(params: TravelSearchParams, modes: List[str]) -> Dict[str, Any]:
    """
    Search buses and trains using Perplexity with structured JSON output.
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
            train_query_outbound = f"""
            Find train options from {params.origin} to {params.destination} on {params.departure_date} for {params.travelers} travelers.
            {"Budget per person: " + params.currency + " " + str(params.budget_limit / params.travelers) if params.budget_limit else ""}
            
            Return ONLY a JSON array (no other text) with 5-8 best train options in this EXACT format:
            [
              {{
                "operator": "Train Name with Number (e.g., Rajdhani Express 12951)",
                "service_type": "Class (2A/3A/Sleeper)",
                "departure_time": "HH:MM",
                "arrival_time": "HH:MM", 
                "duration_minutes": 920,
                "price_per_person": 2500.0,
                "platform": "IRCTC"
              }}
            ]
            
            Use mid-range pricing (2A or 3A class). Times in 24-hour format. Currency: {params.currency}
            """
            
            train_system_prompt = """You are a train search API. Return ONLY valid JSON array, no explanations.
            Each train must have: operator (with number), service_type (class), departure_time (HH:MM), arrival_time (HH:MM), 
            duration_minutes (integer), price_per_person (float), platform (IRCTC).
            List actual trains with real numbers and realistic pricing."""
            
            outbound_trains_raw = perplexity_service.search(
                query=train_query_outbound,
                system_prompt=train_system_prompt,
                temperature=0.1
            )
            
            # Parse JSON directly from Perplexity
            try:
                outbound_trains_text = outbound_trains_raw if isinstance(outbound_trains_raw, str) else ""
                # Clean markdown code blocks if present
                if outbound_trains_text.startswith('```json'):
                    outbound_trains_text = outbound_trains_text.replace('```json', '').replace('```', '').strip()
                elif outbound_trains_text.startswith('```'):
                    outbound_trains_text = outbound_trains_text.replace('```', '').strip()
                
                parsed_trains = json.loads(outbound_trains_text)
                # Limit to top 3 results
                results['outbound_trains'] = parsed_trains[:3] if isinstance(parsed_trains, list) else []
                
                if results['outbound_trains']:
                    print(f"✅ Found {len(results['outbound_trains'])} outbound trains")
                else:
                    print(f"⚠️ No train options available for {params.origin} to {params.destination}")
                    
            except json.JSONDecodeError as e:
                results['outbound_trains'] = []
                print(f"⚠️ Failed to parse outbound train results: {str(e)[:100]}")
                print(f"⚠️ No train options available for {params.origin} to {params.destination}")
            except Exception as e:
                results['outbound_trains'] = []
                print(f"⚠️ Train search error: {str(e)}")
                print(f"⚠️ No train options available for {params.origin} to {params.destination}")
            
            # Return trains (if round trip)
            if params.trip_type == "round_trip" and params.return_date:
                train_query_return = f"""
                Find train options from {params.destination} to {params.origin} on {params.return_date} for {params.travelers} travelers.
                {"Budget per person: " + params.currency + " " + str(params.budget_limit / params.travelers) if params.budget_limit else ""}
                
                Return ONLY a JSON array (no other text) with 5-8 best train options in this EXACT format:
                [
                  {{
                    "operator": "Train Name with Number",
                    "service_type": "Class (2A/3A/Sleeper)",
                    "departure_time": "HH:MM",
                    "arrival_time": "HH:MM",
                    "duration_minutes": 920,
                    "price_per_person": 2500.0,
                    "platform": "IRCTC"
                  }}
                ]
                
                Use mid-range pricing. Times in 24-hour format. Currency: {params.currency}
                """
                
                return_trains_raw = perplexity_service.search(
                    query=train_query_return,
                    system_prompt=train_system_prompt,
                    temperature=0.1
                )
                
                try:
                    return_trains_text = return_trains_raw if isinstance(return_trains_raw, str) else ""
                    if return_trains_text.startswith('```json'):
                        return_trains_text = return_trains_text.replace('```json', '').replace('```', '').strip()
                    elif return_trains_text.startswith('```'):
                        return_trains_text = return_trains_text.replace('```', '').strip()
                    
                    parsed_return_trains = json.loads(return_trains_text)
                    # Limit to top 3 results  
                    results['return_trains'] = parsed_return_trains[:3] if isinstance(parsed_return_trains, list) else []
                    
                    if results['return_trains']:
                        print(f"✅ Found {len(results['return_trains'])} return trains")
                    else:
                        print(f"⚠️ No return train options available for {params.destination} to {params.origin}")
                        
                except json.JSONDecodeError as e:
                    results['return_trains'] = []
                    print(f"⚠️ Failed to parse return train results: {str(e)[:100]}")
                    print(f"⚠️ No return train options available for {params.destination} to {params.origin}")
                except Exception as e:
                    results['return_trains'] = []
                    print(f"⚠️ Return train search error: {str(e)}")
                    print(f"⚠️ No return train options available for {params.destination} to {params.origin}")
        
        # Search buses if requested
        if 'bus' in modes:
            # Improved bus query with specific route focus
            bus_query_outbound = f"""
            Find the TOP 3 BEST bus options from {params.origin} to {params.destination} on {params.departure_date} for {params.travelers} travelers.
            {"Budget per person: " + params.currency + " " + str(params.budget_limit / params.travelers) if params.budget_limit else ""}
            For {params.origin} to {params.destination}, check actual bus services like RedBus, AbhiBus.
            
            Return ONLY a JSON array (no other text) with the TOP 3 bus options in this EXACT format:
            [
              {{
                "operator": "VRL Travels",
                "service_type": "AC Sleeper",
                "departure_time": "22:30",
                "arrival_time": "06:00",
                "duration_minutes": 450,
                "price_per_person": 1200.0,
                "platform": "RedBus"
              }}
            ]
            
            IMPORTANT: If no buses available for this route, return empty array [].
            Currency: {params.currency}
            """
            
            bus_system_prompt = """You are a bus search API. Return ONLY valid JSON array, no explanations.
            Return TOP 3 BEST options only. Each bus must have: operator (name), service_type (bus type), 
            departure_time (HH:MM), arrival_time (HH:MM), duration_minutes (integer), price_per_person (float), platform.
            Use actual Indian bus operators and realistic pricing. If route has no buses, return empty array []."""
            
            outbound_buses_raw = perplexity_service.search(
                query=bus_query_outbound,
                system_prompt=bus_system_prompt,
                temperature=0.1
            )
            
            try:
                outbound_buses_text = outbound_buses_raw if isinstance(outbound_buses_raw, str) else ""
                # Clean markdown code blocks if present
                if outbound_buses_text.startswith('```json'):
                    outbound_buses_text = outbound_buses_text.replace('```json', '').replace('```', '').strip()
                elif outbound_buses_text.startswith('```'):
                    outbound_buses_text = outbound_buses_text.replace('```', '').strip()
                
                parsed_buses = json.loads(outbound_buses_text)
                # Limit to top 3 results
                results['outbound_buses'] = parsed_buses[:3] if isinstance(parsed_buses, list) else []
                
                if results['outbound_buses']:
                    print(f"✅ Found {len(results['outbound_buses'])} outbound buses")
                else:
                    print(f"⚠️ No bus options available for {params.origin} to {params.destination}")
                    
            except json.JSONDecodeError as e:
                results['outbound_buses'] = []
                print(f"⚠️ Failed to parse outbound bus results: {str(e)[:100]}")
                print(f"Raw response (first 300 chars): {outbound_buses_text[:300]}")
                # Add fallback message for no buses
                print(f"⚠️ No bus options available for {params.origin} to {params.destination}")
            except Exception as e:
                results['outbound_buses'] = []
                print(f"⚠️ Bus search error: {str(e)}")
                print(f"⚠️ No bus options available for {params.origin} to {params.destination}")
            
            # Return buses (if round trip)
            if params.trip_type == "round_trip" and params.return_date:
                bus_query_return = f"""
                Find the TOP 3 BEST bus options from {params.destination} to {params.origin} on {params.return_date} for {params.travelers} travelers.
                {"Budget per person: " + params.currency + " " + str(params.budget_limit / params.travelers) if params.budget_limit else ""}
                
                Focus on: VRL Travels, SRS Travels, KSRTC, or other major operators serving this route.
                
                Return ONLY a JSON array (no other text) with the TOP 3 bus options in this EXACT format:
                [
                  {{
                    "operator": "VRL Travels",
                    "service_type": "AC Sleeper",
                    "departure_time": "22:30",
                    "arrival_time": "06:00",
                    "duration_minutes": 450,
                    "price_per_person": 1200.0,
                    "platform": "RedBus"
                  }}
                ]
                
                IMPORTANT: If no buses available for this route, return empty array [].
                Currency: {params.currency}
                """
                
                return_buses_raw = perplexity_service.search(
                    query=bus_query_return,
                    system_prompt=bus_system_prompt,
                    temperature=0.1
                )
                
                try:
                    return_buses_text = return_buses_raw if isinstance(return_buses_raw, str) else ""
                    if return_buses_text.startswith('```json'):
                        return_buses_text = return_buses_text.replace('```json', '').replace('```', '').strip()
                    elif return_buses_text.startswith('```'):
                        return_buses_text = return_buses_text.replace('```', '').strip()
                    
                    parsed_return_buses = json.loads(return_buses_text)
                    # Limit to top 3 results
                    results['return_buses'] = parsed_return_buses[:3] if isinstance(parsed_return_buses, list) else []
                    
                    if results['return_buses']:
                        print(f"✅ Found {len(results['return_buses'])} return buses")
                    else:
                        print(f"⚠️ No return bus options available for {params.destination} to {params.origin}")
                        
                except json.JSONDecodeError as e:
                    results['return_buses'] = []
                    print(f"⚠️ Failed to parse return bus results: {str(e)[:100]}")
                    print(f"Raw response (first 300 chars): {return_buses_text[:300]}")
                    print(f"⚠️ No return bus options available for {params.destination} to {params.origin}")
                except Exception as e:
                    results['return_buses'] = []
                    print(f"⚠️ Return bus search error: {str(e)}")
                    print(f"⚠️ No return bus options available for {params.destination} to {params.origin}")
        
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
                      return_date: Optional[str] = None, budget_limit: Optional[float] = None, 
                      currency: str = "INR", currency_symbol: str = "₹", 
                      destination_currency: str = "INR", origin_airport: Optional[str] = None,
                      destination_airport: Optional[str] = None, is_domestic: bool = True,
                      is_international: bool = False, trip_type: str = "round_trip") -> str:
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
        currency: Currency code (always INR)
        currency_symbol: Currency symbol (default ₹)
        destination_currency: Destination currency for international trips
        origin_airport: Airport code resolved by agent (optional)
        destination_airport: Airport code resolved by agent (optional) 
        is_domestic: Whether route is domestic
        is_international: Whether route is international
        trip_type: "round_trip" or "one_way"
        
    Returns:
        JSON string with search results
        
    Example Agent Usage:
        results = travel_search_tool(
            origin="Mumbai", destination="Delhi", 
            departure_date="2024-12-01", return_date="2024-12-05",
            transport_modes=["flight", "train"], travelers=2,
            budget_limit=15000, currency="INR", currency_symbol="₹",
            origin_airport="BOM", destination_airport="DEL",
            is_domestic=True
        )
        
    Example Direct Testing:
        results = travel_search_tool(
            origin="Mumbai", destination="Delhi",
            departure_date="2024-12-01", 
            transport_modes=["flight"], travelers=1,
            currency="USD", currency_symbol="$"
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
            currency_symbol=currency_symbol,
            destination_currency=destination_currency,
            transport_modes=transport_modes,
            trip_type=trip_type,
            is_domestic=is_domestic,
            is_international=is_international,
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
            flight_results = _search_flights_with_serp(params)
            search_results['results']['flights'] = flight_results
            search_results['summary']['providers_used'].append('serp_api')
            search_results['summary']['transport_modes_searched'].append('flight')
        
        # Search ground transport with Perplexity if requested
        ground_modes = [mode for mode in params.transport_modes if mode in ['bus', 'train']]
        
        if ground_modes and params.use_perplexity_for_ground:
            ground_results = _search_ground_transport_with_perplexity(params, ground_modes)
            search_results['results']['ground_transport'] = ground_results
            search_results['summary']['providers_used'].append('perplexity')
            search_results['summary']['transport_modes_searched'].extend(ground_modes)
        
        # Return JSON results for agent to process
        return json.dumps(search_results, indent=2, default=str)
        
    except Exception as e:
        # Simple error handling as requested
        raise Exception(f"Travel search failed: {str(e)}")

def format_travel_results_as_markdown(results: Dict[str, Any], currency_symbol: Optional[str] = None) -> str:
    """
    Format travel search results into clean Markdown tables for better user experience.
    Handles both flights and ground transport (buses/trains).
    
    Args:
        results: Travel search results dictionary
        currency_symbol: Currency symbol to use (defaults to ₹ if not provided)
    """
    try:
        # Parse results structure
        if isinstance(results, str):
            parsed = json.loads(results)
        elif isinstance(results, dict):
            parsed = results
        else:
            return "❌ No travel results found"
        
        search_params = parsed.get('search_params', {})
        result_data = parsed.get('results', {})
        
        # Debug: Show what we received from API
        print(f"🔍 DEBUG - Full result_data keys: {list(result_data.keys())}")
        if 'flights' in result_data:
            print(f"🔍 DEBUG - Flight result keys: {list(result_data['flights'].keys())}")
        else:
            print(f"🔍 DEBUG - No 'flights' key in result_data")
        
        # Use currency_symbol from search_params if available, otherwise use provided or default
        if currency_symbol is None:
            currency_symbol = search_params.get('currency_symbol', '₹')
        
        origin = search_params.get('origin', 'Origin')
        destination = search_params.get('destination', 'Destination') 
        departure_date = search_params.get('departure_date', 'Date')
        return_date = search_params.get('return_date')
        
        output = [f"## ✈️🚌🚂 Travel Options: {origin} ↔ {destination}\n"]
        
        # Handle Flights
        if 'flights' in result_data:
            flights_data = result_data['flights']
            output.append("### ✈️ Flight Options\n")
            
            outbound_flights = flights_data.get('outbound_flights', [])
            return_flights = flights_data.get('return_flights', [])
            
            # Debug: Show what we received
            print(f"🔍 DEBUG - Flights data structure: {list(flights_data.keys())}")
            print(f"🔍 DEBUG - Outbound flights count: {len(outbound_flights)}")
            print(f"🔍 DEBUG - Return flights count: {len(return_flights)}")
            if outbound_flights:
                print(f"🔍 DEBUG - First outbound flight keys: {list(outbound_flights[0].keys())}")
            
            if outbound_flights:
                output.append(f"**>> Outbound Journey ({origin} → {destination}) - {departure_date}**\n")
                output.append("| # | Flight | Transit | Price/Person | Departure | Arrival | Duration | Layovers | Class |")
                output.append("|---|--------|---------|-------|-----------|---------|----------|----------|-------|")
                
                for idx, flight in enumerate(outbound_flights[:3], 1):
                    airline = flight.get('airline', 'Unknown')[:30]
                    airplane = flight.get('airplane_names', 'Unknown')
                    flight_number = flight.get('flight_number', '')
                    travel_class = flight.get('travel_class', 'N/A')
                    
                    # Combine airline and aircraft/flight number into single Flight column
                    if flight_number and airplane != 'Unknown':
                        flight_info = f"{airline} - {airplane} ({flight_number})"
                    elif flight_number:
                        flight_info = f"{airline} - {flight_number}"
                    elif airplane != 'Unknown':
                        flight_info = f"{airline} - {airplane}"
                    else:
                        flight_info = airline
                    
                    departure = flight.get('departure_time', 'N/A')
                    arrival = flight.get('arrival_time', 'N/A')
                    duration_min = flight.get('duration_minutes', 0)
                    duration = f"{duration_min//60}h {duration_min%60}m" if duration_min else "N/A"
                    price = flight.get('price_per_person', 0)
                    layovers = flight.get('layovers', 'Direct')
                    route_flow = flight.get('route_flow', 'N/A')
                    
                    output.append(f"| {idx} | {flight_info} | {route_flow} | {currency_symbol}{price:,.0f} | {departure} | {arrival} | {duration} | {layovers} | {travel_class} |")
                output.append("")
            else:
                output.append(f"⚠️ No flight options available for outbound journey.\n")
            
            if return_flights and return_date:
                output.append(f"**<< Return Journey ({destination} → {origin}) - {return_date}**\n")
                output.append("| # | Flight | Transit | Price/Person | Departure | Arrival | Duration | Layovers | Class |")
                output.append("|---|--------|---------|-------|-----------|---------|----------|----------|-------|")
                
                for idx, flight in enumerate(return_flights[:3], 1):
                    airline = flight.get('airline', 'Unknown')[:30]
                    airplane = flight.get('airplane_names', 'Unknown')
                    flight_number = flight.get('flight_number', '')
                    travel_class = flight.get('travel_class', 'N/A')
                    
                    # Combine airline and aircraft/flight number into single Flight column
                    if flight_number and airplane != 'Unknown':
                        flight_info = f"{airline} - {airplane} ({flight_number})"
                    elif flight_number:
                        flight_info = f"{airline} - {flight_number}"
                    elif airplane != 'Unknown':
                        flight_info = f"{airline} - {airplane}"
                    else:
                        flight_info = airline
                    
                    departure = flight.get('departure_time', 'N/A')
                    arrival = flight.get('arrival_time', 'N/A')
                    duration_min = flight.get('duration_minutes', 0)
                    duration = f"{duration_min//60}h {duration_min%60}m" if duration_min else "N/A"
                    price = flight.get('price_per_person', 0)
                    layovers = flight.get('layovers', 'Direct')
                    route_flow = flight.get('route_flow', 'N/A')
                    
                    output.append(f"| {idx} | {flight_info} | {route_flow} | {currency_symbol}{price:,.0f} | {departure} | {arrival} | {duration} | {layovers} | {travel_class} |")
                output.append("")
            elif return_date:
                output.append(f"⚠️ No flight options available for return journey.\n")
        
        # Handle Ground Transport
        if 'ground_transport' in result_data:
            ground_transport = result_data['ground_transport']
            
            # Bus Options
            output.append("### 🚌 Bus Options\n")
            if ground_transport.get('outbound_buses'):
                output.append(f"**>> Outbound Journey ({origin} → {destination}) - {departure_date}**\n")
                output.append("| # | Operator | Price/Person | Departure | Arrival | Duration | Service | Platform |")
                output.append("|---|----------|-------|-----------|---------|----------|---------|----------|")
                
                for idx, bus in enumerate(ground_transport['outbound_buses'][:3], 1):
                    operator = bus.get('operator', 'Unknown')[:20]
                    service = bus.get('service_type', 'N/A')[:15]
                    departure = bus.get('departure_time', 'N/A')
                    arrival = bus.get('arrival_time', 'N/A')
                    duration_min = bus.get('duration_minutes', 0)
                    duration = f"{duration_min//60}h {duration_min%60}m" if duration_min else "N/A"
                    price = bus.get('price_per_person', 0)
                    platform = bus.get('platform', 'N/A')
                    
                    output.append(f"| {idx} | {operator} | {currency_symbol}{price:,.0f} | {departure} | {arrival} | {duration} | {service} | {platform} |")
                output.append("")
            else:
                output.append(f"⚠️ No bus options available for outbound journey.\n")
                
            if ground_transport.get('return_buses') and return_date:
                output.append(f"**<< Return Journey ({destination} → {origin}) - {return_date}**\n")
                output.append("| # | Operator | Price/Person | Departure | Arrival | Duration | Service | Platform |")
                output.append("|---|----------|-------|-----------|---------|----------|---------|----------|")
                
                for idx, bus in enumerate(ground_transport['return_buses'][:3], 1):
                    operator = bus.get('operator', 'Unknown')[:20]
                    service = bus.get('service_type', 'N/A')[:15]
                    departure = bus.get('departure_time', 'N/A')
                    arrival = bus.get('arrival_time', 'N/A')
                    duration_min = bus.get('duration_minutes', 0)
                    duration = f"{duration_min//60}h {duration_min%60}m" if duration_min else "N/A"
                    price = bus.get('price_per_person', 0)
                    platform = bus.get('platform', 'N/A')
                    
                    output.append(f"| {idx} | {operator} | {currency_symbol}{price:,.0f} | {departure} | {arrival} | {duration} | {service} | {platform} |")
                output.append("")
            elif return_date:
                output.append(f"⚠️ No bus options available for return journey.\n")
            
            # Train Options  
            output.append("### 🚂 Train Options\n")
            if ground_transport.get('outbound_trains'):
                output.append(f"**>> Outbound Journey ({origin} → {destination}) - {departure_date}**\n")
                output.append("| # | Train | Price/Person | Departure | Arrival | Duration | Class | Platform |")
                output.append("|---|-------|-------|-----------|---------|----------|-------|----------|")
                
                for idx, train in enumerate(ground_transport['outbound_trains'][:3], 1):
                    operator = train.get('operator', 'Unknown')[:20]
                    service = train.get('service_type', 'N/A')[:10]
                    departure = train.get('departure_time', 'N/A')
                    arrival = train.get('arrival_time', 'N/A')
                    duration_min = train.get('duration_minutes', 0)
                    duration = f"{duration_min//60}h {duration_min%60}m" if duration_min else "N/A"
                    price = train.get('price_per_person', 0)
                    platform = train.get('platform', 'N/A')
                    
                    output.append(f"| {idx} | {operator} | {currency_symbol}{price:,.0f} | {departure} | {arrival} | {duration} | {service} | {platform} |")
                output.append("")
            else:
                output.append(f"⚠️ No train options available for outbound journey.\n")
                
            if ground_transport.get('return_trains') and return_date:
                output.append(f"**<< Return Journey ({destination} → {origin}) - {return_date}**\n")
                output.append("| # | Train | Price/Person | Departure | Arrival | Duration | Class | Platform |")
                output.append("|---|-------|-------|-----------|---------|----------|-------|----------|")
                
                for idx, train in enumerate(ground_transport['return_trains'][:3], 1):
                    operator = train.get('operator', 'Unknown')[:20]
                    service = train.get('service_type', 'N/A')[:10]
                    departure = train.get('departure_time', 'N/A')
                    arrival = train.get('arrival_time', 'N/A')
                    duration_min = train.get('duration_minutes', 0)
                    duration = f"{duration_min//60}h {duration_min%60}m" if duration_min else "N/A"
                    price = train.get('price_per_person', 0)
                    platform = train.get('platform', 'N/A')
                    
                    output.append(f"| {idx} | {operator} | {currency_symbol}{price:,.0f} | {departure} | {arrival} | {duration} | {service} | {platform} |")
                output.append("")
            elif return_date:
                output.append(f"⚠️ No train options available for return journey.\n")
        
        # Add a note if no results found for any transport mode
        if 'flights' not in result_data and 'ground_transport' not in result_data:
            output.append("⚠️ No travel options found for the specified route and dates.\n")
        
        return "\n".join(output)
        
    except Exception as e:
        return f"❌ Error formatting travel results: {str(e)}"
        
    except Exception as e:
        return f"❌ Error formatting travel results: {str(e)}"

# For testing
if __name__ == "__main__":
    print("Testing Unified Travel Search Tool...")
    
    test_result = travel_search_tool.invoke({
            "origin": "Bangalore",
            "destination": "Dubai",
            "origin_airport": "BLR",
            "destination_airport": "DXB",
            "departure_date": "2025-10-30",
            "transport_modes": ["flight"],
            "travelers": 2,
            "return_date": "2025-10-31",
            # "budget_limit": 35000,
            "sort_by": 2,
            "currency": "INR",
            "is_domestic": False
        })
        
    
    results = json.loads(test_result)

    print("\n" + "="*80)
    print("SEARCH RESULTS (Markdown Format)")
    print("="*80)
    print(format_travel_results_as_markdown(results))

       