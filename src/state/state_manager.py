"""
State Manager for Trip Optimization Agent

Manages state variables for tracking budget, user preferences, tool results,
and execution flow throughout the trip planning process.
"""

from typing import Dict, List, Optional, Any, TypedDict
from dataclasses import dataclass, field
from datetime import datetime
import json


class TripState(TypedDict):
    """State schema for trip optimization agent."""
    # Input Information
    original_query: str
    user_preferences: Dict[str, Any]
    total_budget: float
    currency: str
    dates: str
    from_location: str
    to_location: str
    travelers: int
    
    # Budget Tracking
    remaining_budget: float
    budget_allocation: Dict[str, float]
    spent_amounts: Dict[str, float]
    
    # Tool Execution Order
    tool_sequence: List[str]
    current_step: int
    completed_tools: List[str]
    
    # Tool Results
    accommodation_result: Optional[str]
    itinerary_result: Optional[str]
    restaurant_result: Optional[str]
    travel_result: Optional[str]
    
    # Error Handling
    errors: List[str]
    warnings: List[str]
    retry_count: int
    
    # Final Output
    combined_result: Optional[str]
    execution_summary: Optional[str]


@dataclass
class StateManager:
    """Manages state for trip optimization agent."""
    
    def __init__(self):
        self.state: TripState = self._initialize_state()
    
    def _initialize_state(self) -> TripState:
        """Initialize empty state."""
        return TripState(
            # Input Information
            original_query="",
            user_preferences={},
            total_budget=0.0,
            currency="",
            dates="",
            from_location="",
            to_location="",
            travelers=1,
            
            # Budget Tracking
            remaining_budget=0.0,
            budget_allocation={},
            spent_amounts={},
            
            # Tool Execution Order
            tool_sequence=[],
            current_step=0,
            completed_tools=[],
            
            # Tool Results
            accommodation_result=None,
            itinerary_result=None,
            restaurant_result=None,
            travel_result=None,
            
            # Error Handling
            errors=[],
            warnings=[],
            retry_count=0,
            
            # Final Output
            combined_result=None,
            execution_summary=None
        )
    
    def update_input_info(self, query: str, preferences: Dict[str, Any], 
                         budget: float, currency: str, dates: str,
                         from_loc: str, to_loc: str, travelers: int):
        """Update input information in state."""
        self.state.update({
            "original_query": query,
            "user_preferences": preferences,
            "total_budget": budget,
            "currency": currency,
            "dates": dates,
            "from_location": from_loc,
            "to_location": to_loc,
            "travelers": travelers,
            "remaining_budget": budget
        })
    
    def set_tool_sequence(self, sequence: List[str]):
        """Set the execution order of tools."""
        self.state["tool_sequence"] = sequence
        self.state["current_step"] = 0
    
    def allocate_budget(self, allocation: Dict[str, float]):
        """Allocate budget across different categories."""
        self.state["budget_allocation"] = allocation
        
        # Initialize spent amounts
        for category in allocation.keys():
            self.state["spent_amounts"][category] = 0.0
    
    def spend_budget(self, category: str, amount: float) -> bool:
        """
        Record budget spending for a category.
        
        Returns:
            bool: True if spending is within allocation, False otherwise
        """
        current_spent = self.state["spent_amounts"].get(category, 0.0)
        allocated = self.state["budget_allocation"].get(category, 0.0)
        
        if current_spent + amount <= allocated:
            self.state["spent_amounts"][category] = current_spent + amount
            self.state["remaining_budget"] -= amount
            return True
        else:
            # Over budget - add warning
            self.add_warning(f"Budget exceeded for {category}: trying to spend {amount}, only {allocated - current_spent} remaining")
            return False
    
    def get_remaining_budget_for_category(self, category: str) -> float:
        """Get remaining budget for a specific category."""
        allocated = self.state["budget_allocation"].get(category, 0.0)
        spent = self.state["spent_amounts"].get(category, 0.0)
        return allocated - spent
    
    def advance_step(self):
        """Move to next step in execution."""
        self.state["current_step"] += 1
    
    def mark_tool_completed(self, tool_name: str):
        """Mark a tool as completed."""
        if tool_name not in self.state["completed_tools"]:
            self.state["completed_tools"].append(tool_name)
    
    def update_tool_result(self, tool_name: str, result: str):
        """Update result for a specific tool."""
        if tool_name == "accommodation":
            self.state["accommodation_result"] = result
        elif tool_name == "itinerary":
            self.state["itinerary_result"] = result
        elif tool_name == "restaurant":
            self.state["restaurant_result"] = result
        elif tool_name == "travel":
            self.state["travel_result"] = result
    
    def add_error(self, error: str):
        """Add error to state."""
        self.state["errors"].append(f"{datetime.now().isoformat()}: {error}")
    
    def add_warning(self, warning: str):
        """Add warning to state."""
        self.state["warnings"].append(f"{datetime.now().isoformat()}: {warning}")
    
    def increment_retry(self):
        """Increment retry counter."""
        self.state["retry_count"] += 1
    
    def get_current_tool(self) -> Optional[str]:
        """Get current tool to execute."""
        if self.state["current_step"] < len(self.state["tool_sequence"]):
            return self.state["tool_sequence"][self.state["current_step"]]
        return None
    
    def is_execution_complete(self) -> bool:
        """Check if all tools have been executed."""
        return self.state["current_step"] >= len(self.state["tool_sequence"])
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of execution."""
        return {
            "total_budget": self.state["total_budget"],
            "remaining_budget": self.state["remaining_budget"],
            "budget_utilization": self.state["total_budget"] - self.state["remaining_budget"],
            "completed_tools": self.state["completed_tools"],
            "errors": self.state["errors"],
            "warnings": self.state["warnings"],
            "retry_count": self.state["retry_count"]
        }
    
    def export_state(self) -> Dict[str, Any]:
        """Export current state as dictionary."""
        return dict(self.state)
    
    def import_state(self, state_dict: Dict[str, Any]):
        """Import state from dictionary."""
        self.state.update(state_dict)


# Global state manager instance
state_manager = StateManager()


def get_state_manager() -> StateManager:
    """Get the global state manager instance."""
    return state_manager


def reset_state():
    """Reset the global state manager."""
    global state_manager
    state_manager = StateManager()
