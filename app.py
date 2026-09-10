import os
import streamlit as st
from langchain_core.messages import HumanMessage, ToolMessage

from tripmate_backend import (
    llm_with_tools,
    system_msg,
    TOOL_MAP,
    TOOL_LABELS,
    trim_history,
    clean_tool_result,
)

# ----------------------------------------------------------------------------
# Page config
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="TripMate",
    page_icon="🧳",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# Styling
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
        /* Force a fixed dark look regardless of browser/OS theme */
        .stApp {
            background: radial-gradient(circle at 15% 0%, #1c1710 0%, #0e1117 35%) !important;
            color: #fafafa !important;
        }
        #MainMenu, footer {visibility: hidden;}

        /* Make sure every bit of default text stays readable on the dark bg */
        .stApp, .stApp p, .stApp span, .stApp li, .stApp label,
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
        .stMarkdown, .stMarkdown p, .stMarkdown li {
            color: #fafafa !important;
        }

        .tm-hero {
            text-align: center;
            padding: 0.25rem 0 1.25rem 0;
        }
        .tm-hero h1 {
            font-size: 2.1rem;
            margin-bottom: 0.1rem;
            color: #fafafa !important;
        }
        .tm-hero p {
            color: #b7b7b7 !important;
            font-size: 0.95rem;
            margin-top: 0;
        }

        div[data-testid="stChatMessage"] {
            border-radius: 16px;
            padding: 0.4rem 0.2rem;
            background: #1a1d24 !important;
            color: #fafafa !important;
        }
        div[data-testid="stChatMessage"] p {
            color: #fafafa !important;
        }

        div[data-testid="stChatInput"] textarea {
            color: #fafafa !important;
        }
        div[data-testid="stChatInput"] {
            background: #1a1d24 !important;
        }

        .tm-suggest-btn button {
            width: 100%;
            border-radius: 999px;
            border: 1px solid #4a3a1e;
            background: #262019 !important;
            color: #e8b969 !important;
            font-size: 0.85rem;
            padding: 0.4rem 0.8rem;
        }
        .tm-suggest-btn button:hover {
            background: #332811 !important;
            border-color: #e8b969;
            color: #ffd98a !important;
        }
        .tm-suggest-btn button p {
            color: inherit !important;
        }

        section[data-testid="stSidebar"] {
            background: #1a1d24 !important;
        }
        section[data-testid="stSidebar"] * {
            color: #fafafa !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [system_msg]
if "display_messages" not in st.session_state:
    st.session_state.display_messages = []

# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🧳 TripMate")
    st.caption("Tera personal travel planning assistant")

    st.markdown("---")
    st.markdown("**Ye sab kar sakta hoon:**")
    st.markdown(
        "- ✈️ Flights search & book\n"
        "- 🏨 Hotels search & book\n"
        "- 🚆 Train options dhundna\n"
        "- 🚌 Bus options dhundna\n"
        "- 🛵 Bike/scooter rentals\n"
        "- 📍 Nearby attractions"
    )

    st.markdown("---")
    missing_keys = [
        name for name in ["GROQ_API_KEY", "DUFFEL_API_KEY", "TAVILY_API_KEY"]
        if not os.getenv(name)
    ]
    if missing_keys:
        st.warning(
            "⚠️ Ye API keys `.env` me nahi mili: "
            + ", ".join(missing_keys)
            + ". Bina inke tools kaam nahi karenge."
        )
    else:
        st.success("✅ Saari API keys set hain")

    st.markdown("---")
    if st.button("🔄 Nayi Chat", use_container_width=True):
        st.session_state.messages = [system_msg]
        st.session_state.display_messages = []
        st.rerun()

# ----------------------------------------------------------------------------
# Hero
# ----------------------------------------------------------------------------
st.markdown(
    """
    <div class="tm-hero">
        <h1>🧳 TripMate</h1>
        <p>Apna pura trip plan karo — flights, hotels, trains, aur bahut kuch — ek hi jagah</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Quick-start suggestions (only before the first message)
# ----------------------------------------------------------------------------
SUGGESTIONS = [
    "Indore se Goa flight dikhao 20 December ko",
    "Mumbai me 2 din ke liye hotel dhundo budget 5000 me",
    "Delhi se Jaipur train options batao",
    "Goa me ghumne ki best jagah kaunsi hai?",
]

prefill = None
if not st.session_state.display_messages:
    st.markdown("###### Kuch aise try karo 👇")
    cols = st.columns(2)
    for i, suggestion in enumerate(SUGGESTIONS):
        with cols[i % 2]:
            st.markdown('<div class="tm-suggest-btn">', unsafe_allow_html=True)
            if st.button(suggestion, key=f"suggest_{i}"):
                prefill = suggestion
            st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# Render chat history
# ----------------------------------------------------------------------------
for msg in st.session_state.display_messages:
    avatar = "🧳" if msg["role"] == "assistant" else "🙋"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])


def run_turn(user_text: str):
    """Send user_text through the agent loop and render the full exchange."""
    st.session_state.display_messages.append({"role": "user", "content": user_text})
    with st.chat_message("user", avatar="🙋"):
        st.markdown(user_text)

    st.session_state.messages.append(HumanMessage(content=user_text))
    st.session_state.messages = trim_history(st.session_state.messages)

    with st.chat_message("assistant", avatar="🧳"):
        status_area = st.empty()
        try:
            response = llm_with_tools.invoke(st.session_state.messages)
            st.session_state.messages.append(response)

            while response.tool_calls:
                labels = [
                    TOOL_LABELS.get(tc["name"], tc["name"])
                    for tc in response.tool_calls
                ]
                status_area.info("🔎 " + ", ".join(labels) + " ...")

                for tool_call in response.tool_calls:
                    try:
                        tool_fn = TOOL_MAP[tool_call["name"]]
                        result = tool_fn.invoke(tool_call["args"])
                        result = clean_tool_result(result)
                    except Exception as tool_error:
                        result = {"error": f"tool execution failed: {str(tool_error)}"}

                    st.session_state.messages.append(
                        ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                    )

                response = llm_with_tools.invoke(st.session_state.messages)
                st.session_state.messages.append(response)
                st.session_state.messages = trim_history(st.session_state.messages)

            status_area.empty()
            final_text = response.content or "_(khaali response mila)_"

        except Exception as e:
            status_area.empty()
            final_text = f"Arre yaar, kuch gadbad ho gayi - {str(e)}\n\nDobara try kar please."

        st.markdown(final_text)

    st.session_state.display_messages.append({"role": "assistant", "content": final_text})


# ----------------------------------------------------------------------------
# Input
# ----------------------------------------------------------------------------
user_input = st.chat_input("Apna trip plan batao... jaise 'Indore se Goa flight dikhao 15 Dec ko'")

if prefill:
    run_turn(prefill)
elif user_input:
    run_turn(user_input)