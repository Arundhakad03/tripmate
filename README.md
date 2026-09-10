# 🧳 TripMate

**TripMate** is an AI travel-planning assistant that finds flights, hotels, trains, buses, bike/scooter rentals, and nearby attractions — all through a natural, Hinglish conversation. It's built on a **LangChain + Groq** tool-calling agent and wrapped in a clean **Streamlit** chat UI.

> Ask it something like *"Indore se Goa flight dikhao 20 December ko, budget 6000 me"* and it takes care of the rest — searching, comparing, and (with your permission) even booking.

---

## ✨ Features

- 💬 **Conversational agent** — powered by an LLM (via Groq) with tool-calling, so it decides on its own which tools to call based on what you ask.
- ✈️ **Flight search & booking** via the [Duffel](https://duffel.com/) API, with live INR conversion for any currency.
- 🏨 **Hotel/stay search & booking** via Duffel Stays, filtered against your budget.
- 🚆 **Train options** and 🚌 **bus options** via live web search (Tavily).
- 🛵 **Bike/scooter rentals** and 📍 **nearby attractions** for your destination.
- 🔒 **Booking safety** — the agent never books a flight or hotel without an explicit "yes" from the user.
- 🗣️ **Hinglish-first** — responses are always in Hinglish written in Roman script, never Devanagari.
- 🖥️ **Polished Streamlit chat UI** with a forced dark theme, quick-start suggestions, and live tool-call status ("🔎 Flights dhundh raha hoon...").

---

## 🛠️ Tech Stack

| Layer          | Tech                                      |
|----------------|--------------------------------------------|
| LLM / Agent    | [LangChain](https://python.langchain.com/) + [Groq](https://groq.com/) (`openai/gpt-oss-120b`) |
| Flights/Stays  | [Duffel API](https://duffel.com/docs/api) |
| Web search     | [Tavily](https://tavily.com/) (`langchain-tavily`) |
| UI             | [Streamlit](https://streamlit.io/)        |
| Currency FX    | [Frankfurter](https://frankfurter.dev/) / [open.er-api.com](https://www.exchangerate-api.com/) |

---

## 📂 Project Structure

```
tripmate/
├── app.py                  # Streamlit chat UI
├── tripmate_backend.py     # Agent logic: tools, prompt, LLM binding
├── requirements.txt        # Python dependencies
├── .env.example             # Template for required API keys
├── .streamlit/
│   └── config.toml         # Forces a consistent dark theme
└── README.md
```

---

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/tripmate.git
cd tripmate
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up API keys

Copy the example env file and fill in your own keys:

```bash
cp .env.example .env
```

```env
GROQ_API_KEY=your_groq_api_key_here
DUFFEL_API_KEY=your_duffel_api_key_here
RAPIDAPI_KEY=your_rapidapi_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

| Key              | Where to get it                                      |
|------------------|-------------------------------------------------------|
| `GROQ_API_KEY`   | [console.groq.com](https://console.groq.com/)         |
| `DUFFEL_API_KEY` | [duffel.com](https://duffel.com/) (use a **test** key for sandbox bookings) |
| `RAPIDAPI_KEY`   | [rapidapi.com](https://rapidapi.com/) (IRCTC endpoints) |
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com/)                      |

### 5. Run the app

```bash
streamlit run app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`).

---

## 💡 Example prompts

- "Indore se Goa flight dikhao 20 December ko"
- "Mumbai me 2 din ke liye hotel dhundo budget 5000 me"
- "Delhi se Jaipur train options batao"
- "Goa me ghumne ki best jagah kaunsi hai?"
- "Haan, ye flight book kar do" *(after a search, to confirm a booking)*

---

## ⚠️ Notes & Limitations

- Flight/hotel search & booking currently work for a fixed set of major Indian cities (see `CITY_TO_IATA` / `CITY_TO_COORDS` in `tripmate_backend.py`) — easy to extend by adding more entries.
- Bookings use Duffel's **sandbox `balance` payment type** by default — swap this out before going live with real payments.
- Train/bus results come from live web search, so they're for reference only; actual booking still needs to happen on IRCTC/RedBus/etc.
- The chat history is trimmed to the last ~20 messages to stay within the LLM's context/rate limits.

---

## 🗺️ Roadmap Ideas

- [ ] Support more cities/airports dynamically instead of a fixed dictionary
- [ ] Persist chat history across sessions (e.g. with a database)
- [ ] Add a proper itinerary/day-plan view
- [ ] Real payment integration for live bookings

---

## 🤝 Contributing

PRs and suggestions are welcome! Open an issue first for larger changes.

## 📄 License

This project is available under the MIT License — feel free to use and modify it.
