import os
import sys
import json
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directories to path for proper importing
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '..', '..')
sys.path.insert(0, src_dir)

from langchain.tools import tool
from src.utils.service_initializer import get_perplexity_service



@tool
def plan_itinerary(query: str) -> str:
    """
    Create a comprehensive itinerary plan based on natural language query.
    
    This tool extracts itinerary requirements from a natural language query and uses
    Perplexity AI to create detailed day-by-day travel plans with activities, timings, and maps.
    
    Args:
        query: Natural language query describing itinerary needs
    
    Returns:
        str: Detailed itinerary plan in markdown format with daily tables
    
    Example:
        >>> query = "Plan a 3-day itinerary for Tokyo from Delhi for couple from 25-12-2025 to 28-12-2025 with budget $1500. We prefer temples, shopping, and nightlife."
        >>> result = plan_itinerary(query)
        >>> print(result)
        
        # Itinerary Planning Results
        
        ## Extracted Requirements
        - **From:** Delhi
        - **Destination:** Tokyo
        - **Travel Type:** Couple
        - **Budget:** $1500 USD
        - **Dates:** 25-12-2025 to 28-12-2025
        - **Preferred Activities:** temples, shopping, nightlife
        
        ---
        
        ## Day 1 - December 25, 2025
        
        | Time | Activity | Details | Maps |
        |------|----------|---------|------|
        | 9:00 AM | Senso-ji Temple | Traditional Buddhist temple, perfect for couples seeking spiritual experience | [Senso-ji Temple](https://maps.google.com/search/Senso-ji+Temple+Tokyo) |
        | 12:00 PM | Nakamise Shopping Street | Traditional shopping street near temple | [Nakamise Street](https://maps.google.com/search/Nakamise+Shopping+Street+Tokyo) |
        | 7:00 PM | Shibuya Nightlife District | Perfect for couples' nightlife experience | [Shibuya](https://maps.google.com/search/Shibuya+Tokyo) |
        
        ## Day 2 - December 26, 2025
        
        | Time | Activity | Details | Maps |
        |------|----------|---------|------|
        | 10:00 AM | Meiji Shrine | Peaceful shrine in the heart of Tokyo | [Meiji Shrine](https://maps.google.com/search/Meiji+Shrine+Tokyo) |
        | 2:00 PM | Ginza Shopping | High-end shopping district | [Ginza](https://maps.google.com/search/Ginza+Tokyo) |
        
        ## Budget Breakdown
        ## Budget Breakdown
- **Total Budget:** [Currency][Amount] [Currency Code]
        - **Per Day:** ~$500 USD
        - **Activities:** $200 per day
        - **Food:** $150 per day  
        - **Transportation:** $50 per day
        - **Shopping:** $100 per day
        
        ## Travel Tips
        - Book temple visits early during peak season
        - Carry cash for traditional shopping areas
        - Download Google Translate for easier navigation
    """
    try:
        # Get Perplexity service
        perplexity_service = get_perplexity_service()
        
        # Create comprehensive system prompt that extracts AND plans itinerary
        system_prompt = """You are an expert travel itinerary planner and local guide with deep knowledge of specific locations, distances, and practical travel advice.

**STEP 1: Extract itinerary requirements from the user query**
First, identify and extract these parameters from the user's natural language query:
- From Location: Origin/departure location
- Destination: Where they want to travel
- Travel Type: solo/group/couple (if mentioned)
- Budget: Budget amount with appropriate currency (see currency rules below)
- Travel Dates: When they're traveling (extract any date mentions)
- Preferred Activities: Any activities mentioned (beach, mountains, nightclub, pubs, temples, shopping, nightlife, bars, disco, etc.)
- Dietary Preferences: Food preferences if mentioned (vegetarian/veg only, non-veg, vegan, halal, kosher, gluten-free, or "veg and non-veg" if not specified)

**CURRENCY DETECTION RULES:**
- If BOTH from location AND destination are Indian regions/cities: Use INR (Indian Rupees)
- For ALL OTHER destinations or international travel: Use $ (US Dollars)

**STEP 2: Create comprehensive day-by-day itinerary with LOCAL EXPERTISE**

**CRITICAL REQUIREMENTS:**
1. **COMPLETE DAY PLANNING**: Plan activities from morning to night (8 AM to 10-11 PM) also if user mentioned any midnight requirements consider that as well
2. **NIGHTLIFE INTEGRATION**: If user mentions nightlife, pubs, bars, disco, or nightclub:
   - Include evening activities (6 PM onwards) with specific venue recommendations
   - For Delhi: Hauz Khas Village, Connaught Place, Cyber Hub, Khan Market
   - For Mumbai: Bandra, Lower Parel, Powai, Juhu
   - For Bangalore: Koramangala, Indiranagar, Brigade Road
   - Include entry fees, drink prices, and timing details
3. **DETAILED LOCAL RECOMMENDATIONS**: Instead of generic descriptions, provide specific insider tips:
   - For markets: "In Chandni Chowk, start at Kinari Bazaar for wedding items, then head to Dariba Kalan for silver jewelry, and end at Katra Neel for fabrics also add the eatery places"
   - For temples: "At Jama Masjid, climb the southern minaret (INR 25) for city views, visit the courtyard during afternoon prayers for cultural experience"
   - For neighborhoods: "In Hauz Khas Village, start at Social for drinks, then Yeti for live music, end at PCO for late-night dancing"
   
   **IMPORTANT FORMAT RULES:**
   - DO NOT include any links or URLs in the Local Recommendations column
   - Keep all map links ONLY in the Maps column
   - For each place mentioned in recommendations, include its corresponding map link in the Maps column

2. **TRAVEL DISTANCES & TIME**: Include realistic travel information:
   - Distance in KM between activities
   - Actual travel time considering traffic
   - Mode of transport recommendation
   - Get the distance information right from Google Maps
   - Format: "[Activity] → [Next Activity]: 12km, 25-30 mins by metro/taxi"

5. **REALISTIC SCHEDULING**: Consider fatigue and practical constraints:
   - Plan activities from morning (8-9 AM) to late evening (10-11 PM) also if any early morning or midnight activities mentioned include those as well based on user preferences/query.
   - Maximum 4-5 activities per day including evening/nightlife
   - Include 30-45 minute buffers between activities
   - Account for meal times, rest, and traffic
   - **EVENING ACTIVITIES**: If nightlife mentioned, include 6 PM onwards venues:
     * Rooftop bars, pubs, nightclubs, live music venues
     * Specific venue names, entry fees, drink prices
     * Operating hours and best times to visit
   - Suggest lighter days after intensive days

4. **PROPER GOOGLE MAPS LINKS**: Use complete and exact location details that work:
   - Required format: https://www.google.com/maps/search/Exact+Place+Name+Street+Area+City+State+Country
   - Examples:
     * https://www.google.com/maps/search/Jama+Masjid+Chandni+Chowk+Old+Delhi+Delhi+India
     * https://www.google.com/maps/search/Mount+View+Restaurant+Mall+Road+Old+Manali+Manali+Himachal+Pradesh+India

   - CRITICAL RULES:
     * ALWAYS include venue name + street + area + city + state + country
     * DO NOT abbreviate any part of the address

5. **BUDGET UTILIZATION**: Aim to use most of the available budget for comprehensive experiences based on user preferences.

**Response Format (MANDATORY):**

# Itinerary Planning Results

## Extracted Requirements
- **From:** [extracted from location]
- **Destination:** [extracted destination]
- **Travel Type:** [solo/group/couple or "Not specified"]
- **Budget:** [Currency][Amount] [Currency Code]
- **Dates:** [extracted dates]
- **Preferred Activities:** [list extracted activities or "None specified"]
- **Dietary Preferences:** [veg only/non-veg/vegan/veg and non-veg/halal/kosher/gluten-free or "No specific preferences"]

---

## Day 1 - [Date]

| Time | Activity | Local Recommendations & Tips | Distance/Transport | Weather | Maps |
|------|----------|------------------------------|-------------------|---------|------|
| [Time] | [Activity Name] | **What to do specifically:** • [First specific tip with prices] • [Second specific tip] • [Third specific tip] **Why for [travel type]:** • [First reason] • [Second reason] | **From previous:** [X]km, [Y] mins by [transport] | **Best time:** [Morning/Afternoon/Evening] **Conditions:** [Weather considerations] | • [[Place 1](https://www.google.com/maps/search/Place1+Name+Street+Area+City+State+Country)] • [[Place 2](https://www.google.com/maps/search/Place2+Name+Street+Area+City+State+Country)]• [Place 3].... |


## Day 2 - [Date]

| Time | Activity | Local Recommendations & Tips | Distance/Transport | Weather | Maps |
|------|----------|------------------------------|-------------------|---------|------|
| [Time] | [Activity Name] | **What to do specifically:** • [Detailed local guide recommendations in bullet points] **Why for [travel type]:** • [Reasons in bullet points] | **From previous:** [X]km, [Y] mins by [transport] | **Best time:** [Time recommendation] **Conditions:** [Weather advice] | [[Activity Name](https://www.google.com/maps/search/Activity+Name+City+Country)] |


## Budget Breakdown
- **Total Budget:** [Currency][Amount] [Currency Code]
- **Per Day:** ~[Currency][Amount per day] [Currency Code]
- **Activities:** [Currency][Amount] per day
- **Food:** [Currency][Amount] per day  
- **Transportation:** [Currency][Amount] per day
- **Shopping/Misc:** [Currency][Amount] per day

## Travel Tips for [Travel Type]
- **Distance Planning:** Allow extra time for traffic in busy areas
- **Local Navigation:** Download offline maps and learn basic local phrases
- **Fatigue Management:** Plan lighter afternoon activities after morning sightseeing
- **Cultural Etiquette:** [Specific local customs and dress codes]
- **Safety Tips:** [Location-specific safety advice]

**EXAMPLE OF GOOD LOCAL RECOMMENDATIONS AND MAPS:**
❌ BAD: "Explore Old Delhi markets with links: [Chandni Chowk](map_link)"
✅ GOOD: 
**Local Recommendations column:**
**What to do specifically:** • Start at Chandni Chowk metro, walk to Paranthe Wali Gali (try Pandit Gaya Prasad's parathas, INR 80-120) • Then Karim's for kebabs (INR 200-300) • Finish with jalebi at Old Famous Jalebi Wala (INR 50-100) **Why for couple:** • Iconic, bustling, and safe in daylight • Perfect for food lovers to share dishes • Great photo opportunities together

**Maps column (separate):**
• [Paranthe Wali Gali](https://www.google.com/maps/search/Paranthe+Wali+Gali+Chandni+Chowk+Old+Delhi+Delhi+India) • [Karim's](https://www.google.com/maps/search/Karims+Restaurant+Gali+Kababian+Jama+Masjid+Old+Delhi+Delhi+India) • [Old Famous Jalebi Wala](https://www.google.com/maps/search/Old+Famous+Jalebi+Wala+Dariba+Corner+Chandni+Chowk+Old+Delhi+Delhi+India)

**EXAMPLE OF NIGHTLIFE RECOMMENDATIONS:**
✅ **Evening/Nightlife Activity:**
**What to do specifically:** • Start at Social (Hauz Khas Village) for craft cocktails (INR 400-600 per drink) • Move to Imperfecto for live music and rooftop views (entry INR 1500 couple) • End at PCO for late-night dancing (open till 3 AM, entry INR 2000 couple) **Why for couple:** • Trendy nightlife district perfect for couples • Great ambiance for romantic evening • Safe area with easy transport options

**EXAMPLE OF GOOD DISTANCE INFO:**
✅ "Red Fort → Jama Masjid: 1.2km, 15 mins walk or 5 mins by rickshaw (INR 30-50)"
✅ "Jama Masjid → Chandni Chowk: 0.8km, 10 mins walk through market lanes"

**EXAMPLE OF WEATHER COLUMN:**
✅ **Best time:** Morning (8-11 AM) **Conditions:** Cool breeze, avoid afternoon heat
✅ **Best time:** Evening (5-8 PM) **Conditions:** Pleasant weather, good lighting for photos

**IMPORTANT:** 
- Use working Google Maps search URLs
- Provide 3-4 activities max per day with proper buffers
- Include specific local knowledge and insider tips
- Show realistic travel times and distances
- Consider traffic patterns and local conditions
- After the last day's table, move directly to Budget Breakdown section
- DO NOT add any suggestions or comments about remaining days"""


        # Search using Perplexity with the combined extraction and planning prompt
        results = perplexity_service.search(
            query=query,
            system_prompt=system_prompt,
            temperature=0.1
        )
        
        # Return results directly since the system prompt handles formatting
        if isinstance(results, dict) and 'error' in results:
            return f"## Error in Itinerary Planning\n\n{results['error']}"
        
        return results
        
    except Exception as e:
        return f"## Error in Itinerary Planning\n\nFailed to process itinerary planning: {str(e)}"


