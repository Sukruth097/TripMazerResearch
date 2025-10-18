import streamlit as st
import os
import sys
from datetime import datetime, date
from typing import Dict, Any, List
import json

# Add the current directory and parent directory to Python path for proper imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, current_dir)
sys.path.insert(0, parent_dir)

# Import the optimization tools with proper error handling
try:
    from tools.optimization.TravelOptimization import travel_search_tool
    from tools.optimization.AccomidationPlanner import search_accommodations
    from tools.optimization.RestaurantsSearch import search_restaurants
    from tools.optimization.IternaryPlanning import plan_itinerary
    
    # Import the comprehensive trip planning agent
    from agents.worker.trip_optimization_agent.agent import plan_complete_trip
    
    AGENT_AVAILABLE = True
except ImportError as e:
    st.error(f"Import Error: {e}")
    st.info("Please ensure all required modules are properly installed and environment variables are set.")
    AGENT_AVAILABLE = False

# Configure Streamlit page
st.set_page_config(
    page_title="TripMazer - AI Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme with green results
st.markdown("""
<style>
    /* Dark theme - Main background */
    .main {
        background-color: #000000 !important;
        color: #00FF00 !important;
    }
    
    /* Dark theme - Main container */
    .main .block-container {
        background-color: #000000 !important;
        color: #00FF00 !important;
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    
    /* Dark theme - Sidebar */
    .css-1d391kg {
        background-color: #1a1a1a !important;
        color: #00FF00 !important;
    }
    
    /* All text elements */
    .stMarkdown, .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #00FF00 !important;
        background-color: transparent !important;
    }
    
    /* Headers */
    .main-header {
        font-size: 3rem;
        color: #00FF00 !important;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
        background-color: #000000 !important;
    }
    
    .section-header {
        font-size: 2rem;
        color: #00FF00 !important;
        margin: 1.5rem 0 1rem 0;
        border-bottom: 2px solid #00FF00;
        padding-bottom: 0.5rem;
        background-color: #000000 !important;
    }
    
    /* Input fields */
    .stTextInput > div > div > input {
        background-color: #1a1a1a !important;
        color: #00FF00 !important;
        border: 1px solid #00FF00 !important;
    }
    
    .stTextArea > div > div > textarea {
        background-color: #1a1a1a !important;
        color: #00FF00 !important;
        border: 1px solid #00FF00 !important;
    }
    
    .stSelectbox > div > div > select {
        background-color: #1a1a1a !important;
        color: #00FF00 !important;
        border: 1px solid #00FF00 !important;
    }
    
    /* Chat messages - Green results */
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border: 1px solid #00FF00;
    }
    
    .user-message {
        background-color: #001a00 !important;
        border-left: 4px solid #00FF00;
        color: #00FF00 !important;
    }
    
    .assistant-message {
        background-color: #002000 !important;
        border-left: 4px solid #00FF00;
        color: #00FF00 !important;
    }
    
    /* Buttons - Dark with green border */
    .stButton > button {
        background-color: #1a1a1a !important;
        color: #00FF00 !important;
        border: 2px solid #00FF00 !important;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: bold;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        background-color: #00FF00 !important;
        color: #000000 !important;
    }
    
    /* Success/Info/Warning messages - Green theme */
    .stSuccess {
        background-color: #002000 !important;
        border: 1px solid #00FF00 !important;
        border-radius: 4px;
        padding: 0.75rem;
        color: #00FF00 !important;
    }
    
    .stInfo {
        background-color: #001a1a !important;
        border: 1px solid #00FFFF !important;
        border-radius: 4px;
        padding: 0.75rem;
        color: #00FFFF !important;
    }
    
    .stWarning {
        background-color: #1a1a00 !important;
        border: 1px solid #FFFF00 !important;
        border-radius: 4px;
        padding: 0.75rem;
        color: #FFFF00 !important;
    }
    
    .stError {
        background-color: #1a0000 !important;
        border: 1px solid #FF0000 !important;
        border-radius: 4px;
        padding: 0.75rem;
        color: #FF0000 !important;
    }
    
    /* Tables - Green theme */
    .stTable {
        background-color: #000000 !important;
        color: #00FF00 !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #1a1a1a !important;
        color: #00FF00 !important;
        border: 1px solid #00FF00 !important;
    }
    
    /* Code blocks */
    .stCode {
        background-color: #1a1a1a !important;
        color: #00FF00 !important;
        border: 1px solid #00FF00 !important;
    }
    
    /* Multiselect */
    .stMultiSelect > div > div {
        background-color: #1a1a1a !important;
        color: #00FF00 !important;
        border: 1px solid #00FF00 !important;
    }
    
    /* Date input */
    .stDateInput > div > div > input {
        background-color: #1a1a1a !important;
        color: #00FF00 !important;
        border: 1px solid #00FF00 !important;
    }
    
    /* Number input */
    .stNumberInput > div > div > input {
        background-color: #1a1a1a !important;
        color: #00FF00 !important;
        border: 1px solid #00FF00 !important;
    }
    
    /* Sidebar elements */
    .css-1d391kg .stMarkdown {
        color: #00FF00 !important;
    }
    
    .css-1d391kg .stButton > button {
        background-color: #1a1a1a !important;
        color: #00FF00 !important;
        border: 1px solid #00FF00 !important;
    }
    
    /* Force all text to be green */
    * {
        color: #00FF00 !important;
    }
    
    /* Override Streamlit's default white backgrounds */
    .stApp {
        background-color: #000000 !important;
    }
    
    /* Results and markdown content - Bright green */
    .element-container .stMarkdown {
        background-color: #000000 !important;
        color: #00FF00 !important;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-color: #00FF00 !important;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "trip_data" not in st.session_state:
        st.session_state.trip_data = {}
    if "current_step" not in st.session_state:
        st.session_state.current_step = "planning"

def display_header():
    """Display the main header"""
    st.markdown('<h1 class="main-header">🌍 TripMazer - AI Travel Planner</h1>', unsafe_allow_html=True)
    
    # Add a simple test to verify the app is loading
    st.markdown('<h3 style="color: #00FF00;">Welcome to TripMazer! 🎉</h3>', unsafe_allow_html=True)
    st.markdown('<p style="color: #00FF00;">Your intelligent AI-powered travel planning companion</p>', unsafe_allow_html=True)
    
    # Debug information
    if st.checkbox("Show Debug Info", value=False):
        st.success(f"✅ **App Status:** Streamlit is running properly")
        st.success(f"✅ **Agent Available:** {AGENT_AVAILABLE}")
        st.success(f"✅ **Current Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.success("✅ **Dark Theme:** Active with green text")
    
    st.markdown("---")

def sidebar_navigation():
    """Create sidebar navigation"""
    st.sidebar.markdown("# 🧭 Navigation")
    st.sidebar.markdown("---")
    
    sections = {
        "🎯 Trip Planning": "planning",
        "🏨 Accommodations": "accommodations", 
        "🍽️ Restaurants": "restaurants",
        "🗺️ Itinerary": "itinerary",
        "💬 Chat Assistant": "chat"
    }
    
    # Add some info about the app
    st.sidebar.info("🤖 **AI-Powered Travel Planning**\n\nChoose a section to start planning your perfect trip!")
    
    selected_section = st.sidebar.selectbox(
        "Choose a section:",
        list(sections.keys()),
        index=0
    )
    
    # Add agent status in sidebar
    if AGENT_AVAILABLE:
        st.sidebar.success("✅ AI Agent Ready")
    else:
        st.sidebar.warning("⚠️ AI Agent Offline")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🌟 Features:**")
    st.sidebar.markdown("• Multi-transport search")
    st.sidebar.markdown("• Smart accommodations")
    st.sidebar.markdown("• Restaurant discovery")
    st.sidebar.markdown("• AI chat assistant")
    
    return sections[selected_section]

def trip_planning_section():
    """Main trip planning section"""
    st.markdown('<h2 class="section-header">🎯 Trip Planning</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📍 Travel Details")
        
        # Source and destination
        source = st.text_input("From (Source City)", placeholder="e.g., Mumbai")
        destination = st.text_input("To (Destination City)", placeholder="e.g., Paris")
        
        # Travel dates
        start_date = st.date_input("Departure Date", min_value=date.today())
        end_date = st.date_input("Return Date", min_value=start_date)
        
        # Number of travelers
        travelers = st.number_input("Number of Travelers", min_value=1, max_value=10, value=2)
        
        # Budget (always in INR)
        budget = st.number_input("Budget (in INR ₹)", min_value=0, value=50000)
        currency = "INR"  # Always use INR for all destinations
        st.info("💡 All prices are displayed in INR (Indian Rupees) regardless of destination")
    
    with col2:
        st.subheader("⚙️ Preferences")
        
        # Travel modes
        st.write("**Travel Modes to Search:**")
        search_flights = st.checkbox("✈️ Flights", value=True)
        search_trains = st.checkbox("🚆 Trains", value=True)
        search_buses = st.checkbox("🚌 Buses", value=True)
        
        # Trip type
        trip_type = st.selectbox("Trip Type", ["Round Trip", "One Way"])
        
        # Additional preferences
        special_requests = st.text_area(
            "Special Requirements",
            placeholder="e.g., vegetarian food, business class, specific airlines, etc."
        )
    
    # Search button
    if st.button("🔍 Search Travel Options", type="primary", use_container_width=True):
        if source and destination:
            with st.spinner("🔄 Searching for the best travel options..."):
                try:
                    # Construct query for the optimization tool
                    query = f"""
                    Plan travel from {source} to {destination} for {travelers} people.
                    Travel dates: {start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')}
                    Budget: {currency} {budget}
                    Trip type: {trip_type}
                    Special requests: {special_requests}
                    Search modes: {', '.join([m for m, enabled in [('Flights', search_flights), ('Trains', search_trains), ('Buses', search_buses)] if enabled])}
                    """
                    
                    # Call the optimization tool
                    results = travel_search_tool.invoke({"query": query})
                    
                    # Store results in session state
                    st.session_state.trip_data = {
                        'source': source,
                        'destination': destination,
                        'start_date': start_date,
                        'end_date': end_date,
                        'travelers': travelers,
                        'budget': budget,
                        'currency': currency,
                        'results': results
                    }
                    
                    # Display results
                    st.success("✅ Travel options found!")
                    st.markdown("### 🎉 Search Results")
                    st.markdown(results)
                    
                except Exception as e:
                    st.error(f"❌ Error searching travel options: {str(e)}")
                    st.info("💡 Make sure your environment variables are properly configured.")
        else:
            st.warning("⚠️ Please fill in both source and destination cities.")

def accommodations_section():
    """Accommodations search section"""
    st.markdown('<h2 class="section-header">🏨 Accommodations</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🏨 Find Perfect Accommodations")
        
        # Auto-populate from trip data if available
        if st.session_state.trip_data:
            default_destination = st.session_state.trip_data.get('destination', '')
            default_checkin = st.session_state.trip_data.get('start_date', None)
            default_checkout = st.session_state.trip_data.get('end_date', None)
            default_guests = st.session_state.trip_data.get('travelers', 2)
        else:
            default_destination = ''
            default_checkin = None
            default_checkout = None
            default_guests = 2
        
        destination = st.text_input("Destination", value=default_destination, placeholder="e.g., Paris, Mumbai, Dubai")
        checkin_date = st.date_input("Check-in Date", value=default_checkin, min_value=date.today())
        checkout_date = st.date_input("Check-out Date", value=default_checkout, min_value=date.today())
        guests = st.number_input("Number of Guests", min_value=1, max_value=10, value=default_guests)
        
        # Accommodation preference: Budget or Luxury (determines SERP query)
        st.markdown("**Accommodation Preference**")
        accommodation_type = st.radio(
            "Select preference:",
            ["Budget (Hotels & Hostels)", "Luxury (Premium Hotels)"],
            help="Budget: Affordable hotels, hostels, and budget accommodations\nLuxury: Premium hotels, resorts, and high-end properties",
            label_visibility="collapsed"
        )
        
        # Info about what user will get
        if accommodation_type == "Budget (Hotels & Hostels)":
            st.info("🏨 **Budget Search:** Searching for affordable hotels, hostels, and budget-friendly accommodations with best value for money.")
        else:
            st.info("✨ **Luxury Search:** Searching for premium hotels, resorts, and high-end properties with top amenities and services.")
    
    with col2:
        st.subheader("🎯 Quick Options")
        st.info("💡 **Tip:** Use the trip planning section first to auto-populate your accommodation search!")
        
        if st.button("🔄 Use Trip Data", help="Auto-fill from your trip planning"):
            if st.session_state.trip_data:
                st.rerun()
            else:
                st.warning("⚠️ Please complete trip planning first")
    
    # Search accommodations
    if st.button("🏨 Search Accommodations", type="primary", use_container_width=True):
        if destination:
            with st.spinner("🔄 Searching hotels via Google Hotels API..."):
                try:
                    # Extract parameters for SERP hotel search
                    check_in_str = checkin_date.strftime('%Y-%m-%d')
                    check_out_str = checkout_date.strftime('%Y-%m-%d')
                    
                    # Always use INR for all destinations
                    currency = "INR"
                    
                    # Construct simple SERP query based on accommodation type
                    # CRITICAL: SERP API fails with detailed queries - keep it simple!
                    if accommodation_type == "Luxury (Premium Hotels)":
                        serp_query = f"Luxury hotels in {destination}"
                    else:
                        serp_query = f"Budget hotels and hostels in {destination}"
                    
                    # Call tool with structured parameters
                    # Note: rating defaults to [7, 8, 9] in tool - no need to specify
                    results = search_accommodations.invoke({
                        "location": destination,
                        "check_in_date": check_in_str,
                        "check_out_date": check_out_str,
                        "adults": guests,
                        "children": 0,
                        "currency": currency,
                        # rating defaults to [7, 8, 9] in tool
                        "query": serp_query  # Simple query: "Budget hotels and hostels in X" or "Luxury hotels in X"
                    })
                    
                    st.success("✅ Hotels found via Google Hotels API!")
                    st.markdown("### 🏨 Hotel Search Results")
                    st.markdown(results)
                    
                except Exception as e:
                    st.error(f"❌ Error searching accommodations: {str(e)}")
        else:
            st.warning("⚠️ Please enter a destination.")

def restaurants_section():
    """Restaurants search section"""
    st.markdown('<h2 class="section-header">🍽️ Restaurants</h2>', unsafe_allow_html=True)
    
    st.subheader("🍽️ Find Amazing Restaurants")
    
    # Input for itinerary or manual entry
    input_method = st.radio("How would you like to search?", ["Based on Itinerary", "Manual Search"])
    
    if input_method == "Based on Itinerary":
        itinerary_input = st.text_area(
            "Paste your itinerary here:",
            placeholder="Day 1 - Paris: Visit Eiffel Tower (9:00 AM), Louvre Museum (2:00 PM)...",
            height=150
        )
        
        col1, col2 = st.columns(2)
        with col1:
            travel_dates = st.text_input(
                "Travel Dates",
                placeholder="25-12-2025 to 28-12-2025"
            )
        with col2:
            dietary_prefs = st.selectbox(
                "Dietary Preferences",
                ["veg and non-veg", "veg only", "non-veg only", "vegan", "gluten-free"]
            )
        
        budget_hint = st.text_input(
            "Budget Hint (optional)",
            placeholder="e.g., INR 5000 for 2 people for 3 days"
        )
        
        if st.button("🍽️ Find Restaurants", type="primary", use_container_width=True):
            if itinerary_input and travel_dates:
                with st.spinner("🔄 Finding perfect restaurants..."):
                    try:
                        results = search_restaurants(itinerary_input, travel_dates, dietary_prefs, budget_hint)
                        
                        st.success("✅ Restaurants found!")
                        st.markdown("### 🍽️ Restaurant Recommendations")
                        st.markdown(results)
                        
                    except Exception as e:
                        st.error(f"❌ Error finding restaurants: {str(e)}")
            else:
                st.warning("⚠️ Please provide itinerary and travel dates.")
    
    else:  # Manual Search
        col1, col2 = st.columns(2)
        with col1:
            city = st.text_input("City", placeholder="e.g., Paris")
            cuisine_type = st.selectbox("Cuisine Type", ["Any", "Local", "Italian", "Chinese", "Indian", "French", "Japanese", "Mexican"])
        
        with col2:
            meal_time = st.selectbox("Meal Time", ["Any", "Breakfast", "Lunch", "Dinner", "Snacks"])
            price_range = st.selectbox("Price Range", ["Any", "Budget", "Mid-range", "Fine Dining"])
        
        if st.button("🔍 Search Restaurants", type="primary", use_container_width=True):
            if city:
                # Create a simple itinerary for the search
                simple_itinerary = f"Visiting {city} for {meal_time} - looking for {cuisine_type} cuisine in {price_range} price range"
                travel_dates = datetime.now().strftime("%d-%m-%Y")
                
                with st.spinner("🔄 Searching restaurants..."):
                    try:
                        results = search_restaurants(simple_itinerary, travel_dates, "veg and non-veg", "")
                        
                        st.success("✅ Restaurants found!")
                        st.markdown("### 🍽️ Restaurant Options")
                        st.markdown(results)
                        
                    except Exception as e:
                        st.error(f"❌ Error searching restaurants: {str(e)}")
            else:
                st.warning("⚠️ Please enter a city.")

def itinerary_section():
    """Itinerary planning section"""
    st.markdown('<h2 class="section-header">🗺️ Itinerary Planning</h2>', unsafe_allow_html=True)
    
    st.subheader("🗺️ Create Your Perfect Itinerary")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Auto-populate from trip data if available
        if st.session_state.trip_data:
            default_destination = st.session_state.trip_data.get('destination', '')
            default_duration = f"{st.session_state.trip_data.get('start_date', '')} to {st.session_state.trip_data.get('end_date', '')}"
            default_travelers = st.session_state.trip_data.get('travelers', 2)
        else:
            default_destination = ''
            default_duration = ''
            default_travelers = 2
        
        destination = st.text_input("Destination", value=default_destination, placeholder="e.g., Tokyo, Japan")
        duration = st.text_input("Duration", value=default_duration, placeholder="e.g., 26-11-2025 to 30-11-2025 or 5 days")
        travelers_count = st.number_input("Number of Travelers", min_value=1, max_value=20, value=default_travelers)
        
        interests = st.multiselect(
            "Interests & Activities",
            ["Historical Sites", "Museums", "Adventure Sports", "Nature & Parks", "Shopping", 
             "Nightlife", "Cultural Experiences", "Food Tours", "Beach Activities", "Photography"]
        )
    
    with col2:
        travel_style = st.selectbox(
            "Travel Style",
            ["Balanced", "Relaxed", "Packed/Adventurous", "Cultural Focus", "Nature Focus"]
        )
        
        budget_level = st.selectbox(
            "Budget Level",
            ["Budget-friendly", "Mid-range", "Luxury", "No specific budget"]
        )
        
        special_considerations = st.text_area(
            "Special Considerations",
            placeholder="e.g., traveling with kids, accessibility needs, specific events to attend...",
            height=100
        )
    
    # Additional preferences
    with st.expander("🎯 Advanced Preferences"):
        transportation_pref = st.selectbox(
            "Local Transportation Preference",
            ["Public Transport", "Taxis/Rideshare", "Rental Car", "Walking", "Mixed"]
        )
        
        accommodation_area = st.text_input(
            "Preferred Accommodation Area",
            placeholder="e.g., city center, near airport, specific neighborhood"
        )
    
    if st.button("🗺️ Create Itinerary", type="primary", use_container_width=True):
        if destination and duration:
            with st.spinner("🔄 Creating your perfect itinerary..."):
                try:
                    interests_str = ", ".join(interests) if interests else "general sightseeing"
                    
                    query = f"""
                    Create a detailed itinerary for {destination} for {travelers_count} people.
                    Duration: {duration}
                    Interests: {interests_str}
                    Travel style: {travel_style}
                    Budget level: {budget_level}
                    Transportation preference: {transportation_pref}
                    Special considerations: {special_considerations}
                    Preferred area: {accommodation_area}
                    """
                    
                    results = plan_itinerary.invoke({"query": query})
                    
                    st.success("✅ Itinerary created!")
                    st.markdown("### 🗺️ Your Custom Itinerary")
                    st.markdown(results)
                    
                    # Store itinerary for restaurant search
                    st.session_state.current_itinerary = results
                    
                    # Option to find restaurants based on this itinerary
                    if st.button("🍽️ Find Restaurants for this Itinerary"):
                        st.session_state.current_step = "restaurants"
                        st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error creating itinerary: {str(e)}")
        else:
            st.warning("⚠️ Please provide destination and duration.")

def chat_section():
    """Chat assistant section"""
    st.markdown('<h2 class="section-header">💬 Chat Assistant</h2>', unsafe_allow_html=True)
    
    st.subheader("💬 Ask Me Anything About Your Trip")
    
    if AGENT_AVAILABLE:
        st.success("🤖 **AI Trip Planning Agent Available** - I can create complete trip plans!")
        st.info("💡 **Try asking:** *'Plan a trip for 3 people with budget 50000 INR from Bangalore to Mumbai on 27-11-25 to 30-11-25, we prefer flights and like beaches'*")
    else:
        st.warning("⚠️ **Limited Mode** - Individual tools available, but comprehensive AI agent is offline.")
    
    st.info("💡 You can ask about travel tips, local customs, weather, or request complete trip planning!")
    
    # Chat interface
    chat_container = st.container()
    
    # Display chat history
    with chat_container:
        for i, message in enumerate(st.session_state.chat_history):
            if message["role"] == "user":
                st.markdown(f'<div class="chat-message user-message"><strong>You:</strong> {message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message assistant-message"><strong>TripMazer:</strong> {message["content"]}</div>', unsafe_allow_html=True)
    
    # Chat input
    user_input = st.text_input("Type your message here...", key="chat_input", placeholder="e.g., What's the weather like in Paris in December?")
    
    col1, col2, col3 = st.columns([1, 1, 3])
    
    with col1:
        if st.button("Send 📤", type="primary"):
            if user_input.strip():
                # Add user message to history
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                
                # Generate response (simple rule-based for now)
                response = generate_chat_response(user_input)
                
                # Add assistant response to history
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                
                # Clear input and refresh
                st.rerun()
    
    with col2:
        if st.button("Clear Chat 🗑️"):
            st.session_state.chat_history = []
            st.rerun()
    
    # Quick action buttons
    st.markdown("### 🚀 Quick Actions")
    
    # Add comprehensive trip planning button if agent is available
    if AGENT_AVAILABLE:
        cols_planning = st.columns(2)
        with cols_planning[0]:
            if st.button("🎯 **Complete Trip Planning**", key="comprehensive_planning"):
                sample_query = "Plan a trip for 2 people with budget 30000 INR from Delhi to Goa from 15-12-2025 to 20-12-2025, we prefer beaches and comfortable stays"
                st.session_state.chat_history.append({"role": "user", "content": sample_query})
                response = generate_chat_response(sample_query)
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()
        
        with cols_planning[1]:
            if st.button("📝 **Custom Trip Query**", key="custom_planning"):
                st.info("💡 **Type your complete trip planning request above!** Include: source, destination, dates, budget, preferences")
    
    quick_actions = {
        "💰 Travel Budget Tips": "Give me tips for budgeting my trip",
        "🎒 Packing Checklist": "What should I pack for my trip?",
        "📱 Travel Apps": "What are the best travel apps to download?",
        "💳 Payment Methods": "What payment methods should I use while traveling?",
        "🏥 Travel Insurance": "Do I need travel insurance and what should it cover?",
        "📋 Travel Documents": "What documents do I need for international travel?"
    }
    
    cols = st.columns(3)
    for i, (button_text, query) in enumerate(quick_actions.items()):
        with cols[i % 3]:
            if st.button(button_text, key=f"quick_{i}"):
                st.session_state.chat_history.append({"role": "user", "content": query})
                response = generate_chat_response(query)
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()

def generate_chat_response(user_input: str) -> str:
    """Generate a response for the chat (enhanced with trip planning agent)"""
    user_input_lower = user_input.lower()
    
    # Check if this is a comprehensive trip planning query
    trip_planning_keywords = [
        "plan a trip", "plan trip", "complete trip", "trip plan", "itinerary",
        "travel plan", "plan my travel", "organize trip", "trip planning",
        "vacation plan", "holiday plan", "travel itinerary"
    ]
    
    # Check if user is asking for comprehensive trip planning
    is_trip_planning = any(keyword in user_input_lower for keyword in trip_planning_keywords)
    
    # Also check for location patterns (from X to Y)
    has_locations = any(word in user_input_lower for word in [
        "from", "to", "bangalore", "mumbai", "delhi", "chennai", "kolkata", 
        "hyderabad", "pune", "goa", "kerala", "paris", "london", "tokyo", "new york"
    ])
    
    # Check for budget indicators
    has_budget = any(word in user_input_lower for word in [
        "budget", "rupees", "inr", "₹", "$", "dollars", "cost", "price"
    ])
    
    # Check for date indicators
    has_dates = any(word in user_input_lower for word in [
        "25", "26", "27", "28", "29", "30", "january", "february", "march", 
        "april", "may", "june", "july", "august", "september", "october", 
        "november", "december", "2025", "2026"
    ])
    
    # If it looks like a comprehensive trip planning request, use the agent
    if AGENT_AVAILABLE and (is_trip_planning or (has_locations and (has_budget or has_dates))):
        try:
            st.info("🤖 **Processing your trip planning request with AI Agent...**")
            st.info("This may take a moment as I analyze your requirements and create a comprehensive plan.")
            
            # Use the comprehensive trip planning agent
            with st.spinner("🔄 Creating your personalized trip plan..."):
                result = plan_complete_trip(user_input)
                
                if "error" in result:
                    return f"""❌ **Error in trip planning:** {result['error']}
                    
Please make sure you have set up your environment variables:
- PERPLEXITY_API_KEY
- GEMINI_API_KEY  
- SERP_API_KEY

You can also try using the individual planning sections above."""
                
                # Extract the comprehensive result
                combined_result = result.get("combined_result", "")
                execution_summary = result.get("execution_summary", "")
                
                if combined_result:
                    response = f"""🎉 **Your Complete Trip Plan is Ready!**

{combined_result}

---

### 📊 **Planning Summary**
{execution_summary if execution_summary else "Planning completed successfully with all tools executed."}

---

💡 **Next Steps:**
- Review the itinerary and make any adjustments needed
- Book accommodations and flights as recommended
- Save restaurant recommendations for your trip
- Check visa requirements if traveling internationally

*This comprehensive plan was created using AI analysis of your preferences and real-time data.*"""
                    return response
                else:
                    return """⚠️ **Trip planning completed but no detailed results available.**
                    
Please try using the individual planning sections above, or rephrase your query with more specific details like:
- Source and destination cities
- Travel dates
- Budget amount
- Number of travelers
- Specific preferences"""
                    
        except Exception as e:
            return f"""❌ **Error with AI Trip Planning Agent:** {str(e)}
            
Don't worry! You can still use the individual planning sections:
- 🎯 **Trip Planning** - Search transport options
- 🏨 **Accommodations** - Find hotels
- 🍽️ **Restaurants** - Discover dining
- 🗺️ **Itinerary** - Create day plans

Or try rephrasing your request with clear details about your destination, dates, and budget."""

    # For non-trip planning queries, use existing responses
    if "budget" in user_input_lower or "money" in user_input_lower:
        return """💰 **Budget Travel Tips:**
        
        1. **Plan ahead** - Book flights and accommodations early
        2. **Use comparison sites** - Compare prices across different platforms
        3. **Travel off-season** - Avoid peak tourist seasons
        4. **Local transportation** - Use public transport instead of taxis
        5. **Local food** - Eat where locals eat for authentic and cheaper meals
        6. **Free activities** - Look for free walking tours, museums, and parks
        7. **Travel insurance** - Protect yourself from unexpected expenses
        """
    
    elif "pack" in user_input_lower or "luggage" in user_input_lower:
        return """🎒 **Essential Packing Checklist:**
        
        **Documents:**
        - Passport/ID, Visa (if required)
        - Travel insurance documents
        - Flight tickets, hotel confirmations
        - Emergency contact information
        
        **Clothing:**
        - Weather-appropriate clothes
        - Comfortable walking shoes
        - One formal outfit
        - Undergarments and socks
        
        **Electronics:**
        - Phone charger, power bank
        - Camera and charger
        - Universal adapter
        - Headphones
        
        **Health & Personal:**
        - Medications, first aid kit
        - Toiletries, sunscreen
        - Hand sanitizer
        """
    
    elif "app" in user_input_lower or "application" in user_input_lower:
        return """📱 **Best Travel Apps:**
        
        **Navigation:**
        - Google Maps (offline maps)
        - Citymapper (public transport)
        
        **Translation:**
        - Google Translate (offline mode)
        - Microsoft Translator
        
        **Accommodation:**
        - Booking.com, Airbnb
        - Hostelworld
        
        **Transportation:**
        - Uber/Lyft, local ride apps
        - Rome2Rio (route planning)
        
        **General:**
        - TripAdvisor (reviews)
        - XE Currency (exchange rates)
        - Weather apps
        """
    
    elif "payment" in user_input_lower or "card" in user_input_lower:
        return """💳 **Payment Methods for Travel:**
        
        **Recommended:**
        - Credit cards with no foreign transaction fees
        - Debit card from major network (Visa/Mastercard)
        - Some local currency cash
        - Mobile payment apps (where accepted)
        
        **Tips:**
        - Notify your bank of travel plans
        - Have backup payment methods
        - Research local payment preferences
        - Keep payment methods in separate places
        - Check ATM networks at your destination
        """
    
    elif "insurance" in user_input_lower:
        return """🏥 **Travel Insurance Guide:**
        
        **Why you need it:**
        - Medical emergencies abroad
        - Trip cancellation/interruption
        - Lost/stolen luggage
        - Emergency evacuation
        
        **What to look for:**
        - Medical coverage (minimum $100,000)
        - Emergency evacuation
        - Trip cancellation/interruption
        - Baggage loss/delay
        - 24/7 emergency assistance
        
        **When to buy:**
        - As soon as you book your trip
        - Before any cancellation penalties apply
        """
    
    elif "document" in user_input_lower:
        return """📋 **Essential Travel Documents:**
        
        **International Travel:**
        - Valid passport (6+ months validity)
        - Visa (if required for destination)
        - Travel insurance documents
        - Flight tickets (electronic is fine)
        
        **Accommodation:**
        - Hotel/accommodation confirmations
        - Contact information
        
        **Health:**
        - Vaccination records (if required)
        - Prescription medications letter
        - Medical history summary
        
        **Financial:**
        - Credit cards, bank notifications
        - Emergency contact information
        """
    
    else:
        return f"""I'd be happy to help you with your travel question about: "{user_input}"
        
        For specific travel planning, I recommend using the dedicated sections:
        - 🎯 **Trip Planning** - Search flights, trains, and buses
        - 🏨 **Accommodations** - Find hotels and stays
        - 🍽️ **Restaurants** - Discover local dining
        - 🗺️ **Itinerary** - Create detailed day plans
        
        You can also ask me about:
        - Travel tips and advice
        - Destination information
        - Packing suggestions
        - Budget planning
        - Travel safety
        
        What specific aspect of travel planning can I help you with?"""

def main():
    """Main application function"""
    # Simple loading test
    st.write("🔄 Loading TripMazer...")
    
    # Check if agent is available
    if not AGENT_AVAILABLE:
        st.error("⚠️ **Agent Import Error**: Some features may not work properly.")
        st.info("💡 **You can still use individual planning tools**, but the comprehensive AI agent won't be available in chat.")
    
    # Initialize session state
    initialize_session_state()
    
    # Display header
    display_header()
    
    # Get current section from sidebar
    current_section = sidebar_navigation()
    
    # Clear the loading message
    st.empty()
    
    # Display appropriate section
    if current_section == "planning":
        trip_planning_section()
    elif current_section == "accommodations":
        accommodations_section()
    elif current_section == "restaurants":
        restaurants_section()
    elif current_section == "itinerary":
        itinerary_section()
    elif current_section == "chat":
        chat_section()
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666; padding: 2rem;'>
            <p>🌍 <strong>TripMazer AI Travel Planner</strong> - Your intelligent travel companion</p>
            <p>Powered by AI • Built with ❤️ for travelers</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"❌ **Application Error:** {str(e)}")
        st.info("🔧 **Troubleshooting:**")
        st.info("1. Make sure all dependencies are installed: `pip install -r requirements.txt`")
        st.info("2. Check your .env file has the required API keys")
        st.info("3. Try refreshing the page")
        st.code(f"Error details: {str(e)}", language="text")