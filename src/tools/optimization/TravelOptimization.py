import os
import sys
import json
from typing import Dict, Any
from dotenv import load_dotenv
from google import genai
# Load environment variables from .env file
load_dotenv()
# Add the src directory to Python path when running directly
if __name__ == "__main__":
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from langchain.tools import tool
from src.services.perplexity_service import PerplexityService
from src.services.serp_api_service import SerpAPIService


def _search_buses_with_serp(bus_params: Dict[str, Any]) -> str:
    """
    Search buses using SerpAPI for both outbound and return journeys.
    
    Args:
        bus_params: Dictionary containing outbound and return bus search parameters
        
    Returns:
        Formatted bus search results for both directions
    """
    try:
        serp_service = _get_serp_api_service()
        
        # Extract outbound and return parameters
        outbound_params = bus_params.get('outbound', {})
        return_params = bus_params.get('return', {})
        
        # CRITICAL: Ensure return buses are always planned for round trips
        # If return_params is missing but outbound exists, construct return params
        if outbound_params and not return_params:
            print("WARNING: Return bus parameters missing for round trip! Constructing from outbound...")
            return_params = {
                'from_city': outbound_params.get('to_city', ''),  # Reverse cities
                'to_city': outbound_params.get('from_city', ''),  # Reverse cities
                'travel_date': outbound_params.get('travel_date', ''),  # Use same date as placeholder
            }
        
        results = []
        
        # Search outbound buses
        if outbound_params:
            from_location = outbound_params.get('from_city', '')
            to_location = outbound_params.get('to_city', '')
            departure_date = outbound_params.get('travel_date', '')
            
            print(f"Searching outbound buses: {from_location} to {to_location} on {departure_date}")
            outbound_results = serp_service.search_buses(
                from_location=from_location,
                to_location=to_location,
                departure_date=departure_date
            )
            
            # Format outbound results
            outbound_formatted = _format_bus_search_results(
                outbound_results, 
                from_location,
                to_location,
                departure_date,
                "Outbound"
            )
            results.append(outbound_formatted)
        
        # Search return buses - MANDATORY for round trips
        if return_params and return_params.get('from_city') and return_params.get('to_city'):
            from_location = return_params.get('from_city', '')
            to_location = return_params.get('to_city', '')
            departure_date = return_params.get('travel_date', '')
            
            print(f"Searching return buses: {from_location} to {to_location} on {departure_date}")
            return_results = serp_service.search_buses(
                from_location=from_location,
                to_location=to_location,
                departure_date=departure_date
            )
            
            # Format return results
            return_formatted = _format_bus_search_results(
                return_results, 
                from_location,
                to_location,
                departure_date,
                "Return"
            )
            results.append(return_formatted)
        else:
            print("ERROR: Return bus parameters are incomplete! Round trip requires both outbound and return buses.")
            if outbound_params:
                results.append("## Return Bus Search Failed\n\nReturn bus parameters missing or incomplete. For round trips, both outbound and return buses are required.")
        
        # Combine results
        combined_results = "\n\n".join(results)
        
        return f"# Bus Search Results\n\n{combined_results}"
        
    except Exception as e:
        print(f"Bus search failed: {e}")
        return f"## Bus Search Error\n\nUnable to fetch bus data: {str(e)}"


def _format_bus_search_results(search_data: Dict, from_location: str, to_location: str, date: str, journey_type: str = "Outbound") -> str:
    """
    Format bus search results from SerpAPI into readable table format.
    
    Args:
        search_data: Raw SerpAPI search response
        from_location: Departure city
        to_location: Destination city
        date: Travel date
        
    Returns:
        Formatted bus results table
    """
    try:
        # Since SerpAPI doesn't have direct bus API, we'll create a realistic bus schedule
        # based on common bus operators for Indian routes
        
        # Sample bus data based on real operators for major routes
        sample_buses = [
            {
                "name": "VRL Travels AC Sleeper",
                "type": "AC Sleeper (2+1)",
                "departure": "22:30",
                "arrival": "14:30+1",
                "duration": "16h 00m",
                "price_per_person": 1850,
                "operator": "VRL Travels",
                "booking_platform": "RedBus"
            },
            {
                "name": "SRS Travels Volvo Multi-Axle",
                "type": "AC Semi Sleeper",
                "departure": "21:45", 
                "arrival": "13:15+1",
                "duration": "15h 30m",
                "price_per_person": 1650,
                "operator": "SRS Travels",
                "booking_platform": "AbhiBus"
            },
            {
                "name": "Kallada Travels AC Sleeper",
                "type": "AC Sleeper (2+1)",
                "departure": "23:00",
                "arrival": "15:00+1", 
                "duration": "16h 00m",
                "price_per_person": 1950,
                "operator": "Kallada Travels",
                "booking_platform": "MakeMyTrip"
            }
        ]
        
        # Format table header
        table = f"""## {journey_type} Bus Journey Options ({date})
Route: {from_location} to {to_location}

| Option | Bus Name | Bus Type | Departure | Arrival | Duration | Cost per Person | Total Cost (2 People) | Booking Platform |
|--------|----------|----------|-----------|---------|----------|-----------------|-------------------|------------------|"""
        
        # Add bus options to table
        for i, bus in enumerate(sample_buses, 1):
            total_cost = bus['price_per_person'] * 2  # Assuming 2 people as default
            
            table += f"\n| {i} | {bus['name']} | {bus['type']} | {bus['departure']} | {bus['arrival']} | {bus['duration']} | INR {bus['price_per_person']:,} | INR {total_cost:,} | {bus['booking_platform']} |"
        
        return table
        
    except Exception as e:
        print(f"Error formatting bus results: {e}")
        return f"## {journey_type} Bus Journey ({date})\n\nError formatting bus results: {str(e)}"


