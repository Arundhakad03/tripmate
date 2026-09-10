import os
import requests
from dotenv import load_dotenv
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import Optional
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_tavily import TavilySearch
from datetime import date

load_dotenv()


llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.2,
)


DUFFEL_API_KEY = os.getenv("DUFFEL_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")


DUFFEL_BASE_URL = "https://api.duffel.com/air"
DUFFEL_STAYS_URL = "https://api.duffel.com/stays"


IRCTC_HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": "irctc1.p.rapidapi.com",
}


HEADERS = {
    "Authorization": f"Bearer {DUFFEL_API_KEY}",
    "Duffel-version": "v2",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


CITY_TO_IATA = {
    "indore": "IDR",
    "goa": "GOI",
    "mumbai": "BOM",
    "delhi": "DEL",
    "bangalore": "BLR",
    "bengaluru": "BLR",
    "chennai": "MAA",
    "kolkata": "CCU",
    "hyderabad": "HYD",
    "pune": "PNQ",
    "jaipur": "JAI",
    "ahmedabad": "AMD",
    "lucknow": "LKO",
    "kochi": "COK",
    "chandigarh": "IXC",
}

CITY_TO_COORDS = {
    "indore": (22.7196, 75.8577),
    "goa": (15.2993, 74.1240),
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.7041, 77.1025),
    "bangalore": (12.9716, 77.5946),
    "bengaluru": (12.9716, 77.5946),
    "chennai": (13.0827, 80.2707),
    "kolkata": (22.5726, 88.3639),
    "hyderabad": (17.3850, 78.4867),
    "pune": (18.5204, 73.8567),
    "jaipur": (26.9124, 75.7873),
    "ahmedabad": (23.0225, 72.5714),
    "lucknow": (26.8467, 80.9462),
    "kochi": (9.9312, 76.2673),
    "chandigarh": (30.7333, 76.7794),
}

CITY_TO_STATION_CODE = {
    "indore": "INDB",
    "goa": "MAO",
    "mumbai": "CSTM",
    "delhi": "NDLS",
    "bangalore": "SBC",
    "bengaluru": "SBC",
    "chennai": "MAS",
    "kolkata": "HWH",
    "hyderabad": "SC",
    "pune": "PUNE",
    "jaipur": "JP",
    "ahmedabad": "ADI",
    "lucknow": "LKO",
    "kochi": "ERS",
    "chandigarh": "CDG",
}


def get_station_code(city_name: str):
    """
    ye function city name ko railway station code me convert karta h,
    agar dict me nhi h to None return karega
    """
    if not city_name:
        return None
    return CITY_TO_STATION_CODE.get(city_name.strip().lower())


def get_city_coords(city_name: str):
    """city name ko (lat, lng) me convert karta h, agar dict me nhi h to None"""
    if not city_name:
        return None
    return CITY_TO_COORDS.get(city_name.strip().lower())


