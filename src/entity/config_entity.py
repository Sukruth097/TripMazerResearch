from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class AccommodationPlannerEntity(BaseModel):
    """Entity for accommodation planning requirements."""
    from_location: str
    destination: str
    no_of_people: int
    budget: float
    dates: str  # Format: DD-MM-YYYY to DD-MM-YYYY (e.g., 26-11-2025 to 30-11-2025)
    preferences: Optional[List[str]] = Field(default_factory=list)


class ItineraryPlannerEntity(BaseModel):
    """Entity for itinerary planning requirements."""
    from_location: str
    to_location: str
    dates: str
    budget: float
    travel_type: Optional[str] = None  
    preferred_activities: Optional[List[str]] = Field(default_factory=list)  # beach, mountains, night club, pubs, etc


class RestaurantsSearchEntity(BaseModel):
    """Entity for restaurants search requirements."""
    itinerary_details: str  # JSON/Markdown format
    dates: str


class TravelOptimizationEntity(BaseModel):
    """Entity for travel optimization requirements."""
    from_location: str
    to_location: str
    dates: str
    mode_of_transport: str  # bus, flights, trains, etc
    budget: float
    no_of_people: int
    preferences: Optional[List[str]] = Field(default_factory=list) 
