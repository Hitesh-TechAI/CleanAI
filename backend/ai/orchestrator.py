from cleaning.missing import handle_missing
from cleaning.duplicates import remove_duplicates
from cleaning.outliers import remove_outliers
from cleaning.types import handle_types

from utils.chatbot import call_ai


ALLOWED_ACTIONS = {
    "handle_missing": handle_missing,
    "remove_duplicates": remove_duplicates,
    "remove_outliers": remove_outliers,
    "handle_types": handle_types,
}


def build_metadata(df):
    return {
        "row_count": len(df),
        "columns": list(df.columns)
    }


def execute_action(df, action_dict):

    action_name = action_dict.get("action")

    if action_name not in ALLOWED_ACTIONS:
        return df, {"error": "Unauthorized function"}

    func = ALLOWED_ACTIONS[action_name]

    kwargs = action_dict.copy()
    kwargs.pop("action", None)

    df_updated, summary = func(df, **kwargs)

    return df_updated, summary


def run_orchestrator(df, user_message, session_state):

    user_lower = user_message.lower()

    if "duplicate" in user_lower:
        df_updated, summary = remove_duplicates(df)
        session_state["metadata"] = build_metadata(df_updated)

        return df_updated, {
            "type": "executed",
            "message": "I've removed duplicate rows instantly.",
            "summary": summary
        }

    if "metadata" not in session_state:
        session_state["metadata"] = build_metadata(df)

    metadata = session_state["metadata"]

    pending_action = (
        session_state.get("pending_action")
        if session_state.get("pending_action")
        else None
    )

    plan = call_ai(
        user_message=user_message,
        metadata=metadata,
        chat_history=session_state.get("chat_history", []),
        pending_action=pending_action
    )

    if plan.get("mode") == "redirect":
        session_state["pending_action"] = None
        return df, {
            "type": "redirect",
            "message": plan.get("message")
        }

    if plan.get("mode") == "error":
        return df, {
            "type": "error",
            "message": plan.get("message")
        }

    if plan.get("mode") == "proposal":
        session_state["pending_action"] = plan.get("action")
        return df, {
            "type": "proposal",
            "message": plan.get("message"),
            "action": plan.get("action")
        }

    if plan.get("mode") in ["execute", "modify"]:
        action = plan.get("action")

        df_updated, summary = execute_action(df, action)

        session_state["pending_action"] = None
        session_state["metadata"] = build_metadata(df_updated)

        return df_updated, {
            "type": "executed",
            "message": plan.get("message"),
            "summary": summary
        }

    if plan.get("mode") == "complete":
        return df, {
            "type": "complete",
            "message": plan.get("message")
        }

    return df, {
        "type": "error",
        "message": "Unknown response from AI."
    }
