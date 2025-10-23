import os
import sys
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from functools import wraps

# Add path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

from src.tools.optimization import (
    search_accommodations, 
    plan_itinerary, 
    search_restaurants, 
    travel_search_tool
)

# Import travel search entity
from src.entity.travel_search_params import TravelSearchParams
from src.state.state_manager import get_state_manager, reset_state
from google import genai
from src.services.perplexity_service import PerplexityService

# Import centralized logging configuration
from src.logs.logger_config import LoggerConfig, get_agent_logger


def retry_on_overload(max_retries=3, initial_delay=2):
    """
    Decorator to retry Azure OpenAI API calls when model is overloaded (503 error).
    Uses exponential backoff: 2s, 4s, 8s delays.
    
    Args:
        max_retries: Maximum number of retry attempts (default 3)
        initial_delay: Initial delay in seconds (default 2)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            delay = initial_delay
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    error_str = str(e)
                    last_error = e
                    
                    # Check if it's a 503 overload error
                    if '503' in error_str and 'overloaded' in error_str.lower():
                        if attempt < max_retries:
                            self.logger.warning(f"⚠️ Azure OpenAI overloaded (attempt {attempt + 1}/{max_retries + 1}), retrying in {delay}s...")
                            time.sleep(delay)
                            delay *= 2  # Exponential backoff
                            continue
                    
                    # If not overload error or max retries reached, raise
                    raise last_error
            
            # If we exhausted all retries
            self.logger.error(f"❌ Failed after {max_retries + 1} attempts")
            raise last_error
        
        return wrapper
    return decorator

load_dotenv()

class TripOptimizationAgent:
    """
    Intelligent trip optimization agent that routes through multiple tools
    based on user preferences and manages budget allocation.
    """
    
    def __init__(self, enable_logging=True):
        self.state_manager = get_state_manager()
        self.graph = self._build_graph()
        
        # Setup logger using centralized configuration
        self._logger = get_agent_logger() if enable_logging else None
        
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
    
    @property
    def logger(self):
        """Safe logger property that returns a no-op logger if disabled."""
        if self._logger is None:
            # Create a simple no-op logger
            import logging
            noop_logger = logging.getLogger('noop')
            noop_logger.addHandler(logging.NullHandler())
            return noop_logger
        return self._logger
    
    def _log_tool_output(self, tool_name: str, output: str):
        """Log full tool output to separate file using centralized logger."""
        LoggerConfig.log_tool_output(tool_name, output, self.execution_id)
    
    def _log_final_output(self, final_result: dict):
        """Log final agent output to separate file using centralized logger."""
        LoggerConfig.log_final_output(final_result, self.execution_id)
    
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
    
    def _get_azure_openai_client(self):
        """Get Azure OpenAI client with key-based authentication."""
        from openai import AzureOpenAI
        
        endpoint = "https://tripmazer-aoai-dev-1.openai.azure.com/"
        deployment = "gpt-4.1-mini"
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError("AZURE_OPENAI_API_KEY environment variable is required")
        
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2025-01-01-preview",
        )
        
        return client, deployment
    
    def _call_azure_openai(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        """
        Call Azure OpenAI with system and user prompts.
        
        Args:
            system_prompt: System instructions
            user_prompt: User query/request
            temperature: Sampling temperature (0.0-1.0)
            
        Returns:
            Model response text
        """
        try:
            client, deployment = self._get_azure_openai_client()
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            completion = client.chat.completions.create(
                model=deployment,
                messages=messages,
                # max_tokens=4096,
                temperature=0.1,
                # top_p=0.95,
                frequency_penalty=0,
                presence_penalty=0,
                stop=None,
                stream=False
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Azure OpenAI call failed: {e}")
            raise
    
    @retry_on_overload(max_retries=3, initial_delay=2)
    def extract_travel_parameters_with_azure_openai(self, query: str) -> TravelSearchParams:
        """
        Extract travel search parameters using Azure OpenAI.
        
        This method handles the parameter extraction that was previously done in tools.
        Now the agent takes responsibility for AI-powered parameter extraction.
        
        Args:
            query: Natural language travel query
            
        Returns:
            TravelSearchParams entity with extracted parameters
        """
        self.logger.info("Extracting travel parameters with Azure OpenAI...")
        
        try:
            system_prompt = """You are a travel parameter extraction expert. Extract travel search parameters from natural language queries and return them as valid JSON."""
            
            user_prompt = f"""
            TASK: Extract travel search parameters from natural language query.
            
            QUERY: "{query}"
            
            CRITICAL: Always provide valid values for departure_date and budget_limit. Never return null/None for these fields.
            
            Extract the following parameters and return as JSON:
            
            {{
                "origin": "departure city/location (extract from phrases like 'from X', 'starting from X', 'Bangalore to')",
                "destination": "arrival city/location (extract from phrases like 'to X', 'destination X', 'to Coorg')", 
                "departure_date": "YYYY-MM-DD format (convert dates like 25-10-25 to 2025-10-25) - REQUIRED, use 2025-12-01 if not specified",
                "return_date": "YYYY-MM-DD format or null for one-way (calculate from trip duration)",
                "travelers": "number of travelers (extract from '3 people', '2 persons', etc.)",
                "budget_limit": "budget amount (number only) - REQUIRED, use 30000 if not specified (extract from '30000rs', 'budget 50k', etc.)",
                "currency": "INR for all destinations (always use INR)",
                "transport_modes": ["flight", "bus", "train"] - extract from user preference (buses → ["bus", "train"], flights → ["flight"]),
                "preferred_mode": "user's preferred transport mode or null (extract 'prefer buses' → 'bus')",
                "trip_type": "round_trip or one_way",
                "is_domestic": true/false,
                "budget_priority": "tight/moderate/flexible (extract from 'budget stays', 'cheap', 'economical' → tight)",
                "time_sensitivity": "urgent/moderate/flexible"
            }}
            
            EXTRACTION RULES:
            1. **Locations**: 
               - "Bangalore to Coorg" → origin="Bangalore", destination="Coorg"
               - "Plan a trip to Delhi" → origin="Not specified", destination="Delhi"
            2. **Dates (NEVER null)**: 
               - "25-10-25 to 29-10-25" → departure_date="2025-10-25", return_date="2025-10-29"
               - "from 25-10-25 to 29-10-25" → departure_date="2025-10-25", return_date="2025-10-29"
               - "from 1st Dec to 5th Dec 2025" → departure_date="2025-12-01", return_date="2025-12-05"
               - CRITICAL: Extract exact dates from query, don't use fallback dates unless NO dates mentioned
               - If no date mentioned → departure_date="2025-12-01"
            3. **Budget (NEVER null)**:
               - "30000rs", "30k", "budget 30000" → budget_limit=30000
               - "budget stays", "cheap", "economical" → budget_limit=20000
               - **DOMESTIC trips**: If no budget mentioned → budget_limit=30000
               - **INTERNATIONAL trips**: If no budget mentioned → budget_limit=100000 (flights are expensive)
            4. **Transport**:
               - "prefer buses" → transport_modes=["bus", "train"], preferred_mode="bus"
               - "flight only" → transport_modes=["flight"]
               - Not mentioned → transport_modes=["flight", "bus", "train"]
            5. **Travelers**:
               - "3 people", "2 persons", "family of 4" → extract exact number
            6. Always set currency="INR" regardless of destination
            7. Calculate is_domestic based on Indian cities (Bangalore, Coorg, Delhi, Mumbai, etc.)
            
            EXAMPLE:
            Query: "Plan a trip to bangalore to coorg for 3 people and budget is 30000rs for 4 days from 25-10-25 to 29-10-25 we prefer buses"
            Output: {{
                "origin": "Bangalore",
                "destination": "Coorg",
                "departure_date": "2025-10-25",
                "return_date": "2025-10-29",
                "travelers": 3,
                "budget_limit": 30000,
                "currency": "INR",
                "transport_modes": ["bus", "train"],
                "preferred_mode": "bus",
                "trip_type": "round_trip",
                "is_domestic": true,
                "budget_priority": "tight",
                "time_sensitivity": "flexible"
            }}
            
            REMEMBER: departure_date and budget_limit must NEVER be null. Always provide valid values.
            
            Return ONLY valid JSON.
            """
            
            response_text = self._call_azure_openai(system_prompt, user_prompt, temperature=0.1)
            
            self.logger.info(f"📋 RAW Azure OpenAI response: {response_text[:500]}...")
            
            # Clean response
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()
            
            # Parse response
            extracted_data = json.loads(response_text)
            
            # Add fallbacks for missing critical fields
            if not extracted_data.get('departure_date'):
                extracted_data['departure_date'] = "2025-12-01"  # Default date
                self.logger.warning("⚠️ No departure_date extracted, using default: 2025-12-01")
                
            if not extracted_data.get('budget_limit'):
                # Set higher default budget for international trips
                is_international = not extracted_data.get('is_domestic', True)
                if is_international:
                    extracted_data['budget_limit'] = 100000  # Higher default for international
                    self.logger.warning("⚠️ No budget_limit extracted for international trip, using default: 100000")
                else:
                    extracted_data['budget_limit'] = 30000  # Default budget for domestic
                    self.logger.warning("⚠️ No budget_limit extracted for domestic trip, using default: 30000")
            
            # Create TravelSearchParams entity
            params = TravelSearchParams.from_dict(extracted_data)
            
            self.logger.info(f"✅ Extracted parameters: {extracted_data}")
            return params
            
        except Exception as e:
            self.logger.error(f"Parameter extraction failed: {e}")
            # Fallback to basic parameters with valid values
            fallback_params = TravelSearchParams(
                origin="Not specified",
                destination="Not specified", 
                departure_date="2025-12-01",  # Valid date
                return_date="2025-12-05",     # Valid return date
                transport_modes=["flight", "bus", "train"],
                travelers=1,
                currency="INR",  # Always use INR
                budget_limit=50000,  # Higher fallback budget to accommodate potential international trips
                trip_type="round_trip",
                is_domestic=True
            )
            self.logger.warning(f"⚠️ Using fallback parameters: {fallback_params}")
            return fallback_params
    
    @retry_on_overload(max_retries=3, initial_delay=2)
    def resolve_airport_codes_and_currency(self, params: TravelSearchParams) -> TravelSearchParams:
        """
        Use Azure OpenAI to resolve airport codes for any location and determine currency.
        
        This replaces the static airport mapping with dynamic LLM-based resolution
        that can handle any city/region globally.
        
        Args:
            params: TravelSearchParams with city names
            
        Returns:
            Updated TravelSearchParams with airport codes and correct currency
        """
        self.logger.info(f"Resolving airport codes and currency for {params.origin} -> {params.destination}")
        
        try:
            system_prompt = """You are a travel logistics expert. Analyze travel locations for airport availability and transport recommendations. Return accurate information about airports, distances, and suitable transport modes."""
            
            user_prompt = f"""
            TASK: Analyze travel locations for airport availability and transport recommendations.
            
            ORIGIN: "{params.origin}"
            DESTINATION: "{params.destination}"
            
            For each location, intelligently analyze:
            
            1. **Direct Airport Availability**:
               - Does the location have its own airport? (true/false)
               - If yes: Provide 3-letter IATA code
               - If no: Identify nearest major airport with distance
            
            2. **Airport Details**:
               - origin_has_airport: true/false (does origin have direct airport?)
               - destination_has_airport: true/false (does destination have direct airport?)
               - origin_airport: "3-letter IATA code" (if available) or nearest airport code
               - destination_airport: "3-letter IATA code" (if available) or nearest airport code
               - origin_airport_distance_km: Distance to nearest airport (0 if direct, else actual distance)
               - destination_airport_distance_km: Distance to nearest airport (0 if direct, else actual distance)
            
            3. **Transport Recommendations**:
               Based on airport availability and distance, recommend suitable transport modes:
               - "flight_suitable": true/false (flight makes sense for this route?)
               - "train_suitable": true/false (train is good option?)
               - "bus_suitable": true/false (bus is good option?)
               - "recommended_modes": ["flight", "train", "bus"] ordered by suitability
            
            **EXAMPLES:**
            
            Bangalore to Coorg:
            - Coorg has NO direct airport (nearest: Mangalore 120km or Bangalore 270km)
            - Flight NOT suitable (no direct airport, long ground travel needed)
            - Train/Bus HIGHLY suitable (direct connectivity, scenic route)
            Result: {{"origin_has_airport": true, "destination_has_airport": false, "destination_airport_distance_km": 120, "flight_suitable": false, "recommended_modes": ["bus", "train"]}}
            
            Mumbai to Goa:
            - Both have airports (BOM, GOI/GOX)
            - Flight suitable (direct connectivity)
            - Bus/Train also suitable (well-connected)
            Result: {{"origin_has_airport": true, "destination_has_airport": true, "origin_airport_distance_km": 0, "destination_airport_distance_km": 0, "flight_suitable": true, "recommended_modes": ["flight", "train", "bus"]}}
            
            Delhi to Shimla:
            - Shimla has NO airport (nearest: Chandigarh 120km)
            - Flight less suitable (requires Chandigarh + 3-4hr drive)
            - Train/Bus better (direct Kalka-Shimla toy train, direct buses)
            Result: {{"destination_has_airport": false, "destination_airport_distance_km": 120, "flight_suitable": false, "recommended_modes": ["train", "bus"]}}
            
            **RULES:**
            - Direct airport (distance=0) → flight_suitable=true
            - No airport but <80km → flight_suitable=maybe (consider budget/time)
            - No airport and >80km → flight_suitable=false (too much ground travel)
            - Always check if locations are in India for domestic classification
            - Currency always "INR" for all destinations
            
            Return ONLY valid JSON:
            {{
                "origin_city": "standardized city name",
                "destination_city": "standardized city name",
                "origin_has_airport": true/false,
                "destination_has_airport": true/false,
                "origin_airport": "3-letter code or nearest",
                "destination_airport": "3-letter code or nearest",
                "origin_airport_distance_km": 0 or actual distance,
                "destination_airport_distance_km": 0 or actual distance,
                "origin_is_indian": true/false,
                "destination_is_indian": true/false,
                "currency": "INR",
                "is_domestic": true/false,
                "is_international": true/false,
                "flight_suitable": true/false,
                "train_suitable": true/false,
                "bus_suitable": true/false,
                "recommended_modes": ["ordered by suitability"]
            }}
            """
            
            response_text = self._call_azure_openai(system_prompt, user_prompt, temperature=0.1)
            
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
            params.currency = 'INR'  # Always use INR regardless of destination
            params.is_domestic = resolution_data.get('is_domestic', False)
            params.is_international = resolution_data.get('is_international', True)
            
            # Store airport codes and availability info
            params.origin_airport = resolution_data.get('origin_airport', params.origin[:3].upper())
            params.destination_airport = resolution_data.get('destination_airport', params.destination[:3].upper())
            params.origin_has_airport = resolution_data.get('origin_has_airport', True)
            params.destination_has_airport = resolution_data.get('destination_has_airport', True)
            params.origin_airport_distance = resolution_data.get('origin_airport_distance_km', 0)
            params.destination_airport_distance = resolution_data.get('destination_airport_distance_km', 0)
            
            # Smart transport mode adjustment based on airport analysis
            flight_suitable = resolution_data.get('flight_suitable', True)
            recommended_modes = resolution_data.get('recommended_modes', params.transport_modes)
            
            # If flight not suitable due to no airport, adjust transport modes
            if not flight_suitable and 'flight' in params.transport_modes:
                self.logger.warning(f"⚠️ Flight not suitable for this route (no direct airport or >80km distance)")
                self.logger.info(f"📍 Origin airport distance: {params.origin_airport_distance}km, Destination: {params.destination_airport_distance}km")
                self.logger.info(f"✅ Recommended modes: {recommended_modes}")
                
                # Use Azure OpenAI's intelligent recommendations
                params.transport_modes = [mode for mode in recommended_modes if mode in ['flight', 'train', 'bus']]
                
                # Ensure at least train and bus are included if flight removed
                if 'flight' not in params.transport_modes:
                    if 'train' not in params.transport_modes:
                        params.transport_modes.append('train')
                    if 'bus' not in params.transport_modes:
                        params.transport_modes.append('bus')
            
            self.logger.info(f"Resolved: {params.origin}({params.origin_airport}) -> {params.destination}({params.destination_airport})")
            self.logger.info(f"Airport availability - Origin: {params.origin_has_airport}, Destination: {params.destination_has_airport}")
            self.logger.info(f"Final transport modes: {params.transport_modes}")
            return params
            
        except Exception as e:
            self.logger.error(f"Airport code resolution failed: {e}")
            # Fallback: Always use INR
            params.currency = 'INR'  # Always use INR regardless of destination
            
            # Ensure origin and destination are not None before calling .lower()
            origin_str = params.origin if params.origin else ""
            dest_str = params.destination if params.destination else ""
            
            indian_keywords = ['mumbai', 'delhi', 'bangalore', 'chennai', 'kolkata', 'hyderabad', 'pune', 'goa', 'kerala', 'tamil nadu', 'karnataka', 'maharashtra']
            
            origin_is_indian = any(keyword in origin_str.lower() for keyword in indian_keywords)
            dest_is_indian = any(keyword in dest_str.lower() for keyword in indian_keywords)
            
            params.is_domestic = origin_is_indian and dest_is_indian
            params.is_international = not params.is_domestic
            
            # Basic airport codes as fallback
            params.origin_airport = params.origin[:3].upper()
            params.destination_airport = params.destination[:3].upper()
            
            return params
    
    @retry_on_overload(max_retries=3, initial_delay=2)
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
        self.logger.info("Formatting travel results with Azure OpenAI...")
        
        try:
            # Parse raw results if it's JSON string
            if isinstance(raw_results, str):
                try:
                    results_data = json.loads(raw_results)
                except:
                    results_data = {"raw_text": raw_results}
            else:
                results_data = raw_results
            
            budget = user_context.get('budget', 'Not specified')
            currency = user_context.get('currency', 'INR')  # Always use INR
            travelers = user_context.get('travelers', 1)
            preferred_mode = user_context.get('preferred_mode', 'any')
            
            system_prompt = """You are a travel results formatting expert. Format travel search results into beautiful, professional markdown tables with clear pricing and recommendations."""
            
            user_prompt = f"""
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
            - Format prices with currency symbol and commas (10698 → Rs.10,698)
            - Calculate total cost = price_per_person × {travelers}
            - Extract time only from departure_time/arrival_time (e.g., "2025-12-01 07:05" → "07:05")
            - Use clear section headings with DATES
            - Include journey date in headers: ">> Outbound Journey (Origin to Destination) - Date"
            - Include journey date in headers: "<< Return Journey (Destination to Origin) - Date"
            - Highlight best value options with asterisk (*) or BEST VALUE label
            - Add budget status: [WITHIN BUDGET] | [NEAR LIMIT] | [OVER BUDGET]
            
            OUTPUT STRUCTURE:
            # Travel Search Results
            
            ## Flight Options
            
            IF no flights available OR flight not suitable for route:
            ⚠️ **Flight not suitable for this route** (no direct airport connectivity)
            
            IF flights available:
            ### >> Outbound Journey (Origin to Destination) - Departure Date
            [Clean markdown table with ALL flights from outbound_flights array]
            
            **Budget Status:** [Check total cost against budget {budget}]
            **Recommended:** [Highlight 1-2 best options based on price/value]
            
            ### << Return Journey (Destination to Origin) - Return Date
            [Clean markdown table with ALL flights from return_flights array]
            
            ## Train Options (if available)
            ### >> Outbound Journey (Origin to Destination) - Departure Date
            [Format ground_transport.outbound_trains[] into table]
            
            ### << Return Journey (Destination to Origin) - Return Date
            [Format ground_transport.return_trains[] into table]
            
            ## Bus Options (if available)
            ### >> Outbound Journey (Origin to Destination) - Departure Date
            [Format ground_transport.outbound_buses[] into table]
            
            ### << Return Journey (Destination to Origin) - Return Date
            [Format ground_transport.return_buses[] into table]
            
            ## Cost Summary & Recommendations
            | Transport Mode | Cheapest Option | Most Convenient | Best Value (*) |
            |----------------|-----------------|-----------------|---------------|
            
            **Total Trip Cost Range:** ₹X,XXX - ₹Y,YYY for {travelers} travelers
            **Budget Remaining:** [Calculate from {budget}]
            **Booking Recommendations:** [Practical booking advice]
            
            Make tables visually clean, well-aligned, and easy to compare options.
            Process ALL flights in the arrays, not just top 3.
            """
            
            formatted_result = self._call_azure_openai(system_prompt, user_prompt, temperature=0.1)
            
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
        1. Agent extracts parameters using Azure OpenAI
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
            params = self.extract_travel_parameters_with_azure_openai(query)
            
            # Step 1.5: Resolve airport codes and currency using intelligent LLM analysis
            # This now handles airport availability, distance, and transport mode recommendations
            params = self.resolve_airport_codes_and_currency(params)
            
            # Step 2: Additional validation for edge cases
            # Budget constraint: Very low budgets should prefer ground transport
            if params.budget_limit and params.budget_limit < 10000 and 'flight' in params.transport_modes:
                self.logger.info(f"⚠️ Budget constraint: ₹{params.budget_limit} < ₹10,000 - Prioritizing budget transport")
                # Keep flight but move to end of list (lowest priority)
                if 'flight' in params.transport_modes:
                    params.transport_modes.remove('flight')
                    params.transport_modes.append('flight')
            
            # International routes: Remove ground transport (buses/trains don't cross borders)
            if not params.is_domestic:
                original_modes = params.transport_modes.copy()
                params.transport_modes = [mode for mode in params.transport_modes if mode not in ['bus', 'train']]
                if params.transport_modes != original_modes:
                    self.logger.info(f"🌍 International route detected - Removed ground transport (buses/trains)")
                    self.logger.info(f"Available modes: {params.transport_modes}")
            
            # Step 3: Call tool with direct parameters (clean interface)
            self.logger.info(f"🚀 Calling travel_search_tool with parameters:")
            self.logger.info(f"  📍 Origin: {params.origin} ({params.origin_airport})")
            self.logger.info(f"  📍 Destination: {params.destination} ({params.destination_airport})")
            self.logger.info(f"  📅 Departure: {params.departure_date}, Return: {params.return_date}")
            self.logger.info(f"  🚌 Transport Modes: {params.transport_modes}")
            self.logger.info(f"  👥 Travelers: {params.travelers}")
            self.logger.info(f"  💰 Budget: ₹{params.budget_limit}")
            
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
            
            self.logger.info(f"✅ Travel search completed, formatting results...")
            
            # Step 4: Agent formats results (no longer in tool)
            user_context = {
                'budget': params.budget_limit,
                'currency': params.currency,
                'travelers': params.travelers,
                'preferred_mode': params.preferred_mode,
                'budget_priority': params.budget_priority
            }
            
            try:
                formatted_results = self.format_travel_results_with_prompt(raw_results, user_context)
                return formatted_results
            except Exception as format_error:
                self.logger.error(f"⚠️ Azure OpenAI formatting failed: {format_error}")
                self.logger.info("📋 Returning raw results as fallback")
                # Return raw results with a note
                return f"""# Travel Search Results

