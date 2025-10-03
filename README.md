# TripMazer Research - AI-Powered Trip Planning System

## 🌟 Overview
TripMazer is an advanced AI-powered trip planning system that uses multi-agent architecture with LangGraph to intelligently optimize travel itineraries, budgets, and recommendations. The system employs LLM-based preference extraction and intelligent routing to provide comprehensive travel planning solutions.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+ installed on your system
- Git (for cloning the repository)

### Setup Instructions

1. **Clone the Repository**
```bash
git clone https://github.com/Sukruth097/TripMazerResearch.git
cd TripMazerResearch
```

2. **Create Virtual Environment**
```bash
python -m venv venv
```

3. **Activate Virtual Environment**
```bash
# Windows
source venv/Scripts/activate

# macOS/Linux
source venv/bin/activate
```

4. **Install Dependencies**
```bash
pip install -r src/requirements.txt
```

5. **Run the Trip Optimization Agent**
```bash
python src/agents/worker/trip_optimization_agent/agent.py
```

### Environment Configuration
Create a `.env` file in the root directory with your API keys:
```env
PERPLEXITY_API_KEY=your_perplexity_api_key_here
```

## 🏗️ System Architecture

### High-Level Architecture

The TripMazer system follows a multi-agent architecture built on LangGraph, providing intelligent routing and state management for comprehensive trip planning.

```
┌─────────────────────────────────────────────────────────────┐
│                    TripMazer System                         │
├─────────────────────────────────────────────────────────────┤
│  User Query (Natural Language)                             │
│  ↓                                                         │
│  ┌─────────────────────────────────────┐                   │
│  │     Trip Optimization Agent         │                   │
│  │     (LangGraph Orchestrator)        │                   │
│  └─────────────────────────────────────┘                   │
│  ↓                                                         │
│  ┌─────────────────────────────────────┐                   │
│  │     LLM-Based Preference            │                   │
│  │     Extraction & Routing            │                   │
│  └─────────────────────────────────────┘                   │
│  ↓                                                         │
│  ┌─────────────────────────────────────┐                   │
│  │     State Management System         │                   │
│  │     (Budget + Execution Tracking)   │                   │
│  └─────────────────────────────────────┘                   │
│  ↓                                                         │
│  ┌─────────────────────────────────────┐                   │
│  │        Optimization Tools           │                   │
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐   │                   │
│  │  │ Acc │ │ Itn │ │ Rst │ │ Trv │   │                   │
│  │  └─────┘ └─────┘ └─────┘ └─────┘   │                   │
│  └─────────────────────────────────────┘                   │
│  ↓                                                         │
│  ┌─────────────────────────────────────┐                   │
│  │     Perplexity AI Service           │                   │
│  │     (Real-time Information)         │                   │
│  └─────────────────────────────────────┘                   │
│  ↓                                                         │
│  Comprehensive Trip Report (Markdown)                      │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

1. **Trip Optimization Agent**: Main orchestrator using LangGraph StateGraph
2. **LLM-Based Preference Extraction**: Intelligent parsing of natural language queries
3. **State Management System**: Tracks budget allocation and execution state
4. **Optimization Tools**: Specialized agents for different aspects of trip planning
5. **Perplexity AI Service**: External API for real-time travel information

## 📋 Low-Level Design (LLD)

### 1. Trip Optimization Agent (`agent.py`)

**Class: TripOptimizationAgent**

**Responsibilities:**
- Orchestrate multi-agent workflow using LangGraph
- Manage state transitions and budget allocation
- Route requests to appropriate optimization tools
- Combine results into comprehensive reports

**Key Methods:**
```python
__init__()                              # Initialize agent with tools and graph
_extract_preferences_and_routing()      # LLM-based preference extraction
_allocate_budget()                      # Intelligent budget distribution
_build_graph()                          # Construct LangGraph workflow
_execute_current_tool()                 # Execute optimization tools
plan_trip()                             # Main entry point for trip planning
```

**State Flow:**
```
Input Processing → Budget Allocation → Tool Execution → 
Budget Tracking → Result Combination → Output Formatting
```

### 2. State Management System (`state_manager.py`)

**Class: StateManager**

**Data Structure: TripState (TypedDict)**
```python
{
    original_query: str
    user_preferences: Dict[str, Any]
    total_budget: float
    remaining_budget: float
    currency: str
    dates: str
    from_location: str
    to_location: str
    travelers: int
    tool_sequence: List[str]
    current_step: int
    budget_allocation: Dict[str, float]
    spent_amounts: Dict[str, float]
    accommodation_result: str
    itinerary_result: str
    restaurant_result: str
    travel_result: str
    combined_result: str
    completed_tools: List[str]
    warnings: List[str]
    errors: List[str]
    retry_count: int
}
```

**Key Operations:**
- Budget allocation and tracking
- Tool execution sequence management
- State persistence and recovery
- Error and warning collection

### 3. Optimization Tools

#### A. Accommodation Planner (`AccommodationPlanner.py`)
**Function: search_accommodations()**
- **Input**: Natural language query with budget constraints
- **Processing**: LLM-based extraction of accommodation preferences
- **Output**: Structured accommodation recommendations with pricing

#### B. Itinerary Planner (`ItineraryPlanning.py`)
**Function: plan_itinerary()**
- **Input**: Destination, dates, budget, preferences
- **Processing**: Day-by-day schedule creation with Google Maps integration
- **Output**: Markdown table with Time|Activity|Details|Maps format

#### C. Restaurant Search (`RestaurantsSearch.py`)
**Function: search_restaurants()**
- **Input**: Itinerary details, dates, dietary preferences
- **Processing**: Location-based restaurant recommendations
- **Output**: Restaurant suggestions with cuisine types and pricing

#### D. Travel Optimization (`TravelOptimization.py`)
**Function: optimize_travel()**
- **Input**: Route requirements, budget, transport preferences
- **Processing**: Multi-modal transport analysis
- **Output**: Optimized travel routes with cost/time comparison

### 4. LLM-Based Preference Extraction

**System Prompt Structure:**
```
Role Definition → Task Specification → Output Format → 
Constraint Rules → Example Patterns → Validation Requirements
```

**Extraction Categories:**
- Budget and currency detection
- Date range parsing
- Location identification
- Traveler count analysis
- Priority routing determination

**Fallback Mechanism:**
- Primary: LLM-based extraction with structured prompts
- Fallback: Keyword-based pattern matching
- Error Handling: Default value assignment

### 5. Integration Layer

**Perplexity Service (`perplexity_service.py`)**
- **API Endpoint**: https://api.perplexity.ai/chat/completions
- **Authentication**: API key-based
- **Response Processing**: JSON parsing with error handling
- **Rate Limiting**: Built-in retry mechanisms

**Tool Orchestration (`__init__.py`)**
- Centralized tool imports
- Workflow management functions
- Error propagation and handling

### 6. Data Flow Architecture

**Request Processing Pipeline:**
```
1. Natural Language Query
   ↓