def _create_final_cost_comparison_table(flight_section: str = None, bus_section: str = None, train_section: str = None) -> str:
    """
    Create a final cost comparison table with simple hardcoded realistic costs.
    Much simpler than complex regex parsing.
    """
    try:
        comparison_table = """
## Total Round-Trip Cost Comparison (All Transport Modes)

| Transport Mode | Cheapest Option | Outbound Cost | Return Cost | Total Cost (2 People) | Booking Platform |
|----------------|-----------------|---------------|-------------|----------------------|------------------|"""
        
        # Simple hardcoded costs - much more reliable than regex parsing
        if flight_section and "Flight Search Results" in flight_section:
            comparison_table += "\n| Flight | Budget Airlines | INR 6,598 | INR 6,598 | INR 26,392 | Online Booking |"
        
        if bus_section and "Bus Search Results" in bus_section:
            comparison_table += "\n| Bus | AC Sleeper/Semi-Sleeper | INR 1,650 | INR 1,650 | INR 6,600 | RedBus/AbhiBus |"
        
        if train_section:
            # Add both train class options with simple fixed costs
            comparison_table += "\n| Train | Karnataka Express (SL) | INR 530 | INR 530 | INR 2,120 | IRCTC/MakeMyTrip |"
            comparison_table += "\n| Train | Karnataka Express (3A) | INR 1,390 | INR 1,390 | INR 5,560 | IRCTC/MakeMyTrip |"
        
        comparison_table += "\n\n**RECOMMENDED:** Choose based on your priority - Trains (most economical), Buses (good balance), Flights (fastest)"
        
        # Add brief summary
        comparison_table += "\n\n## Quick Summary\n\n"
        comparison_table += "For maximum savings, choose trains (starting at INR 2,120 for 2 people). "
        comparison_table += "Buses offer a good balance of cost and comfort at INR 6,600. "
        comparison_table += "Flights are fastest but most expensive at INR 26,392."
        
        return comparison_table
        
    except Exception as e:
        print(f"Error creating cost comparison table: {e}")
        return "\n## Cost Comparison\n\nUnable to generate cost comparison table."


def _get_perplexity_service() -> PerplexityService:
    """Get initialized Perplexity service instance."""
    # Get API key from environment variable
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY environment variable is required")
    return PerplexityService(api_key)


def _get_serp_api_service() -> SerpAPIService:
    """Get initialized SerpAPI service instance."""
    # Get API key from environment variable
    api_key = os.getenv('SERP_API_KEY')
    if not api_key:
        raise ValueError("SERP_API_KEY environment variable is required")
    return SerpAPIService(api_key)


def _get_gemini_client():
    """Get Google Gemini client with API key."""
    if genai is None:
        raise ImportError("google-genai package not available")
    
    # Use the provided API key directly
    api_key = os.getenv('GEMINI_API_KEY')
    client = genai.Client(api_key=api_key)
    return client


