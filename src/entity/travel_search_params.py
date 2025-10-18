"""
Travel Search Parameter Entity
=============================
Structured entity for passing travel search parameters between agent and tools.
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
import json


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
    
    # Provider Instructions (for agent to specify)
    use_serp_for_flights: bool = True
    use_perplexity_for_ground: bool = True  # buses and trains
    
    # Airport Codes (resolved by agent using LLM)
    origin_airport: Optional[str] = None
    destination_airport: Optional[str] = None
    
    def to_json(self) -> str:
        """Convert to JSON string for tool parameter passing"""
        return json.dumps(asdict(self), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TravelSearchParams':
        """Create instance from JSON string"""
        data = json.loads(json_str)
        return cls(**data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TravelSearchParams':
        """Create instance from dictionary"""
        return cls(**data)
    
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

# Pass to tool:
results = travel_search_tool(params.to_json())

# In Tool:
parsed_params = TravelSearchParams.from_json(json_params)
"""