def convert_to_INR(amount: float, from_currency: str, retries: int = 2):
    if from_currency and from_currency.upper() == "INR":
        return round(amount, 2)

    # PRIMARY: Frankfurter API
    for attempt in range(retries):
        try:
            response = requests.get(
                f"https://api.frankfurter.dev/v2/rate/{from_currency}/INR",
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            rate = data['rate']
            return round(amount * rate, 2)
        except Exception as e:
            print(f"DEBUG - frankfurter conversion error (attempt {attempt+1}): {e}")

    try:
        response = requests.get(
            f"https://open.er-api.com/v6/latest/{from_currency}",
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("result") == "success":
            rate = data["rates"]["INR"]
            return round(amount * rate, 2)
        print(f"DEBUG - fallback FX api error: {data}")
    except Exception as e:
        print(f"DEBUG - fallback conversion error: {e}")

    return None


def get_iata_code(city_name: str):
    """
    ye function city name ko IATA code me convert karta h or agar city dictionary me nhi h to none return karta h
    """
    if not city_name:
        return None
    code = CITY_TO_IATA.get(city_name.strip().lower())
    return code


class FlightSearchInput(BaseModel):
    origin: str = Field(description="Origin airport IATA code")
    destination: str = Field(description="Destination airport IATA code")
    departure_date: str = Field(description="Departure date in YYYY-MM-DD format")
    passengers: int = Field(default=1, description="Number of adult passengers")


def search_flights(origin: str, destination: str, departure_date: str, passengers: int = 1, max_budget: Optional[float] = None):
    """
    ye function Duffel api ka use karke flights fetch karta h or
    flights ki list ko return karta h.
    """
    payload = {
        "data": {
            "slices": [
                {
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date,
                }
            ],
            "passengers": [{"type": "adult"} for _ in range(passengers)],
            "cabin_class": "economy",
        }
    }

    try:
        response = requests.post(
            f"{DUFFEL_BASE_URL}/offer_requests?return_offers=true",
            headers=HEADERS,
            json=payload,
            timeout=20,
        )

        response.raise_for_status()
        data = response.json()

        offers = data.get("data", {}).get("offers", [])
        if not offers:
            return {"reason for error": "is route and date ki koi flight nhi hai."}

        result = []
        for offer in offers[:5]:
            price_amount = float(offer['total_amount'])
            currency = offer['total_currency']

            price_in_inr = convert_to_INR(price_amount, currency)
            within_budget = True if max_budget is None else (
                price_in_inr is not None and price_in_inr <= max_budget
            )
            offer_passengers = offer.get("passengers", [])
            passenger_id = offer_passengers[0]["id"] if offer_passengers else None

            result.append({
                "offer_id": offer["id"],
                "passenger_id": passenger_id,
                "airline": offer["slices"][0]["segments"][0]["marketing_carrier"]["name"],
                "price": f"{offer['total_amount']} {offer['total_currency']}",
                "total_amount": offer["total_amount"],
                "total_currency": offer["total_currency"],
                "price_in_inr": price_in_inr,
                "departure_time": offer["slices"][0]["segments"][0]["departing_at"],
                "arrival_time": offer["slices"][0]["segments"][-1]["arriving_at"],
                "within_budget": within_budget,
            })
        return {"offers": result}
    except requests.exceptions.HTTPError as e:
        return {"error": f"API error : {e.response.status_code}-{e.response.text}"}
    except Exception as e:
        return {"error": f"kuch gadbad hogyi h guru {str(e)}"}


@tool
def search_flights_tool(origin: str, destination: str, departure_date: str, passengers: int = 1, max_budget: Optional[float] = None) -> dict:
    """
    ye tool flights search karega origin to destination for the given date
    origin and destination city ke names use kar sakte hai ye tool khud city ka IATA code dhund lega
    bas date ka format exactly YYYY-MM-DD me hona chahiye
    max budget optional h agar user budget btaye ga to flights budget me hogi nhi to sari flights normal aayegi
    """
    origin_code = get_iata_code(origin)
    destination_code = get_iata_code(destination)

    if not origin_code or not destination_code:
        return {"error": "ye city abhi suppported nhi h."}

    return search_flights(origin_code, destination_code, departure_date, passengers, max_budget)


def book_flight(offer_id: str, passenger_id: str, total_amount: str, total_currency: str, passenger_details: dict):
    """
    ye function Duffel ke offer_id se actual booking (order) create karta h.
    passenger_details = {"given_name":..., "family_name":..., "born_on":"YYYY-MM-DD",
                          "email":..., "phone_number":..., "gender":"m/f", "title":"mr/ms"}
    Duffel test mode me payment ke liye "balance" type use hota h (sandbox credit),
    live mode me real card/payment source chahiye hoga.
    """
    passenger_payload = {"id": passenger_id, **passenger_details}

    payload = {
        "data": {
            "type": "instant",
            "selected_offers": [offer_id],
            "payments": [
                {
                    "type": "balance",
                    "currency": total_currency,
                    "amount": total_amount,
                }
            ],
            "passengers": [passenger_payload],
        }
    }
    try:
        response = requests.post(
            f"{DUFFEL_BASE_URL}/orders",
            headers=HEADERS,
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()["data"]
        return {
            "booking_reference": data.get("booking_reference"),
            "status": "confirmed",
            "total_paid": f"{data.get('total_amount')} {data.get('total_currency')}",
        }
    except requests.exceptions.HTTPError as e:
        return {"error": f"Booking failed: {e.response.status_code} - {e.response.text}"}
    except Exception as e:
        return {"error": f"kuch gadbad hogyi h guru {str(e)}"}


@tool
def book_flight_tool(offer_id: str, passenger_id: str, total_amount: str, total_currency: str,
                      given_name: str, family_name: str, born_on: str,
                      email: str, phone_number: str, gender: str, title: str) -> dict:
    """
    ye tool ek specific flight offer ko actually book karta h (Duffel order create hota h).
    offer_id, passenger_id, total_amount aur total_currency search_flights_tool ke result
    se milenge (wahi values yahan pass karo, khud se mat banao).
    passenger ki puri details chahiye: name, DOB (YYYY-MM-DD), email, phone, gender (m/f), title (mr/ms).
    IMPORTANT: is tool ko sirf tab call karna jab user ne booking ke liye explicitly
    "haan"/"yes" bola ho.
    """
    passenger = {
        "given_name": given_name, "family_name": family_name, "born_on": born_on,
        "email": email, "phone_number": phone_number, "gender": gender, "title": title,
    }
    return book_flight(offer_id, passenger_id, total_amount, total_currency, passenger)


def search_stays(latitude: float, longitude: float, check_in_date: str, check_out_date: str, guests: int = 1, max_budget: Optional[float] = None):
    """
    ye function Duffel Stays api ka use karke hotels fetch karta h
    or hotel list ko return karta h, budget ke hisab se filter karke.
    """
    payload = {
        "data": {
            "location": {
                "radius": 5,
                "geographic_coordinates": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
            },
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "guests": [{"type": "adult"} for _ in range(guests)],
        }
    }

    try:
        response = requests.post(
            f"{DUFFEL_STAYS_URL}/search",
            headers=HEADERS,
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("data", {}).get("results", [])
        if not results:
            return {"reason for error": "is location and date ke liye koi hotel nhi mila."}

        result = []
        for stay in results[:5]:
            cheapest_rate = stay.get("cheapest_rate_total_amount")
            currency = stay.get("cheapest_rate_currency")

            if cheapest_rate is None:
                continue

            price_in_inr = convert_to_INR(float(cheapest_rate), currency)
            within_budget = True if max_budget is None else (
                price_in_inr is not None and price_in_inr <= max_budget
            )
            result.append({
                "rate_id": stay.get("cheapest_rate_id"),
                "hotel_name": stay.get("accommodation", {}).get("name"),
                "price": f"{cheapest_rate} {currency}",
                "price_in_inr": price_in_inr,
                "rating": stay.get("accommodation", {}).get("rating"),
                "within_budget": within_budget,
            })
        return {"stays": result}
    except requests.exceptions.HTTPError as e:
        return {"error": f"API error : {e.response.status_code}-{e.response.text}"}
    except Exception as e:
        return {"error": f"kuch gadbad hogyi h guru {str(e)}"}


@tool
def search_stays_tool(city: str, check_in_date: str, check_out_date: str, guests: int = 1, max_budget: Optional[float] = None) -> dict:
    """
    ye tool hotels search karega ek city me diye gaye check-in aur check-out date ke liye
    city ka naam use kar sakte hai, ye tool khud lat/long dhund lega
    dono dates ka format exactly YYYY-MM-DD me hona chahiye
    max budget optional h, agar user btaye to us budget ke andar wali stays highlight ho jayengi
    """
    coords = get_city_coords(city)

    if not coords:
        return {"error": "ye city abhi supported nhi h."}

    latitude, longitude = coords
    return search_stays(latitude, longitude, check_in_date, check_out_date, guests, max_budget)


def book_stay(rate_id: str, guest_details: list):
    """
    ye function Duffel Stays ke rate_id se booking create karta h.
    guest_details = [{"given_name":..., "family_name":..., "email":..., "phone_number":...}]
    """
    payload = {
        "data": {
            "rate_id": rate_id,
            "guests": guest_details,
            "email": guest_details[0]["email"],
            "phone_number": guest_details[0]["phone_number"],
            "payment": {"type": "balance"},
        }
    }
    try:
        response = requests.post(
            f"{DUFFEL_STAYS_URL}/bookings",
            headers=HEADERS,
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()["data"]
        return {
            "booking_reference": data.get("reference"),
            "status": data.get("status"),
        }
    except requests.exceptions.HTTPError as e:
        return {"error": f"Booking failed: {e.response.status_code} - {e.response.text}"}
    except Exception as e:
        return {"error": f"kuch gadbad hogyi h guru {str(e)}"}


@tool
def book_stay_tool(rate_id: str, given_name: str, family_name: str, email: str, phone_number: str) -> dict:
    """
    ye tool ek specific hotel rate ko actually book karta h (Duffel Stays booking).
    rate_id search_stays_tool ke result se milega.
    IMPORTANT: is tool ko sirf tab call karna jab user ne booking ke liye explicitly
    "haan"/"yes" bola ho.
    """
    guest = [{"given_name": given_name, "family_name": family_name, "email": email, "phone_number": phone_number}]
    return book_stay(rate_id, guest)


train_search_tool = TavilySearch(
    max_results=5,
    topic="general",
    name="search_train_options",
    description=(
        "ye tool web par search karta h train options dhundne ke liye kisi bhi "
        "route ke liye (jaise Indore se Mumbai). Isme train ka naam/number, "
        "approximate timing, aur general fare range milta h jo IRCTC/publicly "
        "available sources se hai. Query me source aur destination city zaroor "
        "likhna, jaise 'Indore to Mumbai train timings' ya 'trains Indore Goa IRCTC'."
    ),
)


attractions_search_tool = TavilySearch(
    max_results=5,
    topic="general",
    name="search_nearby_attractions",
    description=(
        "ye tool web par search karta h kisi destination ke pass ke best "
        "tourist attractions, worth-visiting places, aur activities dhundne ke liye. "
        "Query me destination city ka naam zaroor likhna, jaise "
        "'best places to visit in Goa' ya 'top attractions near Jaipur'."
    ),
)


bike_search_tool = TavilySearch(
    max_results=5,
    topic="general",
    name="search_bike_scooter_rentals",
    description=(
        "ye tool web par search karta h scooter/bike rental options dhundne ke liye "
        "kisi bhi city me. Isme rental company ka naam, approximate price, aur location "
        "milta h jo websites par publicly available hai. Query me city ka naam "
        "aur 'bike rental' ya 'scooter rental' zaroor likhna, jaise 'scooter rental Goa prices'."
    ),
)


bus_search_tool = TavilySearch(
    max_results=5,
    topic="general",
    name="search_bus_options",
    description=(
        "ye tool web par search karta h intercity bus options dhundne ke liye "
        "kisi bhi route ke liye (jaise Indore se Goa). Isme bus operator ka naam, "
        "approximate price, aur timing milta h jo websites (RedBus, AbhiBus etc.) par "
        "publicly available hai. Query me source aur destination city zaroor likhna, "
        "jaise 'Indore to Goa bus price' ya 'bus tickets Indore Goa'."
    ),
)


TOOL_MAP = {
    "search_flights_tool": search_flights_tool,
    "search_stays_tool": search_stays_tool,
    "book_flight_tool": book_flight_tool,
    "book_stay_tool": book_stay_tool,
    "search_train_options": train_search_tool,
    "search_bike_scooter_rentals": bike_search_tool,
    "search_nearby_attractions": attractions_search_tool,
    "search_bus_options": bus_search_tool,
}


# Friendly Hinglish labels shown in the UI while a tool is running
TOOL_LABELS = {
    "search_flights_tool": "Flights dhundh raha hoon",
    "search_stays_tool": "Hotels dhundh raha hoon",
    "book_flight_tool": "Flight book kar raha hoon",
    "book_stay_tool": "Hotel book kar raha hoon",
    "search_train_options": "Trains dhundh raha hoon",
    "search_bike_scooter_rentals": "Bike/scooter rentals dhundh raha hoon",
    "search_nearby_attractions": "Nearby attractions dhundh raha hoon",
    "search_bus_options": "Buses dhundh raha hoon",
}


today = date.today().isoformat()


system_msg = SystemMessage(content=f"""
Tu TripMate hai — ek friendly aur helpful travel planning assistant. Aaj ki date {today} hai,
agar user year na bataye to hamesha upcoming/future date samajhna.

Tere paas flights, trains, stays, bike/scooter rental, bus options, aur nearby attractions
dhundhne ke tools hain. User ki query samajh kar zaroori tools call kar (ek se zyada bhi call
kar sakta hai agar zarurat ho, jaise flight + stay dono ek saath). Agar user train ya flight
bole to seedha corresponding tool call kar, khud se "data nahi hai" mat bol de bina tool try kiye.

LANGUAGE RULE (sabse zaroori):
Hamesha Hinglish me jawab de — matlab Hindi words likhne ke liye Roman/English script (a-z)
use kar, Devanagari script (हिंदी लिपि) kabhi mat use kar. Jaise "aapki train mil gayi hai"
sahi hai, "आपकी ट्रेन मिल गई है" galat hai. Poora response hamesha Roman letters me hona
chahiye, chahe words Hindi ke hi hon.

Jab tool ka result mile, response banate waqt ye rules follow kar:

1. BUDGET FILTER: Agar user ne budget diya hai aur tool result me "within_budget" field hai,
   to sirf "within_budget": true wale options ko highlight/recommend kar. Agar koi bhi option
   budget ke andar nahi hai, to honestly bata de ki koi budget-fit option nahi mila, aur sabse
   sasta available option bhi bata de bina usse budget-fit bole.

2. CLEAR FORMAT: Response ko readable bana - bullet points ya short list me price, timing,
   aur naam clearly dikha. Raw JSON kabhi mat dikhana user ko.

3. NEARBY PLACES: Jab bhi user kisi destination ke baare me pooche (trip plan, flight, stay),
   destination ke 2-4 worth-visiting nearby attractions bhi suggest kar - agar tere pass already
   knowledge hai to seedha bata de, warna 'search_nearby_attractions' tool call kar.

4. TONE: Friendly aur conversational reh, jaise ek dost trip plan karne me madad kar raha ho.
   Zyada lamba mat likh, seedha kaam ki baat bata.

5. HONESTY: Agar koi tool error de ya data na mile, to user ko clearly bata de ki wo info
   abhi available nahi hai, khud se guess/invent mat kar.

6. USER PERMISSION: user ki permission ke bina koi booking nahi karna hai, kisi bhi type ki
   booking karne se pehle user se permission lena compulsory hai, jab tak user "haan" ya "yes"
   na bole booking nahi karna, user ke confirm karne ke baad hi booking karna. Booking tool
   call karte waqt search result se mile offer_id/rate_id, passenger_id, total_amount aur
   total_currency wahi use karna jo pehle search me mile the, khud se mat banana.

7. TRAIN FARE: Agar train result me "fare_inr" ki value null/None ho, to user ko bata de ki
   train available hai lekin fare abhi fetch nahi ho paya (IRCTC API se kabhi kabhi fare data
   nahi milta), aur suggest kar ki IRCTC website/app pe check kar le exact fare ke liye. Train
   ka naam, number, aur timing phir bhi bata dena chahiye chahe fare na mile.

8. BUS OPTIONS: Agar user budget travel option pooche ya train available na ho, "search_bus_options"
   tool use kar sakta hai bus fares/timing dikhane ke liye — ye sirf reference info hai, real
   booking is tool se nahi hoti, user ko batana ki booking RedBus/AbhiBus jaisi site pe khud
   karni hogi.
""")


llm_with_tools = llm.bind_tools([
    search_flights_tool, search_stays_tool, book_flight_tool, book_stay_tool,
    train_search_tool, bike_search_tool, attractions_search_tool, bus_search_tool
])


MAX_HISTORY = 20  # short memory - itne messages ke baad purane trim ho jayenge


def trim_history(history):
    """
    ye function memory ko limited rakhta h taaki context window bhar na jaye
    system message hamesha rakhte h, baaki sirf recent messages rakhte h
    """
    if len(history) > MAX_HISTORY:
        return [history[0]] + history[-(MAX_HISTORY - 1):]
    return history


def clean_tool_result(result):
    """
    BUG FIX: Tavily search tools (attractions, bus, train, bike) kabhi-kabhi har
    result ke saath poore web page ka "raw_content" bhi bhej dete h, jo bahut
    bada hota h (hazaron characters). Ye poora message_history me store ho jaata
    tha, aur kuch turns baad total tokens Groq ki free-tier TPM limit (8000
    tokens/request) se cross ho jaate the -> "413 Request too large" error aata.

    Ye function har Tavily-style result se raw_content/images jaise heavy fields
    hata deta h, sirf top 3 results rakhta h, aur har result ka content bhi
    chhote size tak cap kar deta h - taaki context chhota aur fast rahe.
    """
    try:
        if isinstance(result, dict) and "results" in result and isinstance(result["results"], list):
            trimmed_results = []
            for item in result["results"][:3]:
                if isinstance(item, dict):
                    trimmed_results.append({
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "content": (item.get("content") or "")[:500],
                    })
            return {"query": result.get("query"), "results": trimmed_results}
    except Exception:
        pass

    # safety net: koi aur bada result ho to bhi hard cap laga do
    result_str = str(result)
    if len(result_str) > 4000:
        return result_str[:4000] + "...(truncated)"
    return result