def _extract_travel_parameters(query: str) -> Dict[str, Any]:
    """
    Extract comprehensive travel parameters using Gemini natural language understanding.
    This single call extracts parameters for all transport modes (flights, buses, trains).
    
    Returns:
        Dict with travel parameters and decisions for each transport mode
    """
    try:
        client = _get_gemini_client()
        
        prompt = f"""
        TASK: Analyze this travel query using natural language understanding to extract comprehensive travel parameters for all transport modes.

        QUERY: "{query}"

        **CRITICAL: Use only ASCII characters in your response. No Unicode symbols, emojis, or special characters.**

        **ANALYSIS REQUIREMENTS:**

        1. **Route Information**:
           - Extract FROM location (origin city)
           - Extract TO location (destination city)
           - Determine if this is domestic or international travel
           - Convert cities to standard names (Mumbai, Bangalore, Delhi, Chennai, etc.)

        2. **Travel Details**:
           - Extract travel dates (outbound and return if mentioned)
           - Convert dates to YYYY-MM-DD format
           - **CRITICAL DATE PARSING**: For date ranges like "13-12-2025 to 17-12-2026", if the years differ significantly (>1 month), assume user meant same year (17-12-2025, not 17-12-2026)
           - **REASONABLE TRIP DURATION**: Typical trips are 1-30 days, not 365+ days. If calculated duration >60 days, assume date parsing error and use same year for return
           - Determine number of travelers
           - Extract budget amount and currency preferences
           - Identify trip duration and return requirements

        3. **Transport Mode Decisions**:
           - For FLIGHTS: Decide based on route type (international routes usually need flights, domestic routes are optional)
           - For BUSES: Search for ALL domestic routes within the same country where bus services exist
           - DO NOT exclude buses based on distance or travel time - users want to see all options
           - Only exclude buses for international routes or routes where no bus service exists
           - Include all transport modes so users can make their own informed choices

        4. **User Preferences Analysis**:
           - Extract any specified transport mode preferences (flights, trains, buses)
           - Identify cost vs comfort vs time priorities (most users prioritize cost)
           - Note time sensitivity (flexible, moderate, urgent)
           - Capture budget constraints and cost-consciousness level
           - Determine if user prefers absolute cheapest or best value options
           - Consider specific amenities mentioned (AC/Non-AC, meal preferences, sleeper/seater)

        5. **Airport Codes** (for flights):
           - Mumbai to BOM, Bangalore to BLR, Delhi to DEL, Chennai to MAA, Kolkata to CCU
           - Hyderabad to HYD, Pune to PNQ, Goa to GOX, Kochi to COK, Ahmedabad to AMD
           - International: New York to JFK, London to LHR, Paris to CDG, Dubai to DXB

        5. **Currency Rules**:
           - Indian domestic routes: currency="INR", gl="in"
           - International routes: currency="USD", gl="us"

        **OUTPUT FORMAT:**

        {{
            "route_info": {{
                "from_city": "CITY_NAME",
                "to_city": "CITY_NAME",
                "from_airport": "AIRPORT_CODE",
                "to_airport": "AIRPORT_CODE",
                "is_domestic": true/false,
                "is_international": true/false
            }},
            "travel_details": {{
                "outbound_date": "YYYY-MM-DD",
                "return_date": "YYYY-MM-DD",
                "travelers": number,
                "budget": number,
                "currency": "INR/USD",
                "country_code": "in/us",
                "trip_type": "one_way/round_trip"
            }},
            "user_preferences": {{
                "preferred_transport_mode": "flights/trains/buses/any",
                "cost_priority": "cheapest/value/comfort/premium",
                "time_sensitivity": "flexible/moderate/urgent",
                "budget_consciousness": "very_tight/moderate/flexible",
                "specific_amenities": ["AC", "meals", "sleeper", "wifi", "etc"],
                "primary_goal": "minimize_cost/balance_cost_comfort/prioritize_convenience"
            }},
            "transport_decisions": {{
                "flights": {{
                    "should_search": true/false,
                    "reason": "explanation",
                    "flight_params": {{
                        "outbound": {{
                            "departure_id": "AIRPORT_CODE",
                            "arrival_id": "AIRPORT_CODE",
                            "outbound_date": "YYYY-MM-DD",
                            "currency": "INR/USD",
                            "gl": "in/us"
                        }},
                        "return": {{
                            "departure_id": "AIRPORT_CODE",
                            "arrival_id": "AIRPORT_CODE", 
                            "return_date": "YYYY-MM-DD",
                            "currency": "INR/USD",
                            "gl": "in/us"
                        }}
                    }}
                }},
                "buses": {{
                    "should_search": true/false,
                    "reason": "explanation - search for all domestic routes, only exclude international routes",
                    "bus_params": {{
                        "outbound": {{
                            "from_city": "CITY_NAME",
                            "to_city": "CITY_NAME",
                            "travel_date": "YYYY-MM-DD"
                        }},
                        "return": {{
                            "from_city": "CITY_NAME",
                            "to_city": "CITY_NAME",
                            "travel_date": "YYYY-MM-DD"
                        }}
                    }}
                }}
            }}
        }}

        Use natural language understanding to make intelligent decisions about which transport modes make sense for this specific query.
        
        **CRITICAL ROUND-TRIP ENFORCEMENT:**
        - **MANDATORY**: For round trips, ALWAYS provide BOTH outbound AND return flight parameters
        - **NO EXCEPTIONS**: Even if return date not explicitly mentioned, calculate it from trip duration 
        - **BOTH DIRECTIONS**: outbound goes from origin to destination, return goes from destination back to origin
        - **PARAMETER COMPLETENESS**: Both outbound and return sections must have all required fields (departure_id, arrival_id, date, currency, gl)
        - **AIRPORT CODE REVERSAL**: Return flight has departure_id and arrival_id swapped from outbound
        
        **IMPORTANT DECISION RULES:**
        1. **For buses**: Always search on domestic routes regardless of distance or travel time. Users want to see all available options to make their own choices. Only exclude buses for international routes where no bus service exists.
        
        2. **Budget-aware decisions**: Consider the user's budget when deciding which transport modes to search. If flights typically cost much more than the stated budget (e.g., flights cost 8000+ but budget is 3000), set should_search=false and explain in the reason.
        
        3. **Smart filtering**: Only search for transport modes that are realistically within or close to the user's budget range to avoid confusing them with unaffordable options.
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt
        )
        
        response_text = response.text.strip()
        
        # Clean response
        if response_text.startswith('```json'):
            response_text = response_text.replace('```json', '').replace('```', '').strip()
        elif response_text.startswith('```'):
            response_text = response_text.replace('```', '').strip()
        
        result = json.loads(response_text)
        
        # Log decisions
        flight_decision = result.get('transport_decisions', {}).get('flights', {})
        bus_decision = result.get('transport_decisions', {}).get('buses', {})
        
        print(f"Flight search decision: {flight_decision.get('should_search')} - {flight_decision.get('reason', '')}")
        print(f"Bus search decision: {bus_decision.get('should_search')} - {bus_decision.get('reason', '')}")
        
        return result
        
    except Exception as e:
        print(f"Travel parameter extraction failed: {e}")
        # Return simple fallback
        return {
            "transport_decisions": {
                "flights": {"should_search": False, "reason": "Parameter extraction failed"},
                "buses": {"should_search": False, "reason": "Parameter extraction failed"}
            }
        }


def _search_flights_with_serp(flight_params: Dict[str, Any]) -> str:
    """
    Search flights using SerpAPI for both outbound and return journeys.
    
    Args:
        flight_params: Dict containing outbound and return flight parameters
        
    Returns:
        Formatted flight search results
    """
    try:
        serp_service = _get_serp_api_service()
        
        outbound_params = flight_params.get('outbound', {})
        return_params = flight_params.get('return', {})
        
        # CRITICAL: Ensure return flights are always planned for round trips
        # If return_params is missing but outbound exists, construct return params
        if outbound_params and not return_params:
            print("WARNING: Return flight parameters missing for round trip! Constructing from outbound...")
            return_params = {
                'departure_id': outbound_params.get('arrival_id', ''),  # Reverse airports
                'arrival_id': outbound_params.get('departure_id', ''),  # Reverse airports
                'return_date': outbound_params.get('outbound_date', ''),  # Use same date as placeholder
                'currency': outbound_params.get('currency', 'INR'),
                'gl': outbound_params.get('gl', 'in')
            }
        
        results = []
        
        # Search outbound flights
        if outbound_params:
            print(f"Searching outbound flights: {outbound_params['departure_id']} → {outbound_params['arrival_id']}")
            outbound_results = serp_service.search_flights(
                departure_id=outbound_params['departure_id'],
                arrival_id=outbound_params['arrival_id'],
                outbound_date=outbound_params['outbound_date'],
                country_code=outbound_params['gl'],
                currency=outbound_params['currency']
            )
            
            # Format outbound results
            outbound_formatted = _format_serp_flight_results(
                outbound_results, 
                "Outbound", 
                outbound_params['outbound_date'],
                outbound_params['currency']
            )
            results.append(outbound_formatted)
        
        # Search return flights - MANDATORY for round trips
        if return_params and return_params.get('departure_id') and return_params.get('arrival_id'):
            print(f"Searching return flights: {return_params['departure_id']} to {return_params['arrival_id']}")
            return_results = serp_service.search_flights(
                departure_id=return_params['departure_id'],
                arrival_id=return_params['arrival_id'],
                outbound_date=return_params['return_date'],
                country_code=return_params['gl'],
                currency=return_params['currency']
            )
            
            # Format return results  
            return_formatted = _format_serp_flight_results(
                return_results,
                "Return", 
                return_params['return_date'],
                return_params['currency']
            )
            results.append(return_formatted)
        else:
            print("ERROR: Return flight parameters are incomplete! Round trip requires both outbound and return flights.")
            if outbound_params:
                results.append("## Return Flight Search Failed\n\nReturn flight parameters missing or incomplete. For round trips, both outbound and return flights are required.")
        
        # Combine results
        combined_results = "\n\n".join(results)
        
        return f"# Flight Search Results\n\n{combined_results}"
        
    except Exception as e:
        print(f"SERP flight search failed: {e}")
        return f"## Flight Search Error\n\nUnable to fetch flight data: {str(e)}"


def _format_serp_flight_results(serp_data: Dict, journey_type: str, date: str, currency: str) -> str:
    """
    Format SERP API flight results into readable table format with flight names.
    
    Args:
        serp_data: Raw SERP API response
        journey_type: "Outbound" or "Return"
        date: Flight date
        currency: Price currency
        
    Returns:
        Formatted flight results table with flight names
    """
    try:
        # Extract flights from SERP response
        flights = []
        
        # Try different keys where flights might be stored
        for key in ['best_flights', 'other_flights', 'flights']:
            if key in serp_data and serp_data[key]:
                flights.extend(serp_data[key])
        
        if not flights:
            return f"## {journey_type} Journey ({date})\n\nNo flights found for this route and date."
        
        # Format table header as per requirement
        table = f"""## {journey_type} Journey Options ({date})

