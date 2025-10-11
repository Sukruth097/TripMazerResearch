#!/usr/bin/env python3

# Quick test to demonstrate the new table formatting
def test_format_demonstration():
    print("🧪 DEMONSTRATING NEW TABLE FORMAT")
    print("="*80)
    
    # Mock flight results (SerpAPI format)
    mock_flight_results = """# ✈️ Flight Search Results (SERP API)

## Outbound Journey (2025-02-10)

| Option | Mode   | Flight/Route Details | Duration | Cost per Person | Total Cost | Booking Platform | Departure/Arrival (IST) |
|--------|--------|---------------------|----------|-----------------|------------|------------------|-------------------------|
| 1 | Flight | **Air India AI-131** | 2h 30m | INR 8,500 | INR 17,000 | SerpAPI | 08:00 - 10:30 |
| 2 | Flight | **IndiGo 6E-345** | 2h 25m | INR 7,200 | INR 14,400 | SerpAPI | 14:00 - 16:25 |

## Return Journey (2025-02-15)

| Option | Mode   | Flight/Route Details | Duration | Cost per Person | Total Cost | Booking Platform | Departure/Arrival (IST) |
|--------|--------|---------------------|----------|-----------------|------------|------------------|-------------------------|
| 1 | Flight | **Air India AI-132** | 2h 35m | INR 9,200 | INR 18,400 | SerpAPI | 18:00 - 20:35 |
| 2 | Flight | **IndiGo 6E-346** | 2h 30m | INR 8,100 | INR 16,200 | SerpAPI | 12:00 - 14:30 |"""

    # Mock ground transport results (Perplexity format) 
    mock_ground_results = """Here are comprehensive ground transportation options combining buses and trains:

| Option | Mode | Route Details | Duration | Cost per Person | Total Cost | Booking Platform | Departure/Arrival |
|--------|------|---------------|----------|-----------------|------------|------------------|-------------------|
| 1 | Train | Rajdhani Express (AC 2-Tier) | 16h 30m | ₹3,800 | ₹7,600 | IRCTC | 16:00 - 08:30 |
| 2 | Bus | Volvo AC Sleeper | 18h 00m | ₹2,500 | ₹5,000 | RedBus | 20:00 - 14:00 |
| 3 | Train | August Kranti (AC 3-Tier) | 17h 15m | ₹2,900 | ₹5,800 | IRCTC | 17:30 - 10:45 |
| 4 | Bus | Mercedes Luxury Sleeper | 19h 30m | ₹3,200 | ₹6,400 | MakeMyTrip | 19:00 - 14:30 |
| 5 | Train | Mumbai Express (Sleeper) | 20h 45m | ₹1,800 | ₹3,600 | IRCTC | 22:00 - 18:45 |"""

    # Demonstrate the new hybrid format
    print("📋 NEW FORMAT: Separate Flight Table + Combined Bus/Train Table")
    print("="*80)
    
    hybrid_result = f"""# 🌟 Hybrid Travel Optimization Results

## ✈️ Flight Options (Live Pricing)
{mock_flight_results}

## 🚌🚂 Buses & Trains Options (Ground Transport)
{mock_ground_results}

---

## 💡 Travel Options Summary
- **Flight Options**: Live pricing data from SerpAPI for accurate flight costs (displayed in separate table above)
- **Ground Transport**: Comprehensive buses and trains options from Perplexity (combined in one table above)
- **Decision Logic**: Natural language understanding determines when to include flights
- **Optimization**: Smart API usage - flights only searched when budget and preferences support it"""

    print(hybrid_result)
    
    print("\n" + "="*80)
    print("✅ FORMAT ANALYSIS:")
    print("1. ✅ Flights: Separate table with live SerpAPI pricing")
    print("2. ✅ Ground Transport: Single combined table for buses AND trains")
    print("3. ✅ Clear section headers with emoji indicators")
    print("4. ✅ Consistent table structure across both sections")
    print("5. ✅ Summary section explaining the dual approach")

if __name__ == "__main__":
    test_format_demonstration()