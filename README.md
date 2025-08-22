# Tripmazer

## 1. Travel Budget Optimization

### Overview
Tripmazer is an intelligent travel planning system that helps users optimize their travel budget and itinerary using AI and mapping technologies.

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

### Process Flow
1. User fills the template with mandatory and optional fields
2. LLM generates an initial itinerary based on user input
3. Search APIs enrich the itinerary with real-time data
4. Mapping APIs add location and route details
5. Final output is presented in a table format

---

# Example

**Step 1: User Input**

```To generate a personalized itinerary, the user must fill in the mandatory and optional parameters in the template.```

<img src="images/image-1.png" alt="User Input Screenshot" width="400" height="450" />


**Step 2: System Response**

```Once the required information is submitted, the system processes the input and returns an optimized itinerary in table format.```

![alt text](images/image.png)

---

### Future Enhancements
- Support for multi-city trips
- Integration with booking APIs
- Real-time budget tracking
- User feedback and rating system

---

### Limitations
- Dependent on accuracy of external APIs
- Budget estimates may vary
- Limited to supported locations and transport modes

---
