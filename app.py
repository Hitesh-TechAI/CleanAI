import streamlit as st
import pandas as pd

# Orchestrator (Gemini-controlled)
from ai.orchestrator import run_orchestrator
from utils.summary_formatter import format_execution_summary


# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(page_title="CleanAI", layout="wide")
st.title("🧠 CleanAI - Conversational Data Cleaning Agent")


# -----------------------------
# Session State Initialization
# -----------------------------
if "current_df" not in st.session_state:
    st.session_state.current_df = None

if "original_df" not in st.session_state:
    st.session_state.original_df = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "pending_action" not in st.session_state:
    st.session_state.pending_action = None


# -----------------------------
# File Upload
# -----------------------------
uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

if uploaded_file is not None and st.session_state.current_df is None:
    df = pd.read_csv(uploaded_file)
    st.session_state.current_df = df
    st.session_state.original_df = df.copy()
    st.success("Dataset loaded successfully.")


# -----------------------------
# If Dataset Loaded
# -----------------------------
if st.session_state.current_df is not None:

    df = st.session_state.current_df

    st.subheader("📄 Current Dataset Preview")
    st.dataframe(df.head(50), use_container_width=True)

    st.divider()

    # -----------------------------
    # Chat Interface
    # -----------------------------
    st.subheader("💬 Talk to CleanAI")

    # Display Chat History
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_input = st.chat_input("Tell CleanAI what to do next...")

    if user_input:

        # Save User Message
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input
        })

        with st.chat_message("user"):
            st.markdown(user_input)

        # Run Gemini-powered Orchestrator
        updated_df, response = run_orchestrator(
            st.session_state.current_df,
            user_input,
            st.session_state
        )

        # Update Dataset
        st.session_state.current_df = updated_df

        # -----------------------------
        # Handle AI Response
        # -----------------------------
        if response["type"] == "proposal":

            message = (
                "### ⚠ Proposed Action\n\n"
                f"{response['message']}\n\n"
                f"**Suggested Action:**\n\n"
                f"`{response.get('action')}`"
            )

        elif response["type"] == "executed":

            action_name = None
            if "action" in response:
                action_name = response["action"].get("action")

            formatted_summary = format_execution_summary(
                action_name,
                response.get("summary", {})
            )

            message = (
                "### ✅ Action Executed\n\n"
                f"{response['message']}\n\n"
                f"**Execution Summary:**\n\n"
                f"{formatted_summary}"
            )

        elif response["type"] == "complete":

            message = f"🎉 {response['message']}"

        elif response["type"] == "error":

            message = f"⚠ Error: {response['message']}"

        else:
            message = "⚠ Unknown response from AI."

        # Save Assistant Response
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": message
        })

        with st.chat_message("assistant"):
            st.markdown(message)

    st.divider()

    # -----------------------------
    # Download Updated Dataset
    # -----------------------------
    cleaned_csv = st.session_state.current_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="⬇ Download Current Dataset",
        data=cleaned_csv,
        file_name="cleaned_dataset.csv",
        mime="text/csv"
    )