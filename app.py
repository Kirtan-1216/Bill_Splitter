import os

import streamlit as st
from google import genai
from PIL import Image
from prompts import SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE, SUMMARY_REQUEST_PROMPT
import urllib.parse

# ---------------------------------------------------------
# Page Setup & Configuration
# ---------------------------------------------------------
st.set_page_config(page_title="Quick Bill Splitter", page_icon="🧾", layout="centered")

st.title("🧾 Quick Bill Splitter")
st.write("Upload a receipt photo or paste bill details to split expenses instantly.")

# Retrieve API Key from .streamlit/secrets.toml
api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("Missing `GEMINI_API_KEY`. Please add it to your `.streamlit/secrets.toml` file.")
    st.stop()

# Initialize Gemini Client
client = genai.Client(api_key=api_key)

# ---------------------------------------------------------
# User Inputs (Sidebar & Main UI)
# ---------------------------------------------------------
st.sidebar.header("User Options")
user_name = st.sidebar.text_input("Your Name", value="Friend")
st.sidebar.markdown("---")
st.sidebar.write("### Welcome")
st.sidebar.info(WELCOME_MESSAGE_TEMPLATE.format(name=user_name))

st.subheader("1. Provide Bill Information")
uploaded_file = st.file_uploader("Upload Receipt Image", type=["jpg", "jpeg", "png"])
text_details = st.text_area("Or type bill details manually (e.g., Pizza $20, Drinks $10, Tax $3)", height=100)

num_people = st.number_input("How many people are splitting?", min_value=1, value=2, step=1)
split_instructions = st.text_input("Specific split instructions (optional)", placeholder="e.g., Alex had the burger, Sam had the salad")

# ---------------------------------------------------------
# Processing & Gemini API Call
# ---------------------------------------------------------
if st.button("Calculate Split", type="primary"):
    if not uploaded_file and not text_details.strip():
        st.warning("Please upload a receipt image or type bill details.")
    else:
        with st.spinner("Analyzing receipt and calculating splits..."):
            try:
                # Prepare input content list for Gemini
                contents = [
                    f"Number of people splitting: {num_people}\n",
                    f"Split instructions: {split_instructions if split_instructions else 'Split equally'}\n"
                ]

                # Append receipt image if provided
                if uploaded_file:
                    image = Image.open(uploaded_file)
                    st.image(image, caption="Uploaded Receipt", use_container_width=True)
                    contents.append(image)

                # Append manual text details if provided
                if text_details.strip():
                    contents.append(f"Bill Details: {text_details}")

                #    Call Gemini API using the new google-genai SDK
                # Try calling the model with fallback models if Google's servers are overloaded (503)
                models_to_try = ["gemini-3.8-flash", "gemini-2.5-flash-lite"]
                response = None

                for model_name in models_to_try:
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=contents,
                            config={"system_instruction": SYSTEM_PROMPT}
                        )
                        # If call succeeds, break out of the fallback loop
                        break
                    except Exception as err:
                        # If it's a 503 high demand error, log a warning and try the next model string
                        # # Handle 404 error (Page or Resource Not Found)
                        if "503" in str(err):
                            st.warning(f"Model {model_name} is currently busy. Trying alternative endpoint...")
                            continue
                        elif "404" in str(err):
                            st.error(f"Model {model_name} not found.")
                            continue
                        else:
                            raise err

                # Check if all models failed before using response.text
                if response is None:
                    st.error("All AI models are currently overloaded. Please wait a few seconds and try clicking 'Calculate Split' again.")
                else:
                    # Render response and Telegram share block safely
                    st.success("Analysis Complete!")
                    st.markdown("### 📊 Split Breakdown")
                    st.markdown(response.text)

                    st.divider()
                    st.subheader("📲 Shareable Summary")

                    # format the string for sharing
                    summary_text = f"🧾 *Bill Split Breakdown\nPeople Splitting : {num_people}\n\n{response.text}"

                    # Streamlit code (provides built-in 'Copy' button)
                    st.code(summary_text, language="text")

                    # generate Telegram share link
                    encoded_summary = urllib.parse.quote(summary_text)
                    telegram_url = f"https://t.me/share/url?url=https://streamlit.io&text={encoded_summary}"

                    # display telegram share button 
                    st.link_button("📤 Share via Telegram", url=telegram_url)


            except Exception as e:
                st.error(f"An error occurred while processing: {e}")