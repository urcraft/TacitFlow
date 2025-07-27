import gradio as gr
import os
from google import genai
import functools
from frontend import initial_bpmn_xml, head_html
from gemini_handler import get_bpmn_from_gemini_internal

# Use GEMINI_FREE_API_KEY for free tier access
# If you have a paid tier, you can use "GEMINI_API_KEY" instead
API_KEY = os.environ.get("GEMINI_FREE_API_KEY") 

if API_KEY:
    client = genai.Client(api_key=API_KEY)
    GEMINI_API_AVAILABLE = True
    print("Successfully loaded GEMINI_API_KEY from .env file or environment variables.")
else:
    client = None
    GEMINI_API_AVAILABLE = False
    print("WARNING: GEMINI_API_KEY not found. Please create a .env file and add your key.")

# Create partial function with bound client and API status
get_bpmn_handler = functools.partial(
    get_bpmn_from_gemini_internal, 
    client=client, 
    gemini_api_available=GEMINI_API_AVAILABLE
)

# --- Gradio UI and Backend Logic ---

# Define the Gradio interface
with gr.Blocks(head=head_html, title="BPMN Chatbot") as demo:
    chat_state = gr.State()
    gr.Markdown("# 🤖 BPMN Generation Chatbot")
    gr.Markdown("Describe a business process and I'll create a BPMN diagram for you. You can also ask me to modify existing diagrams with specific changes.")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## 💬 Chat")
            chatbot = gr.Chatbot(
                elem_id="chatbot",
                value=[(None, "Hello! I can help you design business processes by creating BPMN diagrams.\n\n**How to use:**\n1. **Generate BPMN diagrams**: Describe your business process and I'll create a BPMN diagram\n2. **Modify diagrams**: Once you have a diagram, ask me to make specific changes\n\nHow can I help you today?")]
            )
            user_input = gr.Textbox(
                show_label=False,
                placeholder="e.g., 'A customer places an order for a pizza...' or 'Please add a payment step after order confirmation'",
            )
            submit_btn = gr.Button("Send", variant="primary")

        with gr.Column(scale=6):
            gr.Markdown("## 🖼️ BPMN Diagram Editor")
            
            gr.HTML('<div id="bpmn-canvas" class="bpmn-container"></div>')
            
            # Hidden field to store the current XML
            bpmn_xml_output = gr.Textbox(
                value=initial_bpmn_xml,
                elem_id="bpmn_xml_output",
                visible=False
            )

    # The .then() event listener is used to chain events.
    # 1. The user's input is submitted.
    # 2. add_user_message runs first, adding the user's prompt to the chat and clearing the input box.
    # 3. get_ai_response runs second, taking the updated chat history to get the AI's reply.
    user_input.submit(
        fn=lambda u, c: (c + [[u, None]], ""),
        inputs=[user_input, chatbot],
        outputs=[chatbot, user_input],
        queue=False
    ).then(
        fn=get_bpmn_handler,
        inputs=[chatbot, chat_state, bpmn_xml_output],
        outputs=[chatbot, bpmn_xml_output, chat_state]
    )

    submit_btn.click(
        fn=lambda u, c: (c + [[u, None]], ""),
        inputs=[user_input, chatbot],
        outputs=[chatbot, user_input],
        queue=False
    ).then(
        fn=get_bpmn_handler,
        inputs=[chatbot, chat_state, bpmn_xml_output],
        outputs=[chatbot, bpmn_xml_output, chat_state]
    )

if __name__ == "__main__":
    # To run this app on your local computer:
    # 1. Create a file named .env in the same directory as this script.
    # 2. Add your Google API key to the .env file like this:
    #    GEMINI_API_KEY="your_actual_api_key"
    # 3. Run the script from your terminal: python your_script_name.py
    if not GEMINI_API_AVAILABLE:
        print("="*80)
        print("WARNING: GEMINI_API_KEY could not be loaded.")
        print("The application will run, but the chatbot will not connect to the Gemini API.")
        print("Please create a .env file and add your key.")
        print("="*80)
        
    demo.launch()
