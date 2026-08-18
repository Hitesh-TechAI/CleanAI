import google.generativeai as genai
import json
import re
import os

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash")


def call_gemini(user_message, metadata, chat_history, pending_action=None):
    """
    Stable Gemini Caller
    - Lightweight metadata
    - Limited chat history
    - No streaming
    - Regex JSON extraction
    """

    # -----------------------------
    # 1️⃣ Lightweight Metadata
    # -----------------------------
    light_metadata = {
        "rows": metadata.get("row_count"),
        "columns": metadata.get("columns", [])
    }

    # -----------------------------
    # 2️⃣ Limit Chat History (last 4)
    # -----------------------------
    recent_history = chat_history[-4:] if chat_history else []

    conversation = "\n".join(
        [f"{m['role']}: {m['content']}" for m in recent_history]
    )

    # -----------------------------
    # 3️⃣ System Prompt
    # -----------------------------
    system_prompt = f"""
You are CleanAI — a friendly, intelligent AI Data Cleaning Assistant.

Your personality:
- Warm and conversational
- Slightly enthusiastic
- Clear and confident
- Never robotic
- Keep responses short (2–3 friendly sentences)

IMPORTANT RULES:

1) You ONLY help with:
   - Cleaning data
   - Analyzing dataset
   - Transforming columns
   - Explaining dataset state

2) If user asks something unrelated to dataset:
   - Respond warmly
   - Gently redirect them back to working on the data
   - Do NOT perform any action

3) Always return STRICT JSON.
   No markdown.
   No explanation outside JSON.

Allowed actions:
- handle_missing
- remove_duplicates
- remove_outliers
- handle_types

Dataset Metadata:
{json.dumps(light_metadata)}

Pending Action:
{json.dumps(pending_action)}

Return JSON format:

{{
  "mode": "proposal" | "execute" | "modify" | "complete" | "redirect",
  "message": "Friendly response here",
  "action": {{
    "action": "function_name",
    "column": "column_name",
    "strategy": "mean/median/mode/drop",
    "method": "remove/cap",
    "subset": "column_name",
    "date_format": "%Y-%m-%d"
  }}
}}

If unrelated question:
{{
  "mode": "redirect",
  "message": "Friendly redirection message"
}}

If nothing to do:
{{
  "mode": "complete",
  "message": "Friendly dataset summary"
}}
"""

    full_prompt = (
        f"{system_prompt}\n\n"
        f"Conversation:\n{conversation}\n\n"
        f"User: {user_message}"
    )

    # -----------------------------
    # 4️⃣ Gemini Call
    # -----------------------------
    try:
        response = model.generate_content(
            full_prompt,
            generation_config={
                "max_output_tokens": 500,
                "temperature": 0.1,   # Lower = more structured
                "top_p": 0.8,
            },
        )

        full_text = response.text.strip()

    except Exception as e:
        return {
            "mode": "error",
            "message": f"Gemini API error: {str(e)}"
        }

    # -----------------------------
    # 5️⃣ Robust JSON Extraction
    # -----------------------------
    try:
        # Remove markdown wrapping if present
        cleaned = full_text.replace("```json", "").replace("```", "").strip()

        # Find first JSON object manually
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1

        if start == -1 or end == -1:
            raise ValueError("No JSON found")

        json_block = cleaned[start:end]

        return json.loads(json_block)

    except Exception as e:
        print("JSON PARSE ERROR:", e)
        print("RAW RESPONSE:", full_text)
        return {
            "mode": "error",
            "message": "Model returned invalid JSON."
        }