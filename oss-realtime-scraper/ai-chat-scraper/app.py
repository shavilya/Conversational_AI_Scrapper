"""
app.py
Conversational Real-Time Web Scraper
Powered by Streamlit, Crawl4AI, and Local Ollama (Qwen 2.5).
"""

import json
import pandas as pd
import streamlit as st
from crawl4ai import CacheMode

from scraper_engine import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_SERVER,
    check_ollama_connection,
    plan_scrape_task,
    crawl_page,
    extract_records,
)

# ---------------------------------------------------------
# Page Configuration & Modern Theme Styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="AI Conversational Web Scraper",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for polished ChatGPT/Gemini look
st.markdown("""
<style>
    /* Global styling */
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }
    .badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
    }
    .badge-primary {
        background-color: #e0e7ff;
        color: #3730a3;
    }
    .badge-success {
        background-color: #dcfce7;
        color: #166534;
    }
    .badge-info {
        background-color: #e0f2fe;
        color: #075985;
    }
    .download-container {
        display: flex;
        gap: 0.75rem;
        margin-top: 0.75rem;
    }
    .stDownloadButton > button {
        border-radius: 8px;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "quick_prompt" not in st.session_state:
    st.session_state.quick_prompt = None


# ---------------------------------------------------------
# Sidebar Controls & Configuration
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### 🕸️ Scraper Settings")

    # 1. Ollama Connection Status & Model Selector
    conn_info = check_ollama_connection(DEFAULT_OLLAMA_SERVER)
    if conn_info["connected"]:
        st.success("🟢 Local Ollama Online", icon="✅")
        available_models = conn_info.get("models", [])
        if DEFAULT_MODEL not in available_models and available_models:
            default_index = 0
        elif DEFAULT_MODEL in available_models:
            default_index = available_models.index(DEFAULT_MODEL)
        else:
            available_models = [DEFAULT_MODEL]
            default_index = 0

        selected_model = st.selectbox(
            "Select LLM Model",
            options=available_models,
            index=default_index,
            help="Models loaded in your local Ollama instance."
        )
    else:
        st.error(f"🔴 Ollama Offline ({DEFAULT_OLLAMA_SERVER})", icon="⚠️")
        st.caption("Run `ollama serve` in your terminal to start Ollama.")
        selected_model = DEFAULT_MODEL

    st.divider()

    # 2. Crawler Cache Toggle
    st.markdown("#### ⚙️ Crawler Engine")
    force_fresh = st.toggle(
        "Force Fresh Scrape (Bypass Cache)",
        value=True,
        help="When enabled, Crawl4AI fetches fresh HTML using headless Chromium and ignores local cache."
    )
    cache_mode = CacheMode.BYPASS if force_fresh else CacheMode.ENABLED

    st.divider()

    # 3. Quick-Fill Example Prompts
    st.markdown("#### 💡 Quick Examples")
    example_prompts = [
        ("📚 Books to Scrape", "Scrape the top 5 books from https://books.toscrape.com with title, price, and availability in a table"),
        ("💬 Quotes to Scrape", "Extract 5 quotes from https://quotes.toscrape.com with quote, author, and tags as json"),
        ("🚀 Hacker News", "Scrape top 10 stories from https://news.ycombinator.com with title and link in csv format"),
        ("💻 GitHub Trending", "Extract trending repositories from https://github.com/trending with repo_name, description, and language as a table"),
    ]

    for label, prompt_text in example_prompts:
        if st.button(label, use_container_width=True):
            st.session_state.quick_prompt = prompt_text

    st.divider()

    # 4. Clear Chat History
    if st.button("🗑️ Clear Conversation", use_container_width=True, type="secondary"):
        st.session_state.messages = []
        st.session_state.quick_prompt = None
        st.rerun()


# ---------------------------------------------------------
# Main Chat Header
# ---------------------------------------------------------
st.markdown('<div class="main-title">Conversational Web Scraper</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title"><b>100% Free & Open-Source </b></div>',
    unsafe_allow_html=True
)


# ---------------------------------------------------------
# Helper: Render Assistant Scraped Dataset
# ---------------------------------------------------------
def render_assistant_dataset(msg: dict, msg_idx: int):
    """Render the structured dataset in requested format with working export buttons."""
    content = msg.get("content", "")
    if content:
        st.markdown(content)

    plan = msg.get("plan")
    records = msg.get("records")

    if plan:
        # Display plan tags
        badges_html = (
            f'<div style="margin-bottom: 0.75rem;">'
            f'<span class="badge badge-primary">🌐 URL: {plan.get("url")}</span>'
            f'<span class="badge badge-info">🎯 Fields: {", ".join(plan.get("fields", []))}</span>'
            f'<span class="badge badge-success">📊 Format: {plan.get("output_format", "table").upper()}</span>'
            f'</div>'
        )
        st.markdown(badges_html, unsafe_allow_html=True)

    if records:
        output_format = plan.get("output_format", "table") if plan else "table"
        df = pd.DataFrame(records)

        # 1. Render in requested format
        if output_format == "json":
            st.json(records)
        elif output_format == "csv":
            csv_str = df.to_csv(index=False)
            st.code(csv_str, language="csv")
            with st.expander("Show interactive data table", expanded=False):
                st.dataframe(df, use_container_width=True)
        else:
            # Default: Table
            st.dataframe(df, use_container_width=True)

        # 2. Download Buttons (unique key per message index to prevent collisions)
        col1, col2, _ = st.columns([1, 1, 3])
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        json_bytes = json.dumps(records, indent=2).encode("utf-8")

        with col1:
            st.download_button(
                label="📥 Download CSV",
                data=csv_bytes,
                file_name=f"scraped_data_{msg_idx}.csv",
                mime="text/csv",
                key=f"dl_csv_{msg_idx}",
                use_container_width=True
            )
        with col2:
            st.download_button(
                label="📥 Download JSON",
                data=json_bytes,
                file_name=f"scraped_data_{msg_idx}.json",
                mime="application/json",
                key=f"dl_json_{msg_idx}",
                use_container_width=True
            )

    error = msg.get("error")
    if error:
        st.error(error)


# ---------------------------------------------------------
# Render Message History
# ---------------------------------------------------------
for idx, message in enumerate(st.session_state.messages):
    role = message["role"]
    avatar = "👤" if role == "user" else "🤖"
    with st.chat_message(role, avatar=avatar):
        if role == "user":
            st.markdown(message["content"])
        else:
            render_assistant_dataset(message, idx)


# ---------------------------------------------------------
# Handle User Input / Quick Examples
# ---------------------------------------------------------
user_prompt = st.chat_input("Enter target URL and fields (e.g., 'Scrape books from books.toscrape.com with title and price')...")

# Check if a quick example button was pressed
active_prompt = None
if st.session_state.quick_prompt:
    active_prompt = st.session_state.quick_prompt
    st.session_state.quick_prompt = None
elif user_prompt:
    active_prompt = user_prompt

if active_prompt:
    # 1. Append user prompt to state & render
    st.session_state.messages.append({"role": "user", "content": active_prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(active_prompt)

    # 2. Execute scraping pipeline in assistant bubble
    with st.chat_message("assistant", avatar="🤖"):
        assistant_entry = {"role": "assistant"}

        with st.status("Executing Scraping Pipeline...", expanded=True) as status:
            try:
                # Step 1: Planning
                st.write("🧠 **Step 1/3:** Parsing prompt & generating extraction schema...")
                plan = plan_scrape_task(active_prompt, model=selected_model)
                assistant_entry["plan"] = plan.model_dump()

                if not plan.url:
                    raise ValueError(
                        "No target URL found in your prompt. Please include a target webpage (e.g. `https://books.toscrape.com`)."
                    )

                st.write(f"✓ **Target:** `{plan.url}` | **Fields:** `{', '.join(plan.fields)}` | **Format:** `{plan.output_format}`")

                # Step 2: Crawling
                st.write(f"🌐 **Step 2/3:** Crawling target webpage with headless Chromium (Crawl4AI)...")
                crawl_res = crawl_page(plan.url, cache_mode=cache_mode)
                st.write(f"✓ Crawled successfully ({crawl_res['length']:,} characters retrieved)")

                # Step 3: Extraction
                st.write(f"🔍 **Step 3/3:** Extracting requested fields using `{selected_model}`...")
                records = extract_records(crawl_res["markdown"], plan, model=selected_model)
                assistant_entry["records"] = records
                st.write(f"✓ Extracted {len(records)} structured record(s) matching schema!")

                status.update(label=f"Completed! Extracted {len(records)} records.", state="complete", expanded=False)
                assistant_entry["content"] = f"Successfully scraped **{len(records)}** records from [{plan.url}]({plan.url}):"

            except Exception as e:
                err_msg = str(e)
                status.update(label="Scraping encountered an error", state="error", expanded=True)
                st.error(f"Error: {err_msg}")
                assistant_entry["error"] = err_msg
                assistant_entry["content"] = "Could not complete the scrape request due to an error."

        # Render extracted data
        msg_idx = len(st.session_state.messages)
        render_assistant_dataset(assistant_entry, msg_idx)
        st.session_state.messages.append(assistant_entry)