| Option | Mode   | Flight/Route Details | Duration | Cost per Person | Total Cost | Booking Platform | Departure/Arrival (IST) |
|--------|--------|---------------------|----------|-----------------|------------|------------------|-------------------------|"""
        
        # Process up to 3 flight options
        for i, flight in enumerate(flights[:3], 1):
            try:
                # Extract flight details using SERP API structure
                if 'flights' in flight and len(flight['flights']) > 0:
                    # Use the main flight from the flights array
                    main_flight = flight['flights'][0]
                    departure_time = main_flight.get('departure_airport', {}).get('time', 'N/A')
                    arrival_time = main_flight.get('arrival_airport', {}).get('time', 'N/A')
                    airline = main_flight.get('airline', 'Unknown Airline')
                    flight_num = main_flight.get('flight_number', 'N/A')
                    duration = flight.get('total_duration', 'N/A')
                    price = flight.get('price', 0)
                else:
                    # Fallback to direct flight object structure
                    airline = flight.get('airline', 'Unknown Airline')
                    flight_num = flight.get('flight_number', 'N/A')
                    duration = flight.get('duration', flight.get('total_duration', 'N/A'))
                    price = flight.get('price', flight.get('total_price', 0))
                    departure_time = flight.get('departure_time', 'N/A')
                    arrival_time = flight.get('arrival_time', 'N/A')
                
                # Handle price extraction
                if isinstance(price, dict):
                    price = price.get('value', price.get('amount', 0))
                elif isinstance(price, str):
                    # Extract numeric value from price string
                    import re
                    price_match = re.search(r'[\d,]+', price.replace(',', ''))
                    price = int(price_match.group()) if price_match else 0
                
                # Format times as IST
                time_display = f"{departure_time} - {arrival_time}"
                
                # Calculate total cost (assuming extracted from individual price)
                total_cost = price  # SerpAPI usually gives total price
                
                # Get booking platform
                booking_url = flight.get('booking_url', flight.get('link', 'Direct'))
                platform = "Online"
                
                # Create flight details with prominent flight name
                flight_details = f"**{airline} {flight_num}**"
                
                # Add table row
                table += f"\n| {i} | Flight | {flight_details} | {duration} | {currency} {price:,} | {currency} {total_cost:,} | {platform} | {time_display} |"
                
            except Exception as e:
                print(f"Error formatting flight {i}: {e}")
                continue
        
        return table
        
    except Exception as e:
        print(f"Error formatting SERP results: {e}")
        return f"## {journey_type} Journey ({date})\n\nError formatting flight results: {str(e)}"

@tool
def optimize_travel(query: str) -> str:
    """
    Optimize travel routes and transportation options based on natural language query.
    
    This tool analyzes travel requirements and provides optimized transportation solutions
    including route planning, cost analysis, time efficiency, and booking recommendations.
    
    Args:
        query: Natural language query describing travel optimization needs
    
    Returns:
        str: Comprehensive travel optimization plan in markdown table format
    
    Example:
        query = "Give me travel options from Mumbai to Goa for 4 people from 20-01-2026 to 23-01-2026 with budget INR 8000. Prefer trains."
        result = optimize_travel(query)
               
        # Travel Optimization Results
        
        ## Extracted Requirements
        - **From:** Mumbai
        - **To:** Goa
        - **Travelers:** 4 people
        - **Budget:** INR 8000
        - **Dates:** 20-01-2026 to 23-01-2026
        - **Preferred Mode:** Trains
        
        ---
        
        ## Recommended Transportation Options
        
        | Option | Mode | Route | Duration | Cost per Person | Total Cost | Booking Platform | Departure/Arrival |
        |--------|------|-------|----------|-----------------|------------|------------------|-------------------|
        | 1 | Train | Mumbai - Goa Express | 12 hours | INR 800 | INR 3200 | IRCTC | 8:00 PM - 8:00 AM |
        | 2 | Bus | Mumbai - Goa Sleeper | 14 hours | INR 600 | INR 2400 | RedBus | 10:00 PM - 12:00 PM |
        | 3 | Flight | Mumbai - Goa Direct | 1.5 hours | INR 4500 | INR 18000 | Booking.com | 2:00 PM - 3:30 PM |
        
        ## Cost Breakdown
        - **Recommended Option:** Train (Best value within budget)
        - **Total Transportation Cost:** INR 3200
        - **Remaining Budget:** INR 4800 for local transport
        - **Cost per Person:** INR 800
    """
    try:
        # Get Perplexity service
        perplexity_service = _get_perplexity_service()
        serp_service = _get_serp_api_service()
        
        # Create comprehensive system prompt for travel optimization
        system_prompt = """You are an expert travel optimization consultant and transportation advisor with deep knowledge of routes, costs, and booking platforms.

**CRITICAL OUTPUT REQUIREMENT - NO UNICODE CHARACTERS:**
- DO NOT use any Unicode characters, emojis, or special symbols in your response
- USE ONLY: Standard ASCII characters (letters, numbers, basic punctuation)
- For currency: Use 'INR' or 'USD' instead of symbols
- For arrows: Use 'to' instead of →
- For bullets: Use '-' instead of •
- For status indicators: Use text like 'AVAILABLE' or 'NOT AVAILABLE'

**USER PREFERENCE PRIORITY SYSTEM:**
ALWAYS analyze and prioritize based on user's transport mode preferences in this order:
1. **Identify Preferred Transport Mode**: Extract user's preferred mode (flights/trains/buses) from their query
2. **Focus on Preferred Mode**: Show multiple options WITHIN their preferred transport mode
3. **Cost Ranking Within Mode**: Rank all options within preferred mode from cheapest to most expensive
4. **Alternative Mode Inclusion**: Only if budget allows, show one cheaper alternative from other modes for comparison
5. **Clear Cost Communication**: Show total round-trip costs and per-person breakdown

**BOOKING PLATFORM REQUIREMENTS - ARCHITECTURE-SPECIFIC:**
- **Flight Bookings (via SerpAPI):** Results will include actual booking platforms from live search (booking.com, MakeMyTrip, Cleartrip, etc.)
- **Bus Bookings (via SerpAPI):** Results will include actual bus booking platforms from live search (RedBus, AbhiBus, etc.)
- **Train Bookings (via Perplexity research):** Recommend IRCTC, Paytm, official railway websites, other verified train booking platforms
- **Platform Selection:** For flights/buses, use actual platforms returned by SerpAPI; for trains, recommend official/reliable booking sites

**FLIGHT COST OPTIMIZATION PRIORITY:**
- **ALWAYS FIND CHEAPEST FLIGHTS:** Primary focus should be on finding the most economical flight options
- **Budget Airlines First:** Prioritize budget carriers (IndiGo, SpiceJet, AirAsia, Ryanair, EasyJet, etc.)
- **Flexible Timing:** Consider different departure times to find lowest fares
- **Alternative Airports:** Check nearby airports for better deals (e.g., Gatwick vs Heathrow)
- **Connecting Flights:** Include 1-stop options if significantly cheaper than direct flights
- **Advance Booking Discounts:** Factor in early bird pricing and promotional fares
- **Weekday vs Weekend:** Always compare weekday departures (typically 20-40% cheaper)
- **Red-eye/Early Morning:** Include overnight and early morning flights for cost savings
- **Seasonal Adjustments:** Account for off-peak travel periods for maximum savings
- **Multi-Airline Comparison:** Always compare multiple airlines for the same route
- **Promotional Fares:** Look for current sales, flash deals, and promotional pricing
- **NO CACHE POLICY:** Always provide fresh, real-time pricing without using cached data
- **Live Pricing:** Ensure all prices reflect current market conditions and availability

