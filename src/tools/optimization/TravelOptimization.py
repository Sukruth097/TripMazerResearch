import os
import sys
import json
from typing import Dict, Any

# Add the src directory to Python path when running directly
if __name__ == "__main__":
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from langchain.tools import tool
from src.services.perplexity_service import PerplexityService


def _get_perplexity_service() -> PerplexityService:
    """Get initialized Perplexity service instance."""
    # Get API key from environment variable
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY environment variable is required")
    return PerplexityService(api_key)
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
        >>> query = "Optimize travel from Mumbai to Goa for 4 people from 20-01-2026 to 23-01-2026 with budget ₹8000. Prefer trains."
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
        | 3 | Flight | Mumbai - Goa Direct | 1.5 hours | ₹4500 | ₹18000 | MakeMyTrip | 2:00 PM - 3:30 PM |
        
        ## Cost Breakdown
        - **Recommended Option:** Train (Best value within budget)
        - **Total Transportation Cost:** ₹3200 INR
        - **Remaining Budget:** ₹4800 INR for local transport
        - **Cost per Person:** ₹800 INR
    """
    try:
        # Get Perplexity service
        perplexity_service = _get_perplexity_service()
        
        # Create comprehensive system prompt for travel optimization
        system_prompt = """You are an expert travel optimization consultant and transportation advisor with deep knowledge of routes, costs, and booking platforms.

**STEP 1: Extract travel optimization requirements from the user query**
First, identify and extract these parameters from the user's natural language query:
- From Location: Origin/departure location
- To Location: Destination location
- Number of People: How many travelers
- Budget: Budget amount with appropriate currency (see currency rules below)
- Travel Dates: When they're traveling
- Mode of Transport: Preferred transportation (bus, flights, trains, etc.) - DEFAULT is bus if not specified
- Special Requirements: Any specific needs (luggage, comfort level, time constraints)

**CURRENCY DETECTION RULES:**
- If BOTH from location AND to location are Indian regions/cities (Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad, Pune, Ahmedabad, Jaipur, Surat, Lucknow, Kanpur, Nagpur, Indore, Thane, Bhopal, Visakhapatnam, Patna, Vadodara, Ghaziabad, Ludhiana, Agra, Nashik, Faridabad, Meerut, Rajkot, Kalyan, Vasai-Virar, Varanasi, Srinagar, Aurangabad, Dhanbad, Amritsar, Navi Mumbai, Allahabad, Ranchi, Howrah, Coimbatore, Jabalpur, Gwalior, Vijayawanda, Jodhpur, Madurai, Raipur, Kota, Guwahati, Chandigarh, Solapur, Hubli-Dharwad, Bareilly, Moradabad, Mysore, Gurgaon, Aligarh, Jalandhar, Tiruchirappalli, Bhubaneswar, Salem, Warangal, Mira-Bhayandar, Thiruvananthapuram, Bhiwandi, Saharanpur, Guntur, Amravati, Bikaner, Noida, Jamshedpur, Bhilai Nagar, Cuttack, Firozabad, Kochi, Bhavnagar, Dehradun, Durgapur, Asansol, Nanded-Waghala, Kolhapur, Ajmer, Akola, Gulbarga, Jamnagar, Ujjain, Loni, Siliguri, Jhansi, Ulhasnagar, Nellore, Jammu, Sangli-Miraj & Kupwad, Belgaum, Mangalore, Ambattur, Tirunelveli, Malegaon, Gaya, Jalgaon, Udaipur, Maheshtala, or any other Indian city/state): Use ₹ (Indian Rupees)
- For ALL OTHER destinations or international travel: Use $ (US Dollars)

**STEP 2: Provide comprehensive travel optimization analysis**
Based on the extracted requirements, analyze and optimize transportation options.

**OPTIMIZATION CRITERIA:**
1. **Cost Efficiency:** Find options within budget
2. **Time Efficiency:** Balance cost vs travel time
3. **Comfort Level:** Consider traveler preferences
4. **Availability:** Check realistic availability for dates
5. **Multi-leg Options:** Handle connecting routes if needed
6. **Overnight Options:** Suggest if journey requires overnight stops

**TRANSPORT MODE PRIORITY:**
- If user specifies a mode: Prioritize that mode but show alternatives
- If no mode specified: Default to bus options first, then show other alternatives
- Always compare at least 3 different options when possible

**INSTRUCTIONS:**
1. Extract travel requirements from the query
2. Analyze route options for the specified/default transport modes
3. Calculate costs, duration, and efficiency for each option
4. Handle multi-leg journeys with connections if needed
5. Suggest overnight stops for very long journeys (>18 hours)
6. Provide booking platform recommendations
7. Consider seasonal pricing and availability
8. Use correct currency throughout

**RESPONSE FORMAT (MANDATORY):**

# Travel Optimization Results

## Extracted Requirements
- **From:** [extracted from location]
- **To:** [extracted to location]
- **Travelers:** [number] people
- **Budget:** [₹ for Indian regions or $ for international][extracted budget] [INR for Indian regions or USD for international]
- **Dates:** [extracted dates]
- **Preferred Mode:** [extracted mode or "Bus (default)"]
- **Special Requirements:** [any special needs or "None specified"]

---

## Recommended Transportation Options

