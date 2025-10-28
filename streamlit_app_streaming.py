"""
Streamlit app for TripMazer with streaming support.
Progressive display of trip planning results + individual tool access.
"""

import streamlit as st
import sys
import os
import requests
import json
from datetime import datetime

# Add src to path for imports
sys.path.append(os.path.dirname(__file__))

from src.agents.worker.trip_optimization_agent.agent import TripOptimizationAgent
from src.tools.optimization.AccomidationPlanner import search_accommodations
from src.tools.optimization.IternaryPlanning import plan_itinerary
from src.tools.optimization.TravelOptimization import travel_search_tool, format_travel_results_as_markdown
from src.tools.optimization.RestaurantsSearch import search_restaurants


def display_progress_bar(progress: int, message: str):
    """Display progress bar with message."""
    st.progress(progress / 100)
    st.info(message)


def display_preferences_result(data: dict):
    """Display extracted preferences."""
    st.success("✅ Trip Requirements Analyzed")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("From", data.get('from_location', 'Not specified'))
        st.metric("Travelers", data.get('travelers', '1'))
    
    with col2:
        st.metric("To", data.get('to_location', 'Not specified'))
        st.metric("Budget", f"₹{data.get('budget', 'Not specified')}" if data.get('budget') else 'Not specified')
    
    with col3:
        st.metric("Dates", data.get('dates', 'Not specified'))
        st.metric("Currency", data.get('currency', 'INR'))
    
    # Display accommodation preference if available
    preference_type = data.get('preference_type')
    if preference_type:
        st.info(f"🏨 **Accommodation Preference**: {preference_type.title()}")
    
    with st.expander(" Tool Execution Order", expanded=True):
        routing = data.get('routing_order', [])
        for idx, tool in enumerate(routing, 1):
            st.write(f"{idx}. {tool.capitalize()}")


def display_tool_result(tool: str, data: str, budget_info: dict = None, query: str = None):
    """Display tool-specific result with proper HTML rendering."""
    st.success(f"✅ {tool.capitalize()} Results Ready")
    
    # Show query that was sent to the tool
    if query:
        with st.expander(f"🔍 Query sent to {tool.capitalize()} Tool", expanded=False):
            st.code(query, language="text")
    
    # Budget info display removed as requested by user
    
    with st.expander(f"📄 View {tool.capitalize()} Details", expanded=True):
        # Render markdown with HTML support for proper formatting
        st.markdown(data, unsafe_allow_html=True)


def display_final_result(data: str, execution_time: float):
    """Display final comprehensive result with proper HTML rendering."""
    st.success(f"✅ Trip Plan Complete! (Total time: {execution_time:.1f}s)")
    
    # Render markdown with HTML support for proper formatting
    st.markdown(data, unsafe_allow_html=True)


def streaming_trip_planner():
    """Main streaming trip planner interface."""
    # Input section
    with st.form("trip_query_form"):
        query = st.text_area(
            "Describe your trip:",
            placeholder="Example: Plan a trip for 3 people from Bangalore to Goa from 25-12-2025 to 30-12-2025 with budget 50000 rupees",
            height=100
        )
        
        submit = st.form_submit_button("🚀 Plan My Trip", use_container_width=True)
    
    if submit and query:
        # Create containers for progressive results
        status_container = st.empty()
        progress_container = st.empty()
        preferences_container = st.empty()
        budget_container = st.empty()
        results_container = st.container()
        final_container = st.empty()
        
        try:
            # Create agent
            agent = TripOptimizationAgent()
            
            # Stream results
            for result in agent.plan_trip_stream(query):
                status = result.get('status')
                step = result.get('step')
                message = result.get('message', '')
                progress = result.get('progress', 0)
                data = result.get('data')
                
                # Update progress
                with progress_container:
                    display_progress_bar(progress, message)
                
                # Handle different steps
                if status == "completed":
                    if step == "preferences":
                        with preferences_container:
                            display_preferences_result(data)
                    
                    elif step == "budget":
                        # Budget allocation removed as requested
                        pass
                    
                    elif step in ["itinerary", "travel", "accommodation"]:
                        with results_container:
                            # Get budget info and query if available
                            budget_info = result.get('budget_info')
                            tool_query = result.get('query')
                            display_tool_result(step, data, budget_info, tool_query)
                    
                    elif step == "final":
                        # Skip displaying final combined result to avoid duplication
                        # Individual tool results are already shown above
                        exec_time = result.get('execution_time', 0)
                        st.success(f"✅ Trip Plan Complete! (Total time: {exec_time:.1f}s)")
                        
                        # Clear progress
                        progress_container.empty()
                        status_container.empty()
                
                elif status == "error":
                    st.error(f"❌ {message}")
                    st.error(f"Error details: {result.get('error', 'Unknown error')}")
                    break
                
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.exception(e)
    
    elif submit:
        st.warning("⚠️ Please enter a trip description")