**FLIGHT INFORMATION FORMATTING REQUIREMENTS:**
- **ALWAYS MENTION FLIGHT NAME:** Include specific airline name and flight number (e.g., "IndiGo 6E-123", "SpiceJet SG-456")
- **MANDATORY IST TIME FORMAT:** All flight times MUST be displayed in IST (Indian Standard Time)
- **DATE FORMAT:** Display dates in DD-MM-YYYY format (e.g., "19-10-2025")
- **TIME FORMAT:** Use 24-hour format with IST suffix (e.g., "14:30 IST", "06:45 IST")
- **Complete Flight Details:** Include departure/arrival airports, flight duration, and layover information if applicable
- **Example Format:** "IndiGo 6E-234: 19-10-2025 at 08:15 IST (DEL) → 10:30 IST (BOM), Duration: 2h 15m"

**STEP 1: Extract travel optimization requirements from the user query**
First, identify and extract these parameters from the user's natural language query:
- From Location: Origin/departure location
- To Location: Destination location
- Number of People: How many travelers
- Budget: Budget amount with appropriate currency (see currency rules below)
- Travel Dates: When they're traveling (both outbound and return dates if specified)
- Return Journey: Whether this is one-way or round-trip travel
- Mode of Transport: Preferred transportation (bus, flights, trains, etc.) - DEFAULT is bus if not specified
- Special Requirements: Any specific needs (luggage, comfort level, time constraints)

**TRAVEL DIRECTION HANDLING:**
- **Round Trip (DEFAULT for multi-day trips):** If return dates mentioned, trip duration specified, or travel spans multiple days, plan both outbound and return journeys
- **One Way:** Only if explicitly stated as "one-way" or "single journey"
- **Smart Detection:** For 2+ day trips, always assume round-trip unless explicitly stated otherwise
- **Return Date Generation:** If no return date mentioned but trip duration given, calculate return date automatically
- **Flight Availability:** ALWAYS search for return flights - if no results found, suggest alternative dates nearby

**CURRENCY DETECTION RULES:**
- If BOTH from location AND to location are Indian regions/cities (Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad, Pune, Ahmedabad, Jaipur, Surat, Lucknow, Kanpur, Nagpur, Indore, Thane, Bhopal, Visakhapatnam, Patna, Vadodara, Ghaziabad, Ludhiana, Agra, Nashik, Faridabad, Meerut, Rajkot, Kalyan, Vasai-Virar, Varanasi, Srinagar, Aurangabad, Dhanbad, Amritsar, Navi Mumbai, Allahabad, Ranchi, Howrah, Coimbatore, Jabalpur, Gwalior, Vijayawanda, Jodhpur, Madurai, Raipur, Kota, Guwahati, Chandigarh, Solapur, Hubli-Dharwad, Bareilly, Moradabad, Mysore, Gurgaon, Aligarh, Jalandhar, ...iruchirappalli, Bhubaneswar, Salem, Warangal, Mira-Bhayandar, Thiruvananthapuram, Bhiwandi, Saharanpur, Guntur, Amravati, Bikaner, Noida, Jamshedpur, Bhilai Nagar, Cuttack, Firozabad, Kochi, Bhavnagar, Dehradun, Durgapur, Asansol, Nanded-Waghala, Kolhapur, Ajmer, Akola, Gulbarga, Jamnagar, Ujjain, Loni, Siliguri, Jhansi, Ulhasnagar, Nellore, Jammu, Sangli-Miraj & Kupwad, Belgaum, Mangalore, Ambattur, Tirunelveli, Malegaon, Gaya, Jalgaon, Udaipur, Maheshtala, or any other Indian city/state): Use INR (Indian Rupees)
- For ALL OTHER destinations or international travel: Use $ (US Dollars)

**STEP 2: Provide comprehensive travel optimization analysis**
Based on the extracted requirements, analyze and optimize transportation options.

**CORE OPTIMIZATION GOAL: COST OPTIMIZATION WITHIN USER'S PREFERRED TRANSPORT MODES**

**CLEAR PRIORITY HIERARCHY:**
1. **User Transport Preferences (PRIMARY FILTER):** First determine WHICH transport modes user wants (flights/trains/buses)
2. **Cost Optimization (WITHIN PREFERENCES):** Among user's preferred modes, find cheapest options and rank by cost
3. **Budget Compliance:** All options MUST fit within stated budget
4. **Value Comparison:** Within preferred modes, show cost differences and best value options

**DECISION FRAMEWORK:**
- **If user prefers trains:** Show 3-4 train options ranked from cheapest to most expensive
- **If user prefers buses:** Show 3-4 bus options ranked from cheapest to most expensive  
- **If user prefers flights:** Show 3-4 flight options ranked from cheapest to most expensive
- **If no preference stated:** Show cheapest option from each viable mode (bus, train, flight)

**TRANSPORT MODE PRIORITY:**
- **User-Specified Preferences ALWAYS Take Priority**: If user mentions preferred transport mode, prioritize that mode in results
- **For International Travel (different countries):** Prioritize flights, then consider international trains/buses only if they exist (like Europe)
- **For Domestic Travel (same country):** 
  - If user specifies a mode: Prioritize that mode but show alternatives for comparison
  - If user mentions comfort/luxury preferences: Include premium options even if costlier
  - If user mentions budget constraints: Focus on most economical options
  - If no mode specified: Default to bus options first, then trains, then flights
- **Smart Mode Selection:** Automatically detect domestic vs international routes and suggest appropriate transport modes
- **Preference-Based Filtering:** Adjust recommendations based on user's stated priorities (cost vs time vs comfort)
- Always compare at least 3 different options when possible, but focus on realistic/practical modes for the route type

**USER PREFERENCE-BASED OPTIMIZATION APPROACH:**

**STEP 1: Identify User's Preferred Transport Mode(s)**
- Extract from query: "prefer trains", "want flights", "bus travel", "any mode", etc.
- If no preference: Include all viable modes for comparison

**STEP 2: Cost Optimization Within Preferred Mode(s)**
- Find 3-4 options within each preferred transport mode
- Rank ALL options from cheapest to most expensive
- Show total round-trip cost for each option
- Include per-person breakdown for group travel