2. LLM Preference Extraction
   ↓
3. Budget Allocation
   ↓
4. Tool Routing & Execution
   ↓
5. State Tracking & Updates
   ↓
6. Result Aggregation
   ↓
7. Comprehensive Report Generation
```

**State Transition Model:**
```
INIT → INPUT_PROCESSING → BUDGET_ALLOCATION → 
TOOL_EXECUTION → BUDGET_TRACKING → RESULT_COMBINATION → 
OUTPUT_FORMATTING → COMPLETE
```

**Error Handling Strategy:**
- Tool-level error isolation
- State rollback capabilities
- Graceful degradation with warnings
- Comprehensive error logging

### User Input Template

#### Mandatory Fields
- **FROM**: Starting location of the trip. (e.g., Mumbai)
- **TO**: Destination location. (e.g., Goa)
- **NO OF DAYS**: Total duration of the trip in days. (e.g., 5)
- **BUDGET**: Total budget for the trip. (e.g., ₹20,000)
- **TIMELINE**: Preferred travel dates or period. (e.g., 1st Sep - 5th Sep)

#### Optional Fields
- **Mode of Transport**: Preferred transportation (flight, train, bus, car, etc.)
- **Stay Preferences**: Accommodation type (hotel, hostel, resort, etc.)

### Technical Stack
- **LangGraph (Agent)**: For agent-based workflow orchestration and advanced reasoning
- **LLM**: Claude or GPT models for itinerary generation and recommendations
- **Search**: Google Search or Perplexity for real-time travel information
- **Google Maps API / MapmyIndia API**: For route visualization, POI mapping, and location intelligence

---

# Example

**Step 1: User Input**

```To generate a personalized itinerary, the user must fill in the mandatory and optional parameters in the template.```

<img src="images/image-1.png" alt="User Input Screenshot" width="400" height="450" />


**Step 2: System Response**

```Once the required information is submitted, the system processes the input and returns an optimized itinerary in table format.```

![alt text](images/image.png)

## 🔧 Development & Testing

### Running Individual Tools

Test individual optimization tools:
```bash
# Test Accommodation Planner
python src/tools/optimization/AccommodationPlanner.py

