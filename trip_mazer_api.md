# TripOptimizer Agent approach
    USER QUERY
        ↓
┌───────────────────────────┐
│  1. INPUT PROCESSOR       │ → Gemini extracts preferences
└───────────────────────────┘
        ↓
┌───────────────────────────┐
│  2. BUDGET ALLOCATOR      │ → Gemini allocates budget %
└───────────────────────────┘
        ↓
    ┌───────────────────────┐
    │  3. TOOL EXECUTOR     │ ← LOOPS HERE
    │  (Itinerary/Travel/   │
    │   Accommodation)      │
    └───────────────────────┘
        ↓
┌───────────────────────────┐
│  4. BUDGET TRACKER        │ → Track & reallocate
└───────────────────────────┘
        ↓
    ┌─────────────┐
    │  Continue?  │ ─Yes─→ (back to TOOL EXECUTOR)
    └─────────────┘
        │ No
        ↓
┌───────────────────────────┐
│  6. RESULT COMBINER       │ → Combine all results
└───────────────────────────┘
        ↓
┌───────────────────────────┐
│  7. OUTPUT FORMATTER      │ → Format final output
└───────────────────────────┘
        ↓
    FINAL RESULT
    
## Contents

- [MakeMyTrip API](https://mybiz.makemytrip.com/integrated-travel-solutions/travel-request-api?ef_id=Cj0KCQjwwZDFBhCpARIsAB95qO1Zjq0vB1EfOHHFP5K3ZWhhTHQ69j-7nDpmKShQHChFcXNfk7XldpIaAiysEALw_wcB:G:s&gad_source=1&gad_campaignid=20574983470&gbraid=0AAAAADI4eVPGqdPjNExcBwOS6_1B7naOt&gclid=Cj0KCQjwwZDFBhCpARIsAB95qO1Zjq0vB1EfOHHFP5K3ZWhhTHQ69j-7nDpmKShQHChFcXNfk7XldpIaAiysEALw_wcB)
- [Agoda API](https://www.agodaconnectivity.com/documentation)
- [Booking.com API](#bookingcom-api)
- Additional information

---

## MakeMyTrip API

Website link: [MakeMyTrip API](https://mybiz.makemytrip.com/integrated-travel-solutionshttps://mybiz.makemytrip.com/integrated-travel-solutions/travel-request-api?ef_id=Cj0KCQjwwZDFBhCpARIsAB95qO1Zjq0vB1EfOHHFP5K3ZWhhTHQ69j-7nDpmKShQHChFcXNfk7XldpIaAiysEALw_wcB:G:s&gad_source=1&gad_campaignid=20574983470&gbraid=0AAAAADI4eVPGqdPjNExcBwOS6_1B7naOt&gclid=Cj0KCQjwwZDFBhCpARIsAB95qO1Zjq0vB1EfOHHFP5K3ZWhhTHQ69j-7nDpmKShQHChFcXNfk7XldpIaAiysEALw_wc)

## Overview

MakeMyTrip does **not provide a public B2C developer API**.Instead, it offers B2B APIs under the **myBiz** corporate travel program and a **myPartner** portal for travel agents.

- **B2C Support:** ❌ No public/open API for consumers.
- **B2B Support:** ✅ Available via myBiz (corporates) and myPartner (agents).

  - **myBiz Travel Request API**: Push approved travel requests (flights, hotels) from your system into MMT’s corporate booking flow.
  - **myPartner**: Web portal for travel agents (not an API).
- **Flight Booking**
- **Hotel Booking & Details**
- **User Login / Authentication**

## How to Get Access to MakeMyTrip API
Need to register through MMT’s business partnerships team
[MakeMyTrip partership link](https://mybiz.makemytrip.com/?signup=true&cmp=SEM|D|Corporate|G|Brand|MMT_Corporate_BMM|Brand_BMM_B2B|RSA|Regular&ef_id=Cj0KCQjwwZDFBhCpARIsAB95qO2zpcwCkMneTAiKmAAV0pbTyR9Xpm4JcAxP0NEfog463H5ZTZYsknEaAsRVEALw_wcB:G:s&gad_source=1&gad_campaignid=912555988&gclid=Cj0KCQjwwZDFBhCpARIsAB95qO2zpcwCkMneTAiKmAAV0pbTyR9Xpm4JcAxP0NEfog463H5ZTZYsknEaAsRVEALw_wcB)


### Documentation / Code Examples

API reference: 
[MakeMyTrip Flight API](https://mybiz.makemytrip.com/integrated-travel-solutions/travel-request-api)





## Agoda API

Website link: [Agoda Partner Hub](https://partners.agoda.com)

## Overview

Agoda does not provide a **public B2C API**, but supports multiple **B2B integrations** for affiliates and hospitality partners.
Agoda does not provide any official API's for flight bookings. Currently, only hotel bookings are supported for B2B integrations.

- **B2C Support:** ❌ No open API for general consumers.
- **B2B Support:** ✅ Supported through Affiliate and Connectivity APIs:
  - **Affiliate API (Lite / Search API):** Lets partners access hotel listings, rates, and booking deep-links for monetization.
  - **Connectivity (YCS5 API):** For hotels, channel managers, and PMS systems to update rates, availability, content, and manage reservations.
- **Hotel Content / Pricing Search**
- **Reservation Management**
- **Property Onboarding & Content Push**

## How to Get Access to Agoda API
- Register as an **Affiliate Partner** or **Accommodation Partner** via the Agoda Partner Hub.  
- Affiliates receive an **API key** and site ID.  
- Hotels and PMS/Channel managers must apply for **Connectivity API access**.  
[Agoda Affiliate Account Manager](https://partners.agoda.com/DeveloperPortal/APIDoc/ContactUs)

### Documentation / Code Examples
API reference: [Agoda Connectivity for hotel booking Documentation](https://developer.agoda.com/supply/reference/where-to-start)


## Booking.com API

Website link: [Booking.com Developer Portal](https://developers.booking.com)

## Overview

Booking.com does **not provide a public B2C developer API**. Instead, it supports **B2B integrations** tailored to agencies, property management systems, and affiliates.

- **B2C Support:** ❌ No open API for general consumers.
- **B2B Support:** ✅ Available through controlled, partner-only programs. (This API can be used for B2C solutions through partner programs.)  

  - **Connectivity APIs:** For channel managers and PMS providers to manage properties (availability, rates, reservations, promotions, messaging, guest reviews, payments, and more).
  - **Demand API:** For affiliate and travel platforms, enabling integration of Booking.com’s inventory and booking capabilities.

- **Supported verticals (live):**
  - Hotel *Accommodation & Booking*
  - Car Rentals (limited pilot access)

- **Planned future verticals (“coming soon”):**
  - Flights
  - Attractions
  - Airport Taxis

## How to Get Access to Booking.com API

- **Connectivity API:** Requires joining the **Booking.com Connectivity Partner Program**.
- **Demand API:** Requires approval as a **Managed Affiliate Partner**.
- **Individual property owners** cannot access APIs directly—they must use a channel manager or PMS.

[Booking.com Connectivity Partner Link](https://www.booking.com/affiliate-program/v2/index.html)  
[Booking.com Affiliate Partner Link](https://www.booking.com/affiliate-program/v2/index.html)  


## Documentation / Code Examples

- **Connectivity API Documentation:**  
  Contains tutorials like "Create a test property" and "Create a test reservation", plus detailed endpoint references for property, rooms, rates & availability, reservations, messaging, reports, and more.
  [Booking.com Connectivity API Link](https://developers.booking.com/connectivity/docs)

- **Demand API Documentation:**  
  Includes REST-style endpoints for Accommodation, Car Rentals (pilot), Orders, Locations, Payments, Languages, and messaging. Flights (and other verticals) are **not yet available**, but are planned for future release. 
  [Booking.com Affiliate/Demand API Link](https://developers.booking.com/demand/docs)



## Additional information

No official API support for Goibibo and Ixigo. API's are available through third party website [Adivaha API Link](https://www.adivaha.com/ixigo-api-integration.html)



# OpenAI Computer-Using Agent (CUA)

## 1. Overview
The **Computer-Using Agent (CUA)** is a model that allows AI to interact with graphical user interfaces (GUIs) in a human-like way—clicking, typing, navigating, and self-correcting. It underpins OpenAI’s **Operator** and the newer **ChatGPT Agent**.  
Instead of relying on app-specific APIs, CUA operates in a virtual display and works through vision, reasoning, and reinforcement learning.  

**Benchmarks:**  
- **38.1%** on OSWorld (computer-level tasks)  
- **58.1%** on WebArena (web tasks)  
- **87%** on WebVoyager (web browsing tasks)  
([OpenAI](https://openai.com/index/computer-using-agent/?utm_source=chatgpt.com))

---

## 2. Requirements to Get Access
- **Operator / ChatGPT Agent:** Available to **Pro-tier users** in the U.S., with rollout planned for Plus, Team, and later Enterprise/Education.  
([OpenAI](https://openai.com/index/computer-using-agent/?utm_source=chatgpt.com), [ITPro](https://www.itpro.com/technology/artificial-intelligence/everything-you-need-to-know-about-openais-new-agent-for-chatgpt-including-how-to-access-it-and-what-it-can-do?utm_source=chatgpt.com))  
- **Responses API (computer-use-preview):** Developers in usage tiers 3–5 can access via the Responses API & Agents SDK.  
([OpenAI Docs](https://platform.openai.com/docs/guides/tools-computer-use?utm_source=chatgpt.com))  
- **Tier 3** access can be acquired by depositing $100 paid and 7+ days since first successful payment

---

## 3. Pricing
- **OpenAI API (Responses API):** Token-based pricing: **$3 per 1M input tokens**, **$12 per 1M output tokens**.  
([OpenAI Pricing](https://platform.openai.com/docs/pricing?utm_source=chatgpt.com))  


---

## 4. Sample Python Code

### OpenAI API
```python
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.responses.create(
    model="computer-use-preview",
    tools=[{
        "type": "computer_use_preview",
        "display_width": 1024,
        "display_height": 768,
        "environment": "browser"
    }],
    input=[{"role": "user", "content": "Check the latest AI news on bing.com"}],
    truncation="auto"
)

print(response)
