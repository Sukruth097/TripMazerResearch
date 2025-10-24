"""
Travel Search Parameter Entity
=============================
Structured entity for passing travel search parameters between agent and tools.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class TravelSearchParams:
    """
    Structured entity for travel search parameters.
    Used for communication between agent and travel search tools.
    """
    
    # Route Information
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str] = None
    
    # Traveler Details
    travelers: int = 1
    
    # Budget & Currency
    budget_limit: Optional[float] = None
    currency: str = "INR"
    currency_symbol: str = "₹"
    
    # Transport Preferences
    transport_modes: List[str] = None  # ["flight", "bus", "train"]
    preferred_mode: Optional[str] = None
    
    # Trip Details
    trip_type: str = "round_trip"  # "one_way" or "round_trip"
    is_domestic: bool = True
    is_international: bool = False
    
    # User Preferences
    budget_priority: str = "moderate"  # "tight", "moderate", "flexible"
    time_sensitivity: str = "flexible"  # "urgent", "moderate", "flexible"
    preference_type: str = "mid-range"  # "budget", "mid-range", "luxury" for accommodation preferences
    
    # Provider Instructions (for agent to specify)
    use_serp_for_flights: bool = True
    use_perplexity_for_ground: bool = True  # buses and trains
    
    # Airport Codes (resolved by agent using LLM)
    origin_airport: Optional[str] = None
    destination_airport: Optional[str] = None
    
    # Airport Availability (resolved by intelligent LLM analysis)
    origin_has_airport: bool = True  # Does origin have direct airport?
    destination_has_airport: bool = True  # Does destination have direct airport?
    origin_airport_distance: float = 0.0  # Distance to nearest airport in km (0 if direct)
    destination_airport_distance: float = 0.0  # Distance to nearest airport in km (0 if direct)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TravelSearchParams':
        """
        Create TravelSearchParams from dictionary.
        
        Args:
            data: Dictionary with parameter values
            
        Returns:
            TravelSearchParams instance
        """
        # Ensure required fields have defaults if missing
        defaults = {
            'origin': data.get('origin', 'Not specified'),
            'destination': data.get('destination', 'Not specified'),
            'departure_date': data.get('departure_date', '2025-12-01'),
            'return_date': data.get('return_date'),
            'travelers': data.get('travelers', 1),
            'budget_limit': data.get('budget_limit'),
            'currency': data.get('currency', 'INR'),
            'currency_symbol': data.get('currency_symbol', '₹'),
            'transport_modes': data.get('transport_modes') or ["flight", "bus", "train"],
            'preferred_mode': data.get('preferred_mode'),
            'trip_type': data.get('trip_type', 'round_trip'),
            'is_domestic': data.get('is_domestic', True),
            'is_international': data.get('is_international', False),
            'budget_priority': data.get('budget_priority', 'moderate'),
            'time_sensitivity': data.get('time_sensitivity', 'flexible'),
            'preference_type': data.get('preference_type', 'mid-range'),
            'use_serp_for_flights': data.get('use_serp_for_flights', True),
            'use_perplexity_for_ground': data.get('use_perplexity_for_ground', True),
            'origin_airport': data.get('origin_airport'),
            'destination_airport': data.get('destination_airport'),
            'origin_has_airport': data.get('origin_has_airport', True),
            'destination_has_airport': data.get('destination_has_airport', True),
            'origin_airport_distance': data.get('origin_airport_distance', 0.0),
            'destination_airport_distance': data.get('destination_airport_distance', 0.0),
        }
        
        return cls(**defaults)
    
    def validate(self) -> List[str]:
        """Validate parameters and return list of errors"""
        errors = []
        
        if not self.origin:
            errors.append("Origin is required")
        if not self.destination:
            errors.append("Destination is required")
        if not self.departure_date:
            errors.append("Departure date is required")
        if self.travelers <= 0:
            errors.append("Number of travelers must be positive")
        if self.transport_modes is None or len(self.transport_modes) == 0:
            errors.append("At least one transport mode is required")
        
        return errors
    
    def get_route_info(self) -> Dict[str, Any]:
        """Get route information for the travel search"""
        return {
            'origin': self.origin,
            'destination': self.destination,
            'departure_date': self.departure_date,
            'return_date': self.return_date,
            'is_domestic': self.is_domestic,
            'is_international': self.is_international
        }


# Example usage:
"""
# In Agent:
params = TravelSearchParams(
    origin="Mumbai",
    destination="Delhi", 
    departure_date="2024-12-01",
    return_date="2024-12-05",
    travelers=2,
    budget_limit=10000,
    currency="INR",
    transport_modes=["flight", "train"],
    preferred_mode="train",
    is_domestic=True,
    budget_priority="tight"
)

# Pass to tool directly with parameters:
results = travel_search_tool(
    origin=params.origin,
    destination=params.destination,
    departure_date=params.departure_date,
    transport_modes=params.transport_modes,
    travelers=params.travelers,
    budget_limit=params.budget_limit,
    currency=params.currency,
    origin_airport=params.origin_airport,
    destination_airport=params.destination_airport,
    is_domestic=params.is_domestic
)
"""