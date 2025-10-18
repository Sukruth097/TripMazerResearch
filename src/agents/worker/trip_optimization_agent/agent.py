import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Add path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain.schema import BaseMessage
from dotenv import load_dotenv
# Import optimization tools
from src.tools.optimization import (
    search_accommodations, 
    plan_itinerary, 
    search_restaurants, 
    travel_search_tool
)

# Import travel search entity
from src.entity.travel_search_params import TravelSearchParams

# Import state manager
from src.state.state_manager import get_state_manager, reset_state

# Import Google Gemini for LLM processing
try:
    from google import genai
except ImportError:
    genai = None

from src.services.perplexity_service import PerplexityService
load_dotenv()

class TripOptimizationAgent:
    """
    Intelligent trip optimization agent that routes through multiple tools
    based on user preferences and manages budget allocation.
    """
    
    def __init__(self, enable_logging=True):
        self.state_manager = get_state_manager()
        self.graph = self._build_graph()
        
        # Setup comprehensive logging
        if enable_logging:
            self._setup_logging()
        
        # Default tool routing order (restaurant removed - available via API only)
        self.default_sequence = ["itinerary", "travel", "accommodation"]
        
        # Tool mapping
        self.tools = {
            "accommodation": search_accommodations,
            "itinerary": plan_itinerary,
            "restaurant": search_restaurants,
            "travel": travel_search_tool
        }
        
        # Execution tracking
        self.execution_id = None
        self.execution_start_time = None
        
        self.logger.info("TripOptimizationAgent initialized successfully")
        self.logger.info(f"Available tools: {list(self.tools.keys())}")
        self.logger.info(f"Default tool sequence: {self.default_sequence}")
    
    def _setup_logging(self):
        """Setup comprehensive logging for the agent."""
        # Create logs directory if it doesn't exist
        logs_dir = "logs"
        os.makedirs(logs_dir, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger('TripOptimizationAgent')
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # File handler for detailed logs
        file_handler = logging.FileHandler(f'{logs_dir}/trip_agent_detailed.log', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(detailed_formatter)
        
        # Console handler for simple logs
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Also create execution-specific log file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        execution_handler = logging.FileHandler(f'{logs_dir}/execution_{timestamp}.log', encoding='utf-8')
        execution_handler.setLevel(logging.INFO)
        execution_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(execution_handler)
        
        self.logger.info("=" * 80)
        self.logger.info("LOGGING SYSTEM INITIALIZED")
        self.logger.info("=" * 80)
    
    def _log_tool_output(self, tool_name: str, output: str):
        """Log full tool output to separate file."""
        try:
            logs_dir = "logs"
            tool_log_file = f"{logs_dir}/tool_outputs_{self.execution_id}.log"
            
            with open(tool_log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"TOOL: {tool_name.upper()}\n")
                f.write(f"TIMESTAMP: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*80}\n")
                f.write(str(output))
                f.write(f"\n{'='*80}\n\n")
                
            self.logger.info(f"Full tool output logged to: {tool_log_file}")
        except Exception as e:
            self.logger.error(f"Failed to log tool output: {e}")
    
    def _log_final_output(self, final_result: dict):
        """Log final agent output to separate file."""
        try:
            logs_dir = "logs"
            final_log_file = f"{logs_dir}/final_output_{self.execution_id}.log"
            
            with open(final_log_file, 'w', encoding='utf-8') as f:
                f.write(f"FINAL AGENT OUTPUT\n")
                f.write(f"Execution ID: {self.execution_id}\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*100}\n\n")
                
                # Write combined result
                if final_result.get("combined_result"):
                    f.write("COMBINED RESULT:\n")
                    f.write(f"{'-'*50}\n")
                    f.write(str(final_result["combined_result"]))
                    f.write(f"\n{'-'*50}\n\n")
                
                # Write execution summary
                if final_result.get("execution_summary"):
                    f.write("EXECUTION SUMMARY:\n")
                    f.write(f"{'-'*50}\n")
                    f.write(str(final_result["execution_summary"]))
                    f.write(f"\n{'-'*50}\n\n")
                
                # Write state
                if final_result.get("state"):
                    f.write("FINAL STATE:\n")
                    f.write(f"{'-'*50}\n")
                    f.write(str(final_result["state"]))
                    f.write(f"\n{'-'*50}\n")
                
            self.logger.info(f"Final agent output logged to: {final_log_file}")
        except Exception as e:
            self.logger.error(f"Failed to log final output: {e}")
    
    def _get_perplexity_service(self) -> PerplexityService:
        """Get Perplexity service instance with API key."""
        api_key = os.getenv('PERPLEXITY_API_KEY')
        if not api_key:
            raise ValueError("PERPLEXITY_API_KEY environment variable is required")
        return PerplexityService(api_key)
    
    def _get_gemini_client(self):
        """Get Google Gemini client with API key."""
        if genai is None:
            raise ImportError("google-genai package not available")
            
        # Use the provided API key directly
        api_key = os.getenv('GEMINI_API_KEY')
        client = genai.Client(api_key=api_key)
        return client
    
    def extract_travel_parameters_with_gemini(self, query: str) -> TravelSearchParams:
        """
        Extract travel search parameters using Gemini AI.
        
        This method handles the parameter extraction that was previously done in tools.
        Now the agent takes responsibility for AI-powered parameter extraction.
        
        Args:
            query: Natural language travel query
            
        Returns:
            TravelSearchParams entity with extracted parameters
        """
        self.logger.info("Extracting travel parameters with Gemini...")
        
        try:
            client = self._get_gemini_client()
            
            prompt = f"""
            TASK: Extract travel search parameters from natural language query.
            
            QUERY: "{query}"
            
            Extract the following parameters and return as JSON:
            
            {{
                "origin": "departure city/location",
                "destination": "arrival city/location", 
                "departure_date": "YYYY-MM-DD format",
                "return_date": "YYYY-MM-DD format or null for one-way",
                "travelers": "number of travelers",
                "budget_limit": "budget amount (number only) or null",
                "currency": "INR for Indian routes, USD for international",
                "transport_modes": ["flight", "bus", "train"] - include all relevant modes,
                "preferred_mode": "user's preferred transport mode or null",
                "trip_type": "round_trip or one_way",
                "is_domestic": true/false,
                "budget_priority": "tight/moderate/flexible",
                "time_sensitivity": "urgent/moderate/flexible"
            }}
            
            RULES:
            1. Extract locations as mentioned (currency and domestic/international will be resolved separately)
            2. Include all relevant transport modes mentioned or ["flight", "bus", "train"] as default
            3. For budget-conscious queries, set budget_priority="tight"
            4. Extract actual dates mentioned, convert to YYYY-MM-DD
            5. If no budget mentioned, set budget_limit=null
            6. Default travelers=1 if not specified
            7. Set currency="USD" as placeholder (will be resolved by location analysis)
            8. Set is_domestic=false as placeholder (will be resolved by location analysis)
            
            Return ONLY valid JSON.
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
            
            # Parse response
            extracted_data = json.loads(response_text)
            
            # Create TravelSearchParams entity
            params = TravelSearchParams.from_dict(extracted_data)
            
            self.logger.info(f"Extracted parameters: {extracted_data}")
            return params
            
        except Exception as e:
            self.logger.error(f"Parameter extraction failed: {e}")
            # Fallback to basic parameters
            return TravelSearchParams(
                origin="Not specified",
                destination="Not specified", 
                departure_date="2024-12-01",
                transport_modes=["flight", "bus", "train"],
                travelers=1,
                currency="USD"
            )
    
    def resolve_airport_codes_and_currency(self, params: TravelSearchParams) -> TravelSearchParams:
        """
        Use Gemini to resolve airport codes for any location and determine currency.
        
        This replaces the static airport mapping with dynamic LLM-based resolution
        that can handle any city/region globally.
        
        Args:
            params: TravelSearchParams with city names
            
        Returns:
            Updated TravelSearchParams with airport codes and correct currency
        """
        self.logger.info(f"Resolving airport codes and currency for {params.origin} -> {params.destination}")
        
        try:
            client = self._get_gemini_client()
            
            prompt = f"""
            TASK: Resolve airport codes and determine currency for travel locations.
            
            ORIGIN: "{params.origin}"
            DESTINATION: "{params.destination}"
            
            For each location, provide:
            1. Airport code (3-letter IATA code for the nearest major airport)
            2. Whether it's in India (for currency detection)
            3. Full city/region name (standardized)
            
            RULES:
            - Use major international airports for cities
            - For regions/states, use the main airport (e.g., Goa -> GOX, Kerala -> COK)
            - For small cities, use nearest major airport
            - Indian locations: Mumbai=BOM, Delhi=DEL, Bangalore=BLR, Chennai=MAA, etc.
            - International: New York=JFK/LGA, London=LHR, Paris=CDG, Tokyo=NRT, etc.
            
            CURRENCY LOGIC:
            - If EITHER origin OR destination is in India -> "INR"
            - If BOTH are outside India -> "USD"  
            - Indian regions/states: All states, Union Territories, major cities in India
            
            DOMESTIC vs INTERNATIONAL:
            - is_domestic: true if BOTH locations are in India
            - is_international: true if AT LEAST ONE location is outside India
            
            Return ONLY valid JSON:
            {{
                "origin_airport": "3-letter code",
                "destination_airport": "3-letter code", 
                "origin_city": "standardized city name",
                "destination_city": "standardized city name",
                "origin_is_indian": true/false,
                "destination_is_indian": true/false,
                "currency": "INR or USD",
                "is_domestic": true/false,
                "is_international": true/false
            }}
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
            
            # Parse response
            resolution_data = json.loads(response_text)
            
            # Update parameters with resolved data
            params.origin = resolution_data.get('origin_city', params.origin)
            params.destination = resolution_data.get('destination_city', params.destination) 
            params.currency = resolution_data.get('currency', 'USD')
            params.is_domestic = resolution_data.get('is_domestic', False)
            params.is_international = resolution_data.get('is_international', True)
            
            # Store airport codes for use in flight searches
            params.origin_airport = resolution_data.get('origin_airport', params.origin[:3].upper())
            params.destination_airport = resolution_data.get('destination_airport', params.destination[:3].upper())
            
            self.logger.info(f"Resolved: {params.origin}({params.origin_airport}) -> {params.destination}({params.destination_airport}), Currency: {params.currency}")
            return params
            
        except Exception as e:
            self.logger.error(f"Airport code resolution failed: {e}")
            # Fallback: basic logic
            indian_keywords = ['mumbai', 'delhi', 'bangalore', 'chennai', 'kolkata', 'hyderabad', 'pune', 'goa', 'kerala', 'tamil nadu', 'karnataka', 'maharashtra']
            
            origin_is_indian = any(keyword in params.origin.lower() for keyword in indian_keywords)
            dest_is_indian = any(keyword in params.destination.lower() for keyword in indian_keywords)
            
            if origin_is_indian or dest_is_indian:
                params.currency = 'INR'
            else:
                params.currency = 'USD'
                
            params.is_domestic = origin_is_indian and dest_is_indian
            params.is_international = not params.is_domestic
            
            # Basic airport codes as fallback
            params.origin_airport = params.origin[:3].upper()
            params.destination_airport = params.destination[:3].upper()
            
            return params
    
    def format_travel_results_with_prompt(self, raw_results: str, user_context: Dict[str, Any]) -> str:
        """
        Format travel search results using AI-powered prompt instead of hardcoded methods.
        
        This replaces the multiple formatting methods that were in the tools.
        The agent uses its AI capabilities to intelligently format results.
        
        Args:
            raw_results: Raw JSON results from travel_search_tool
            user_context: User preferences and context
            
        Returns:
            Formatted travel results as markdown tables
        """
        self.logger.info("Formatting travel results with AI...")
        
        try:
            client = self._get_gemini_client()
            
            # Parse raw results if it's JSON string
            if isinstance(raw_results, str):
                try:
                    results_data = json.loads(raw_results)
                except:
                    results_data = {"raw_text": raw_results}
            else:
                results_data = raw_results
            
            budget = user_context.get('budget', 'Not specified')
            currency = user_context.get('currency', 'USD')
            travelers = user_context.get('travelers', 1)
            preferred_mode = user_context.get('preferred_mode', 'any')
            
            formatting_prompt = f"""
            TASK: Format travel search results into beautiful, professional markdown tables.
            
            USER CONTEXT:
            - Budget: {budget} {currency}
            - Travelers: {travelers}
            - Preferred Transport: {preferred_mode}
            - Budget Priority: {user_context.get('budget_priority', 'moderate')}
            
            RAW RESULTS (Pre-structured for easy formatting):
            {json.dumps(results_data, indent=2)[:4000]}
            
            FLIGHT DATA STRUCTURE (Already extracted and clean):
            - Flight data is in: results.results.flights.outbound_flights[] and results.results.flights.return_flights[]
            - Each flight object has these READY-TO-USE fields:
              * airline: string (e.g., "Akasa Air" or "IndiGo, Air India")
              * departure_time: string (e.g., "2025-12-01 07:05")
              * arrival_time: string (e.g., "2025-12-01 09:20")
              * duration_minutes: integer (e.g., 135)
              * price_per_person: float (e.g., 10698)
              * carbon_grams: integer (e.g., 177000)
            
            TRAIN DATA STRUCTURE (Already extracted and clean):
            - Train data is in: results.results.ground_transport.outbound_trains[] and return_trains[]
            - Each train object has these READY-TO-USE fields:
              * operator: string (e.g., "Rajdhani Express 12951")
              * service_type: string (e.g., "2A" or "3A" or "Sleeper")
              * departure_time: string (e.g., "17:00")
              * arrival_time: string (e.g., "08:35")
              * duration_minutes: integer (e.g., 935)
              * price_per_person: float (e.g., 3500)
              * platform: string (e.g., "IRCTC" or "MakeMyTrip")
            
            BUS DATA STRUCTURE (Already extracted and clean):
            - Bus data is in: results.results.ground_transport.outbound_buses[] and return_buses[]
            - Each bus object has these READY-TO-USE fields:
              * operator: string (e.g., "VRL Travels")
              * service_type: string (e.g., "AC Sleeper" or "Volvo")
              * departure_time: string (e.g., "20:00")
              * arrival_time: string (e.g., "08:00")
              * duration_minutes: integer (e.g., 1470)
              * price_per_person: float (e.g., 2000)
              * platform: string (e.g., "RedBus" or "AbhiBus")
            
            TABLE FORMAT REQUIREMENTS:
            
            For FLIGHTS - Use this exact table structure:
            | # | Airline(s) | Departure | Arrival | Duration | Price/Person | Total ({travelers}p) |
            |---|------------|-----------|---------|----------|--------------|---------------------|
            | 1 | Akasa Air  | 07:05     | 09:20   | 2h 15m   | ₹10,698     | ₹21,396            |
            
            For TRAINS - Use this exact table structure:
            | # | Train/Class | Departure | Arrival | Duration | Price/Person | Total ({travelers}p) | Platform |
            |---|-------------|-----------|---------|----------|--------------|---------------------|----------|
            | 1 | Rajdhani 12951 (2A) | 17:00 | 08:35 | 15h 35m | ₹3,500 | ₹7,000 | IRCTC |
            
            For BUSES - Use this exact table structure:
            | # | Operator/Type | Departure | Arrival | Duration | Price/Person | Total ({travelers}p) | Platform |
            |---|---------------|-----------|---------|----------|--------------|---------------------|----------|
            | 1 | VRL Travels (AC Sleeper) | 20:00 | 08:00 | 24h 30m | ₹2,000 | ₹4,000 | RedBus |
            
            FORMATTING RULES:
            - Convert duration_minutes to "Xh Ym" format (e.g., 135 → 2h 15m, 125 → 2h 5m)
            - Format prices with currency symbol and commas (10698 → ₹10,698)
            - Calculate total cost = price_per_person × {travelers}
            - Extract time only from departure_time/arrival_time (e.g., "2025-12-01 07:05" → "07:05")
            - Use clear section headings with emojis and DATES: 🛫 ✈️ 🚆 🚌
            - Include journey date in headers: "📤 Outbound Journey (Origin → Destination) - Date"
            - Include journey date in headers: "📥 Return Journey (Destination → Origin) - Date"
            - Highlight best value options with ⭐ or 💰 emoji
            - Add budget status: ✅ Within Budget | ⚠️ Near Limit | ❌ Over Budget
            
            OUTPUT STRUCTURE:
            # ✈️ Travel Search Results
            
            ## 🛫 Flight Options
            
            ### 📤 Outbound Journey (Origin → Destination) - Departure Date
            [Clean markdown table with ALL flights from outbound_flights array]
            
            **Budget Status:** [Check total cost against budget {budget}]
            **Recommended:** [Highlight 1-2 best options based on price/value]
            
            ### 📥 Return Journey (Destination → Origin) - Return Date
            [Clean markdown table with ALL flights from return_flights array]
            
            **Budget Status:** [Check total cost against budget]
            **Recommended:** [Highlight 1-2 best options]
            
            ## 🚆 Train Options (if available)
            ### 📤 Outbound Journey (Origin → Destination) - Departure Date
            [Format ground_transport.outbound_trains[] into table]
            
            ### 📥 Return Journey (Destination → Origin) - Return Date
            [Format ground_transport.return_trains[] into table]
            
            ## 🚌 Bus Options (if available)
            ### 📤 Outbound Journey (Origin → Destination) - Departure Date
            [Format ground_transport.outbound_buses[] into table]
            
            ### 📥 Return Journey (Destination → Origin) - Return Date
            [Format ground_transport.return_buses[] into table]
            
            ## 💰 Cost Summary & Recommendations
            | Transport Mode | Cheapest Option | Most Convenient | Best Value ⭐ |
            |----------------|-----------------|-----------------|---------------|
            
            **Total Trip Cost Range:** ₹X,XXX - ₹Y,YYY for {travelers} travelers
            **Budget Remaining:** [Calculate from {budget}]
            **Booking Recommendations:** [Practical booking advice]
            
            Make tables visually clean, well-aligned, and easy to compare options.
            Process ALL flights in the arrays, not just top 3.
            """
            
            response = client.models.generate_content(
                model="gemini-2.5-pro",
                contents=formatting_prompt
            )
            
            formatted_result = response.text.strip()
            
            self.logger.info("Travel results formatted successfully")
            return formatted_result
            
        except Exception as e:
            self.logger.error(f"Result formatting failed: {e}")
            # Fallback to basic formatting
            return f"""
            # Travel Search Results
            
            ## Raw Results
            {str(raw_results)[:1000]}...
            
            *Note: AI formatting temporarily unavailable. Raw results shown above.*
            """
    
    def execute_travel_search(self, query: str) -> str:
        """
        Main method to execute travel search with new clean architecture.
        
        This method demonstrates the new approach:
        1. Agent extracts parameters using Gemini
        2. Tool performs pure search orchestration  
        3. Agent formats results using AI-powered prompts
        
        Args:
            query: Natural language travel query
            
        Returns:
            Formatted travel results
        """
        self.logger.info("Executing travel search with clean architecture...")
        
        try:
            # Step 1: Agent extracts parameters (no longer in tool)
            params = self.extract_travel_parameters_with_gemini(query)
            
            # Step 1.5: Resolve airport codes and currency using LLM
            params = self.resolve_airport_codes_and_currency(params)
            
            # Step 2: Validate and adjust parameters based on budget constraints
            if params.budget_limit and params.budget_limit < 10000 and 'flight' in params.transport_modes:
                # Remove flights for very low budgets
                params.transport_modes = [mode for mode in params.transport_modes if mode != 'flight']
                self.logger.info("Removed flights due to budget constraints")
            
            if not params.is_domestic and 'bus' in params.transport_modes:
                # Remove buses for international routes
                params.transport_modes = [mode for mode in params.transport_modes if mode not in ['bus', 'train']]
                self.logger.info("Removed ground transport for international route")
            
            # Step 3: Call tool with direct parameters (clean interface)
            raw_results = travel_search_tool.invoke({
                "origin": params.origin,
                "destination": params.destination,
                "departure_date": params.departure_date,
                "transport_modes": params.transport_modes,
                "travelers": params.travelers,
                "return_date": params.return_date,
                "budget_limit": params.budget_limit,
                "currency": params.currency,
                "origin_airport": params.origin_airport,
                "destination_airport": params.destination_airport,
                "is_domestic": params.is_domestic,
                "trip_type": params.trip_type
            })
            
            # Step 4: Agent formats results (no longer in tool)
            user_context = {
                'budget': params.budget_limit,
                'currency': params.currency,
                'travelers': params.travelers,
                'preferred_mode': params.preferred_mode,
                'budget_priority': params.budget_priority
            }
            
            formatted_results = self.format_travel_results_with_prompt(raw_results, user_context)
            
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"Travel search execution failed: {e}")
            return f"# Travel Search Error\n\nUnable to complete travel search: {str(e)}"
    
    def _extract_preferences_and_routing(self, query: str) -> Dict[str, Any]:
        """
        Extract user preferences and determine tool routing order from query using Google Gemini.
        
        Returns:
            Dict with preferences and routing order
        """
        self.logger.info("Preference extraction started")
        self.logger.info(f"Extracting preferences from query: '{query[:100]}...' (truncated)")
        
        try:
            # Get Gemini client
            self.logger.info("Connecting to Gemini API for preference extraction...")
            client = self._get_gemini_client()
            
            # Create comprehensive system prompt for Gemini
            self.logger.info("Preparing comprehensive prompt for Gemini...")
            prompt = f"""
            TASK: Extract travel information for budget-aware trip planning and tool routing.

            QUERY: "{query}"

            EXTRACT these exact keys for JSON response:

            1. **budget**: Extract ONLY numbers (25000, 1500, 50000). Look for "rupees 25000", "budget $1500", "₹50000", "with 25k budget". If no budget mentioned → null. Budget drives all planning decisions.

            2. **currency**: 
               - "INR" for: Indian locations (Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad, Pune, Goa, Kerala, Tamil Nadu, Karnataka, etc.) OR rupee indicators ("rupees", "₹", "INR")
               - "USD" for: $ symbol, "dollars", international locations (New York, Paris, London, etc.)
               - null if completely unclear

            3. **dates**: Convert to "DD-MM-YYYY to DD-MM-YYYY" format. Handle various inputs:
               - "25-12-2025 to 30-12-2025" → "25-12-2025 to 30-12-2025"
               - "Dec 25-30, 2025" → "25-12-2025 to 30-12-2025"  
               - "25th to 30th December" → "25-12-2025 to 30-12-2025"
               - If unclear → "Not specified"

            4. **from_location**: Departure city. Look for "from [city]", "starting from [city]", or first city mentioned.

            5. **to_location**: Destination city. Look for "to [city]", "destination [city]", or second city mentioned.

            6. **travelers**: EXACT number mentioned first ("3 persons", "5 people", "8 travelers"). Fallbacks only if no number: couple=2, family=4, solo=1.

            7. **dietary_preferences**: Extract food preferences if mentioned:
               - "vegetarian", "veg only", "pure veg" → "veg only"
               - "non-veg", "non vegetarian" → "non-veg only"
               - "vegan" → "vegan"
               - "halal" → "halal"
               - "both veg and non-veg", "all types" → "veg and non-veg"
               - If not mentioned → "veg and non-veg" (default)

            8. **routing_order**: CRITICAL for budget allocation. Rank tools by user emphasis and budget impact:

            BUDGET-DRIVEN ROUTING RULES:
            - **High Budget** (>₹50,000 or >$2000): ["accommodation", "itinerary", "travel"] (luxury focus)
            - **Medium Budget** (₹20,000-₹50,000 or $800-$2000): ["itinerary", "accommodation", "travel"] (balanced)
            - **Low Budget** (<₹20,000 or <$800): ["travel", "itinerary", "accommodation"] (cost optimization)
            - **No Budget**: ["itinerary", "travel", "accommodation"] (experience focus)

            USER EMPHASIS OVERRIDES:
            - Food emphasis ("good food", "dining", "cuisine", "veg/non-veg") → Add "restaurant" tool first
            - Comfort emphasis ("luxury", "comfortable stay", "premium hotels") → accommodation first
            - Activity emphasis ("sightseeing", "activities", "experiences", "adventure") → itinerary first
            - Transport concerns ("prefer trains", "flight booking", "travel options") → travel first

            Tools available:
            - "accommodation": hotels, stays, lodging (35% budget allocation)
            - "itinerary": activities, sightseeing, experiences (30% budget allocation)
            - "travel": transport, flights, trains, buses (35% budget allocation)
            - "restaurant": food, dining (optional - only if user explicitly requests, available via API)

            EXAMPLES:

            Query: "Plan trip from Bangalore to Coorg for 3 persons from 25-12-2025 to 30-12-2025 with budget rupees 25000"
            Output: {{"budget": 25000, "currency": "INR", "dates": "25-12-2025 to 30-12-2025", "from_location": "Bangalore", "to_location": "Coorg", "travelers": 3, "dietary_preferences": "veg and non-veg", "routing_order": ["itinerary", "accommodation", "travel"]}}

            Query: "Luxury food tour in Mumbai for couple, budget ₹80000, good hotels and fine dining, we are vegetarian"
            Output: {{"budget": 80000, "currency": "INR", "dates": "Not specified", "from_location": "Not specified", "to_location": "Mumbai", "travelers": 2, "dietary_preferences": "veg only", "routing_order": ["restaurant", "accommodation", "itinerary", "travel"]}}

            Query: "Budget trip from Delhi to Manali for 5 people, ₹15000 total, prefer buses, non-veg food preferred"
            Output: {{"budget": 15000, "currency": "INR", "dates": "Not specified", "from_location": "Delhi", "to_location": "Manali", "travelers": 5, "dietary_preferences": "non-veg only", "routing_order": ["travel", "itinerary", "accommodation"]}}

            Query: "Family vacation to Goa, comfortable stay, 4 persons"
            Output: {{"budget": null, "currency": "INR", "dates": "Not specified", "from_location": "Not specified", "to_location": "Goa", "travelers": 4, "dietary_preferences": "veg and non-veg", "routing_order": ["accommodation", "itinerary", "travel"]}}

            Return ONLY valid JSON:
            """
            
            # Use Gemini to extract preferences
            response = client.models.generate_content(
                model="gemini-2.5-pro",
                contents=prompt
            )
            
            # Parse response
            response_text = response.text.strip()
            
            # Clean response (remove any markdown formatting)
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()
            
            # Parse JSON response
            try:
                preferences = json.loads(response_text)
                
                # Validate and set defaults for missing fields (no default budget)
                validated_preferences = {
                    'budget': preferences.get('budget'),  # No default budget - must come from query
                    'currency': preferences.get('currency', 'USD'),
                    'dates': preferences.get('dates', 'Not specified'),
                    'from_location': preferences.get('from_location', 'Not specified'),
                    'to_location': preferences.get('to_location', 'Not specified'),
                    'travelers': preferences.get('travelers', 1),
                    'dietary_preferences': preferences.get('dietary_preferences', 'veg and non-veg'),
                    'routing_order': preferences.get('routing_order', ["itinerary", "travel", "accommodation"])
                }
                
                self.logger.info(f"Extracted: {validated_preferences}")
                return validated_preferences
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"JSON parse error: {e}")
                return self._basic_fallback(query)
                
        except Exception as e:
            self.logger.error(f"Gemini error: {e}")
            return self._basic_fallback(query)
    
    def _basic_fallback(self, query: str) -> Dict[str, Any]:
        """
        Basic fallback when Gemini extraction fails.
        """
        self.logger.info("Using fallback...")
        
        query_lower = query.lower()
        
        # Default preferences
        preferences = {
            'budget': None,
            'currency': 'USD',
            'dates': 'Not specified',
            'from_location': 'Not specified',
            'to_location': 'Not specified',
            'travelers': 1,
            'dietary_preferences': 'veg and non-veg',
            'routing_order': ["itinerary", "accommodation", "travel"]
        }
        
        # Simple Indian location detection
        indian_words = ['rupee', '₹', 'inr', 'mumbai', 'delhi', 'bangalore', 'chennai', 'kolkata', 'hyderabad', 'pune', 
                       'goa', 'kerala', 'tamil nadu', 'karnataka', 'maharashtra', 'gujarat', 'rajasthan', 'punjab',
                       'coorg', 'mysore', 'ooty', 'shimla', 'manali', 'darjeeling', 'udaipur', 'jaipur', 'agra']
        
        if any(word in query_lower for word in indian_words):
            preferences['currency'] = 'INR'
        
        # Simple traveler count - prioritize actual numbers in query
        import re
        
        # Look for explicit numbers first
        number_patterns = [r'(\d+)\s*(?:persons?|people|travelers?)', r'for\s*(\d+)']
        travelers_found = False
        
        for pattern in number_patterns:
            match = re.search(pattern, query_lower)
            if match:
                preferences['travelers'] = int(match.group(1))
                travelers_found = True
                break
        
        # Only use couple/family as fallback if no explicit number found
        if not travelers_found:
            if 'couple' in query_lower:
                preferences['travelers'] = 2
            elif 'family' in query_lower:
                preferences['travelers'] = 4  # Default family size as fallback
        
        return preferences
    
    def _allocate_budget(self, total_budget: float, preferences: Dict[str, Any]) -> Dict[str, float]:
        """
        Intelligently allocate budget across tools based on user preferences.
        Dynamic allocation that adjusts based on user emphasis and actual spending.
        """
        routing_order = preferences.get('routing_order', self.default_sequence)
        budget = preferences.get('budget', total_budget)
        
        # Analyze user query for preference indicators
        original_query = preferences.get('original_query', '').lower()
        
        # Dynamic base allocation based on user preferences
        base_allocation = self._get_preference_based_allocation(original_query, budget)
        
        # Adjust based on routing priority (first tool gets additional bonus)
        allocation = base_allocation.copy()
        
        if routing_order:
            priority_tool = routing_order[0]
            # Give 10% bonus to priority tool, reduce others proportionally
            bonus = 0.10
            allocation[priority_tool] += bonus
            
            # Reduce other tools proportionally
            other_tools = [t for t in allocation.keys() if t != priority_tool]
            reduction_per_tool = bonus / len(other_tools)
            
            for tool in other_tools:
                allocation[tool] = max(0.05, allocation[tool] - reduction_per_tool)  # Minimum 5%
        
        # Convert to absolute amounts
        budget_allocation = {tool: total_budget * percentage for tool, percentage in allocation.items()}
        
        self.logger.info(f"💰 Budget allocation based on preferences: {[f'{k}: {v:.1%}' for k, v in allocation.items()]}")
        return budget_allocation
    
    def _get_preference_based_allocation(self, query: str, budget: float) -> Dict[str, float]:
        """
        Use Gemini to intelligently determine budget allocation based on query understanding.
        
        Args:
            query: User query text
            budget: Total budget amount for context
            
        Returns:
            Dict with tool allocation percentages
        """
        try:
            # Get Gemini client
            client = self._get_gemini_client()
            
            # Create allocation analysis prompt
            allocation_prompt = f"""
            TASK: Analyze travel query and determine optimal budget allocation percentages.

            QUERY: "{query}"
            BUDGET: {budget if budget else "Not specified"}

            Understand the user's priorities and intent from the query context, then allocate budget percentages across these 3 categories:

            1. **accommodation** (hotels, stays, lodging)
            2. **itinerary** (activities, sightseeing, experiences) 
            3. **travel** (transport, flights, trains, buses)

            ALLOCATION GUIDELINES:
            - Total must equal 100% (1.0)
            - Minimum 10% (0.10) per category  
            - Maximum 60% (0.60) per category
            - Consider user emphasis, budget level, and trip type
            - Balance between comfort (accommodation), experiences (itinerary), and connectivity (travel)

            CONTEXT UNDERSTANDING:
            - Luxury emphasis → higher accommodation % (40-50%)
            - Adventure/sightseeing focus → higher itinerary % (35-45%)
            - Long distance/transport concerns → higher travel % (40-50%)
            - Budget conscious → balanced allocation optimizing value
            - Family trips → balanced allocation with accommodation focus (40%)
            - Business trips → accommodation and travel focus (40% each)

            REALISTIC EXAMPLES:
            - Budget ₹25,000 for 2 people, 3 days → accommodation: 35%, itinerary: 30%, travel: 35%
            - Budget ₹50,000 for family → accommodation: 40%, itinerary: 25%, travel: 35%
            - Long-distance trip → accommodation: 30%, itinerary: 25%, travel: 45%

            Return ONLY JSON with decimal percentages:
            {{"accommodation": 0.35, "itinerary": 0.30, "travel": 0.35}}
            """
            
            # Use Gemini for intelligent allocation
            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=allocation_prompt
            )
            
            response_text = response.text.strip()
            
            # Clean response
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()
            
            # Parse allocation
            allocation = json.loads(response_text)
            
            # Validate allocation
            total = sum(allocation.values())
            if abs(total - 1.0) > 0.01:  # Allow small rounding errors
                # Normalize to 100%
                allocation = {k: v/total for k, v in allocation.items()}
            
            # Ensure minimums for 3 tools
            for tool in ['accommodation', 'itinerary', 'travel']:
                if tool not in allocation:
                    allocation[tool] = 0.10
                elif allocation[tool] < 0.10:
                    allocation[tool] = 0.10
            
            # Re-normalize after minimum adjustments
            total = sum(allocation.values())
            allocation = {k: v/total for k, v in allocation.items()}
            
            self.logger.info(f"🧠 Gemini-based allocation: {[f'{k}: {v:.1%}' for k, v in allocation.items()]}")
            return allocation
            
        except Exception as e:
            self.logger.warning(f"⚠️ Gemini allocation failed: {e}, using default")
            # Fallback to balanced default with 3 tools
            return {
                'accommodation': 0.35,
                'itinerary': 0.30, 
                'travel': 0.35
            }
    
    def _reallocate_remaining_budget(self, state: Dict[str, Any], completed_tools: List[str]) -> Dict[str, float]:
        """
        Dynamically reallocate remaining budget after tools complete.
        
        Example: Budget ₹10k, travel spent ₹3k → remaining ₹7k redistributed to pending tools
        """
        total_budget = state["total_budget"]
        spent_amounts = state.get("spent_amounts", {})
        
        # Calculate actual remaining budget
        total_spent = sum(spent_amounts.values())
        remaining_budget = total_budget - total_spent
        
        # Get pending tools (not yet completed)
        all_tools = ["accommodation", "itinerary", "travel", "restaurant"]
        pending_tools = [tool for tool in all_tools if tool not in completed_tools]
        
        if not pending_tools or remaining_budget <= 0:
            return {tool: 0 for tool in all_tools}
        
        # Get routing order for priority
        routing_order = state.get("user_preferences", {}).get('routing_order', self.default_sequence)
        
        # Redistribute remaining budget among pending tools based on priority
        if len(pending_tools) == 1:
            # Last tool gets all remaining budget
            new_allocation = {tool: 0 for tool in all_tools}
            new_allocation[pending_tools[0]] = remaining_budget
        else:
            # Base percentages for pending tools only
            base_percentages = {
                'accommodation': 0.40,  # Increased since fewer tools
                'itinerary': 0.25,      
                'travel': 0.25,         
                'restaurant': 0.10      
            }
            
            # Adjust for priority tool among pending tools
            pending_allocation = {}
            for tool in pending_tools:
                pending_allocation[tool] = base_percentages.get(tool, 0.25)  # Default 25%
            
            # Give bonus to highest priority pending tool
            priority_pending = None
            for tool in routing_order:
                if tool in pending_tools:
                    priority_pending = tool
                    break
            
            if priority_pending:
                bonus = 0.15  # 15% bonus
                pending_allocation[priority_pending] += bonus
                # Reduce others proportionally
                other_pending = [t for t in pending_tools if t != priority_pending]
                if other_pending:
                    reduction_per_tool = bonus / len(other_pending)
                    for tool in other_pending:
                        pending_allocation[tool] = max(0.05, pending_allocation[tool] - reduction_per_tool)
            
            # Normalize to 100%
            total_percentage = sum(pending_allocation.values())
            if total_percentage > 0:
                for tool in pending_allocation:
                    pending_allocation[tool] = pending_allocation[tool] / total_percentage
            
            # Apply to remaining budget
            new_allocation = {tool: 0 for tool in all_tools}
            for tool in pending_tools:
                new_allocation[tool] = remaining_budget * pending_allocation[tool]
        
        self.logger.info(f"💰 Budget reallocation: Remaining ₹{remaining_budget:.0f} → {[f'{k}: ₹{v:.0f}' for k, v in new_allocation.items() if v > 0]}")
        return new_allocation
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        # Define the workflow
        workflow = StateGraph(Dict[str, Any])
        
        # Add nodes
        workflow.add_node("input_processor", self._process_input)
        workflow.add_node("budget_allocator", self._allocate_budget_node)
        workflow.add_node("tool_executor", self._execute_current_tool)
        workflow.add_node("budget_tracker", self._track_budget)
        workflow.add_node("result_combiner", self._combine_results)
        workflow.add_node("output_formatter", self._format_output)
        
        # Define edges
        workflow.set_entry_point("input_processor")
        workflow.add_edge("input_processor", "budget_allocator")
        workflow.add_edge("budget_allocator", "tool_executor")
        workflow.add_edge("tool_executor", "budget_tracker")
        
        # Conditional edge for continuing or finishing
        workflow.add_conditional_edges(
            "budget_tracker",
            self._should_continue,
            {
                "continue": "tool_executor",
                "combine": "result_combiner"
            }
        )
        
        workflow.add_edge("result_combiner", "output_formatter")
        workflow.add_edge("output_formatter", END)
        
        return workflow.compile()
    
    def _process_input(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process input query and extract preferences."""
        query = state["original_query"]
        preferences = self._extract_preferences_and_routing(query)
        
        # Add original query to preferences for budget allocation
        preferences['original_query'] = query
        
        # Update state with extracted information
        budget = preferences.get('budget') or 30000  # Default budget if None or not found
        self.state_manager.update_input_info(
            query=query,
            preferences=preferences,
            budget=budget,
            currency=preferences.get('currency', '$'),
            dates=preferences.get('dates', 'Not specified'),
            from_loc=preferences.get('from_location', 'Not specified'),
            to_loc=preferences.get('to_location', 'Not specified'),
            travelers=preferences.get('travelers', 1)
        )
        
        # Set tool sequence
        self.state_manager.set_tool_sequence(preferences.get('routing_order', self.default_sequence))
        
        return self.state_manager.state
    
    def _allocate_budget_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Allocate budget across tools."""
        total_budget = state["total_budget"]
        preferences = state["user_preferences"]
        
        allocation = self._allocate_budget(total_budget, preferences)
        self.state_manager.allocate_budget(allocation)
        
        return self.state_manager.state
    
    def _execute_current_tool(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the current tool in sequence."""
        current_tool = self.state_manager.get_current_tool()
        
        if not current_tool:
            return state
        
        try:
            # Get allocated budget for this tool
            allocated_budget = self.state_manager.get_remaining_budget_for_category(current_tool)
            
            # Prepare query with budget constraint
            original_query = state["original_query"]
            currency = state["currency"]
            
            # Modify query to emphasize using the full allocated budget
            budget_aware_query = f"{original_query} Budget for {current_tool}: {currency}{allocated_budget:.0f} - Please use most of this budget to plan the best possible {current_tool} options according to user preferences."
            
            # Log tool execution start
            self.logger.info("=" * 60)
            self.logger.info(f"EXECUTING TOOL: {current_tool.upper()}")
            self.logger.info("=" * 60)
            self.logger.info(f"Tool Name: {current_tool}")
            self.logger.info(f"Allocated Budget: {currency}{allocated_budget:.0f}")
            self.logger.info(f"Budget-aware Query: '{budget_aware_query[:150]}...' (truncated)")
            
            tool_start_time = datetime.now()
            
            # Execute tool
            if current_tool == "accommodation":
                self.logger.info("Invoking accommodation search tool with extracted parameters...")
                
                # Extract parameters from state
                location = state.get("to_location", "Not specified")
                dates_str = state.get("dates", "")
                travelers = state.get("travelers", 2)
                currency = state.get("currency", "INR")
                
                # Parse dates to get check-in and check-out
                check_in_date = None
                check_out_date = None
                try:
                    if " to " in dates_str:
                        start_date_str, end_date_str = dates_str.split(" to ")
                        start_date = datetime.strptime(start_date_str.strip(), "%d-%m-%Y")
                        end_date = datetime.strptime(end_date_str.strip(), "%d-%m-%Y")
                        check_in_date = start_date.strftime("%Y-%m-%d")
                        check_out_date = end_date.strftime("%Y-%m-%d")
                except Exception as e:
                    self.logger.warning(f"Could not parse dates: {e}")
                
                # Prepare tool parameters
                tool_params = {
                    "query": budget_aware_query,
                    "location": location,
                    "check_in_date": check_in_date,
                    "check_out_date": check_out_date,
                    "adults": travelers,
                    "children": 0,
                    "currency": currency
                }
                self.logger.info(f"Tool Parameters: {tool_params}")
                result = self.tools["accommodation"].invoke(tool_params)
            elif current_tool == "itinerary":
                self.logger.info("Invoking itinerary planning tool...")
                tool_params = {"query": budget_aware_query}
                self.logger.info(f"Tool Parameters: {tool_params}")
                result = self.tools["itinerary"].invoke(tool_params)
            elif current_tool == "restaurant":
                # Restaurant tool now works independently with location parameter
                self.logger.info("Invoking restaurant search tool...")
                
                # Extract parameters
                travelers = state.get("travelers", 2)
                dates_str = state.get("dates", "")
                location = state.get("to_location", "Not specified")
                currency = state.get("currency", "USD")
                
                # Calculate days from dates
                try:
                    if " to " in dates_str:
                        start_date_str, end_date_str = dates_str.split(" to ")
                        start_date = datetime.strptime(start_date_str.strip(), "%d-%m-%Y")
                        end_date = datetime.strptime(end_date_str.strip(), "%d-%m-%Y")
                        num_days = (end_date - start_date).days + 1
                    else:
                        num_days = 3  # Default fallback
                except:
                    num_days = 3  # Fallback on parsing error
                
                # Create budget hint for restaurant recommendations
                budget_hint = f"{currency}{allocated_budget:.0f} for {travelers} person{'s' if travelers > 1 else ''} for {num_days} days"
                
                # Check if itinerary is available for context (optional)
                itinerary_result = state.get("itinerary_result", "")
                
                # Extract dietary preferences from user preferences or itinerary
                dietary_preferences = state.get("user_preferences", {}).get("dietary_preferences", "veg and non-veg")
                
                tool_params = {
                    "location": location,
                    "dates": dates_str,
                    "dietary_preferences": dietary_preferences,
                    "budget_hint": budget_hint,
                    "travelers": travelers,
                    "itinerary_details": itinerary_result if itinerary_result else ""
                }
                self.logger.info(f"Tool Parameters: {tool_params}")
                result = self.tools["restaurant"].invoke(tool_params)
            elif current_tool == "travel":
                self.logger.info("Invoking new travel search with clean architecture...")
                # Use the new clean architecture approach
                result = self.execute_travel_search(budget_aware_query)
            else:
                self.logger.error(f"Unknown tool: {current_tool}")
                result = f"Unknown tool: {current_tool}"
            
            # Log tool execution completion
            tool_execution_time = datetime.now() - tool_start_time
            result_length = len(str(result)) if result else 0
            self.logger.info(f"Tool Execution Time: {tool_execution_time.total_seconds():.2f} seconds")
            self.logger.info(f"Tool Output Length: {result_length} characters")
            
            # Safely handle Unicode in result preview
            try:
                result_preview = str(result)[:200].encode('ascii', 'ignore').decode('ascii')
                self.logger.info(f"Tool Output Preview: '{result_preview}...' (truncated)")
            except Exception:
                self.logger.info("Tool Output Preview: [Contains special characters - check full output in logs]")
            
            # Log full tool output to separate file
            self._log_tool_output(current_tool, result)
            
            # Update tool result
            self.state_manager.update_tool_result(current_tool, result)
            self.state_manager.mark_tool_completed(current_tool)
            
            # If result suggests budget adjustment, add warning
            if "budget" in result.lower() and ("exceed" in result.lower() or "over" in result.lower()):
                self.state_manager.add_warning(f"{current_tool} suggests budget adjustment needed")
                self.logger.warning(f"Budget adjustment warning for {current_tool}")
            
            self.logger.info(f"TOOL {current_tool.upper()} COMPLETED SUCCESSFULLY")
            self.logger.info("=" * 60)
            
        except Exception as e:
            error_msg = f"Error executing {current_tool}: {str(e)}"
            self.state_manager.add_error(error_msg)
            
            # Mark as completed with error
            self.state_manager.update_tool_result(current_tool, f"Error: {error_msg}")
            self.state_manager.mark_tool_completed(current_tool)
        
        return self.state_manager.state
    
    def _track_budget(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Track budget usage and dynamically reallocate remaining budget."""
        current_tool = self.state_manager.get_current_tool()
        
        if current_tool:
            # Estimate budget usage - Use 99% of allocated budget for comprehensive trip planning
            allocated = self.state_manager.get_remaining_budget_for_category(current_tool)
            estimated_usage = allocated * 0.99  # Use 99% of allocated budget for better trip planning
            
            # Record budget usage
            self.state_manager.spend_budget(current_tool, estimated_usage)
            
            # After spending, reallocate remaining budget for pending tools
            completed_tools = list(self.state_manager.state.get("completed_tools", []))
            completed_tools.append(current_tool)  # Include current tool as completed
            
            # Dynamically reallocate remaining budget
            new_allocation = self._reallocate_remaining_budget(self.state_manager.state, completed_tools)
            
            # Update budget allocation in state for remaining tools
            current_allocation = self.state_manager.state.get("budget_allocation", {})
            for tool, amount in new_allocation.items():
                if tool not in completed_tools and amount > 0:
                    current_allocation[tool] = amount
            
            self.state_manager.state["budget_allocation"] = current_allocation
        
        # Advance to next step
        self.state_manager.advance_step()
        
        return self.state_manager.state
    
    def _should_continue(self, state: Dict[str, Any]) -> str:
        """Decide whether to continue with next tool or combine results."""
        if self.state_manager.is_execution_complete():
            return "combine"
        else:
            return "continue"
    
    def _combine_results(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Combine all tool results into a comprehensive report."""
        
        # Get all results
        accommodation = state.get("accommodation_result", "")
        itinerary = state.get("itinerary_result", "")
        restaurant = state.get("restaurant_result", "")
        travel = state.get("travel_result", "")
        
        # Create combined result
        combined_prompt = f"""
        You are a professional travel advisor creating a comprehensive trip report. 
        Combine the following individual planning results into a cohesive, well-organized travel guide.
        
        ORIGINAL QUERY: {state['original_query']}
        BUDGET: {state['currency']}{state['total_budget']}
        REMAINING BUDGET: {state['currency']}{state['remaining_budget']}
        
        PLANNING RESULTS:
        
        ACCOMMODATION PLANNING:
        {accommodation}
        
        ITINERARY PLANNING:
        {itinerary}
        
        RESTAURANT RECOMMENDATIONS:
        {restaurant}
        
        TRAVEL OPTIMIZATION:
        {travel}
        
        Create a final comprehensive report with:
        1. Executive Summary
        2. Complete Trip Overview Table
        3. Daily Schedule Integration
        4. Budget Summary
        5. Important Notes and Recommendations
        
        Format as professional markdown with tables where appropriate.
        Ensure all information is consistent and well-integrated.
        """
        
        # For now, create a structured combination (in real implementation, use LLM)
        combined_result = f"""# 🌟 Comprehensive Trip Planning Report
        
## 📋 Executive Summary
- **Destination:** {state['from_location']} → {state['to_location']}
- **Dates:** {state['dates']}
- **Travelers:** {state['travelers']} people
- **Total Budget:** {state['currency']}{state['total_budget']}
- **Budget Utilized:** {state['currency']}{state['total_budget'] - state['remaining_budget']:.2f}
- **Remaining Budget:** {state['currency']}{state['remaining_budget']:.2f}

---

## 🗺️ Itinerary Planning
{itinerary}

---

## 🚌 Travel Optimization
{travel}

---

## 🏨 Accommodation Recommendations
{accommodation}

---

## 🍽️ Restaurant Recommendations
{restaurant}

---

## 💰 Budget Summary
| Category | Allocated | Estimated Used | Remaining |
|----------|-----------|----------------|-----------|
| Itinerary | {state['currency']}{state['budget_allocation'].get('itinerary', 0):.0f} | {state['currency']}{state['spent_amounts'].get('itinerary', 0):.0f} | {state['currency']}{state['budget_allocation'].get('itinerary', 0) - state['spent_amounts'].get('itinerary', 0):.0f} |
| Travel | {state['currency']}{state['budget_allocation'].get('travel', 0):.0f} | {state['currency']}{state['spent_amounts'].get('travel', 0):.0f} | {state['currency']}{state['budget_allocation'].get('travel', 0) - state['spent_amounts'].get('travel', 0):.0f} |
| Accommodation | {state['currency']}{state['budget_allocation'].get('accommodation', 0):.0f} | {state['currency']}{state['spent_amounts'].get('accommodation', 0):.0f} | {state['currency']}{state['budget_allocation'].get('accommodation', 0) - state['spent_amounts'].get('accommodation', 0):.0f} |
| Restaurant | {state['currency']}{state['budget_allocation'].get('restaurant', 0):.0f} | {state['currency']}{state['spent_amounts'].get('restaurant', 0):.0f} | {state['currency']}{state['budget_allocation'].get('restaurant', 0) - state['spent_amounts'].get('restaurant', 0):.0f} |

## ⚠️ Warnings & Notes
{chr(10).join(f"- {warning}" for warning in state['warnings']) if state['warnings'] else "- No warnings"}

## 🎯 Execution Summary
- **Tools Completed:** {', '.join(state['completed_tools'])}
- **Execution Order:** {' → '.join(state['tool_sequence'])}
- **Total Retries:** {state['retry_count']}
"""
        
        self.state_manager.state["combined_result"] = combined_result
        return self.state_manager.state
    
    def _format_output(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Format final output for presentation."""
        execution_summary = self.state_manager.get_execution_summary()
        self.state_manager.state["execution_summary"] = json.dumps(execution_summary, indent=2)
        
        return self.state_manager.state
    
    def plan_trip(self, query: str) -> Dict[str, Any]:
        """
        Main entry point for trip planning.
        
        Args:
            query: Natural language trip planning query
            
        Returns:
            Complete trip planning results
        """
        # Start execution tracking
        self.execution_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        self.execution_start_time = datetime.now()
        
        self.logger.info("=" * 100)
        self.logger.info("STARTING NEW TRIP PLANNING EXECUTION")
        self.logger.info("=" * 100)
        self.logger.info(f"Execution ID: {self.execution_id}")
        self.logger.info(f"Start Time: {self.execution_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Input Query: '{query}'")
        self.logger.info(f"Query Length: {len(query)} characters")
        
        try:
            # Reset state for new planning
            self.logger.info("Resetting agent state for new planning session")
            reset_state()
            self.state_manager = get_state_manager()
            
            # Initialize state with query
            initial_state = self.state_manager.state
            initial_state["original_query"] = query
            
            self.logger.info("Executing trip planning graph...")
            self.logger.info(f"Initial State Keys: {list(initial_state.keys())}")
            
            # Execute the graph
            result = self.graph.invoke(initial_state)
            
            # Log execution completion
            execution_time = datetime.now() - self.execution_start_time
            self.logger.info("=" * 100)
            self.logger.info("TRIP PLANNING EXECUTION COMPLETED")
            self.logger.info("=" * 100)
            self.logger.info(f"Total Execution Time: {execution_time.total_seconds():.2f} seconds")
            self.logger.info(f"Final Result Keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            
            # Log final agent output
            final_result = {
                "combined_result": result.get("combined_result", ""),
                "execution_summary": result.get("execution_summary", {}),
                "state": self.state_manager.export_state()
            }
            
            self._log_final_output(final_result)
            
            return final_result
            
        except Exception as e:
            execution_time = datetime.now() - self.execution_start_time
            self.logger.error("TRIP PLANNING EXECUTION FAILED")
            self.logger.error(f"Execution Time: {execution_time.total_seconds():.2f} seconds")
            self.logger.error(f"Error: {str(e)}")
            
            return {
                "error": str(e),
                "execution_time": execution_time.total_seconds(),
                "execution_id": self.execution_id
            }


# Create global agent instance
trip_agent = TripOptimizationAgent()


def plan_complete_trip(query: str) -> Dict[str, Any]:
    """
    Convenience function for trip planning.
    
    Args:
        query: Natural language trip planning query
        
    Returns:
        Complete trip planning results
    """
    return trip_agent.plan_trip(query)


if __name__ == "__main__":
    print("🌟 Testing Comprehensive Trip Optimization Agent")
    print("=" * 80)
    
    # Test query with user preferences
    test_query = """
    Plan a complete trip from Bangalore to Mumbai  for 2 persons from 25-12-2025 to 27-12-2025 
    with budget rupees 25000. We prefer mountains, beaches, waterfalls, and avoid traditional experiences. 
    We want comfortable accommodation and good food for both veg and non veg and prefer flights when possible.
    """
    
    print("🎯 Test Query:")
    print(test_query.strip())
    print("\n" + "=" * 80)
    print("🚀 EXECUTING TRIP PLANNING AGENT...")
    print("=" * 80)
    
    try:
        # Execute the agent
        results = plan_complete_trip(test_query)
        
        print("📊 FINAL RESULTS:")
        print("=" * 80)
        print(results["combined_result"])
        
        print("\n" + "=" * 80)
        print("🔍 EXECUTION SUMMARY:")
        print("=" * 80)
        print(results["execution_summary"])
        
        print("\n" + "=" * 80)
        print("✅ TRIP PLANNING COMPLETED SUCCESSFULLY!")
        print("💡 The agent intelligently routed through tools based on user preferences")
        print("💰 Budget was allocated and tracked throughout the process")
        print("📋 All results were combined into a comprehensive report")
        
    except Exception as e:
        print(f"❌ Error in trip planning: {str(e)}")
        