def accommodations_section():
    """Individual accommodations search section."""
    st.markdown("### 🏨 Search Hotels Directly")
    
    col1, col2 = st.columns(2)
    with col1:
        destination = st.text_input("🌍 Destination", placeholder="e.g., Goa, Mumbai, Dubai")
        checkin_date = st.date_input("📅 Check-in Date")
        budget = st.number_input("💰 Budget per Night (₹)", min_value=500, max_value=50000, value=3000, step=500, help="Budget per night for accommodation")
    
    with col2:
        guests = st.number_input("👥 Number of Guests", min_value=1, max_value=20, value=2)
        checkout_date = st.date_input("📅 Check-out Date")
        accommodation_type = st.selectbox(
            "🏨 Accommodation Type",
            ["Budget (Hotels & Hostels)", "Mid-Range (Comfortable Hotels)", "Luxury (Premium Hotels)"]
        )
    
    if st.button("🏨 Search Hotels", type="primary", use_container_width=True):
        if destination:
            # Date validation
            if checkout_date <= checkin_date:
                st.error("❌ Check-out date must be after check-in date")
                return
                
            with st.spinner("🔄 Searching hotels..."):
                try:
                    check_in_str = checkin_date.strftime('%Y-%m-%d')
                    check_out_str = checkout_date.strftime('%Y-%m-%d')
                    
                    # Map UI selection to preference_type
                    if accommodation_type == "Luxury (Premium Hotels)":
                        preference_type = "luxury"
                        serp_query = f"Luxury hotels in {destination}"
                    elif accommodation_type == "Mid-Range (Comfortable Hotels)":
                        preference_type = "mid-range"
                        serp_query = f"Mid-range hotels in {destination}"
                    else:  # Budget
                        preference_type = "budget"
                        serp_query = f"Budget hotels and hostels in {destination}"
                    
                    results = search_accommodations.invoke({
                        "location": destination,
                        "check_in_date": check_in_str,
                        "check_out_date": check_out_str,
                        "adults": guests,
                        "children": 0,
                        "currency": "INR",
                        "budget_per_night": budget,  # Correct parameter name
                        "preference_type": preference_type,  # Add preference_type parameter
                        "query": serp_query
                    })
                    
                    st.success("✅ Hotels found!")
                    st.markdown(results, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("⚠️ Please enter a destination")


def itinerary_section():
    """Individual itinerary planning section."""
    st.markdown("### 🗺️ Plan Your Itinerary")
    
    col1, col2 = st.columns(2)
    with col1:
        destination = st.text_input("🌍 Destination", placeholder="e.g., Paris, Tokyo, Bali", key="itin_dest")
        travelers = st.number_input("👥 Number of Travelers", min_value=1, max_value=20, value=2, key="itin_travelers")
        dates = st.text_input("📅 Travel Dates", placeholder="25-12-2025 to 30-12-2025", key="itin_dates")
    
    with col2:
        budget = st.number_input("💰 Budget (INR)", min_value=1000, value=30000, step=1000, key="itin_budget")
        
        # Preferences field - matching main.py style
        preferences = st.text_area(
            "🎯 Preferences & Interests", 
            placeholder="e.g., temples, shopping, nightlife, trekking, beaches, museums, local food, adventure sports, cultural experiences, etc.",
            height=100,
            key="itin_preferences"
        )
    
    if st.button("🗺️ Generate Itinerary", type="primary", use_container_width=True):
        if destination and dates:
            with st.spinner("🔄 Creating itinerary..."):
                try:
                    # Include preferences in the query
                    query = f"Plan itinerary for {destination} for {travelers} people from {dates} with budget {budget} INR"
                    if preferences.strip():
                        query += f". Preferences: {preferences}"
                    
                    results = plan_itinerary.invoke({"query": query})
                    
                    st.success("✅ Itinerary created!")
                    st.markdown(results, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("⚠️ Please enter destination and dates")


def get_airport_code(city_name: str) -> str:
    """Use Gemini to get IATA airport code for any city worldwide."""
    try:
        from src.utils.service_initializer import get_gemini_client
        
        print(f"🔧 DEBUG: Attempting to get airport code for '{city_name}'")
        
        # Get Gemini client
        client = get_gemini_client()
        print(f"🔧 DEBUG: Gemini client obtained successfully")
        
        prompt = f"""Return ONLY the 3-letter IATA airport code for: {city_name}

Rules:

Return ONLY 3 letters (e.g., BOM, LHR, DXB, BLR, DEL).

For multiple airports in the same city, return the main international airport (e.g., Paris → CDG).

If the input is already an airport code, return it as-is.

✈️ Airport Selection Logic

Nearby airports (within 100 km):

Identify all airports within 100 km of the location.

If none exist, return exactly: no airport in this location.

Priority zone (within 50 km):

If one or more airports lie within 50 km, choose the nearest one from this zone and ignore farther options.

This ensures local airports take precedence over large but distant hubs.

100 km fallback:

If no airport is within 50 km, pick the nearest one within 100 km.

Tie-breaker rule:

If two airports are within 5 km distance of each other, prefer the larger airport (higher passenger volume or international status).

Ambiguity rule:

If the location name refers to multiple distant cities, choose the most globally recognized one.

✅ Examples
Location	Output	Explanation
Mumbai	BOM	Main international airport
London	LHR	Main international airport
New York	JFK	Main international airport
Dubai	DXB	Main international airport
Bangalore	BLR	Main international airport
Paris	CDG	Main international airport
Mysore	MYQ	Has a local domestic airport within 50 km
Coorg	no airport in this location	Nearest airport (Kannur, CNN) is ~120 km away
Munnar	no airport in this location	Nearest airport (COK) is ~110 km away
Ooty	no airport in this location	Nearest airport (CJB) is ~90 km but mountainous route → optional include if you prefer 100 km strict cutoff
Pune	PNQ	Main airport within city
Nashik	ISK	Domestic airport within 50 km
Surat	STV	Local airport within 50 km
Chandigarh	IXC	Main airport within city
Jaipur	JAI	Main airport within city
Kochi	COK	Main airport within city
Amritsar	ATQ	Main international airport
Tirupati	TIR	Domestic airport within city
Puducherry	PNY	Local airport within 50 km
Madurai	IXM	Main airport within city
Coimbatore	CJB	Main airport within city
Vellore	no airport in this location	Nearest airport (MAA) ~120 km
Indore	IDR	Main airport within city
Goa	GOI	Main airport within city
Udaipur	UDR	Main airport within city
Bhubaneswar	BBI	Main airport within city
Agra	AGR	Local airport within city

---

### 🧭 Auto-Correction Logic for Input City Names

If the entered city name (source or destination) has **spelling mistakes, typos, or grammatical errors**, the system should automatically:
1. Detect the most likely intended city name.
2. Correct it internally before applying airport selection rules.
3. Proceed with finding the correct IATA code.

This ensures that users do not need to type city names perfectly.

**Example behavior:**
- Input: “bangluru” → Corrected: “Bangalore” → Output: “BLR”
- Input: “chitoor” → Corrected: “Chittoor” → Output: “nearest airport Tirupati (TIR) (~70 km away)”
- Input: “nyc” or “newyorkk” → Corrected: “New York” → Output: “JFK”

---

### 🧾 Dynamic Nearest-Airport Clarification Message

If a city has **no airport within its boundary**, but a nearby one (within 100 km) is used for flights:
- Display a clarification line **above both the outbound and return journey sections**.
- The message should read:

> “There are no airports in this location; the nearest airport is [Airport Name] ([Code]), approximately [XX] km away.”

- `[XX]` is the dynamically calculated road or aerial distance in kilometers (rounded to the nearest whole number).

**Example Integration Critical to follow below pattern:**
```
There are no airports in this location; the nearest airport is Tirupati (TIR), approximately 70 km away.
>> Outbound Journey (BLR → Chittoor) - 2025-10-27
...
<< Return Journey (Chittoor → BLR) - 2025-10-29
```

If the city has its own airport, skip this line and display results normally.
"""

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        print(f"🔧 DEBUG: Gemini response: '{response.text}'")
        
        airport_code = response.text.strip().upper()
        
        # Validate the response (should be 3 letters)
        if len(airport_code) == 3 and airport_code.isalpha():
            print(f"🔧 DEBUG: Valid airport code '{airport_code}' for '{city_name}'")
            return airport_code
        else:
            # If invalid response, return original city name
            print(f"🔧 DEBUG: Invalid response '{airport_code}', returning city name '{city_name}'")
            return city_name
            
    except Exception as e:
        # Fallback to city name if Gemini fails
        print(f"🔧 DEBUG: Airport code lookup failed for {city_name}: {e}")
        return city_name


def travel_section():
    """Individual travel search section."""
    st.markdown("### ✈️ Search Flights, Trains & Buses")
    
    col1, col2 = st.columns(2)
    with col1:
        origin = st.text_input("🛫 From", placeholder="e.g., Mumbai, Delhi", key="travel_from")
        departure_date = st.date_input("📅 Departure Date", key="travel_depart")
        travelers_travel = st.number_input("👥 Travelers", min_value=1, max_value=20, value=2, key="travel_travelers")
    
    with col2:
        destination_travel = st.text_input("🛬 To", placeholder="e.g., Goa, Bangalore", key="travel_to")
        return_date = st.date_input("📅 Return Date (optional)", key="travel_return")
        budget_travel = st.number_input("💰 Budget (INR)", min_value=1000, value=20000, step=1000, key="travel_budget")
    
    transport_modes = st.multiselect(
        "🚌 Transport Modes",
        ["flight", "train", "bus"],
        default=["flight", "train", "bus"]
    )
    
    if st.button("🔍 Search Travel Options", type="primary", use_container_width=True):
        if origin and destination_travel:
            # Date validation
            if return_date and return_date <= departure_date:
                st.error("❌ Return date must be after departure date")
                return
                
            with st.spinner("🔄 Searching travel options..."):
                try:
                    # Simple logic to detect international routes
                    # List of major Indian cities for domestic detection
                    indian_cities = [
                        'mumbai', 'delhi', 'bangalore', 'bengaluru', 'chennai', 'kolkata', 
                        'hyderabad', 'pune', 'ahmedabad', 'surat', 'jaipur', 'lucknow',
                        'kanpur', 'nagpur', 'indore', 'thane', 'bhopal', 'visakhapatnam',
                        'pimpri', 'patna', 'vadodara', 'ghaziabad', 'ludhiana', 'agra',
                        'nashik', 'faridabad', 'meerut', 'rajkot', 'kalyan', 'vasai',
                        'varanasi', 'srinagar', 'aurangabad', 'dhanbad', 'amritsar',
                        'navi mumbai', 'allahabad', 'ranchi', 'howrah', 'coimbatore',
                        'jabalpur', 'gwalior', 'vijayawada', 'jodhpur', 'madurai',
                        'raipur', 'kota', 'guwahati', 'chandigarh', 'solapur', 'hubli',
                        'tiruchirappalli', 'tiruppur', 'moradabad', 'mysore', 'bareilly',
                        'gurgaon', 'aligarh', 'jalandhar', 'bhubaneswar', 'salem',
                        'mira-bhayandar', 'thiruvananthapuram', 'bhiwandi', 'saharanpur',
                        'gorakhpur', 'guntur', 'bikaner', 'amravati', 'noida', 'jamshedpur',
                        'bhilai', 'cuttak', 'firozabad', 'kochi', 'nellore', 'bhavnagar',
                        'dehradun', 'durgapur', 'asansol', 'rourkela', 'nanded', 'kolhapur',
                        'ajmer', 'akola', 'gulbarga', 'jamnagar', 'ujjain', 'loni',
                        'siliguri', 'jhansi', 'ulhasnagar', 'jammu', 'sangli-miraj',
                        'mangalore', 'erode', 'belgaum', 'ambattur', 'tirunelveli',
                        'malegaon', 'gaya', 'jalgaon', 'udaipur', 'maheshtala', 'goa',
                        'panaji', 'shimla', 'manali', 'rishikesh', 'haridwar', 'mcleodganj',
                        'coorg', 'kodaikanal', 'ooty', 'darjeeling', 'gangtok', 'mount abu',
                        'pushkar', 'kasauli', 'mussoorie', 'nainital', 'ranikhet'
                    ]
                    
                    # Check if both cities are Indian (domestic) or not (international)
                    origin_indian = origin.lower().strip() in indian_cities
                    dest_indian = destination_travel.lower().strip() in indian_cities
                    is_domestic_route = origin_indian and dest_indian
                    
                    # For international routes, only flights make sense
                    if not is_domestic_route:
                        transport_modes_to_use = ["flight"]
                        # Get airport codes for international flights
                        origin_airport = get_airport_code(origin)
                        dest_airport = get_airport_code(destination_travel)
                    else:
                        transport_modes_to_use = transport_modes
                        # For domestic routes with flights, we need airport codes too
                        if "flight" in transport_modes:
                            print(f"🔍 Getting airport code for {origin}...")
                            origin_airport = get_airport_code(origin)
                            print(f"✈️ {origin} → {origin_airport}")
                            
                            print(f"🔍 Getting airport code for {destination_travel}...")
                            dest_airport = get_airport_code(destination_travel)
                            print(f"✈️ {destination_travel} → {dest_airport}")
                        else:
                            origin_airport = None
                            dest_airport = None
                    
                    # Prepare travel search parameters
                    search_params = {
                        "origin": origin,
                        "destination": destination_travel,
                        "departure_date": departure_date.strftime('%Y-%m-%d'),
                        "return_date": return_date.strftime('%Y-%m-%d') if return_date else None,
                        "transport_modes": transport_modes_to_use,
                        "travelers": travelers_travel,
                        "budget_limit": budget_travel,
                        "currency": "INR",
                        "is_domestic": is_domestic_route,
                        "trip_type": "round_trip" if return_date else "one_way"
                    }
                    
                    # Add airport codes if available
                    if origin_airport and origin_airport != origin:
                        search_params["origin_airport"] = origin_airport
                    if dest_airport and dest_airport != destination_travel:
                        search_params["destination_airport"] = dest_airport
                    
                    results = travel_search_tool.invoke(search_params)
                    
                    # Format results as markdown instead of showing raw JSON
                    if isinstance(results, str):
                        # If results is already a string, try to parse it as JSON first
                        try:
                            import json
                            parsed_results = json.loads(results)
                            formatted_results = format_travel_results_as_markdown(parsed_results)
                        except json.JSONDecodeError:
                            # If it's not JSON, use as-is (might already be formatted)
                            formatted_results = results
                    else:
                        # If results is a dict, format it directly
                        formatted_results = format_travel_results_as_markdown(results)
                    
                    st.success("✅ Travel options found!")
                    st.markdown(formatted_results, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("⚠️ Please enter origin and destination")


def restaurants_section():
    """Individual restaurants search section."""
    st.markdown("### 🍽️ Find Restaurants")
    
    itinerary_input = st.text_area(
        "Paste your itinerary or locations:",
        placeholder="Day 1 - Paris: Eiffel Tower (9 AM), Louvre (2 PM)...",
        height=150
    )
    
    col1, col2 = st.columns(2)
    with col1:
        travel_dates_rest = st.text_input("📅 Travel Dates", placeholder="25-12-2025 to 28-12-2025", key="rest_dates")
    with col2:
        dietary_prefs = st.selectbox(
            "🥗 Dietary Preferences",
            ["veg and non-veg", "veg only", "non-veg only", "vegan", "gluten-free"]
        )
    
    budget_hint = st.text_input("💰 Budget Hint (optional)", placeholder="INR 5000 for 2 people for 3 days")
    
    if st.button("🍽️ Find Restaurants", type="primary", use_container_width=True):
        if itinerary_input and travel_dates_rest:
            with st.spinner("🔄 Finding restaurants..."):
                try:
                    results = search_restaurants(itinerary_input, travel_dates_rest, dietary_prefs, budget_hint)
                    
                    st.success("✅ Restaurants found!")
                    st.markdown(results, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("⚠️ Please provide itinerary and dates")


def main():
    """Main app entry point with tabs for agent + individual tools."""
    st.set_page_config(
        page_title="TripMazer - Streaming",
        page_icon="🌍",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Custom CSS
    st.markdown("""
        <style>
        .stProgress > div > div > div > div {
            background-color: #00A86B;
        }
        .metric-card {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Main title
    st.title("🌍 TripMazer AI - Complete Travel Planning")
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🤖 AI Agent (Streaming)",
        "🏨 Hotels",
        "🗺️ Itinerary",
        "✈️ Travel",
        "🍽️ Restaurants"
    ])
    
    with tab1:
        streaming_trip_planner()
    
    with tab2:
        accommodations_section()
    
    with tab3:
        itinerary_section()
    
    with tab4:
        travel_section()
    
    with tab5:
        restaurants_section()
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: #666; padding: 1rem;'>
            <p>🌍 <strong>TripMazer AI</strong> - Real-time Trip Planning</p>
            <p>Powered by Gemini 2.5 Pro • Built with Streamlit</p>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
