from groq import Groq
import json
import os


# Configure Groq API
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

MODEL = "openai/gpt-oss-120b"


def call_ai(user_message, metadata, chat_history, pending_action=None):
    """
    CleanAI GPT-OSS 120B Caller
    - Lightweight metadata
    - Limited chat history
    - Structured JSON output
    - Uses Groq
    """

    # -----------------------------
    # 1. Lightweight Metadata
    # -----------------------------
    light_metadata = {
        "rows": metadata.get("row_count"),
        "columns": metadata.get("columns", [])
    }

    # -----------------------------
    # 2. Limit Chat History
    # -----------------------------
    recent_history = chat_history[-4:] if chat_history else []

    conversation = "\n".join(
        [f"{m['role']}: {m['content']}" for m in recent_history]
    )

    # -----------------------------
    # 3. System Prompt
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

3) Return ONLY the requested JSON structure.

Allowed actions:
- handle_missing
- remove_duplicates
- remove_outliers
- handle_types

Dataset Metadata:
{json.dumps(light_metadata)}

Pending Action:
{json.dumps(pending_action)}

Return JSON with this structure:

{{
  "mode": "proposal",
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

Modes:

proposal:
Suggest a cleaning operation and wait for confirmation.

execute:
Execute a previously proposed operation after user confirmation.

modify:
Modify a pending operation based on the user's request.

complete:
No cleaning action is required. Give a short dataset-related response.

redirect:
The user asked something unrelated to dataset cleaning.

If unrelated:
{{
  "mode": "redirect",
  "message": "Friendly redirection message"
}}

If nothing needs to be done:
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
    # 4. GPT-OSS 120B Call
    # -----------------------------
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": (
                        f"Conversation:\n{conversation}\n\n"
                        f"User: {user_message}"
                    )
                }
            ],
            temperature=0.1,
            max_tokens=500,
            response_format={
                "type": "json_object"
            }
        )

        full_text = response.choices[0].message.content.strip()

    except Exception as e:
        return {
            "mode": "error",
            "message": f"AI API error: {str(e)}"
        }

    # -----------------------------
    # 5. Parse JSON
    # -----------------------------
    try:
        cleaned = (
            full_text
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

        return json.loads(cleaned)

    except Exception as e:
        print("JSON PARSE ERROR:", e)
        print("RAW RESPONSE:", full_text)

        return {
            "mode": "error",
            "message": "Model returned invalid JSON."
        }
