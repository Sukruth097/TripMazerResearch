import os
import json
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

from src.services.perplexity_service import PerplexityService
from src.services.serp_api_service import SerpAPIService
from src.entity.travel_search_params import TravelSearchParams
from langchain.tools import tool


def _get_perplexity_service() -> PerplexityService:
    """Get initialized Perplexity service instance."""
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY environment variable is required")
    return PerplexityService(api_key)


def _get_serp_api_service() -> SerpAPIService:
    """Get initialized SerpAPI service instance."""
    api_key = os.getenv('SERP_API_KEY')
    if not api_key:
        raise ValueError("SERP_API_KEY environment variable is required")
    return SerpAPIService(api_key)


def _search_flights_with_serp(params: TravelSearchParams) -> Dict[str, Any]:
    """
    Search flights using SERP API for both outbound and return journeys.
    Returns raw data for agent processing.
    """
    try:
        serp_service = _get_serp_api_service()
        
        # Use airport codes resolved by agent (fallback to city names if not available)
        origin_airport = params.origin_airport or params.origin
        dest_airport = params.destination_airport or params.destination
        
        results = {
            'provider': 'serp_api',
            'transport_mode': 'flight',
            'success': True,
            'outbound': None,
            'return': None,
            'error': None,
            'airport_codes_used': {'origin': origin_airport, 'destination': dest_airport}
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
        results['outbound'] = outbound_results
        
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
            results['return'] = return_results
        
        return results
        
    except Exception as e:
        return {
            'provider': 'serp_api',
            'transport_mode': 'flight', 
            'success': False,
            'error': str(e),
            'outbound': None,
            'return': None
        }


def _search_ground_transport_with_perplexity(params: TravelSearchParams, modes: List[str]) -> Dict[str, Any]:
    """
    Search buses and trains using Perplexity for both directions.
    Returns raw data for agent processing.
    """
    try:
        perplexity_service = _get_perplexity_service()
        
        # Create search query for Perplexity
        transport_types = " and ".join(modes)
        query = f"""
        Find {transport_types} options from {params.origin} to {params.destination} 
        on {params.departure_date} for {params.travelers} travelers.
        Budget: {params.currency} {params.budget_limit if params.budget_limit else 'flexible'}.
        
        {"Also find return options from " + params.destination + " to " + params.origin + " on " + params.return_date + "." if params.trip_type == "round_trip" and params.return_date else ""}
        
        Provide specific operator names, departure times, journey duration, and pricing.
        Focus on actual available services for this route and date.
        """
        
        # System prompt to ensure structured data
        system_prompt = f"""
        You are a travel search assistant. Provide {transport_types} information with:
        
        1. Specific operator names and service details
        2. Departure and arrival times  
        3. Journey duration
        4. Pricing in {params.currency}
        5. Booking platforms
        
        For Indian domestic routes, focus on:
        - Buses: Government and private operators (KSRTC, MSRTC, VRL, SRS, etc.)
        - Trains: Indian Railways with train names, numbers, and class options
        
        Provide realistic, current information without table formatting.
        Return as structured text that an agent can format appropriately.
        """
        
        results = perplexity_service.search(
            query=query,
            system_prompt=system_prompt,
            temperature=0.1
        )
        
        return {
            'provider': 'perplexity',
            'transport_modes': modes,
            'success': True,
            'raw_results': results,
            'error': None,
            'search_query': query
        }
        
    except Exception as e:
        return {
            'provider': 'perplexity',
            'transport_modes': modes,
            'success': False,
            'error': str(e),
            'raw_results': None
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
    
    # Test with direct parameters
    try:
        test_result = travel_search_tool(
            origin="Mumbai",
            destination="Delhi",
            departure_date="2024-12-01",
            transport_modes=["flight", "train"],
            travelers=2,
            return_date="2024-12-05",
            budget_limit=15000,
            currency="INR",
            is_domestic=True
        )
        
        print("✅ Test successful!")
        print("Results:", test_result[:500], "...")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")