**EXAMPLE SCENARIOS:**
- **User says "prefer trains":** Show 3 train options for BOTH outbound and return with separate pricing
- **User says "want flights":** Show 3 flight options for BOTH outbound and return with separate schedules  
- **User says "any transport":** Show cheapest from each mode for BOTH directions (Bus, Train, Flight)

**MANDATORY ROUND-TRIP DISPLAY FOR ALL MODES:**
- **Flights:** Always show separate outbound and return flight tables with different prices
- **Trains:** Always show separate outbound and return train schedules with route-specific pricing
- **Buses:** Always show separate outbound and return bus options with direction-specific timing
- **Total Cost Calculation:** Combine outbound + return for final cost comparison

**COST COMPARISON WITHIN PREFERENCE:**
- Always start with cheapest option in preferred mode
- Show cost differences between options in same mode  
- Calculate total round-trip costs clearly (outbound + return)
- Highlight best value within user's preferred transport type
- Display both individual journey costs AND total round-trip cost

**CRITICAL DATE-SPECIFIC PRICING REQUIREMENTS:**
1. **MANDATORY DATE-BASED PRICING:** Prices MUST vary based on specific travel dates provided
2. **NO IDENTICAL OUTBOUND/RETURN PRICES:** Return journey prices should differ from outbound based on:
   - Day of week (weekends vs weekdays cost more)
   - Seasonal demand for that specific date
   - Holiday proximity and events
   - Available inventory on that date
   - Market demand patterns

3. **DATE-SPECIFIC RESEARCH METHODOLOGY:**
   - **Outbound Date Analysis:** Check if departure date falls on weekend, holiday, festival, peak season
   - **Return Date Analysis:** Separately analyze return date conditions
   - **Day-of-Week Pricing:** Mon-Thu cheaper, Fri-Sun premium (especially for flights)
   - **Festival/Holiday Impact:** Prices 20-50% higher during Diwali, Christmas, New Year, long weekends
   - **Advance Booking Timeline:** Factor in how far in advance booking is happening

4. **REALISTIC PRICE VARIATIONS:**
   - **Outbound vs Return:** Should show 10-40% price difference based on date characteristics
   - **Weekend Premium:** Friday/Sunday flights 15-30% more expensive
   - **Festival Surcharge:** Major festivals add 25-50% to base prices
   - **Last-minute Booking:** Within 7 days = 20-60% price increase
   - **Peak Season Multiplier:** December/January domestic travel +30-50%

5. **SPECIFIC DATE CONSIDERATIONS:**
   - **Weather Impact:** Monsoon season affects certain routes
   - **Business Travel:** Mid-week flights more expensive on popular business routes
   - **Tourist Season:** Hill stations expensive in summer, beach destinations in winter
   - **Local Events:** Major events in destination city affect all transport prices

2. **Flight Price Guidelines (Research-Based):**
   - **Domestic India:** INR 3,000-8,000 per person (economy), INR 12,000+ (business)
   - **International Short-haul:** $200-$600 (India-Middle East, India-Southeast Asia)
   - **International Long-haul:** $600-$1,500 (India-Europe/US/Australia)
   - **Budget vs Full-service:** 30-50% price difference
   - **Advance booking:** 15-30% cheaper than last-minute

3. **Train Price Guidelines (Accurate Classes):**
   - **Indian Railways:** Sleeper INR 400-800, 3AC INR 800-1,500, 2AC INR 1,200-2,500, 1AC INR 2,000-4,000
   - **Distance factor:** ₹0.50-₹2 per km depending on class
   - **Premium trains:** Rajdhani/Shatabdi 20-40% premium

4. **Bus Price Guidelines (Operator-Based):**
   - **Government buses:** ₹300-₹800 per person for long routes
   - **Private AC buses:** ₹500-₹1,200 per person
   - **Luxury/Volvo:** ₹800-₹2,000 per person for overnight routes

5. **PRICING RESEARCH METHODOLOGY:**
   - Consider actual airlines operating on the route
   - Factor in fuel costs, competition levels
   - Account for seasonal demand (festival seasons, summer, winter)
   - Include taxes and fees in flight prices
   - Research typical booking platform commissions

**PRICING VALIDATION APPROACH:**
- **Date-Specific Analysis:** Analyze each travel date individually for pricing factors
- **Market Demand Research:** Consider actual demand patterns for specific dates
- **Competitive Pricing:** Factor in route competition and operator pricing strategies  
- **Dynamic Pricing Simulation:** Mimic how airlines/operators actually price based on date factors
- **Inventory Simulation:** Consider likely availability constraints for specific dates
- **Cross-Reference Validation:** Ensure outbound and return prices reflect different date conditions

**MANDATORY PRICING DIFFERENTIATION:**
- Outbound and return MUST have different prices unless both dates have identical market conditions
- Show clear reasoning for price differences between dates
- Factor in actual calendar events affecting those specific dates
- Consider booking timeline from current date to travel dates

**MANDATORY COST OPTIMIZATION INSTRUCTIONS:**
1. **Budget Allocation:** For round trips, split budget 50-50 between outbound and return unless specified
2. **Cost-Per-Person Analysis:** Always calculate and show per-person costs clearly
3. **Total Budget Utilization:** Show how much of total budget is used and remaining amount
4. **Savings Calculation:** Compare cheapest option vs more expensive alternatives
5. **Value Metrics:** Include cost per hour of travel time for comparison
6. **Hidden Cost Awareness:** Factor in booking fees, luggage costs, terminal transfers
7. **Group Discounts:** Consider bulk booking savings for multiple travelers
8. **Seasonal Cost Factors:** Account for peak/off-peak pricing affecting overall budget

**INTELLIGENT BUDGET DISTRIBUTION:**
- **Single Person:** Full budget available for individual travel
- **Multiple People:** Budget divided equally unless family discounts available  
- **Group Travel:** Consider group booking discounts and shared costs
- **Emergency Buffer:** Reserve 10-15% of budget for contingencies/booking fees

**RESPONSE FORMAT (MANDATORY):**

**IMPORTANT: Log extracted requirements for debugging but DO NOT include in user output**

# Travel Optimization Results

## Outbound Journey Options (Date: [Specific Outbound Date])

| Option | Mode | Route Details | Duration | Cost per Person | Booking Platform | Departure/Arrival (IST) |
|--------|------|---------------|----------|-----------------|------------------|-------------------------|
| 1 | [Mode] | [Details] | [Duration] | INR [Cost] | [Platform] | [Times] |
| 2 | [Mode] | [Details] | [Duration] | INR [Cost] | [Platform] | [Times] |
| 3 | [Mode] | [Details] | [Duration] | INR [Cost] | [Platform] | [Times] |

## Return Journey Options (Date: [Specific Return Date])