## ⚠️ AI Formatting Temporarily Unavailable

Raw search results below:

```json
{raw_results}
```

*Note: AI formatting temporarily unavailable. Raw results shown above.*"""
            
        except Exception as e:
            self.logger.error(f"Travel search execution failed: {e}")
            return f"# Travel Search Error\n\nUnable to complete travel search: {str(e)}"
    
    def _calculate_actual_budget_usage(self, result: str, tool: str, travelers: int) -> float:
        """
        Parse tool results to extract actual budget usage instead of estimating 99%.
        
        Args:
            result: Tool result string (may contain pricing info)
            tool: Tool name (accommodation, travel, itinerary)
            travelers: Number of travelers
            
        Returns:
            Actual budget used (best estimate from results)
        """
        try:
            # For travel, try to extract cheapest option price
            if tool == "travel":
                # Look for price patterns like ₹8,500 or Rs.8500
                import re
                prices = re.findall(r'₹[\d,]+', result)
                if not prices:
                    prices = re.findall(r'Rs\.[\d,]+', result)
                
                if prices:
                    # Extract numeric values
                    numeric_prices = []
                    for price in prices:
                        clean_price = price.replace('₹', '').replace('Rs.', '').replace(',', '')
                        try:
                            numeric_prices.append(float(clean_price))
                        except:
                            continue
                    
                    if numeric_prices:
                        # Use cheapest option * travelers for round trip
                        cheapest = min(numeric_prices)
                        actual_usage = cheapest * travelers * 2  # Round trip
                        self.logger.info(f"📊 Extracted actual travel cost: ₹{actual_usage:,.0f} ({travelers} travelers, round trip)")
                        return actual_usage
            
            # For accommodation, extract price per night * nights * rooms
            elif tool == "accommodation":
                import re
                prices = re.findall(r'₹[\d,]+', result)
                if prices:
                    numeric_prices = []
                    for price in prices:
                        clean_price = price.replace('₹', '').replace(',', '')
                        try:
                            numeric_prices.append(float(clean_price))
                        except:
                            continue
                    
                    if numeric_prices:
                        # Estimate: cheapest option for trip duration
                        cheapest_per_night = min(numeric_prices)
                        # Assume 3 nights average if not specified
                        actual_usage = cheapest_per_night * 3
                        self.logger.info(f"📊 Extracted actual accommodation cost: ₹{actual_usage:,.0f}")
                        return actual_usage
            
            # For itinerary, harder to extract - use conservative estimate
            # Return None to signal we should use default estimation
            return None
            
        except Exception as e:
            self.logger.warning(f"Could not extract actual budget from {tool} results: {e}")
            return None
    
    def _reallocate_savings_to_remaining_tools(self, current_tool_idx: int, tool_sequence: list, 
                                               savings: float, total_budget: float):
        """
        Redistribute unused budget from completed tool to remaining tools.
        
        Args:
            current_tool_idx: Index of tool that just completed
            tool_sequence: List of all tools in execution order
            savings: Amount saved from current tool
            total_budget: Total trip budget
        """
        # Get remaining tools
        remaining_tools = tool_sequence[current_tool_idx + 1:]
        
        if not remaining_tools or savings <= 0:
            return
        
        # Distribute savings proportionally to remaining tools
        per_tool_bonus = savings / len(remaining_tools)
        
        self.logger.info(f"💰 BUDGET REALLOCATION: ₹{savings:,.0f} saved from {tool_sequence[current_tool_idx]}")
        self.logger.info(f"📊 Redistributing ₹{per_tool_bonus:,.0f} to each of {len(remaining_tools)} remaining tools")
        
        # Update budget allocation for remaining tools
        for remaining_tool in remaining_tools:
            current_allocation = self.state_manager.state['budget_allocation'].get(remaining_tool, 0)
            new_allocation = current_allocation + per_tool_bonus
            self.state_manager.state['budget_allocation'][remaining_tool] = new_allocation
            
            self.logger.info(f"  ✅ {remaining_tool.capitalize()}: ₹{current_allocation:,.0f} → ₹{new_allocation:,.0f} (+₹{per_tool_bonus:,.0f})")
    
    @retry_on_overload(max_retries=3, initial_delay=2)
    def _extract_complete_trip_parameters(self, query: str) -> Dict[str, Any]:
        """
        Single LLM call to extract ALL trip parameters including travel params, preferences, routing, and budget allocation.
        This replaces multiple separate LLM calls for better consistency and performance.
        
        Returns:
            Dict with all parameters needed for trip planning
        """
        self.logger.info("🧠 Extracting ALL trip parameters in single Azure OpenAI call...")
        self.logger.info(f"Query: '{query[:200]}...'")
        
        try:
            system_prompt = """You are a comprehensive travel planning expert. Extract ALL travel parameters, preferences, routing order, and budget allocation from a single natural language query. Ensure consistency across all extracted parameters."""
            
            user_prompt = f"""
            TASK: Extract ALL travel planning parameters from natural language query in a single comprehensive analysis.
            
            QUERY: "{query}"
            
            Extract ALL of the following in one comprehensive JSON response:
            
            {{
                "travel_params": {{
                    "origin": "departure city (extract from 'from X', 'Bangalore to')",
                    "destination": "arrival city (extract from 'to X', 'to Coorg')",
                    "departure_date": "YYYY-MM-DD (CRITICAL: extract exact date from query like 25-10-25 → 2025-10-25)",
                    "return_date": "YYYY-MM-DD or null (calculate from departure + duration)",
                    "travelers": "number (extract from '3 people', '2 persons')",
                    "budget_limit": "number (extract from '30000rs', 'budget 50k')",
                    "currency": "INR",
                    "transport_modes": ["bus", "train"] for domestic OR ["flight"] for international,
                    "preferred_mode": "bus/train/flight based on user preference and route type",
                    "trip_type": "round_trip or one_way",
                    "is_domestic": "AUTOMATIC DETECTION: true if both cities are Indian, false if international route",
                    "budget_priority": "tight/moderate/flexible",
                    "time_sensitivity": "urgent/moderate/flexible"
                }},
                "preferences": {{
                    "budget": "same as budget_limit above",
                    "currency": "INR",
                    "dates": "DD-MM-YYYY to DD-MM-YYYY format",
                    "from_location": "same as origin above", 
                    "to_location": "same as destination above",
                    "travelers": "same as travelers above",
                    "dietary_preferences": "veg and non-veg/veg only/non-veg only",
                    "accommodation_preference": "budget/luxury based on query context"
                }},
                "routing_order": ["travel", "accommodation", "itinerary"] - optimal sequence,
                "budget_allocation": {{
                    "travel": "CALCULATE based on user preferences (0.25-0.70 range)",
                    "accommodation": "CALCULATE based on user preferences (0.20-0.55 range)", 
                    "itinerary": "CALCULATE based on user preferences (0.10-0.45 range)"
                }},
                "tool_queries": {{
                    "travel_query": "Clean travel search for travelers from origin to destination",
                    "accommodation_query": "Budget hotels and hostels in destination OR Luxury hotels in destination",
                    "itinerary_query": "Plan comprehensive X-day itinerary for destination from origin for X people from dates with budget, including all user preferences like trekking, waterfalls, viewpoints etc."
                }}
            }}
            
            **CRITICAL: DOMESTIC vs INTERNATIONAL DETECTION**
            Automatically determine is_domestic and transport_modes based on cities:
            
            **INDIAN CITIES (is_domestic = true):**
            Mumbai, Delhi, Bangalore, Bengaluru, Chennai, Kolkata, Hyderabad, Pune, Ahmedabad, Goa, Panaji, 
            Surat, Jaipur, Lucknow, Kanpur, Nagpur, Indore, Bhopal, Visakhapatnam, Patna, Vadodara, 
            Agra, Nashik, Meerut, Rajkot, Varanasi, Srinagar, Aurangabad, Amritsar, Allahabad, Ranchi, 
            Coimbatore, Jabalpur, Vijayawada, Jodhpur, Madurai, Kota, Guwahati, Chandigarh, Mysore, 
            Gurgaon, Noida, Thiruvananthapuram, Kochi, Dehradun, Shimla, Manali, Rishikesh, Haridwar, 
            Coorg, Kodaikanal, Ooty, Darjeeling, Gangtok, Udaipur, Mount Abu, Pushkar, Mcleodganj
            
            **INTERNATIONAL CITIES (is_domestic = false):**
            Dubai, London, Paris, New York, Singapore, Bangkok, Tokyo, Sydney, Toronto, Amsterdam, etc.
            
            **TRANSPORT MODE LOGIC:**
            - **Domestic Routes**: Can use ["bus", "train", "flight"] based on user preference
            - **International Routes**: ONLY ["flight"] (buses/trains don't cross international borders)
            
            **EXAMPLES:**
            - Bangalore → Coorg = is_domestic: true, transport_modes: ["bus", "train"] (if user prefers ground transport)
            - Mumbai → Delhi = is_domestic: true, transport_modes: ["flight", "train"] (if user wants speed)  
            - Bangalore → Dubai = is_domestic: false, transport_modes: ["flight"] (ONLY flights for international)
            - London → Mumbai = is_domestic: false, transport_modes: ["flight"] (ONLY flights for international)
            
            **IMPORTANT FOR ITINERARY_QUERY**: 
            - MUST include: duration (X-day), destination, origin, number of people, dates, budget amount
            - MUST include: all user activity preferences (trekking, waterfalls, viewpoints, temples, beaches, nightlife, etc.)
            - Example: "Plan a 4-day itinerary for Coorg from Bangalore for 3 people from 2025-10-25 to 2025-10-29 with budget 30000rs. We prefer morning viewpoints, trekking spots, and waterfalls."
            
            CRITICAL RULES:
            1. **Date Extraction**: MUST extract exact dates from query (25-10-25 → 2025-10-25, NOT 2025-12-01)
            2. **Domestic Detection**: AUTOMATICALLY determine based on city locations above
            3. **Transport Logic**: 
               - Domestic routes: Can use bus/train/flight based on user preference
               - International routes: ONLY flight (no buses/trains cross borders)
            4. **Consistency**: travel_params.origin = preferences.from_location, etc.
            5. **No Null Values**: Always provide valid values for all fields
            6. **Tool Queries**: 
               - travel_query: Simple search queries
               - accommodation_query: Simple search queries  
               - itinerary_query: COMPREHENSIVE queries with all trip details (dates, people, budget, preferences)
            
            EXAMPLE 1 (Domestic Route):
            Query: "Plan a trip to bangalore to coorg for 3 people and budget is 30000rs for 4 days from 25-10-25 to 29-10-25 we prefer buses and budget stays"
            
            Expected Output:
            {{
                "travel_params": {{
                    "origin": "Bangalore",
                    "destination": "Coorg", 
                    "departure_date": "2025-10-25",
                    "return_date": "2025-10-29",
                    "travelers": 3,
                    "budget_limit": 30000,
                    "currency": "INR",
                    "transport_modes": ["bus", "train"],
                    "preferred_mode": "bus",
                    "trip_type": "round_trip",
                    "is_domestic": true,
                    "budget_priority": "tight",
                    "time_sensitivity": "flexible"
                }},
                "preferences": {{
                    "budget": 30000,
                    "currency": "INR",
                    "dates": "25-10-2025 to 29-10-2025",
                    "from_location": "Bangalore",
                    "to_location": "Coorg", 
                    "travelers": 3,
                    "dietary_preferences": "veg and non-veg",
                    "accommodation_preference": "budget"
                }},
                "routing_order": ["travel", "accommodation", "itinerary"],
                "budget_allocation": {{
                    "travel": 0.30,
                    "accommodation": 0.40, 
                    "itinerary": 0.30
                }},
                "tool_queries": {{
                    "travel_query": "Search travel options for 3 travelers from Bangalore to Coorg",
                    "accommodation_query": "Budget hotels and hostels in Coorg",
                    "itinerary_query": "Plan a 4-day itinerary for Coorg from Bangalore for 3 people from 25-10-2025 to 29-10-2025 with budget 30000rs. We prefer morning viewpoints, trekking spots, and waterfalls"
                }}
            }}
            
            EXAMPLE 2 (International Route):
            Query: "Plan a trip from Bangalore to Dubai for 2 people budget 100000rs for 5 days from 01-11-25 to 06-11-25"
            
            Expected Output:
            {{
                "travel_params": {{
                    "origin": "Bangalore",
                    "destination": "Dubai",
                    "departure_date": "2025-11-01", 
                    "return_date": "2025-11-06",
                    "travelers": 2,
                    "budget_limit": 100000,
                    "currency": "INR",
                    "transport_modes": ["flight"],
                    "preferred_mode": "flight",
                    "trip_type": "round_trip",
                    "is_domestic": false,
                    "budget_priority": "moderate",
                    "time_sensitivity": "flexible"
                }},
                "preferences": {{
                    "budget": 100000,
                    "currency": "INR", 
                    "dates": "01-11-2025 to 06-11-2025",
                    "from_location": "Bangalore",
                    "to_location": "Dubai",
                    "travelers": 2,
                    "dietary_preferences": "veg and non-veg",
                    "accommodation_preference": "luxury"
                }},
                "routing_order": ["travel", "accommodation", "itinerary"],
                "budget_allocation": {{
                    "travel": 0.55,
                    "accommodation": 0.35,
                    "itinerary": 0.10
                }},
                "tool_queries": {{
                    "travel_query": "Search flight options for 2 travelers from Bangalore to Dubai",
                    "accommodation_query": "Luxury hotels in Dubai", 
                    "itinerary_query": "Plan a 5-day itinerary for Dubai from Bangalore for 2 people from 01-11-2025 to 06-11-2025 with budget 100000rs. Include shopping, beaches, and cultural experiences"
                }}
            }}
            
            Return ONLY valid JSON with ALL sections filled.
            """
            
            response_text = self._call_azure_openai(system_prompt, user_prompt, temperature=0.1)
            
            self.logger.info(f"📋 RAW Azure OpenAI comprehensive response: {response_text[:800]}...")
            
            # Clean response
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()
            
            # Parse comprehensive response
            all_params = json.loads(response_text)
            
            self.logger.info(f"✅ Extracted comprehensive parameters in single call")
            return all_params
            
        except Exception as e:
            self.logger.error(f"Comprehensive extraction failed: {e}")
            return self._basic_comprehensive_fallback(query)
    
    def _basic_comprehensive_fallback(self, query: str) -> Dict[str, Any]:
        """Fallback for comprehensive parameter extraction."""
        return {
            "travel_params": {
                "origin": "Not specified",
                "destination": "Not specified",
                "departure_date": "2025-12-01",
                "return_date": "2025-12-05",
                "travelers": 1,
                "budget_limit": 30000,
                "currency": "INR",
                "transport_modes": ["bus", "train", "flight"],
                "preferred_mode": "bus",
                "trip_type": "round_trip",
                "is_domestic": True,
                "budget_priority": "moderate",
                "time_sensitivity": "flexible"
            },
            "preferences": {
                "budget": 30000,
                "currency": "INR", 
                "dates": "Not specified",
                "from_location": "Not specified",
                "to_location": "Not specified",
                "travelers": 1,
                "dietary_preferences": "veg and non-veg",
                "accommodation_preference": "budget"
            },
            "routing_order": ["travel", "accommodation", "itinerary"],
            "budget_allocation": {
                "travel": 0.35,
                "accommodation": 0.35,
                "itinerary": 0.30
            },
            "tool_queries": {
                "travel_query": "Search travel options",
                "accommodation_query": "Budget hotels and hostels", 
                "itinerary_query": "Top attractions and activities"
            }
        }

    @retry_on_overload(max_retries=3, initial_delay=2)
    def _extract_preferences_and_routing(self, query: str) -> Dict[str, Any]:
        """
        Extract user preferences and determine tool routing order from query using Azure OpenAI.
        
        Returns:
            Dict with preferences and routing order
        """
        self.logger.info("Preference extraction started")
        self.logger.info(f"Extracting preferences from query: '{query[:100]}...' (truncated)")
        
        try:
            # Create comprehensive system prompt for Azure OpenAI
            self.logger.info("Preparing comprehensive prompt for Azure OpenAI...")
            
            system_prompt = """You are a travel planning expert. Extract travel information for budget-aware trip planning and determine optimal tool routing based on user preferences and travel planning best practices."""
            
            user_prompt = f"""
            TASK: Extract travel information for budget-aware trip planning and tool routing.

            QUERY: "{query}"

            EXTRACT these exact keys for JSON response:

            1. **budget**: Extract ONLY numbers (25000, 1500, 50000). Look for "rupees 25000", "budget $1500", "₹50000", "with 25k budget". If no budget mentioned → null. Budget drives all planning decisions.

            2. **currency**: 
               - Always use "INR" for all destinations (domestic and international)
               - This applies to all locations regardless of country or currency symbols mentioned

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

            8. **routing_order**: CRITICAL for tool execution order. UNDERSTAND the entire query holistically and determine the optimal sequence based on INTENT, DEPENDENCIES, and USER PRIORITIES.

            **INTELLIGENT ROUTING FRAMEWORK:**
            
            DO NOT use keyword matching. Instead:
            1. **Understand the FULL CONTEXT** of what the user wants to accomplish
            2. **Identify DEPENDENCIES** between different aspects (e.g., accommodation location depends on activities)
            3. **Detect USER EMPHASIS** from how they structure and phrase their request
            4. **Apply LOGICAL SEQUENCING** based on booking best practices
            
            **DEPENDENCY ANALYSIS:**
            
            → **Transport should come FIRST when:**
               - User needs to secure limited availability (peak season, specific dates, price-sensitive routes)
               - Long-distance travel where transport cost dominates budget
               - User explicitly wants to lock in specific transport mode/price
               - Flight prices are volatile and early booking is critical
            
            → **Accommodation should come FIRST when:**
               - User has specific property type/location requirements (beachfront, city center, specific hotel)
               - Trip is focused on relaxation/comfort at a particular place
               - Activities are flexible but accommodation quality is emphasized
               - User mentions "stay", "hotel", "resort" as primary concern
            
            → **Itinerary should come FIRST when:**
               - User wants to discover what to do and plan around that
               - Generic trip request without specific transport/accommodation preferences
               - Destination is the focus, logistics are secondary
               - User asks "what to do", "places to visit", "things to see"
            
            **LOGICAL SEQUENCING RULES:**
            
            When user mentions MULTIPLE aspects (transport + accommodation + activities):
            → Analyze which creates the CONSTRAINT for others
            → Standard logical flow: Transport (availability/price lock) → Accommodation (location near activities) → Itinerary (detailed planning)
            → Exception: If accommodation type/location is heavily emphasized, it may come before detailed itinerary
            
            When user mentions MINIMAL details (just destination + dates + budget):
            → DEFAULT: ["itinerary", "travel", "accommodation"] OR ["travel", "itinerary", "accommodation"]
            → Rationale: Discover what to do → Secure transport (critical) → Find convenient stay
            
            **CRITICAL CONSTRAINT:**
            ⚠️ TRAVEL SHOULD NEVER BE LAST IN THE SEQUENCE ⚠️
            - Travel (flights/trains) has limited availability and dynamic pricing
            - Transport determines arrival/departure times affecting all other planning
            - Leaving transport for last risks unavailability or price surge
            - ACCEPTABLE: ["travel", "itinerary", "accommodation"], ["travel", "accommodation", "itinerary"], ["itinerary", "travel", "accommodation"]
            - NOT ACCEPTABLE: ["accommodation", "itinerary", "travel"], ["itinerary", "accommodation", "travel"]
            - If you're tempted to put travel last, move it to second position at minimum
            
            **ROUTING DECISION PROCESS:**
            
            Step 1: READ the entire query carefully and identify ALL mentioned aspects
            Step 2: DETERMINE what the user emphasizes MOST (primary concern)
            Step 3: IDENTIFY which aspects CREATE CONSTRAINTS for others (dependencies)
            Step 4: APPLY logical booking sequence based on real-world planning
            Step 5: RETURN the tool order as JSON array
            
            **EXAMPLES (for guidance, not pattern matching):**
            
            Scenario A - Comprehensive trip with transport preference:
            Query: "Plan trip for 3 people with budget 50000 INR from Bangalore to Mumbai on 27-11-25 to 30-11-25, we prefer flights and like beaches and prefer good dormitory"
            Analysis: User specifies dates (time-sensitive) + prefers flights (transport mode) + mentions beaches & dormitory
            Reasoning: Lock flights first (price/availability), find dormitory near beaches, then plan beach activities
            Output: ["travel", "accommodation", "itinerary"]
            
            Scenario B - Accommodation-focused trip:
            Query: "Need luxury hotel in Goa for couple, like beach resorts"
            Analysis: Primary focus is luxury beach resort (specific accommodation type), transport not mentioned
            Reasoning: Find perfect resort first (main requirement), secure transport early (NEVER last), then plan activities
            Output: ["accommodation", "travel", "itinerary"]  # Travel NEVER last!
            
            Scenario C - Discovery/exploration trip:
            Query: "What to do in Mumbai with family for 5 days"
            Analysis: User asking "what to do" (discovery mode), no specific preferences
            Reasoning: Discover attractions first, book accommodation near key areas, arrange transport accordingly
            Output: ["itinerary", "accommodation", "travel"]
            
            Scenario D - Pure transport booking:
            Query: "Book cheapest flight from Delhi to Bangalore for 2 persons"
            Analysis: Explicit transport booking request, price-sensitive, no other aspects mentioned
            Reasoning: This is primarily a flight search, other aspects are minimal/secondary
            Output: ["travel", "itinerary", "accommodation"]
            
            Scenario E - Generic planning (minimal details):
            Query: "Trip to Kerala from 1st to 5th Dec, budget 30000"
            Analysis: Basic trip info, no emphasis on any specific aspect
            Reasoning: Standard exploration approach - discover → stay → transport
            Output: ["itinerary", "accommodation", "travel"] (DEFAULT)
            
            **ADDITIONAL SCENARIOS TO CONSIDER:**
            
            - **Last-minute urgent booking** ("need to leave tomorrow") → Travel first (availability critical)
            - **Multi-city itinerary** (Delhi → Agra → Jaipur) → Itinerary first (route planning), then transport between cities
            - **Weekend getaway** (2-3 days, nearby city) → Accommodation first (limited availability), quick itinerary, flexible transport
            - **Adventure trip** (trekking, rafting, sports) → Itinerary first (activity planning is core), accommodation near activity zones
            - **Business + leisure combo** ("conference in Bangalore, stay extra for sightseeing") → Accommodation first (near conference), itinerary for leisure days
            - **Relaxation/spa retreat** → Accommodation first (resort is the destination), minimal itinerary, transport secondary
            - **Festival/event trip** ("attending Diwali celebrations") → Itinerary first (event is focal point), accommodation near venue, transport to event
            - **Budget backpacking** (tight budget, flexible plans) → Travel first (cheapest transport locks biggest expense), budget accommodation, free/cheap activities
            - **INTERNATIONAL TRIPS** (any cross-border travel) → ALWAYS Travel first (flights are most expensive and have limited availability), then accommodation, then itinerary
            
            **CRITICAL INTERNATIONAL RULE:**
            For ANY international route (India ↔ Other Country): ALWAYS put "travel" FIRST in routing_order.
            Examples: Bangalore → Dubai, Mumbai → London, Delhi → Singapore = routing_order: ["travel", "accommodation", "itinerary"]
            
            **CRITICAL INSTRUCTION:**
            These examples show THINKING PATTERNS, not rules. Don't match patterns—UNDERSTAND the user's actual situation. Every query is unique. Analyze dependencies, priorities, and constraints specific to THAT query. Return routing order that makes practical sense for THAT trip.

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

            Query: "Budget trip from Delhi to Manali for 5 people, ₹55000 total, prefer buses, non-veg food preferred"
            Output: {{"budget": 55000, "currency": "INR", "dates": "Not specified", "from_location": "Delhi", "to_location": "Manali", "travelers": 5, "dietary_preferences": "non-veg only", "routing_order": ["travel", "itinerary", "accommodation"]}}

            Query: "Family vacation to Goa, comfortable stay, 4 persons"
            Output: {{"budget": null, "currency": "INR", "dates": "Not specified", "from_location": "Not specified", "to_location": "Goa", "travelers": 4, "dietary_preferences": "veg and non-veg", "routing_order": ["accommodation", "itinerary", "travel"]}}

            9. **budget_allocation**: CRITICAL - Analyze user query to determine intelligent budget split based on user preferences.
               Return budget split as decimal percentages (must sum to 1.0):
               - "accommodation": hotels/stays allocation
               - "itinerary": activities/experiences allocation  
               - "travel": transport allocation
               
               **ANALYZE USER INTENT FIRST, then apply these guidelines:**
               
               **USER PREFERENCE ANALYSIS:**
               - "luxury", "5-star", "premium", "high-end" → Higher accommodation % (0.40-0.55)
               - "budget", "cheap", "economical", "backpacking" → Balanced allocation (0.30-0.35 each)
               - "adventure", "activities", "sightseeing", "experiences" → Higher itinerary % (0.35-0.50)
               - "comfortable stay", "good hotels", "resort" → Moderate accommodation boost (0.40-0.45)
               - Long distance routes → Moderate travel boost (0.35-0.45)
               
               **DOMESTIC vs INTERNATIONAL ADJUSTMENT:**
               - **Domestic routes**: Base on user preferences above
               - **International routes**: Add +15-25% to travel allocation (flights expensive), reduce others proportionally
               
               **EXAMPLES with REASONING:**
               - "luxury resort in Goa for family" → accommodation: 0.50, itinerary: 0.25, travel: 0.25 (luxury focus)
               - "budget backpacking Bangalore to Manali" → travel: 0.35, accommodation: 0.30, itinerary: 0.35 (balanced budget)
               - "adventure trekking in Himachal" → itinerary: 0.45, accommodation: 0.30, travel: 0.25 (activity focus)
               - "business trip Mumbai to Singapore" → travel: 0.60, accommodation: 0.30, itinerary: 0.10 (international + business)
               - "family vacation Delhi to Dubai" → travel: 0.55, accommodation: 0.35, itinerary: 0.10 (international + family comfort)
               - "honeymoon to Paris" → travel: 0.50, accommodation: 0.40, itinerary: 0.10 (international + luxury)
               
               **KEY RULE**: NEVER use fixed percentages for all queries. Always adapt to user's specific needs and trip type!
               - Mumbai → Dubai (international) → {{"travel": 0.65, "accommodation": 0.25, "itinerary": 0.10}}
               - Delhi → London (international) → {{"travel": 0.70, "accommodation": 0.20, "itinerary": 0.10}}

            Return ONLY valid JSON with ALL fields including budget_allocation:
            Return ONLY valid JSON with ALL fields including budget_allocation:
            """
            
            # Use Azure OpenAI to extract preferences
            response_text = self._call_azure_openai(system_prompt, user_prompt, temperature=0.1)
            
            # Clean response (remove any markdown formatting)
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()
            
            # Parse JSON response
            try:
                preferences = json.loads(response_text)
                
                self.logger.info(f"📋 RAW Azure OpenAI response: {json.dumps(preferences, indent=2)}")
                
                # Extract and validate budget allocation  
                budget_allocation = preferences.get('budget_allocation', {'travel': 0.33, 'accommodation': 0.33, 'itinerary': 0.34})
                
                # Normalize budget allocation to sum to 1.0
                total_alloc = sum(budget_allocation.values())
                if abs(total_alloc - 1.0) > 0.01:
                    budget_allocation = {k: v/total_alloc for k, v in budget_allocation.items()}
                
                # Validate and set defaults for missing fields (no default budget)
                routing_order = preferences.get('routing_order', ["itinerary", "travel", "accommodation"])
                
                # CRITICAL: Ensure travel is NEVER last in routing order
                if len(routing_order) >= 2 and routing_order[-1] == 'travel':
                    self.logger.warning(f"⚠️ FIXING: Travel was last in routing order: {routing_order}")
                    # Move travel to second position
                    routing_order.remove('travel')
                    routing_order.insert(1, 'travel')
                    self.logger.info(f"✅ CORRECTED routing order: {routing_order}")
                
                validated_preferences = {
                    'budget': preferences.get('budget'),  # No default budget - must come from query
                    'currency': 'INR',  # Always use INR for all destinations
                    'dates': preferences.get('dates', 'Not specified'),
                    'from_location': preferences.get('from_location', 'Not specified'),
                    'to_location': preferences.get('to_location', 'Not specified'),
                    'travelers': preferences.get('travelers', 1),
                    'dietary_preferences': preferences.get('dietary_preferences', 'veg and non-veg'),
                    'routing_order': routing_order,  # Use validated routing order
                    'budget_allocation': budget_allocation  # NEW: Include budget allocation from same call
                }
                
                self.logger.info(f"✅ Extracted preferences and budget allocation in single call")
                self.logger.info(f"Preferences: {validated_preferences}")
                return validated_preferences
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"JSON parse error: {e}")
                return self._basic_fallback(query)
                
        except Exception as e:
            self.logger.error(f"Azure OpenAI error: {e}")
            return self._basic_fallback(query)
    
    def _basic_fallback(self, query: str) -> Dict[str, Any]:
        """
        Basic fallback when Azure OpenAI extraction fails.
        """
        self.logger.info("Using fallback...")
        
        query_lower = query.lower()
        
        # Default preferences
        preferences = {
            'budget': None,
            'currency': 'INR',  # Always use INR
            'dates': 'Not specified',
            'from_location': 'Not specified',
            'to_location': 'Not specified',
            'travelers': 1,
            'dietary_preferences': 'veg and non-veg',
            'routing_order': ["itinerary", "travel", "accommodation"],  # Travel NEVER last!
            'original_query': query  # Store original query for dynamic allocation
            # Note: budget_allocation will be calculated dynamically by Azure OpenAI
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
        Now uses budget_allocation from preferences (already calculated in single LLM call).
        If not available, dynamically calculates using Azure OpenAI based on query.
        """
        routing_order = preferences.get('routing_order', self.default_sequence)
        
        # Get budget allocation from preferences (already calculated by Azure OpenAI in combined call)
        base_allocation = preferences.get('budget_allocation')
        
        # If budget allocation not in preferences, calculate it dynamically using Gemini
        if not base_allocation:
            self.logger.info("⚠️ Budget allocation not in preferences, calculating dynamically with Azure OpenAI...")
            original_query = preferences.get('original_query', '')
            base_allocation = self._get_preference_based_allocation(original_query, total_budget)
        
        # Final safety check: If still None (shouldn't happen), use default
        if not base_allocation or not isinstance(base_allocation, dict):
            self.logger.warning("⚠️ Budget allocation is None or invalid, using default balanced allocation")
            base_allocation = {
                'accommodation': 0.35,
                'itinerary': 0.30,
                'travel': 0.35
            }
        
        self.logger.info(f"💰 Using budget allocation: {[f'{k}: {v:.1%}' for k, v in base_allocation.items()]}")
        
        # Adjust based on routing priority (first tool gets additional bonus)
        allocation = base_allocation.copy()
        
        if routing_order and len(routing_order) > 0:
            priority_tool = routing_order[0]
            
            # Only adjust if priority tool exists in allocation
            if priority_tool in allocation:
                # Give 10% bonus to priority tool, reduce others proportionally
                bonus = 0.10
                allocation[priority_tool] += bonus
                
                # Reduce other tools proportionally
                other_tools = [t for t in allocation.keys() if t != priority_tool]
                
                if len(other_tools) > 0:
                    reduction_per_tool = bonus / len(other_tools)
                    
                    for tool in other_tools:
                        allocation[tool] = max(0.05, allocation[tool] - reduction_per_tool)  # Minimum 5%
            else:
                self.logger.warning(f"⚠️ Priority tool '{priority_tool}' not in allocation, skipping bonus adjustment")
        
        # Convert to absolute amounts (with safety check for total_budget)
        if not total_budget or total_budget <= 0:
            self.logger.warning(f"⚠️ Invalid total_budget: {total_budget}, using default 30000")
            total_budget = 30000
        
        budget_allocation = {tool: total_budget * percentage for tool, percentage in allocation.items()}
        
        self.logger.info(f"💰 Budget allocation based on preferences: {[f'{k}: {v:.1%}' for k, v in allocation.items()]}")
        self.logger.info(f"💰 Absolute budget amounts: {[f'{k}: ₹{v:.0f}' for k, v in budget_allocation.items()]}")
        return budget_allocation
    
    @retry_on_overload(max_retries=3, initial_delay=2)
    def _get_preference_based_allocation(self, query: str, budget: float) -> Dict[str, float]:
        """
        Use Azure OpenAI to intelligently determine budget allocation based on query understanding.
        
        Args:
            query: User query text
            budget: Total budget amount for context
            
        Returns:
            Dict with tool allocation percentages
        """
        try:
            # Use Azure OpenAI to determine allocation
            system_prompt = """You are a travel budget allocation expert. Analyze travel queries and determine optimal budget distribution across accommodation, itinerary, and travel based on user priorities."""
            
            user_prompt = f"""
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
            Return ONLY valid JSON with percentages that sum to 1.0:
            {{"accommodation": 0.XX, "itinerary": 0.XX, "travel": 0.XX}}
            """
            
            # Use Azure OpenAI for intelligent allocation
            response_text = self._call_azure_openai(system_prompt, user_prompt, temperature=0.1)
            
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
            
            self.logger.info(f"🧠 Azure OpenAI-based allocation: {[f'{k}: {v:.1%}' for k, v in allocation.items()]}")
            return allocation
            
        except Exception as e:
            self.logger.warning(f"⚠️ Azure OpenAI allocation failed: {e}, using default")
            # Fallback to balanced default with 3 tools
            return {
                'accommodation': 0.35,
                'itinerary': 0.30, 
                'travel': 0.35
            }
    
    @retry_on_overload(max_retries=3, initial_delay=2)
    def _determine_accommodation_preference(self, query: str, location: str, budget: float) -> str:
        """
        Use Azure OpenAI to naturally understand accommodation preference from user query.
        
        CRITICAL: SERP API fails with detailed queries. Only return one of TWO simple formats:
        1. "Budget hotels and hostels in {location}"
        2. "Luxury hotels in {location}"
        
        Args:
            query: User's original natural language query
            location: Destination location
            budget: Allocated budget for accommodation
            
        Returns:
            str: Simple SERP query - either "Budget hotels and hostels in X" or "Luxury hotels in X"
        """
        try:
            # Use Azure OpenAI for accommodation preference
            system_prompt = """You are an accommodation preference analyzer. Determine if users want budget or luxury accommodations based on their travel query."""
            
            user_prompt = f"""
            TASK: Analyze the user's travel query and determine their accommodation preference.

            USER QUERY: "{query}"
            DESTINATION: {location}
            ACCOMMODATION BUDGET: {budget}

            Understand the user's accommodation preferences from their natural language query.
            Consider:
            - Explicit mentions (luxury, premium, budget, cheap, hostel, etc.)
            - Implicit preferences from budget level (high budget suggests luxury, low budget suggests budget)
            - Travel style indicators (backpacking = budget, comfort = luxury, business = luxury)
            - Context clues (honeymoon/anniversary = luxury, student trip = budget)

            Based on your understanding, return ONLY one of these TWO options:
            1. "Budget hotels and hostels in {location}" - for budget-conscious travelers
            2. "Luxury hotels in {location}" - for comfort/luxury-seeking travelers

            EXAMPLES:
            Query: "Planning a budget trip to Goa with friends"
            Output: Budget hotels and hostels in Goa

            Query: "Honeymoon in Dubai, want best hotels with great service"
            Output: Luxury hotels in Dubai

            Query: "Backpacking through Thailand, need cheap hostels"
            Output: Budget hotels and hostels in Thailand

            Query: "Business trip to Mumbai, prefer comfortable stay"
            Output: Luxury hotels in Mumbai

            Query: "Family vacation to Paris with 50000 rupees budget"
            Output: Luxury hotels in Paris

            Return ONLY the query string, nothing else.
            """
            
            # Use Azure OpenAI for natural language understanding
            response_text = self._call_azure_openai(system_prompt, user_prompt, temperature=0.1)
            
            serp_query = response_text.strip()
            
            # Validate response format
            if "Budget hotels and hostels in" in serp_query or "Luxury hotels in" in serp_query:
                return serp_query
            else:
                # Fallback: default to budget
                self.logger.warning(f"⚠️ Azure OpenAI returned unexpected format: '{serp_query}', using budget default")
                return f"Budget hotels and hostels in {location}"
            
        except Exception as e:
            self.logger.warning(f"⚠️ Azure OpenAI accommodation preference failed: {e}, using budget default")
            # Fallback to budget
            return f"Budget hotels and hostels in {location}"
    
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
        # Initialize or update conversation history
        if "history" not in state:
            state["history"] = []
        state["history"].append({"role": "user", "content": query})

        preferences = self._extract_preferences_and_routing(query)
        preferences['original_query'] = query

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

        self.state_manager.set_tool_sequence(preferences.get('routing_order', self.default_sequence))
        return self.state_manager.state
    
    def _generate_tool_specific_query(self, current_tool: str, state: Dict[str, Any], allocated_budget: float) -> str:
        """
        Generate a focused, tool-specific query instead of passing the entire original query.
        This makes it clearer what each tool should focus on.
        
        Args:
            current_tool: Name of the tool being executed
            state: Current state with user preferences
            allocated_budget: Budget allocated for this tool
            
        Returns:
            Tool-specific query string
        """
        location = state.get("to_location", "destination")
        from_location = state.get("from_location", "origin")
        dates = state.get("dates", "your dates")
        travelers = state.get("travelers", 1)
        currency = state.get("currency", "INR")
        dietary_prefs = state.get("user_preferences", {}).get("dietary_preferences", "veg and non-veg")
        
        if current_tool == "itinerary":
            # Itinerary tool needs: destination, dates, travelers, budget, activity preferences
            return f"""Plan a detailed day-by-day itinerary for {location} from {dates} for {travelers} person(s).
Budget for activities and experiences: {currency}{allocated_budget:.0f}.
Dietary preferences: {dietary_prefs}.
Focus on creating memorable experiences within the allocated budget."""
        
        elif current_tool == "accommodation":
            # Accommodation query will be determined by _determine_accommodation_preference
            # which creates simple SERP-friendly queries like "Budget hotels in Coorg"
            # This query is just for context, actual SERP query is generated separately
            return f"""Find hotels in {location} for {travelers} person(s).
User preferences: {state.get('original_query', '')}
Note: Dates and specific preferences will be passed as structured parameters."""
        
        elif current_tool == "travel":
            # Travel tool receives all parameters via structured params
            return f"Search travel options for {travelers} traveler(s) from {from_location} to {location}"
        
        elif current_tool == "restaurant":
            # Restaurant tool needs: location, budget, dietary preferences, meal count
            return f"""Recommend restaurants in {location} for {travelers} person(s).
Budget for dining: {currency}{allocated_budget:.0f}.
Dietary preferences: {dietary_prefs}.
Suggest restaurants for various meal times and occasions."""
        
        else:
            # Fallback to simplified query
            return f"Plan {current_tool} for {location} with budget {currency}{allocated_budget:.0f}"
    
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
            
            # Generate tool-specific query instead of passing entire original query
            tool_query = self._generate_tool_specific_query(current_tool, state, allocated_budget)
            
            # Keep original query for reference
            original_query = state["original_query"]
            currency = state["currency"]
            
            # Log tool execution start
            self.logger.info("=" * 60)
            self.logger.info(f"EXECUTING TOOL: {current_tool.upper()}")
            self.logger.info("=" * 60)
            self.logger.info(f"Tool Name: {current_tool}")
            self.logger.info(f"Allocated Budget: {currency}{allocated_budget:.0f}")
            self.logger.info(f"Tool-Specific Query: '{tool_query[:150]}...' (truncated)")
            self.logger.info(f"Original User Query: '{original_query[:100]}...' (for context)")
            
            tool_start_time = datetime.now()
            
            # Execute tool
            if current_tool == "accommodation":
                self.logger.info("Invoking accommodation search tool with extracted parameters...")
                
                # Extract parameters from state
                location = state.get("to_location", "Not specified")
                dates_str = state.get("dates", "")
                travelers = state.get("travelers", 2)
                # Always use INR regardless of destination
                currency = "INR"
                
                # Parse dates to get check-in and check-out
                check_in_date = None
                check_out_date = None
                try:
                    if " to " in dates_str and dates_str != "Not specified":
                        start_date_str, end_date_str = dates_str.split(" to ")
                        start_date = datetime.strptime(start_date_str.strip(), "%d-%m-%Y")
                        end_date = datetime.strptime(end_date_str.strip(), "%d-%m-%Y")
                        check_in_date = start_date.strftime("%Y-%m-%d")
                        check_out_date = end_date.strftime("%Y-%m-%d")
                except Exception as e:
                    self.logger.warning(f"Could not parse dates: {e}")
                
                # Provide fallback dates if parsing failed (required by Pydantic)
                if not check_in_date or not check_out_date:
                    today = datetime.now()
                    check_in_date = (today + timedelta(days=7)).strftime("%Y-%m-%d")
                    check_out_date = (today + timedelta(days=10)).strftime("%Y-%m-%d")
                    self.logger.info(f"📅 Using fallback dates: {check_in_date} to {check_out_date}")
                
                # Use Azure OpenAI to determine accommodation preference (Budget vs Luxury)
                # CRITICAL: SERP API fails with detailed queries - keep it simple!
                # Only 2 query types: "Budget hotels and hostels in X" or "Luxury hotels in X"
                serp_query = self._determine_accommodation_preference(original_query, location, allocated_budget)
                self.logger.info(f"🏨 Azure OpenAI-determined query: '{serp_query}'")
                
                # Note: Rating filter defaults to [7, 8, 9] in the tool
                # No need to override - SERP rating filter doesn't differentiate budget vs luxury
                # The query term (Budget/Luxury) handles the type of accommodation
                
                # Prepare tool parameters
                tool_params = {
                    "location": location,
                    "check_in_date": check_in_date,
                    "check_out_date": check_out_date,
                    "adults": travelers,
                    "children": 0,
                    "currency": "INR",  # Always use INR for all destinations
                    # rating defaults to [7, 8, 9] in tool - no need to specify
                    "query": serp_query  # Simple query determined by Azure OpenAI
                }
                self.logger.info(f"Tool Parameters: {tool_params}")
                result = self.tools["accommodation"].invoke(tool_params)
            elif current_tool == "itinerary":
                self.logger.info("Invoking itinerary planning tool...")
                tool_params = {"query": tool_query}
                self.logger.info(f"Tool Parameters: {tool_params}")
                result = self.tools["itinerary"].invoke(tool_params)
            elif current_tool == "restaurant":
                # Restaurant tool now works independently with location parameter
                self.logger.info("Invoking restaurant search tool...")
                
                # Extract parameters
                travelers = state.get("travelers", 2)
                dates_str = state.get("dates", "")
                location = state.get("to_location", "Not specified")
                currency = "INR"  # Always use INR for all destinations
                
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
                # Use the new clean architecture approach with tool-specific query
                result = self.execute_travel_search(tool_query)
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

## 💰 Budget Summary
| Category | Allocated | Estimated Used |
|----------|-----------|----------------|
| Itinerary | {state['currency']}{state['budget_allocation'].get('itinerary', 0):.0f} | {state['currency']}{state['spent_amounts'].get('itinerary', 0):.0f} |
| Travel | {state['currency']}{state['budget_allocation'].get('travel', 0):.0f} | {state['currency']}{state['spent_amounts'].get('travel', 0):.0f} |
| Accommodation | {state['currency']}{state['budget_allocation'].get('accommodation', 0):.0f} | {state['currency']}{state['spent_amounts'].get('accommodation', 0):.0f} |

**Note:** Restaurant recommendations are included in the itinerary planning.

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
        # Optionally append agent response to history
        response = self.state_manager.state.get("combined_result", "")
        if "history" not in self.state_manager.state:
            self.state_manager.state["history"] = []
        self.state_manager.state["history"].append({"role": "agent", "content": response})

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
    
    def plan_trip_stream(self, query: str):
        """
        Stream trip planning results progressively as each step completes.
        
        This is a generator function that yields results at each stage:
        - Preferences extraction
        - Budget allocation
        - Each tool execution (itinerary, travel, accommodation)
        - Final combined result
        
        Args:
            query: Natural language trip planning query
            
        Yields:
            Dict with status, step, and data for each completed stage
        """
        # Start execution tracking
        self.execution_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        self.execution_start_time = datetime.now()
        
        self.logger.info("=" * 100)
        self.logger.info("STARTING STREAMING TRIP PLANNING EXECUTION")
        self.logger.info("=" * 100)
        
        try:
            # Reset state
            reset_state()
            self.state_manager = get_state_manager()
            
            # Step 1: Extract ALL parameters in single comprehensive call
            yield {
                "status": "processing", 
                "step": "preferences",
                "message": "🧠 Analyzing your trip requirements (single AI call)...",
                "progress": 10
            }
            
            # Single comprehensive extraction
            all_params = self._extract_complete_trip_parameters(query)
            
            # Extract components
            travel_params = all_params.get('travel_params', {})
            preferences = all_params.get('preferences', {})
            routing_order = all_params.get('routing_order', ['travel', 'accommodation', 'itinerary'])
            
            # Simple fallback - the AI should provide proper budget_allocation based on prompts
            budget_allocation = all_params.get('budget_allocation', {'travel': 0.33, 'accommodation': 0.33, 'itinerary': 0.34})
            tool_queries = all_params.get('tool_queries', {})
            
            budget = preferences.get('budget') or 30000
            
            # Log extracted parameters for debugging
            self.logger.info(f"🎯 EXTRACTED TRAVEL PARAMS: {travel_params}")
            self.logger.info(f"🎯 EXTRACTED PREFERENCES: {preferences}")
            self.logger.info(f"🎯 TOOL QUERIES: {tool_queries}")
            
            # Update state
            self.state_manager.update_input_info(
                query=query,
                preferences=preferences,
                budget=budget,
                currency=preferences.get('currency', 'INR'),
                dates=preferences.get('dates', 'Not specified'),
                from_loc=preferences.get('from_location', 'Not specified'),
                to_loc=preferences.get('to_location', 'Not specified'),
                travelers=preferences.get('travelers', 1)
            )
            
            yield {
                "status": "completed",
                "step": "preferences",
                "message": "✅ Trip requirements analyzed",
                "data": {
                    "from": preferences.get('from_location'),
                    "to": preferences.get('to_location'),
                    "dates": preferences.get('dates'),
                    "travelers": preferences.get('travelers'),
                    "budget": f"₹{budget:,}",
                    "routing_order": routing_order,
                    "budget_allocation": budget_allocation
                },
                "progress": 20
            }
            
            # Step 2: Use extracted budget allocation (no additional LLM call needed)
            yield {
                "status": "processing",
                "step": "budget",
                "message": "� Using extracted budget allocation...",
                "progress": 25
            }
            
            # Convert percentage allocation to absolute amounts
            allocation = {tool: budget * percentage for tool, percentage in budget_allocation.items()}
            self.state_manager.allocate_budget(allocation)
            self.state_manager.set_tool_sequence(routing_order)
            
            yield {
                "status": "completed",
                "step": "budget",
                "message": "✅ Budget allocated",
                "data": {
                    tool: f"₹{amount:,.0f}" for tool, amount in allocation.items()
                },
                "progress": 30
            }
            
            # Step 3: Execute tools sequentially using extracted parameters and queries
            tool_sequence = routing_order
            progress_per_tool = 50 // len(tool_sequence)  # Distribute 50% progress across tools
            base_progress = 30
            
            self.logger.info("=" * 80)
            self.logger.info("🔍 STATE VERIFICATION BEFORE TOOL EXECUTION")
            self.logger.info("=" * 80)
            self.logger.info(f"📍 From Location: {self.state_manager.state.get('from_location')}")
            self.logger.info(f"📍 To Location: {self.state_manager.state.get('to_location')}")
            self.logger.info(f"📅 Dates: {self.state_manager.state.get('dates')}")
            self.logger.info(f"👥 Travelers: {self.state_manager.state.get('travelers')}")
            self.logger.info(f"💰 Budget: {self.state_manager.state.get('total_budget')}")
            self.logger.info(f"🔄 Routing Order: {tool_sequence}")
            self.logger.info("=" * 80)
            
            for idx, tool in enumerate(tool_sequence):
                current_progress = base_progress + (idx * progress_per_tool)
                
                yield {
                    "status": "processing",
                    "step": tool,
                    "message": f"🔄 Searching {tool}...",
                    "progress": current_progress
                }
                
                # Execute tool
                allocated_budget = self.state_manager.get_remaining_budget_for_category(tool)
                self.logger.info(f"💰 {tool.capitalize()} - Allocated Budget: ₹{allocated_budget:,.0f}")
                
                # Log state being used for query generation
                self.logger.info(f"📊 State for {tool} query generation:")
                self.logger.info(f"  - from_location: {self.state_manager.state.get('from_location')}")
                self.logger.info(f"  - to_location: {self.state_manager.state.get('to_location')}")
                self.logger.info(f"  - dates: {self.state_manager.state.get('dates')}")
                
                tool_query = self._generate_tool_specific_query(tool, self.state_manager.state, allocated_budget)
                self.logger.info(f"🔍 {tool.capitalize()} - Query: {tool_query[:200]}...")
                
                # Execute based on tool type
                if tool == "accommodation":
                    # Use extracted parameters directly (no re-parsing needed)
                    accommodation_query = tool_queries.get('accommodation_query', 'Budget accommodation options')
                    
                    self.logger.info("🏨 Calling accommodation tool with extracted parameters:")
                    self.logger.info(f"  📍 Location: {travel_params.get('destination')}")
                    self.logger.info(f"  📅 Check-in: {travel_params.get('departure_date')}")
                    self.logger.info(f"  📅 Check-out: {travel_params.get('return_date')}")
                    self.logger.info(f"  👥 Travelers: {travel_params.get('travelers')}")
                    self.logger.info(f"  💰 Budget: ₹{allocated_budget}")
                    self.logger.info(f"  🔍 Query: {accommodation_query}")
                    
                    # Use extracted travel parameters directly
                    check_in_date = travel_params.get('departure_date', (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"))
                    check_out_date = travel_params.get('return_date', (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"))
                    location = travel_params.get('destination', 'Not specified')
                    travelers = travel_params.get('travelers', 2)
                    
                    result = self.tools["accommodation"].invoke({
                        "location": location,
                        "check_in_date": check_in_date,
                        "check_out_date": check_out_date,
                        "adults": travelers,
                        "children": 0,
                        "currency": travel_params.get('currency', 'INR'),
                        "query": accommodation_query  # Use extracted clean query instead of generating new one
                    })
                elif tool == "itinerary":
                    # Use extracted itinerary query directly (like travel and accommodation)
                    itinerary_query = tool_queries.get('itinerary_query', 'Plan comprehensive itinerary')
                    
                    self.logger.info("🗓️ Calling itinerary tool with extracted query:")
                    self.logger.info(f"  📍 Destination: {travel_params.get('destination')}")
                    self.logger.info(f"  📅 Duration: {travel_params.get('departure_date')} to {travel_params.get('return_date')}")
                    self.logger.info(f"  👥 Travelers: {travel_params.get('travelers')}")
                    self.logger.info(f"  💰 Budget: ₹{allocated_budget}")
                    self.logger.info(f"  🔍 Query: {itinerary_query}")
                    
                    result = self.tools["itinerary"].invoke({"query": itinerary_query})
                elif tool == "travel":
                    # Use extracted travel parameters directly (no re-extraction needed)
                    self.logger.info("🚀 Calling travel_search_tool with extracted parameters:")
                    self.logger.info(f"  📍 Origin: {travel_params.get('origin')} ({travel_params.get('origin', 'UNK')[:3].upper()})")
                    self.logger.info(f"  📍 Destination: {travel_params.get('destination')} ({travel_params.get('destination', 'UNK')[:3].upper()})")
                    self.logger.info(f"  📅 Departure: {travel_params.get('departure_date')}, Return: {travel_params.get('return_date')}")
                    self.logger.info(f"  🚌 Transport Modes: {travel_params.get('transport_modes')}")
                    self.logger.info(f"  👥 Travelers: {travel_params.get('travelers')}")
                    
                    # CRITICAL FIX: Resolve airport codes for international trips (like Streamlit does)
                    origin = travel_params.get('origin', 'Not specified')
                    destination = travel_params.get('destination', 'Not specified')
                    is_international = not travel_params.get('is_domestic', True)
                    
                    # Resolve airport codes if international trip using existing method
                    origin_airport = None
                    destination_airport = None
                    if is_international:
                        try:
                            # Use existing resolve_airport_codes_and_currency method
                            temp_params = TravelSearchParams(
                                origin=origin,
                                destination=destination,
                                departure_date=travel_params.get('departure_date', '2025-12-01'),
                                return_date=travel_params.get('return_date'),
                                transport_modes=['flight'],
                                travelers=travel_params.get('travelers', 1),
                                budget_limit=50000,
                                currency='INR',
                                trip_type='round_trip'
                            )
                            
                            resolved_params = self.resolve_airport_codes_and_currency(temp_params)
                            origin_airport = resolved_params.origin_airport
                            destination_airport = resolved_params.destination_airport
                            
                            self.logger.info(f"🌍 Airport Code Resolution: {origin} → {origin_airport}, {destination} → {destination_airport}")
                            
                        except Exception as e:
                            self.logger.warning(f"⚠️ Airport code resolution failed: {e}")
                    
                    # For international trips, ensure sufficient budget for flight availability
                    total_budget = travel_params.get('budget_limit', 50000)
                    
                    if is_international and tool == "travel":
                        # Calculate minimum needed for international flights (based on total budget)
                        min_international_budget = total_budget * 0.45  # At least 45% for international flights
                        effective_budget = max(allocated_budget, min_international_budget)
                        
                        if effective_budget > allocated_budget:
                            self.logger.info(f"🌍 INTERNATIONAL TRIP: Boosting travel budget to ₹{effective_budget:,.0f} (was ₹{allocated_budget:,.0f})")
                        else:
                            effective_budget = allocated_budget
                    else:
                        effective_budget = allocated_budget
                    
                    self.logger.info(f"  💰 Budget: ₹{effective_budget}")
                    
                    # Call travel tool directly with clean parameters (including airport codes)
                    try:
                        search_params = {
                            "origin": origin,
                            "destination": destination,
                            "departure_date": travel_params.get('departure_date', '2025-12-01'),
                            "return_date": travel_params.get('return_date'),
                            "transport_modes": travel_params.get('transport_modes', ['bus', 'train']),
                            "travelers": travel_params.get('travelers', 1),
                            "budget_limit": effective_budget,
                            "currency": travel_params.get('currency', 'INR'),
                            "trip_type": travel_params.get('trip_type', 'round_trip'),
                            "is_domestic": travel_params.get('is_domestic', True)
                        }
                        
                        # Add airport codes if resolved (critical for international flights)
                        if origin_airport and origin_airport != origin:
                            search_params["origin_airport"] = origin_airport
                            self.logger.info(f"  ✈️ Origin Airport: {origin_airport}")
                        if destination_airport and destination_airport != destination:
                            search_params["destination_airport"] = destination_airport
                            self.logger.info(f"  ✈️ Destination Airport: {destination_airport}")
                        
                        result_json = self.tools["travel"].invoke(search_params)
                        
                        # Format the JSON results as clean markdown tables for better user experience
                        from src.tools.optimization.TravelOptimization import format_travel_results_as_markdown
                        result = format_travel_results_as_markdown(json.loads(result_json))
                        
                        self.logger.info("✅ Travel search completed - formatted as clean Markdown tables")
                        
                    except Exception as e:
                        self.logger.error(f"Travel search failed: {e}")
                        result = f"Travel search failed: {str(e)}"
                else:
                    result = f"Tool {tool} not implemented"
                
                # Update state
                self.state_manager.update_tool_result(tool, result)
                self.state_manager.mark_tool_completed(tool)
                
                # Calculate ACTUAL budget usage from results (instead of estimating 99%)
                travelers = self.state_manager.state.get("travelers", 1)
                actual_usage = self._calculate_actual_budget_usage(result, tool, travelers)
                
                # If we couldn't extract actual usage, use conservative estimate (70% of allocated)
                if actual_usage is None:
                    actual_usage = allocated_budget * 0.70
                    self.logger.info(f"📊 Using conservative estimate: ₹{actual_usage:,.0f} (70% of allocated)")
                
                # Ensure actual usage doesn't exceed allocated
                if actual_usage > allocated_budget:
                    self.logger.warning(f"⚠️ Actual usage (₹{actual_usage:,.0f}) exceeds allocated (₹{allocated_budget:,.0f}), capping at allocated")
                    actual_usage = allocated_budget
                
                # Track actual spending
                self.state_manager.spend_budget(tool, actual_usage)
                
                # Calculate savings
                savings = allocated_budget - actual_usage
                remaining = allocated_budget - actual_usage
                utilization = (actual_usage / allocated_budget * 100) if allocated_budget > 0 else 0
                
                self.logger.info(f"💸 {tool.capitalize()} - Actual Usage: ₹{actual_usage:,.0f} ({utilization:.1f}%)")
                self.logger.info(f"💵 {tool.capitalize()} - Savings: ₹{savings:,.0f}")
                
                # Reallocate savings to remaining tools if significant (>10% saved)
                if savings > allocated_budget * 0.10:
                    total_budget = self.state_manager.state.get('total_budget', 30000)
                    self._reallocate_savings_to_remaining_tools(idx, tool_sequence, savings, total_budget)
                
                # Get the appropriate clean query for display
                display_query = None
                if tool == "accommodation":
                    display_query = tool_queries.get('accommodation_query', 'Budget accommodation search')
                elif tool == "itinerary":
                    # Use the comprehensive itinerary query from LLM extraction
                    display_query = tool_queries.get('itinerary_query', 'Plan comprehensive itinerary')
                elif tool == "travel":
                    display_query = f"Travel from {travel_params.get('origin')} to {travel_params.get('destination')} for {travel_params.get('travelers')} travelers"
                else:
                    display_query = tool_query  # Fallback to old query
                
                yield {
                    "status": "completed",
                    "step": tool,
                    "message": f"✅ {tool.capitalize()} results ready",
                    "data": result,
                    "query": display_query,  # Use clean extracted query for visibility
                    "budget_info": {
                        "allocated": f"₹{allocated_budget:,.0f}",
                        "used": f"₹{actual_usage:,.0f}",
                        "remaining": f"₹{remaining:,.0f}",
                        "utilization": f"{utilization:.1f}%",
                        "savings": f"₹{savings:,.0f}"
                    },
                    "progress": current_progress + progress_per_tool
                }
                
                # Advance to next tool
                self.state_manager.advance_step()
            
            # Step 4: Complete (skip expensive combining since we show individual results)
            execution_time = datetime.now() - self.execution_start_time
            
            yield {
                "status": "completed",
                "step": "final",
                "message": "✅ Trip plan complete!",
                "data": None,  # No combined result needed
                "execution_time": execution_time.total_seconds(),
                "progress": 100
            }
            
        except Exception as e:
            execution_time = datetime.now() - self.execution_start_time
            self.logger.error(f"Streaming execution failed: {e}")
            
            yield {
                "status": "error",
                "step": "error",
                "message": f"❌ Error: {str(e)}",
                "error": str(e),
                "execution_time": execution_time.total_seconds(),
                "progress": 0
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
        