# Test Itinerary Planner
python src/tools/optimization/ItineraryPlanning.py

# Test Restaurant Search
python src/tools/optimization/RestaurantsSearch.py

# Test Travel Optimization
python src/tools/optimization/TravelOptimization.py
```

### Configuration Files

**Requirements Management:**
- `src/requirements.txt`: Python dependencies
- `.env`: Environment variables (API keys)

**Agent Configuration:**
- `src/config/configurations.py`: System configurations
- `src/entity/config_entity.py`: Pydantic data models

### Project Structure
```
TripMazerResearch/
├── README.md
├── src/
│   ├── requirements.txt
│   ├── main.py
│   ├── agents/
│   │   └── worker/
│   │       └── trip_optimization_agent/
│   │           └── agent.py                 # Main agent orchestrator
│   ├── tools/
│   │   └── optimization/
│   │       ├── __init__.py                  # Tool registry
│   │       ├── AccommodationPlanner.py      # Hotel/stay search
│   │       ├── ItineraryPlanning.py         # Day-by-day planning
│   │       ├── RestaurantsSearch.py         # Dining recommendations
│   │       └── TravelOptimization.py        # Transport optimization
│   ├── state/
│   │   └── state_manager.py                 # State tracking system
│   ├── services/
│   │   └── perplexity_service.py           # LLM API service
│   ├── config/
│   │   └── configurations.py               # System settings
│   └── entity/
│       └── config_entity.py                # Data models
├── database/
│   └── schemas/                             # Database schemas
├── Documentation/
├── examples/
└── images/
```

## 📊 Example Usage

**Input Query:**
```
Plan a complete trip to Tokyo from Delhi for a couple from 25-12-2025 to 30-12-2025 
with budget $3000. We prefer temples, traditional experiences, and good food. 
We want comfortable accommodation and prefer trains over flights when possible.
```

**System Processing:**
1. **LLM Preference Extraction**: Identifies budget ($3000), travelers (2), preferences (temples, food)
2. **Intelligent Routing**: Prioritizes itinerary → travel → accommodation → restaurant
3. **Budget Allocation**: Distributes budget across tools (35% accommodation, 30% travel, 20% itinerary, 15% restaurant)
4. **Tool Execution**: Executes tools in priority order with budget constraints
5. **Result Combination**: Generates comprehensive markdown report

**Output Features:**
- Executive summary with budget breakdown
- Day-by-day itinerary tables
- Transportation optimization analysis
- Accommodation recommendations with pricing
- Restaurant suggestions based on itinerary locations
- Budget utilization tracking

---

# Example

**Step 1: User Input**

```To generate a personalized itinerary, the user must fill in the mandatory and optional parameters in the template.```

<img src="images/image-1.png" alt="User Input Screenshot" width="400" height="450" />


**Step 2: System Response**

```Once the required information is submitted, the system processes the input and returns an optimized itinerary in table format.```

![alt text](images/image.png)

---

## 🚀 Future Enhancements
- Support for multi-city trips
- Integration with booking APIs
- Real-time budget tracking
- User feedback and rating system
- Mobile application interface
- Advanced ML-based preference learning
- Integration with payment gateways
- Social sharing and collaboration features

---

## ⚠️ Limitations
- Dependent on accuracy of external APIs
- Budget estimates may vary
- Limited to supported locations and transport modes
- Requires stable internet connection for real-time data
- API rate limits may affect performance

---

## 🤝 Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

---

## 📞 Support
For questions or support, please open an issue in the GitHub repository or contact the development team.

---

**Built with ❤️ using LangGraph, LangChain, and Perplexity AI**