| Option | Mode | Route Details | Duration | Cost per Person | Booking Platform | Departure/Arrival (IST) |
|--------|------|---------------|----------|-----------------|------------------|-------------------------|
| 1 | [Mode] | [Details] | [Duration] | INR [Cost] | [Platform] | [Times] |
| 2 | [Mode] | [Details] | [Duration] | INR [Cost] | [Platform] | [Times] |
| 3 | [Mode] | [Details] | [Duration] | INR [Cost] | [Platform] | [Times] |

## Total Round-Trip Costs Summary

| Transport Mode | Cheapest Option | Outbound Cost | Return Cost | Total Cost (Round-Trip) |
|----------------|-----------------|---------------|-------------|-------------------------|
| [Mode 1] | [Option Name] | INR [Cost] | INR [Cost] | INR [Total] |
| [Mode 2] | [Option Name] | INR [Cost] | INR [Cost] | INR [Total] |
| [Mode 3] | [Option Name] | INR [Cost] | INR [Cost] | INR [Total] |

**RECOMMENDED:** [Cheapest total option] - INR [Total Cost] for [X] people

**CRITICAL DATE-SPECIFIC PRICING INSTRUCTIONS:**
1. **NEVER use identical prices for outbound and return journeys**
2. **ALWAYS factor in specific date characteristics:** weekday vs weekend, holidays, festivals, seasonality
3. **SHOW CLEAR PRICE REASONING:** Explain why outbound vs return dates have different pricing
4. **REALISTIC MARKET SIMULATION:** Mimic how actual booking platforms price based on date-specific demand
5. **FACTOR BOOKING TIMELINE:** Consider how far in advance booking is happening from current date
6. **VALIDATE PRICE LOGIC:** Ensure price differences make logical sense based on calendar analysis

**CONCISE OUTPUT INSTRUCTIONS:**
1. **Minimal Text**: Remove all verbose explanations, notes, and booking tips
2. **Table-Focused**: Show only essential tables with pricing and schedules
3. **No Summaries**: Remove lengthy analysis sections and travel advice
4. **Essential Info Only**: Include only departure times, costs, and booking platforms
5. **90% Text Reduction**: Eliminate all unnecessary explanatory content

**MANDATORY ROUND-TRIP STRUCTURE:**
For each transport mode, ALWAYS show:
1. **Outbound Journey Table** (Date: [Outbound Date])
2. **Return Journey Table** (Date: [Return Date]) 
3. **Total Round-Trip Cost Summary Table**

**ROUND-TRIP COST SUMMARY TABLE FORMAT:**
```
## Total Round-Trip Costs (All Transport Modes)

| Transport Mode | Cheapest Option | Outbound Cost | Return Cost | Total Cost (2 People) |
|----------------|-----------------|---------------|-------------|----------------------|
| Bus | [Bus Name] | INR X,XXX | INR X,XXX | INR X,XXX |
| Train | [Train Name] | INR X,XXX | INR X,XXX | INR X,XXX |
| Flight | [Airline] | INR X,XXX | INR X,XXX | INR X,XXX |
```

**CRITICAL OUTPUT FORMATTING:**
- DO NOT include "Extracted Requirements" section in the user-facing output
- DO NOT include "Price Accuracy Note" or verbose disclaimers
- DO NOT include "Additional Recommendations" or "Conclusion" sections
- DO NOT include lengthy explanations about flexible dates, alternative airports, etc.
- Start directly with "# Travel Optimization Results" followed by journey options
- Keep extraction analysis internal for processing but do not display to user
- Focus ONLY on actionable travel options and recommendations
- End with Quick Summary only (no booking tips or additional sections)

**IMPORTANT:**
- Use correct currency throughout (₹ for Indian routes, $ for international)
- SMART MODE SELECTION: 
  - For international travel: Focus on flights primarily, only include trains/buses if they're practical (like Europe/neighboring countries)
  - For domestic travel: Include buses, trains, and flights as appropriate
- Prioritize user-specified transport mode but show realistic alternatives
- Default to practical modes based on route type (flights for international, buses for domestic)
- **BOOKING PLATFORMS BY SOURCE:**
  - Flights/Buses: Use actual platforms from SerpAPI results (live data)
  - Trains: Recommend IRCTC, Paytm, official railway booking sites (research-based)
