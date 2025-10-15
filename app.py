import gradio as gr
import os
from google import genai
import functools
from frontend import initial_bpmn_xml, head_html
from gemini_handler import get_bpmn_from_gemini_internal

API_KEY = os.environ.get("GEMINI_API_KEY")
#API_KEY = os.environ.get("GEMINI_FREE_API_KEY")
if API_KEY:
    client = genai.Client(api_key=API_KEY)
    GEMINI_API_AVAILABLE = True
else:
    client = None
    GEMINI_API_AVAILABLE = False

get_bpmn_handler = functools.partial(
    get_bpmn_from_gemini_internal,
    client=client,
    gemini_api_available=GEMINI_API_AVAILABLE
)


with gr.Blocks(head=head_html, title="BPMN Chatbot") as demo:
    chat_state = gr.State()
    gr.Markdown("# 🤖 BPMN Generation Chatbot")
    gr.Markdown("Describe a business process to generate a BPMN diagram. Once you have a model, ask for comments or analysis to identify improvement opportunities for AS-IS to TO-BE transformation.")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## 💬 Chat")
            chatbot = gr.Chatbot(
                elem_id="chatbot",
                value=[(None,
                        "Hello! I can help you design business processes by creating BPMN diagrams…")]
            )
            user_input = gr.Textbox(show_label=False,
                                    placeholder="Describe a process or modification")
            submit_btn = gr.Button("Send", variant="primary")

        with gr.Column(scale=6):
            gr.Markdown("## 🖼️ BPMN Diagram Editor")
            gr.HTML('<div id="bpmn-canvas" class="bpmn-container"></div>')

            bpmn_xml_output = gr.Textbox(value=initial_bpmn_xml,
                                         elem_id="bpmn_xml_output",
                                         visible=False)
            overlay_specs_output = gr.Textbox(value="[]",          # default empty array
                                              elem_id="overlay_specs",
                                              visible=False)
    
    def _add_user_msg(user_msg, chat_hist):
        return chat_hist + [[user_msg, None]], ""

    user_input.submit(
        fn=_add_user_msg,
        inputs=[user_input, chatbot],
        outputs=[chatbot, user_input],
        queue=False
    ).then(
        fn=get_bpmn_handler,
        # inputs are unchanged – chat_state & XML suffice
        inputs=[chatbot, chat_state, bpmn_xml_output],
        # now FOUR outputs in the order expected by gemini_handler
        outputs=[chatbot, bpmn_xml_output, overlay_specs_output, chat_state]
    )

    submit_btn.click(
        fn=_add_user_msg,
        inputs=[user_input, chatbot],
        outputs=[chatbot, user_input],
        queue=False
    ).then(
        fn=get_bpmn_handler,
        inputs=[chatbot, chat_state, bpmn_xml_output],
        outputs=[chatbot, bpmn_xml_output, overlay_specs_output, chat_state]
    )

if __name__ == "__main__":
    if not GEMINI_API_AVAILABLE:
        print("WARNING: GEMINI_API_KEY not found – the app will run offline.")
    demo.launch()
