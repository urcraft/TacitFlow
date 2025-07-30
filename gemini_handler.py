"""
gemini_handler.py
-----------------
Handles all interaction with the Google Gemini model for the BPMN Chatbot.

Key additions:
  • The system and follow-up prompts now instruct Gemini to append a JSON
    code-block containing overlay comment specs.
  • Robust parsing of that JSON block; defaults to "[]" if missing.
  • Function signature, imports and client usage remain unchanged so the
    surrounding app code continues to work.
"""

import re
from frontend import initial_bpmn_xml


def _build_system_prompt() -> str:
    """
    A single, reusable instruction that forces the model to reply
    with TWO fenced code blocks:

      1. Complete BPMN 2.0 XML (```xml … ```)
      2. Overlay comment array (```json … ```)

    The second block enables sticky-note overlays in the front-end.
    """
    return (

        """You are a senior BPMN architect.  
        Your task on every request is to **create or modify a BPMN 2.0 diagram** that faithfully represents the business process described by the user.

        ────────────────────────────────────────  OUTPUT FORMAT  ────────────────────────────────────────
        You MUST respond with **exactly two fenced code-blocks and nothing else**:

        1️⃣ A ```xml``` block containing the COMPLETE BPMN 2.0 XML.  
        2️⃣ A ```json``` block containing an ARRAY of overlay comment objects.

        Do **NOT** print any prose, explanations, Markdown headers, or empty lines outside those two blocks.

        ─ XML code-block  ───────────────────────────────────────────────────────────────────────────────
        • Include an explicit XML declaration line (`<?xml version="1.0" encoding="UTF-8"?>`).  
        • The root element must be `<bpmn:definitions>` with all standard BPMN namespaces.  
        • Every `<bpmn:*>` element needs a unique `id`.  
        • Add a proper `<bpmndi:BPMNDiagram>` + `<bpmndi:BPMNPlane>` with realistic coordinates so the diagram can render without manual layout.  
        • Keep the diagram **minimal**: use the simplest constructs that convey the logic; avoid superfluous tasks or gateways.  
        • Use explicit start and end events wherever the process begins or ends.  
        • Use pools/lanes only when roles are relevant; otherwise omit for clarity.  
        • SequenceFlow labels should be concise and, where obvious, may be omitted.  
        • If the user asks to *modify* an existing diagram, re-use the element IDs that are still valid.

        ─ JSON code-block (overlay comments) ────────────────────────────────────────────────────────────
        Return an array, e.g.

        ```json
        [
        {
            "id": "Gateway_12",
            "text": "Mixed up the yes/no labels?",
            "markerClass": "needs-discussion",
            "position": { "bottom": 0, "right": 0 }   // optional; omit for default bottom-right
        }
        ]
        ````

        • **id** - the BPMN element `id` the comment refers to.
        • **text** - ≤ 60-char note written in second person (“Clarify …”, “Check …”).
        • **markerClass** - always `"needs-discussion"`.
        • **position** - optional object with any combination of `top`, `left`, `right`, `bottom` (integers, px offsets).
        • If no comments are needed, output an empty array `[]`.
        • **Only create comment objects when the user explicitly asks for comments, feedback, review, critique, or similar. If the user does not request this, return an empty array `[]`.**


        ────────────────────────────────────────  MODELLING GUIDELINES  ─────────────────────────────────
        • Model the *happy path* first; add exceptions only when described.
        • Prefer XOR gateways for exclusive decisions; use Parallel gateways for splits/joins that are truly concurrent.
        • Avoid ad-hoc subprocesses unless explicitly requested.
        • Use clear, action-oriented task names (“Validate Order”, “Send Invoice”).
        • Do not invent domain steps the user never mentioned.
        • Keep lane-role names consistent with what the user provides.

        ────────────────────────────────────────  REMEMBER  ─────────────────────────────────────────────
        The only valid response format is:

        ```xml
        <!-- full XML here -->
        ```

        ```json
        <!-- overlay array here -->
        ```

        No extra commentary, no markdown outside the fences."""
    )


