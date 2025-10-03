"""
Trip Optimization Agent using LangGraph

A comprehensive multi-agent system for trip planning that intelligently routes
through accommodation, itinerary, restaurant, and travel optimization based on
user preferences while managing budget allocation and state tracking.
"""

import os
import sys
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Add path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain.schema import BaseMessage

# Import optimization tools
from src.tools.optimization import (
    search_accommodations, 
    plan_itinerary, 
    search_restaurants, 
    optimize_travel
)

# Import state manager
from src.state.state_manager import TripState, get_state_manager, reset_state

# Import Perplexity service
from src.services.perplexity_service import PerplexityService


class TripOptimizationAgent:
    """
    Intelligent trip optimization agent that routes through multiple tools
    based on user preferences and manages budget allocation.
    """
    
    def __init__(self):
        self.state_manager = get_state_manager()
        self.graph = self._build_graph()
        
        # Default tool routing order
        self.default_sequence = ["itinerary", "travel", "accommodation", "restaurant"]
        
        # Tool mapping
        self.tools = {
            "accommodation": search_accommodations,
            "itinerary": plan_itinerary,
            "restaurant": search_restaurants,
            "travel": optimize_travel
        }
    
    def _get_perplexity_service(self) -> PerplexityService:
        """Get Perplexity service instance with API key."""
        api_key = os.getenv('PERPLEXITY_API_KEY')
        if not api_key:
            raise ValueError("PERPLEXITY_API_KEY environment variable is required")
        return PerplexityService(api_key)
    
    def _extract_preferences_and_routing(self, query: str) -> Dict[str, Any]:
        """
        Extract user preferences and determine tool routing order from query using LLM.
        
        Returns:
            Dict with preferences and routing order
        """
        try:
            perplexity = self._get_perplexity_service()
            
            # System prompt for preference extraction
            system_prompt = """
            You are an expert travel preferences analyzer. Extract specific travel information from user queries.
            
            Analyze the user's travel query and extract the following information in a structured JSON format:
            
            1. **Budget**: Extract any mentioned budget amount (numbers only, no currency symbols)
            2. **Currency**: Determine currency based on:
               - ₹ symbol OR Indian cities (Mumbai, Delhi, Bangalore, Chennai, Kolkata, etc.) = ₹
               - $ symbol OR international cities = $
               - Default to $ if unclear
            3. **Dates**: Extract travel dates in DD-MM-YYYY format, look for "from X to Y" or "X to Y" patterns
            4. **From Location**: Source/departure location
            5. **To Location**: Destination location
            6. **Travelers**: Number of people (look for "couple", "family", "2 people", "solo", etc.)
            7. **Priorities**: Rank these categories by user interest/mentions (1=highest, 4=lowest):
               - accommodation (hotels, stay, lodging, resort)
               - itinerary (plan, schedule, activities, sightseeing, temples, experiences)
               - restaurant (food, dining, eat, meal, cuisine)
               - travel (transport, flight, train, bus, route)
            
            Return ONLY a valid JSON object with these exact keys:
            {
                "budget": number or null,
                "currency": "₹" or "$",
                "dates": "DD-MM-YYYY to DD-MM-YYYY" or null,
                "from_location": "location" or null,
                "to_location": "location" or null,
                "travelers": number,
                "routing_order": ["tool1", "tool2", "tool3", "tool4"]
            }
            
            For routing_order, arrange tools by priority: ["highest_priority", "second", "third", "lowest"]
            Use these exact tool names: "accommodation", "itinerary", "restaurant", "travel"
            If no clear preferences, use: ["itinerary", "travel", "accommodation", "restaurant"]
            """
            
            # Use LLM to extract preferences
            result = perplexity.search(
                query=f"Extract travel preferences from this query: {query}",
                system_prompt=system_prompt,
                temperature=0.1
            )
            
            # Parse LLM response
            response_text = result.get('content', '')
            
            # Try to extract JSON from response
            try:
                # Look for JSON in response
                import re
                json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
                if json_match:
                    extracted_json = json_match.group(0)
                    preferences = json.loads(extracted_json)
                else:
                    # Fallback: try to parse entire response as JSON
                    preferences = json.loads(response_text)
                
                # Validate and set defaults
                preferences = {
                    'budget': preferences.get('budget') or 10000,
                    'currency': preferences.get('currency') or '$',
                    'dates': preferences.get('dates') or 'Not specified',
                    'from_location': preferences.get('from_location') or 'Not specified',
                    'to_location': preferences.get('to_location') or 'Not specified',
                    'travelers': preferences.get('travelers') or 1,
                    'routing_order': preferences.get('routing_order') or ["itinerary", "travel", "accommodation", "restaurant"]
                }
                
                return preferences
                
            except (json.JSONDecodeError, KeyError) as e:
                print(f"⚠️ JSON parsing failed: {e}")
                print(f"LLM Response: {response_text}")
                # Fallback to basic keyword-based extraction
                return self._fallback_extraction(query)
                
        except Exception as e:
            print(f"⚠️ LLM extraction failed: {e}")
            # Fallback to basic keyword-based extraction
            return self._fallback_extraction(query)
    
    def _fallback_extraction(self, query: str) -> Dict[str, Any]:
        """
        Fallback preference extraction using simple keyword matching.
        """
        query_lower = query.lower()
        preferences = {
            'budget': 10000,  # Default budget
            'currency': '$',   # Default currency
            'dates': 'Not specified',
            'from_location': 'Not specified',
            'to_location': 'Not specified',
            'travelers': 1,
            'routing_order': ["itinerary", "travel", "accommodation", "restaurant"]
        }
        
        # Simple currency detection
        if '₹' in query or any(city in query_lower for city in ['mumbai', 'delhi', 'bangalore', 'chennai', 'kolkata']):
            preferences['currency'] = '₹'
        
        # Simple traveler detection
        if 'couple' in query_lower:
            preferences['travelers'] = 2
        elif 'family' in query_lower:
            preferences['travelers'] = 4
        
        # Simple priority detection based on keyword frequency
        tool_priorities = {
            'accommodation': sum(1 for word in ['hotel', 'stay', 'accommodation', 'lodging', 'resort'] if word in query_lower),
            'itinerary': sum(1 for word in ['plan', 'itinerary', 'schedule', 'activities', 'sightseeing', 'temple'] if word in query_lower),
            'restaurant': sum(1 for word in ['food', 'restaurant', 'dining', 'eat', 'meal'] if word in query_lower),
            'travel': sum(1 for word in ['transport', 'flight', 'train', 'bus', 'travel', 'route'] if word in query_lower)
        }
        
        # Sort by priority
        sorted_tools = sorted(tool_priorities.items(), key=lambda x: x[1], reverse=True)
        preferences['routing_order'] = [tool for tool, _ in sorted_tools]
        
        return preferences
    
    def _allocate_budget(self, total_budget: float, preferences: Dict[str, Any]) -> Dict[str, float]:
        """
        Intelligently allocate budget across tools based on preferences.
        """
        routing_order = preferences.get('routing_order', self.default_sequence)
        
        # Base allocation percentages
        base_allocation = {
            'accommodation': 0.35,  # 35%
            'itinerary': 0.20,      # 20%
            'travel': 0.30,         # 30%
            'restaurant': 0.15      # 15%
        }
        
        # Adjust based on routing priority (first tool gets 10% bonus)
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
        
        return budget_allocation
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        # Define the workflow
        workflow = StateGraph(TripState)
        
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
    
    def _process_input(self, state: TripState) -> TripState:
        """Process input query and extract preferences."""
        query = state["original_query"]
        preferences = self._extract_preferences_and_routing(query)
        
        # Update state with extracted information
        self.state_manager.update_input_info(
            query=query,
            preferences=preferences,
            budget=preferences.get('budget', 10000),  # Default budget
            currency=preferences.get('currency', '$'),
            dates=preferences.get('dates', 'Not specified'),
            from_loc=preferences.get('from_location', 'Not specified'),
            to_loc=preferences.get('to_location', 'Not specified'),
            travelers=preferences.get('travelers', 1)
        )
        
        # Set tool sequence
        self.state_manager.set_tool_sequence(preferences.get('routing_order', self.default_sequence))
        
        return self.state_manager.state
    
    def _allocate_budget_node(self, state: TripState) -> TripState:
        """Allocate budget across tools."""
        total_budget = state["total_budget"]
        preferences = state["user_preferences"]
        
        allocation = self._allocate_budget(total_budget, preferences)
        self.state_manager.allocate_budget(allocation)
        
        return self.state_manager.state
    
    def _execute_current_tool(self, state: TripState) -> TripState:
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
            
            # Modify query to include budget constraint
            budget_aware_query = f"{original_query} Budget for {current_tool}: {currency}{allocated_budget:.0f}"
            
            # Execute tool
            if current_tool == "accommodation":
                result = self.tools["accommodation"].invoke({"query": budget_aware_query})
            elif current_tool == "itinerary":
                result = self.tools["itinerary"].invoke({"query": budget_aware_query})
            elif current_tool == "restaurant":
                # Restaurant tool needs special handling - use itinerary result if available
                itinerary_result = state.get("itinerary_result", "")
                if itinerary_result:
                    result = self.tools["restaurant"].invoke({
                        "itinerary_details": itinerary_result,
                        "dates": state["dates"],
                        "dietary_preferences": "veg and non-veg"  # Default
                    })
                else:
                    result = f"No itinerary available for restaurant planning. Budget: {currency}{allocated_budget:.0f}"
            elif current_tool == "travel":
                result = self.tools["travel"].invoke({"query": budget_aware_query})
            else:
                result = f"Unknown tool: {current_tool}"
            
            # Update tool result
            self.state_manager.update_tool_result(current_tool, result)
            self.state_manager.mark_tool_completed(current_tool)
            
            # If result suggests budget adjustment, add warning
            if "budget" in result.lower() and ("exceed" in result.lower() or "over" in result.lower()):
                self.state_manager.add_warning(f"{current_tool} suggests budget adjustment needed")
            
        except Exception as e:
            error_msg = f"Error executing {current_tool}: {str(e)}"
            self.state_manager.add_error(error_msg)
            
            # Mark as completed with error
            self.state_manager.update_tool_result(current_tool, f"Error: {error_msg}")
            self.state_manager.mark_tool_completed(current_tool)
        
        return self.state_manager.state
    
    def _track_budget(self, state: TripState) -> TripState:
        """Track budget usage and advance to next step."""
        current_tool = self.state_manager.get_current_tool()
        
        if current_tool:
            # Estimate budget usage (for simulation - in reality, extract from tool response)
            allocated = self.state_manager.get_remaining_budget_for_category(current_tool)
            estimated_usage = allocated * 0.8  # Assume 80% of allocated budget is used
            
            # Record budget usage
            self.state_manager.spend_budget(current_tool, estimated_usage)
        
        # Advance to next step
        self.state_manager.advance_step()
        
        return self.state_manager.state
    
    def _should_continue(self, state: TripState) -> str:
        """Decide whether to continue with next tool or combine results."""
        if self.state_manager.is_execution_complete():
            return "combine"
        else:
            return "continue"
    
    def _combine_results(self, state: TripState) -> TripState:
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
    
    def _format_output(self, state: TripState) -> TripState:
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
        # Reset state for new planning
        reset_state()
        self.state_manager = get_state_manager()
        
        # Initialize state with query
        initial_state = self.state_manager.state
        initial_state["original_query"] = query
        
        # Execute the graph
        result = self.graph.invoke(initial_state)
        
        return {
            "combined_result": result.get("combined_result", ""),
            "execution_summary": result.get("execution_summary", {}),
            "state": self.state_manager.export_state()
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
    Plan a complete trip to Tokyo from Delhi for a couple from 25-12-2025 to 30-12-2025 
    with budget rupeees 15000. We prefer temples, traditional experiences, and good food. 
    We want comfortable accommodation and prefer trains over flights when possible.
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
        import traceback
        traceback.print_exc()
