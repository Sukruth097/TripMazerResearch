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


def _get_gemini_client() -> genai.Client:
    """Get Google Gemini client with API key."""
    # Use the provided API key directly
    api_key = "AIzaSyBQ-W6UDXRxkUHp15PT1N96RDp_iUV0PdE"
    client = genai.Client(api_key=api_key)
    return client


def _extract_flight_parameters(query: str) -> Dict[str, Any]:
    """
    Extract flight search parameters using Gemini natural language understanding.
    Uses standard format conversion and intelligent flight decision making.
    
    Returns:
        Dict with flight search parameters or decision not to search
    """
    try:
        client = _get_gemini_client()
        
        prompt = f"""
        TASK: Analyze this travel query using natural language understanding to extract flight parameters and make intelligent flight search decision.

        QUERY: "{query}"

        **ANALYSIS REQUIREMENTS:**

        1. **Natural Language Understanding**: 
           - Understand the user's budget level, travel preferences, and intent
           - Analyze if they mention luxury, comfort, speed preferences, or budget constraints
           - Determine if they can afford flights based on budget and route type
           - Consider if they specifically prefer flights or ground transport

        2. **Airport Code Conversion** (use most popular/main airport):
           - Mumbai → BOM, Bangalore → BLR, Delhi → DEL, Chennai → MAA, Kolkata → CCU
           - Hyderabad → HYD, Pune → PNQ, Goa → GOX, Kochi → COK, Ahmedabad → AMD  
           - New York → JFK, London → LHR, Paris → CDG, Dubai → DXB, Singapore → SIN
           - For any city, use the main commercial airport

        3. **Date Standardization** (convert to YYYY-MM-DD):
           - "27-10-25" → "2025-10-27"
           - "31-10-25" → "2025-10-31" 
           - "Oct 27, 2025" → "2025-10-27"
           - Always use standard YYYY-MM-DD format

        4. **Currency & Country Rules**:
           - Indian domestic routes: currency="INR", gl="in"
           - International routes: currency="USD", gl="us"

        **INTELLIGENT FLIGHT DECISION** (No hardcoded rules):
        - Use natural language understanding to decide if flights make sense
        - Consider: user's budget level, preferences mentioned, route distance, time constraints
        - If budget is low AND user doesn't specifically want flights → recommend against flights
        - If user mentions luxury/comfort/speed OR has good budget → include flights
        - If international route → flights usually needed regardless of budget
        - If user specifically mentions "prefer flights" → include flights

        **OUTPUT FORMAT:**

        If flights should be searched:
        {{
            "should_search_flights": true,
            "reason": "Natural language explanation of decision",
            "outbound": {{
                "departure_id": "AIRPORT_CODE",
                "arrival_id": "AIRPORT_CODE", 
                "outbound_date": "YYYY-MM-DD",
                "currency": "INR_or_USD",
                "gl": "in_or_us"
            }},
            "return": {{
                "departure_id": "AIRPORT_CODE",
                "arrival_id": "AIRPORT_CODE",
                "outbound_date": "YYYY-MM-DD", 
                "currency": "INR_or_USD",
                "gl": "in_or_us"
            }}
        }}

        If flights should NOT be searched:
        {{
            "should_search_flights": false,
            "reason": "Natural language explanation why flights not recommended"
        }}

        Use your natural understanding - no hardcoded budget thresholds or keyword matching.
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
        print(f"✈️ Flight search decision: {result.get('should_search_flights')} - {result.get('reason', '')}")
        
        return result
        
    except Exception as e:
        print(f"⚠️ Flight parameter extraction failed: {e}")
        # Return simple "no flights" decision - no fallback needed as per requirement
        return {"should_search_flights": False, "reason": "Parameter extraction failed"}


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
        
        results = []
        
        # Search outbound flights
        if outbound_params:
            print(f"🛫 Searching outbound flights: {outbound_params['departure_id']} → {outbound_params['arrival_id']}")
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
        
        # Search return flights
        if return_params:
            print(f"🛬 Searching return flights: {return_params['departure_id']} → {return_params['arrival_id']}")
            return_results = serp_service.search_flights(
                departure_id=return_params['departure_id'],
                arrival_id=return_params['arrival_id'],
                outbound_date=return_params['outbound_date'],
                country_code=return_params['gl'],
                currency=return_params['currency']
            )
            
            # Format return results  
            return_formatted = _format_serp_flight_results(
                return_results,
                "Return", 
                return_params['outbound_date'],
                return_params['currency']
            )
            results.append(return_formatted)
        
        # Combine results
        combined_results = "\n\n".join(results)
        return f"# ✈️ Flight Search Results\n\n{combined_results}"
        
    except Exception as e:
        print(f"❌ SERP flight search failed: {e}")
        return f"## ⚠️ Flight Search Error\n\nUnable to fetch flight data: {str(e)}"


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
                print(f"⚠️ Error formatting flight {i}: {e}")
                continue
        
        return table
        
    except Exception as e:
        print(f"❌ Error formatting SERP results: {e}")
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
        >>> query = "Give me travel options from Mumbai to Goa for 4 people from 20-01-2026 to 23-01-2026 with budget ₹8000. Prefer trains."
        >>> result = optimize_travel(query)
        >>> print(result)
        
        # Travel Optimization Results
        
        ## Extracted Requirements
        - **From:** Mumbai
        - **To:** Goa
        - **Travelers:** 4 people
        - **Budget:** ₹8000 INR
        - **Dates:** 20-01-2026 to 23-01-2026
        - **Preferred Mode:** Trains
        
        ---
        
        ## Recommended Transportation Options
        
        | Option | Mode | Route | Duration | Cost per Person | Total Cost | Booking Platform | Departure/Arrival |
        |--------|------|-------|----------|-----------------|------------|------------------|-------------------|
        | 1 | Train | Mumbai - Goa Express | 12 hours | ₹800 | ₹3200 | IRCTC | 8:00 PM - 8:00 AM |
        | 2 | Bus | Mumbai - Goa Sleeper | 14 hours | ₹600 | ₹2400 | RedBus | 10:00 PM - 12:00 PM |
        | 3 | Flight | Mumbai - Goa Direct | 1.5 hours | ₹4500 | ₹18000 | Booking.com | 2:00 PM - 3:30 PM |
        
        ## Cost Breakdown
        - **Recommended Option:** Train (Best value within budget)
        - **Total Transportation Cost:** ₹3200 INR
        - **Remaining Budget:** ₹4800 INR for local transport
        - **Cost per Person:** ₹800 INR
    """
    try:
        # Get Perplexity service
        perplexity_service = _get_perplexity_service()
        serp_service = _get_serp_api_service()
        
        # Create comprehensive system prompt for travel optimization
        system_prompt = """You are an expert travel optimization consultant and transportation advisor with deep knowledge of routes, costs, and booking platforms.

**BOOKING PLATFORM REQUIREMENTS:**
- **Flight Bookings:** ONLY use booking.com and skyscanner.net for flight recommendations
- **Train Bookings:** Use IRCTC for Indian trains, official railway websites for international
- **Bus Bookings:** Use RedBus, official state transport websites, or regional bus operators
- **DO NOT recommend:** Expedia, MakeMyTrip, Cleartrip, Goibibo, Yatra for any bookings
- **Platform Selection:** Always verify platform availability for the specific route and date

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
- **Round Trip:** If return dates are mentioned or trip duration is specified, plan both outbound and return journeys
- **One Way:** If only departure mentioned or explicitly stated as one-way
- **Default Assumption:** If travel dates span multiple days, assume round-trip unless specified otherwise

**CURRENCY DETECTION RULES:**
- If BOTH from location AND to location are Indian regions/cities (Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad, Pune, Ahmedabad, Jaipur, Surat, Lucknow, Kanpur, Nagpur, Indore, Thane, Bhopal, Visakhapatnam, Patna, Vadodara, Ghaziabad, Ludhiana, Agra, Nashik, Faridabad, Meerut, Rajkot, Kalyan, Vasai-Virar, Varanasi, Srinagar, Aurangabad, Dhanbad, Amritsar, Navi Mumbai, Allahabad, Ranchi, Howrah, Coimbatore, Jabalpur, Gwalior, Vijayawanda, Jodhpur, Madurai, Raipur, Kota, Guwahati, Chandigarh, Solapur, Hubli-Dharwad, Bareilly, Moradabad, Mysore, Gurgaon, Aligarh, Jalandhar, Tiruchirappalli, Bhubaneswar, Salem, Warangal, Mira-Bhayandar, Thiruvananthapuram, Bhiwandi, Saharanpur, Guntur, Amravati, Bikaner, Noida, Jamshedpur, Bhilai Nagar, Cuttack, Firozabad, Kochi, Bhavnagar, Dehradun, Durgapur, Asansol, Nanded-Waghala, Kolhapur, Ajmer, Akola, Gulbarga, Jamnagar, Ujjain, Loni, Siliguri, Jhansi, Ulhasnagar, Nellore, Jammu, Sangli-Miraj & Kupwad, Belgaum, Mangalore, Ambattur, Tirunelveli, Malegaon, Gaya, Jalgaon, Udaipur, Maheshtala, or any other Indian city/state): Use ₹ (Indian Rupees)
- For ALL OTHER destinations or international travel: Use $ (US Dollars)

**STEP 2: Provide comprehensive travel optimization analysis**
Based on the extracted requirements, analyze and optimize transportation options.

**OPTIMIZATION CRITERIA:**
1. **Cost Efficiency (PRIMARY):** Find the cheapest possible options within budget - this is the TOP PRIORITY
2. **Flight Cost Minimization:** For flights, ALWAYS prioritize the lowest fares over convenience
3. **Time Efficiency:** Balance cost vs travel time (cost takes precedence)
4. **Comfort Level:** Consider traveler preferences (after cost optimization)
5. **Availability:** Check realistic availability for dates
6. **Multi-leg Options:** Handle connecting routes if they offer significant savings
7. **Overnight Options:** Suggest if journey requires overnight stops

**TRANSPORT MODE PRIORITY:**
- **For International Travel (different countries):** Prioritize flights, then consider international trains/buses only if they exist (like Europe)
- **For Domestic Travel (same country):** 
  - If user specifies a mode: Prioritize that mode but show alternatives
  - If no mode specified: Default to bus options first, then trains, then flights
- **Smart Mode Selection:** Automatically detect domestic vs international routes and suggest appropriate transport modes
- Always compare at least 3 different options when possible, but focus on realistic/practical modes for the route type

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
   - **Domestic India:** ₹3,000-₹8,000 per person (economy), ₹12,000+ (business)
   - **International Short-haul:** $200-$600 (India-Middle East, India-Southeast Asia)
   - **International Long-haul:** $600-$1,500 (India-Europe/US/Australia)
   - **Budget vs Full-service:** 30-50% price difference
   - **Advance booking:** 15-30% cheaper than last-minute

3. **Train Price Guidelines (Accurate Classes):**
   - **Indian Railways:** Sleeper ₹400-₹800, 3AC ₹800-₹1,500, 2AC ₹1,200-₹2,500, 1AC ₹2,000-₹4,000
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

**INSTRUCTIONS:**
1. Extract travel requirements from the query including SPECIFIC DATES
2. **ANALYZE EACH DATE INDIVIDUALLY:** Research market conditions for outbound date vs return date
3. **CALCULATE DATE-SPECIFIC PRICING:** Factor in day-of-week, holidays, seasonality, demand for each date
4. **PRIORITIZE CHEAPEST OPTIONS:** ALWAYS list flight options from cheapest to most expensive
5. **FLIGHT COST RESEARCH:** Extensively research budget airlines, promotional fares, and connecting flights
6. **MANDATORY FLIGHT DETAILS:** ALWAYS include airline name, flight number, and times in IST format
7. **IST TIME CONVERSION:** Convert all flight times to Indian Standard Time (IST) regardless of origin/destination
8. Analyze route options for the specified/default transport modes
9. **ENSURE PRICE DIFFERENTIATION:** Outbound and return prices must reflect actual date-based market conditions
10. Handle multi-leg journeys with connections if needed (especially if they save money)
11. Suggest overnight stops for very long journeys (>18 hours)
12. Provide booking platform recommendations (booking.com, skyscanner.net for flights)
13. Consider seasonal pricing and availability FOR SPECIFIC DATES
14. Use correct currency throughout
15. **NO CACHED DATA:** Always provide fresh, real-time results without using any cached information
16. **BUDGET UTILIZATION**: Recommend transportation options that make good use of the available budget while PRIORITIZING LOWEST COST

**RESPONSE FORMAT (MANDATORY):**

**IMPORTANT: Log extracted requirements for debugging but DO NOT include in user output**

# Travel Optimization Results

## Outbound Journey Options (Date: [Specific Outbound Date])

| Option | Mode | Flight/Route Details | Duration | Cost per Person | Total Cost | Booking Platform | Departure/Arrival (IST) |
|--------|------|---------------------|----------|-----------------|------------|------------------|-------------------------|
| 1 | Flight | [Airline Flight#: Route] | [Duration] | [Currency][Cost] | [Currency][Total] | [Platform] | [DD-MM-YYYY HH:MM IST → HH:MM IST] |
| 2 | [Mode] | [Route details] | [Duration] | [Currency][Cost] | [Currency][Total] | [Platform] | [DD-MM-YYYY HH:MM IST → HH:MM IST] |
| 3 | [Mode] | [Route details] | [Duration] | [Currency][Cost] | [Currency][Total] | [Platform] | [DD-MM-YYYY HH:MM IST → HH:MM IST] |

## Return Journey Options (Date: [Specific Return Date])

| Option | Mode | Flight/Route Details | Duration | Cost per Person | Total Cost | Booking Platform | Departure/Arrival (IST) |
|--------|------|---------------------|----------|-----------------|------------|------------------|-------------------------|
| 1 | Flight | [Airline Flight#: Route] | [Duration] | [Currency][Cost] | [Currency][Total] | [Platform] | [DD-MM-YYYY HH:MM IST → HH:MM IST] |
| 2 | [Mode] | [Route details] | [Duration] | [Currency][Cost] | [Currency][Total] | [Platform] | [DD-MM-YYYY HH:MM IST → HH:MM IST] |
| 3 | [Mode] | [Route details] | [Duration] | [Currency][Cost] | [Currency][Total] | [Platform] | [Specific times for return date] |

## Date-Based Price Analysis
- **Outbound Date Factors:** [Why outbound date has this pricing - weekend/holiday/season impact]
- **Return Date Factors:** [Why return date has different pricing - market conditions]
- **Price Difference Explanation:** [Clear reasoning for outbound vs return price variations]

## Multi-leg Journey Details (if applicable)

| Leg | From | To | Mode | Duration | Cost | Connection Time |
|-----|------|----|----|----------|------|----------------|
| 1 | [Origin] | [Stop] | [Mode] | [Duration] | [Cost] | [Wait time] |
| 2 | [Stop] | [Destination] | [Mode] | [Duration] | [Cost] | - |

## Quick Summary
- **� CHEAPEST (RECOMMENDED):** [Most economical option with cost - PRIORITIZE THIS]
- **�💰 Best Value:** [Recommended option balancing cost and convenience]
- **⚡ Fastest:** [Quickest option with duration] 
- ** Budget Used:** [Currency][Used] of [Currency][Total budget]
- **💡 Cost Savings:** [How much saved compared to premium options]

**CRITICAL DATE-SPECIFIC PRICING INSTRUCTIONS:**
1. **NEVER use identical prices for outbound and return journeys**
2. **ALWAYS factor in specific date characteristics:** weekday vs weekend, holidays, festivals, seasonality
3. **SHOW CLEAR PRICE REASONING:** Explain why outbound vs return dates have different pricing
4. **REALISTIC MARKET SIMULATION:** Mimic how actual booking platforms price based on date-specific demand
5. **FACTOR BOOKING TIMELINE:** Consider how far in advance booking is happening from current date
6. **VALIDATE PRICE LOGIC:** Ensure price differences make logical sense based on calendar analysis

**CONCISE OUTPUT INSTRUCTIONS:**
1. Keep Cost Analysis section to max 4 bullet points with essential info only
2. Remove all booking recommendations and tips sections
3. Remove verbose explanations - use brief, actionable points
4. Focus on decision-making info that users actually need
5. Use emojis and formatting to make it scannable

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
- Include fresh, non-cached booking platforms and costs (flights: booking.com, skyscanner.net only)
- Handle multi-city/connecting routes appropriately
- ALWAYS plan both outbound AND return journeys for round-trips
- For round-trips: Show separate tables for outbound and return with cost breakdown
- Budget allocation: Split budget appropriately between outbound and return journeys
- One-way trips: Only show outbound journey options"""

        # Search using Perplexity with the comprehensive optimization prompt
        results = perplexity_service.search(
            query=query,
            system_prompt=system_prompt,
            temperature=0.1,
            search_domain_filter=['booking.com', 'skyscanner.net']
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
        print(f"🔄 Processing hybrid travel optimization query: {query[:100]}...")
        
        results = []
        
        # Step 1: Extract flight parameters and decide if flight search is needed using Gemini
        flight_params = _extract_flight_parameters(query)
        
        # Step 2: Search flights with SerpAPI if decision is positive
        if flight_params.get('should_search_flights', False):
            print("✈️ Searching flights with SerpAPI based on natural language analysis...")
            serp_results = _search_flights_with_serp(flight_params)
            results.append(serp_results)
        else:
            print(f"🚫 Skipping flight search: {flight_params.get('reason', 'Not needed')}")
        
        # Step 3: Always get Perplexity results for buses/trains and general travel options
        print("🚌 Getting buses/trains options from Perplexity...")
        perplexity_service = _get_perplexity_service()
        
        # Create travel-specific prompt for Perplexity
        perplexity_prompt = f"""
        Provide ground transportation options for: {query}
        """
        
        perplexity_results = perplexity_service.search(
            query=perplexity_prompt,
            system_prompt="You are a travel expert. Provide concise, accurate information about buses and trains with pricing and booking details. Keep explanations brief and avoid lengthy notes or tips."
        )
        
        # Extract content from Perplexity response
        if isinstance(perplexity_results, dict) and 'choices' in perplexity_results:
            perplexity_content = perplexity_results['choices'][0]['message']['content']
        else:
            perplexity_content = str(perplexity_results)
        
        results.append(perplexity_content)
        
        # Step 4: Format results with separate tables for flights vs buses/trains
        if len(results) > 1:
            # Both SerpAPI and Perplexity results - format with separate tables
            combined_response = f"""{results[0]}

{results[1]}"""
        else:
            # Only one result (either flights skipped or only Perplexity)
            if flight_params.get('should_search_flights', False):
                # Only flights (no ground transport needed)
                combined_response = f"""{results[0]}"""
            else:
                # Only ground transport (flights skipped)
                combined_response = f"""{results[0]}"""
        
        return combined_response
        
    except Exception as e:
        print(f"❌ Hybrid travel optimization error: {e}")
        # Simple error message - no fallback method as per requirement
        return f"# ⚠️ Optimization Error\n\nError processing query: {str(e)}"


if __name__ == "__main__":
    print("🚌 Testing Travel Optimization with Different Scenarios...")
    
    # Test 1: Indian domestic round-trip with train preference
    test_query_train = """
    Optimize travel from Bangalore to Delhi for 2 people from 10-04-2026 to 15-04-2026
    with budget ₹50000. Consider all transport modes.
    """
    
    # Test 2: International travel (should prioritize flights)
    test_query_international = """
    Optimize travel from New York to London for 2 people 
    from 15-03-2026 to 25-03-2026 with budget $2000. Round trip needed.
    """
    
    # Test 3: Long distance requiring multi-leg journey
    test_query_multileg = """
    Optimize travel from Bangalore to Kashmir for 3 people from 10-04-2026 to 15-04-2026
    with budget ₹25000. Consider all transport modes.
    """
    
    print("\n📍 TEST 1 - Indian Domestic Round-Trip with Train Preference:")
    print(f"Query: {test_query_train.strip()}")
    print("\n" + "="*70)
    print("OPTIMIZATION RESULTS:")
    print("="*70)
    
    try:
        result1 = hybrid_travel_optimization.invoke({"query": test_query_train})
        print(result1)
        print("\n" + "="*70)
        print("✅ Round-trip train preference test completed!")
    except Exception as e:
        print(f"❌ Error in train test: {str(e)}")
    
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
    
    