def _build_followup_prompt(user_prompt: str, current_xml: str) -> str:
    """
    Prompt used after the first turn.  Gives the model the existing diagram
    to edit and repeats the overlay instruction.
    """
    return (
        "Here is the CURRENT BPMN diagram you produced.  The user now requests changes.\n\n"
        "```xml\n"
        f"{current_xml}\n"
        "```\n\n"
        f"USER REQUEST:\n{user_prompt}\n\n"
        "Return ONLY the two code-blocks (xml + json) as previously described."
    )


# ------------------------------------------------------------------------
#  Main handler expected by app.py
# ------------------------------------------------------------------------
def get_bpmn_from_gemini_internal(
    chat_history,
    chat_state,
    current_xml,
    client,
    gemini_api_available,
):
    """
    Parameters
    ----------
    chat_history : list[list[str|None, str|None]]
        Gradio's running history [(user, bot), …]
    chat_state : genai.Chat | None
        The live Gemini chat session
    current_xml : str
        Latest BPMN XML shown in the UI
    client : genai.Client | None
        Already-initialised Gemini client (or None if key missing)
    gemini_api_available : bool
        Flags whether we can call the API

    Returns
    -------
    tuple
        (chat_history, bpmn_xml, overlay_json, chat_state)
    """
    user_prompt = chat_history[-1][0]

    # ------------------------------------------------------------------ #
    # 0.  Safeguard: no API key                                          #
    # ------------------------------------------------------------------ #
    if not gemini_api_available or not client:
        err = "Google Gemini API key not found. Add GEMINI_FREE_API_KEY to .env."
        chat_history[-1] = (user_prompt, err)
        return chat_history, initial_bpmn_xml, "[]", None

    # ------------------------------------------------------------------ #
    # 1.  First-turn vs follow-up logic                                  #
    # ------------------------------------------------------------------ #
    is_first_turn = chat_state is None
    if is_first_turn:
        system_prompt = _build_system_prompt()

        # Start a **brand-new** chat session and send the system prompt
        chat = client.chats.create(model="gemini-2.5-pro")
        chat.send_message(system_prompt)

        # User’s actual request (diagram description)
        message_to_send = (
            user_prompt
            + "\n\nRemember: respond with the two code-blocks (xml + json)."
        )
    else:
        chat = chat_state
        message_to_send = _build_followup_prompt(user_prompt, current_xml)

    # ------------------------------------------------------------------ #
    # 2.  Ask Gemini                                                     #
    # ------------------------------------------------------------------ #
    try:
        response = chat.send_message(message_to_send)
        raw_text = response.text or ""

        # -------------------------------------------------------------- #
        # 2a.  Extract BPMN XML code-block                               #
        # -------------------------------------------------------------- #
        xml_match = re.search(r"```xml\s*([\s\S]*?)\s*```", raw_text, re.IGNORECASE)
        generated_xml = xml_match.group(1).strip() if xml_match else ""

        # Pre-flight: if we somehow got markdown chatter or no defs tag,
        # fall back to initial template so the front-end never breaks.
        if not generated_xml or "<bpmn:definitions" not in generated_xml:
            generated_xml = initial_bpmn_xml
        # Ensure XML declaration
        if not generated_xml.lstrip().startswith("<?xml"):
            generated_xml = (
                '<?xml version="1.0" encoding="UTF-8"?>\n' + generated_xml
            )

        print(f"Generated XML:\n{generated_xml}")

        # -------------------------------------------------------------- #
        # 2b.  Extract overlay JSON code-block                           #
        # -------------------------------------------------------------- #
        json_match = re.search(
            r"```json\s*([\s\S]*?)\s*```", raw_text, re.IGNORECASE
        )
        overlay_json = json_match.group(1).strip() if json_match else "[]"

        print(f"Overlay comments: {overlay_json}")

        # -------------------------------------------------------------- #
        # 2c.  Update chat history (bot message is generic)              #
        # -------------------------------------------------------------- #
        chat_history[-1] = (
            user_prompt,
            "Here is the updated BPMN diagram based on your request:",
        )

        return chat_history, generated_xml, overlay_json, chat

    except Exception as exc:
        # Fail gracefully: keep previous XML, drop overlays
        err_msg = f"❌ Gemini API error: {exc}"
        chat_history[-1] = (user_prompt, err_msg)
        return chat_history, current_xml or initial_bpmn_xml, "[]", chat_state