| Option | Mode | Route | Duration | Cost per Person | Total Cost | Booking Platform | Departure/Arrival |
|--------|------|-------|----------|-----------------|------------|------------------|-------------------|
| 1 | [Mode] | [Route details] | [Duration] | [Currency][Cost] | [Currency][Total] | [Platform] | [Times] |
| 2 | [Mode] | [Route details] | [Duration] | [Currency][Cost] | [Currency][Total] | [Platform] | [Times] |
| 3 | [Mode] | [Route details] | [Duration] | [Currency][Cost] | [Currency][Total] | [Platform] | [Times] |

## Multi-leg Journey Details (if applicable)

| Leg | From | To | Mode | Duration | Cost | Connection Time |
|-----|------|----|----|----------|------|----------------|
| 1 | [Origin] | [Stop] | [Mode] | [Duration] | [Cost] | [Wait time] |
| 2 | [Stop] | [Destination] | [Mode] | [Duration] | [Cost] | - |

## Cost Analysis
- **Recommended Option:** [Best option with reasoning]
- **Most Economical:** [Cheapest option] - [Currency][Cost] total
- **Fastest Option:** [Quickest option] - [Duration]
- **Best Value:** [Best balance of cost/time/comfort]
- **Budget Utilization:** [Currency][Used] of [Currency][Total budget]

## Booking Recommendations
- **Best Booking Time:** [When to book for best prices]
- **Platform Comparison:** [Compare booking platforms]
- **Payment Options:** [Available payment methods]
- **Cancellation Policies:** [Important cancellation terms]

## Travel Tips
- **Best Travel Times:** [Optimal departure times]
- **Luggage Guidelines:** [Baggage restrictions and tips]
- **Route Conditions:** [Seasonal considerations, road/rail conditions]
- **Alternative Routes:** [Backup options if primary route unavailable]
- **Local Transportation:** [Getting to/from stations/airports]

**IMPORTANT:**
- Use correct currency throughout (₹ for Indian routes, $ for international)
- Prioritize user-specified transport mode but show alternatives
- Default to bus if no mode specified
- Include realistic booking platforms and costs
- Handle multi-city/connecting routes appropriately"""

        # Search using Perplexity with the comprehensive optimization prompt
        results = perplexity_service.search(
            query=query,
            system_prompt=system_prompt,
            temperature=0.1
        )
        
        # Return results directly since the system prompt handles formatting
        if isinstance(results, dict) and 'error' in results:
            return f"## Error in Travel Optimization\n\n{results['error']}"
        
        return results
        
    except Exception as e:
        return f"## Error in Travel Optimization\n\nFailed to process travel optimization: {str(e)}"


if __name__ == "__main__":
    print("🚌 Testing Travel Optimization with Different Scenarios...")
    
    # Test 1: Indian domestic travel with train preference
    test_query_train = """
    Optimize travel from Mumbai to Goa for 4 people from 20-01-2026 to 23-01-2026 
    with budget ₹8000. Prefer trains but show other options too.
    """
    
    # Test 2: International travel with default bus (should show flights)
    test_query_international = """
    Optimize travel from New York to Washington DC for 2 people 
    from 15-03-2026 to 18-03-2026 with budget $500.
    """
    
    # Test 3: Long distance requiring multi-leg journey
    test_query_multileg = """
    Optimize travel from Bangalore to Kashmir for 3 people from 10-04-2026 to 15-04-2026
    with budget ₹25000. Consider all transport modes.
    """
    
    print("\n📍 TEST 1 - Indian Domestic with Train Preference:")
    print(f"Query: {test_query_train.strip()}")
    print("\n" + "="*70)
    print("OPTIMIZATION RESULTS:")
    print("="*70)
    
    try:
        result1 = optimize_travel.invoke({"query": test_query_train})
        print(result1)
        print("\n" + "="*70)
        print("✅ Train preference test completed!")
    except Exception as e:
        print(f"❌ Error in train test: {str(e)}")
    
    print("\n" + "="*80 + "\n")
    
    print("📍 TEST 2 - International Travel (Default Bus/Flight):")
    print(f"Query: {test_query_international.strip()}")
    print("\n" + "="*70)
    print("OPTIMIZATION RESULTS:")
    print("="*70)
    
    try:
        result2 = optimize_travel.invoke({"query": test_query_international})
        print(result2)
        print("\n" + "="*70)
        print("✅ International travel test completed!")
    except Exception as e:
        print(f"❌ Error in international test: {str(e)}")
    
    print("\n" + "="*80 + "\n")
    
    print("📍 TEST 3 - Multi-leg Long Distance Journey:")
    print(f"Query: {test_query_multileg.strip()}")
    print("\n" + "="*70)
    print("OPTIMIZATION RESULTS:")
    print("="*70)
    
    try:
        result3 = optimize_travel.invoke({"query": test_query_multileg})
        print(result3)
        print("\n" + "="*70)
        print("✅ Multi-leg journey test completed!")
    except Exception as e:
        print(f"❌ Error in multi-leg test: {str(e)}")
    
    print("\n" + "="*80)
    print("🎉 All travel optimization tests completed!")
    print("💡 Check the following features:")
    print("   - Currency detection (₹ vs $)")
    print("   - Transport mode preferences vs defaults")
    print("   - Cost optimization within budget")
    print("   - Multi-leg journey handling")
    print("   - Booking platform recommendations")
