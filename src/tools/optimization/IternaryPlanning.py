import os
import sys
import json
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directories to path for proper importing
if __name__ == "__main__":
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

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
        - **Total Budget:** ₹125000 INR
        - **Per Day:** ~₹42000 INR
        - **Activities:** ₹17000 per day
        - **Food:** ₹12000 per day  
        - **Transportation:** ₹4000 per day
        - **Shopping:** ₹9000 per day
        
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

**STEP 1: Extract itinerary requirements from the user query (INTERNAL - DO NOT SHOW IN OUTPUT)**
First, identify and extract these parameters from the user's natural language query (FOR YOUR UNDERSTANDING ONLY, DO NOT PRINT THIS):
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

**IMPORTANT: Start DIRECTLY with Day 1. Do NOT include any "Extracted Requirements" or summary section.**

## Day 1 - [Date]

| Time | Activity | Local Recommendations & Tips | Distance/Transport | Weather | Maps |
|------|----------|------------------------------|-------------------|---------|------|
| [Time] | [Activity Name] | **What to do specifically:**<br>• [Very detailed first tip with specific prices, timings, contact info, and insider knowledge]<br>• [Very detailed second tip with practical information, alternatives, and local secrets]<br>• [Additional detailed tips as needed - not mandatory to have exactly 3, can be 2-4 based on activity complexity] | **From previous:** [X]km, [Y] mins by [transport] | **Best time:** [Morning/Afternoon/Evening]<br>**Conditions:** [Weather considerations] | [[Activity Name](https://www.google.com/maps/search/Activity+Name+City+Country)] |


## Day 2 - [Date]

| Time | Activity | Local Recommendations & Tips | Distance/Transport | Weather | Maps |
|------|----------|------------------------------|-------------------|---------|------|
| [Time] | [Activity Name] | **What to do specifically:**<br>• [Comprehensive first recommendation with all necessary details]<br>• [Comprehensive second recommendation with practical insights]<br>• [Add more recommendations only if the activity warrants detailed guidance] | **From previous:** [X]km, [Y] mins by [transport] | **Best time:** [Time recommendation]<br>**Conditions:** [Weather advice] | [[Activity Name](https://www.google.com/maps/search/Activity+Name+City+Country)] |


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
**What to do specifically:**<br>• Start at Chandni Chowk metro (₹10 entry), walk 5 mins to Paranthe Wali Gali - try Pandit Gaya Prasad's parathas (₹80-120 each, 6 varieties available, open 7 AM-11 PM, cash only). Best parathas: Aloo, Gobhi, Paneer<br>• Visit Karim's for authentic Mughlai kebabs (₹200-300 per plate, established 1913, try Mutton Burra and Chicken Jehangiri, open 11 AM-11 PM, accepts cards). Get there early to avoid 30-min wait times

**EXAMPLE OF SIMPLE ACTIVITY (2 recommendations):**
✅ **Temple Visit:**
**What to do specifically:**<br>• Entry free, remove shoes at entrance, photography allowed in courtyard only (₹20 for camera inside). Best time: 6-8 AM for morning prayers and fewer crowds<br>• Local prasad shop outside sells coconut, flowers (₹50 combo), and temple guides available (₹100-200 for 30-min tour in Hindi/English)

**EXAMPLE OF COMPLEX ACTIVITY (4 recommendations):**
✅ **Trekking Activity:**
**What to do specifically:**<br>• Start early at 6 AM from base camp (₹50 parking), carry 2L water per person, trek takes 2-3 hours, difficulty: moderate. Rental shoes available (₹100/day) at Sharma Trekking Shop near parking<br>• Hire local guide Ravi (+91-98765-43210, ₹500/group, knows secret photo spots), he provides walking sticks and basic first aid. Speaks English, Hindi, local dialect<br>• Pack light snacks from village shop (₹200 for trail mix, bananas, energy bars), no food available on trek. Mobile network available only at start and peak<br>• Weather changes quickly - carry light rain jacket (available for rent ₹100/day), wear layers, avoid monsoon season (July-Sept). Best months: Oct-March

**EXAMPLE OF GOOD DISTANCE INFO:**
✅ "Red Fort → Jama Masjid: 1.2km, 15 mins walk or 5 mins by rickshaw (INR 30-50)"
✅ "Jama Masjid → Chandni Chowk: 0.8km, 10 mins walk through market lanes"

**EXAMPLE OF WEATHER COLUMN:**
✅ **Best time:** Morning (8-11 AM)<br>**Conditions:** Cool breeze, avoid afternoon heat
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
    
    # Test 1: International travel with preferences (should use INR)
    test_query_international = """
    Plan a 4-day itinerary for Tokyo from Delhi for a couple 
    from 25-12-2025 to 29-12-2025 with budget ₹165000. 
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
    print(f"\nTEST 1 - International Travel (Should use INR):")
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