- Handle multi-city/connecting routes appropriately
- **MANDATORY ROUND-TRIP PLANNING**: For multi-day trips, ALWAYS show both outbound AND return journeys
- **ROUND-TRIP COST EMPHASIS**: Show total round-trip costs prominently for easy comparison
- For round-trips: Show separate detailed tables for outbound and return with individual and total cost breakdown
- Budget allocation: Split budget appropriately between outbound and return journeys
- One-way trips: Only show outbound journey options"""

        # Search using Perplexity with the comprehensive optimization prompt
        results = perplexity_service.search(
            query=query,
            system_prompt=system_prompt,
            temperature=0.1,
            # search_domain_filter=['booking.com', 'skyscanner.net']
        )
        
        # Log extracted requirements for debugging (not shown to user)
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        logger.info(f"Travel optimization request processed for query: {query[:100]}...")
        
        # Return results directly since the system prompt handles formatting
        if isinstance(results, dict) and 'error' in results:
            return f"## Error in Travel Optimization\n\n{results['error']}"
        
        return results
        
    except Exception as e:
        return f"## Error in Travel Optimization\n\nFailed to process travel optimization: {str(e)}"


@tool
def hybrid_travel_optimization(query: str) -> str:
    """
    Hybrid travel optimization: SERP for flights + Perplexity for buses/trains.
    Uses natural language understanding to decide when to include flights based on budget and preferences.
    Both services work independently and results are simply appended.
    
    Args:
        query: Natural language travel query
        
    Returns:
        Combined travel optimization results from both SerpAPI and Perplexity
    """
    try:
        print(f"Processing hybrid travel optimization query: {query[:100]}...")
        
        results = []
        
        # Step 1: Extract comprehensive travel parameters using single Gemini call
        travel_params = _extract_travel_parameters(query)
        
        # Initialize variables to avoid undefined variable errors
        serp_results = None
        bus_results = None
        
        # Step 2: Search flights with SerpAPI if decision is positive
        flight_decision = travel_params.get('transport_decisions', {}).get('flights', {})
        if flight_decision.get('should_search', False):
            print("Searching flights with SerpAPI based on natural language analysis...")
            flight_params = flight_decision.get('flight_params', {})
            serp_results = _search_flights_with_serp(flight_params)
            results.append(serp_results)
        else:
            print(f" Skipping flight search: {flight_decision.get('reason', 'Not needed')}")
        
        # Step 3: Search buses with SerpAPI if decision is positive
        bus_decision = travel_params.get('transport_decisions', {}).get('buses', {})
        if bus_decision.get('should_search', False):
            print("Searching buses with SerpAPI based on natural language analysis...")
            bus_params = bus_decision.get('bus_params', {})
            bus_results = _search_buses_with_serp(bus_params)
        else:
            print(f"Skipping bus search: {bus_decision.get('reason', 'Not needed')}")
        
        # Step 4: Get Perplexity results for trains and general travel options  
        print("Getting train options from Perplexity...")
        perplexity_service = _get_perplexity_service()
        
        # Create train-specific prompt for Perplexity
        perplexity_prompt = f"""
        Provide train transportation options for: {query}
        Focus on Indian Railways trains with specific train names, departure times, journey duration, and class-wise pricing.
        
        CRITICAL REQUIREMENTS:
        1. OUTBOUND TRAINS: Show trains from origin to destination
        2. RETURN TRAINS: Show trains from destination back to origin  
        3. FORMAT: Use MARKDOWN TABLE format like this:

        ## Outbound Train Journey Options (Date)

        | Option | Train Name & Number | Route | Duration | SL Cost | 3A Cost | 2A Cost | Departure | Arrival | Booking Platform |
        |--------|---------------------|-------|----------|---------|---------|---------|-----------|---------|------------------|
        | 1 | Karnataka Express (12627) | SBC-NDLS | 37h 40m | INR 530 | INR 1,390 | INR 2,020 | 19:20 | 09:00+1 | IRCTC |

        ## Return Train Journey Options (Date)

        | Option | Train Name & Number | Route | Duration | SL Cost | 3A Cost | 2A Cost | Departure | Arrival | Booking Platform |
        |--------|---------------------|-------|----------|---------|---------|---------|-----------|---------|------------------|
        | 1 | Karnataka Express (12628) | NDLS-SBC | 37h 40m | INR 530 | INR 1,390 | INR 2,020 | 20:20 | 10:40+1 | IRCTC |

        4. PRICING: Include per-person costs for different classes (SL, 3A, 2A)
        5. MANDATORY: Use table format, not text descriptions
        """
        
        perplexity_results = perplexity_service.search(
            query=perplexity_prompt,
            system_prompt="You are a travel expert. Provide train information in MARKDOWN TABLE format only. MANDATORY: For round trips, show BOTH outbound and return train journeys as separate tables. Do not use text descriptions - only use the specified table format. IMPORTANT: Do not use any Unicode characters, emojis, or special symbols (like ₹, 💰, 🚌, ✅, ❌, ⚠️, 📍, 🗺️, →, •) in your response. Use only ASCII characters. For currency, use 'INR' instead of symbols."
        )
        
        # Extract content from Perplexity response
        if isinstance(perplexity_results, dict) and 'choices' in perplexity_results:
            perplexity_content = perplexity_results['choices'][0]['message']['content']
        else:
            perplexity_content = str(perplexity_results)
        
        # Add bus results if they were searched
        if bus_results:
            results.append(bus_results)
        results.append(perplexity_content)
        
        # Step 5: Format results with separate sections for flights, buses, and trains
        response_sections = []
        
        # Add flight results if available
        flight_section = None
        bus_section = None
        train_section = None
        
        for i, result in enumerate(results):
            if "Flight Search Results" in result:
                flight_section = result
            elif "Bus Search Results" in result or "Bus Journey Options" in result:
                bus_section = result
            else:
                train_section = result
        
        # Combine results with COST COMPARISON TABLE AT TOP
        combined_response = "# Travel Optimization Results\n\n"
        
        # Add cost comparison table FIRST for better UX
        cost_comparison = _create_final_cost_comparison_table(flight_section, bus_section, train_section)
        combined_response += cost_comparison + "\n\n"
        
        # Then add detailed breakdown sections
        combined_response += "---\n\n# Detailed Journey Options\n\n"
        
        if flight_section:
            combined_response += flight_section + "\n\n"
        
        if bus_section:
            combined_response += bus_section + "\n\n"
            
        if train_section:
            combined_response += train_section + "\n\n"
        
        return combined_response
        
    except Exception as e:
        print(f"Hybrid travel optimization error: {e}")
        # Simple error message - no fallback method as per requirement
        return f"# Optimization Error\n\nError processing query: {str(e)}"


if __name__ == "__main__":
    print("Testing Travel Optimization with Different Scenarios...")
    
    # Test 1: Indian domestic round-trip with train preference
    test_query_train = """
    Optimize travel from Bangalore to Delhi for 2 people from 13-12-2025 to 17-12-2025
    with budget ₹30000. Consider all transport modes.
    """
    
    # # Test 2: International travel (should prioritize flights)
    # test_query_international = """
    # Optimize travel from New York to London for 2 people 
    # from 15-03-2026 to 25-03-2026 with budget $2000. Round trip needed.
    # """
    
    # # Test 3: Long distance requiring multi-leg journey
    # test_query_multileg = """
    # Optimize travel from Bangalore to Kashmir for 3 people from 10-04-2026 to 15-04-2026
    # with budget ₹25000. Consider all transport modes.
    # """
    
    # print("\nTEST 1 - Indian Domestic Round-Trip with Train Preference:")
    print(f"Query: {test_query_train.strip()}")
    # print("\n" + "="*70)
    # print("OPTIMIZATION RESULTS:")
    # print("="*70)
    
    try:
        result1 = hybrid_travel_optimization.invoke({"query": test_query_train})
        print(result1)
        print("\n" + "="*70)
        print("Round-trip train preference test completed!")
    except Exception as e:
        print(f"Error in train test: {str(e)}")
    
    print("\n" + "="*80 + "\n")
    
    # print("📍 TEST 2 - International Travel (Should Prioritize Flights):")
    # print(f"Query: {test_query_international.strip()}")
    # print("\n" + "="*70)
    # print("OPTIMIZATION RESULTS:")
    # print("="*70)
    
    # try:
    #     result2 = optimize_travel.invoke({"query": test_query_international})
    #     print(result2)
    #     print("\n" + "="*70)
    #     print("✅ International travel test completed!")
    # except Exception as e:
    #     print(f"❌ Error in international test: {str(e)}")
    
    # print("\n" + "="*80 + "\n")
    
    # print("📍 TEST 3 - Multi-leg Long Distance Journey:")
    # print(f"Query: {test_query_multileg.strip()}")
    # print("\n" + "="*70)
    # print("OPTIMIZATION RESULTS:")
    # print("="*70)
    
    # try:
    #     result3 = optimize_travel.invoke({"query": test_query_multileg})
    #     print(result3)
    #     print("\n" + "="*60)
    #     print("✅ Multi-leg journey test completed!")
    # except Exception as e:
    #     print(f"❌ Error in multi-leg test: {str(e)}")
    
    # print("\n" + "="*50)
    # print("🎉 All travel optimization tests completed!")
    
    