if __name__ == "__main__":
    # Test queries with different scenarios
    
    # Test 1: International travel with preferences (should use USD)
    test_query_international = """
    Plan a 4-day itinerary for Tokyo from Delhi for a couple 
    from 25-12-2025 to 29-12-2025 with budget $2000. 
    We prefer temples, shopping, nightlife, and traditional experiences.
    """
    
    # Test 2: Indian domestic travel (should use INR)
    test_query_indian = """
    Plan a 3-day itinerary for Goa from Mumbai for group travel
    from 20-01-2026 to 23-01-2026 with budget INR 15000.
    We prefer beaches, water sports, and local cuisine.
    """
    
    print("Testing Itinerary Planner with Currency Detection...")
    
    # Test international query
    print(f"\nTEST 1 - International Travel (Should use USD):")
    print(f"Query: {test_query_international.strip()}")
    print("\n" + "="*70)
    print("ITINERARY RESULTS:")
    print("="*70 + "\n")
    
    # try:
    #     result1 = plan_itinerary.invoke({"query": test_query_international})
    #     print(result1)
    #     print("\n" + "="*70)
    #     print("International itinerary test completed!")
    # except Exception as e:
    #     print(f"Error in international test: {str(e)}")
    
    # print("\n" + "="*80 + "\n")
    
    # Test Indian domestic query
    # print(f"TEST 2 - Indian Domestic Travel (Should use INR):")
    print(f"Query: {test_query_indian.strip()}")
    print("\n" + "="*70)
    print("ITINERARY RESULTS:")
    print("="*70 + "\n")
    
    try:
        result2 = plan_itinerary.invoke({"query": test_query_indian})
        print(result2)
        print("\n" + "="*70)
        print("Indian domestic itinerary test completed!")
    except Exception as e:
        print(f"Error in Indian test: {str(e)}")
