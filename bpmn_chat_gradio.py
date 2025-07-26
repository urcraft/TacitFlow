import gradio as gr
import os
from google import genai
from google.genai import types
import re

API_KEY = os.environ.get("GOOGLE_API_KEY")

if API_KEY:
    os.environ["GOOGLE_API_KEY"] = API_KEY
    client = genai.Client()
    GEMINI_API_AVAILABLE = True
    print("Successfully loaded GOOGLE_API_KEY from .env file or environment variables.")
else:
    client = None
    GEMINI_API_AVAILABLE = False
    print("WARNING: GOOGLE_API_KEY not found. Please create a .env file and add your key.")


# --- BPMN and JS Integration ---

# A default empty diagram to show on startup.
initial_bpmn_xml = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                  xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" 
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" 
                  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" 
                  xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
                  xmlns:semantic="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  targetNamespace="http://bpmn.io/schema/bpmn" 
                  id="Definitions_1">
  <bpmn:process id="Process_1" isExecutable="false">
    <bpmn:startEvent id="StartEvent_1"/>
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
      <bpmndi:BPMNShape id="_BPMNShape_StartEvent_2" bpmnElement="StartEvent_1">
        <dc:Bounds x="179" y="159" width="36" height="36" />
      </bpmndi:BPMNShape>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>
"""

# The HTML and JavaScript code to be injected into the Gradio app's <head>.
head_html = f"""
<head>
    <!-- bpmn-js Modeler CSS -->
    <link rel="stylesheet" href="https://unpkg.com/bpmn-js@18.6.2/dist/assets/bpmn-js.css">
    <link rel="stylesheet" href="https://unpkg.com/bpmn-js@18.6.2/dist/assets/diagram-js.css">
    <link rel="stylesheet" href="https://unpkg.com/bpmn-js@18.6.2/dist/assets/bpmn-font/css/bpmn.css">

    <!-- bpmn-js Modeler JS -->
    <script src="https://unpkg.com/bpmn-js@18.6.2/dist/bpmn-modeler.development.js"></script>

    <style>
        .bpmn-container {{ height: 600px; border: 1px solid #eee; border-radius: 8px; background-color: #f9f9f9; }}
        #chatbot {{ height: 560px; overflow-y: auto; }}
        .bpmn-error {{ color: red; padding: 10px; background-color: #ffe6e6; border-radius: 4px; margin: 10px 0; }}
        .bpmn-buttons {{ padding: 10px; display: flex; gap: 10px; }}
        .bpmn-button {{ 
            padding: 8px 16px; 
            background-color: #1976d2; 
            color: white; 
            border: none; 
            border-radius: 4px;
            cursor: pointer;
        }}
        .bpmn-button:hover {{ background-color: #1565c0; }}
    </style>

    <script>
        let bpmnModeler;
        let isModelerInitialized = false;

        async function renderBpmn(xml) {{
            console.log("renderBpmn called with XML length:", xml ? xml.length : 0);
            
            if (!bpmnModeler) {{
                console.error("BPMN Modeler not initialized.");
                return;
            }}
            
            if (!xml || xml.trim().length === 0) {{
                console.warn("Empty XML provided to renderBpmn");
                return;
            }}
            
            try {{
                console.log("Attempting to import XML:", xml.substring(0, 200) + "...");
                
                await bpmnModeler.importXML(xml);
                bpmnModeler.get('canvas').zoom('fit-viewport');
                console.log("BPMN diagram rendered successfully.");
                
                // Remove any error messages
                const container = document.getElementById('bpmn-canvas');
                const errorMsg = container.querySelector('.bpmn-error');
                if (errorMsg) errorMsg.remove();
                
            }} catch (err) {{
                console.error('Error rendering BPMN XML:', err);
                
                // Show error in the BPMN container
                const container = document.getElementById('bpmn-canvas');
                let errorMsg = container.querySelector('.bpmn-error');
                if (!errorMsg) {{
                    errorMsg = document.createElement('div');
                    errorMsg.className = 'bpmn-error';
                    container.appendChild(errorMsg);
                }}
                errorMsg.innerHTML = `<strong>BPMN Rendering Error:</strong><br>${{err.message || err}}`;
            }}
        }}



        function initializeBpmnModeler() {{
            try {{
                console.log("Initializing BPMN Modeler...");
                
                // Initialize BPMN modeler
                bpmnModeler = new BpmnJS({{
                    container: '#bpmn-canvas'
                }});
                
                isModelerInitialized = true;
                console.log("BPMN Modeler initialized successfully");
                
                // Render initial XML
                const xmlOutputElement = document.getElementById('bpmn_xml_output');
                if (xmlOutputElement && xmlOutputElement.querySelector('textarea')) {{
                    const initialXml = xmlOutputElement.querySelector('textarea').value;
                    if (initialXml && initialXml.trim().length > 0) {{
                        renderBpmn(initialXml);
                    }}
                }}
            }} catch (err) {{
                console.error("Failed to initialize BPMN Modeler:", err);
            }}
        }}

        function setupBpmnWatcher() {{
            const xmlOutputElement = document.getElementById('bpmn_xml_output');
            if (xmlOutputElement) {{
                console.log("Setting up BPMN XML watcher...");
                
                const observer = new MutationObserver((mutations) => {{
                    console.log("XML output changed, checking for updates...");
                    const textarea = xmlOutputElement.querySelector('textarea');
                    if (textarea) {{
                        const newXml = textarea.value;
                        if (newXml && newXml.trim().length > 0 && isModelerInitialized) {{
                            console.log("New XML detected, rendering...");
                            renderBpmn(newXml);
                        }}
                    }}
                }});
                
                observer.observe(xmlOutputElement, {{ 
                    childList: true, 
                    subtree: true, 
                    attributes: true,
                    attributeOldValue: true 
                }});
                
                console.log("BPMN XML watcher setup complete");
            }} else {{
                console.error("Could not find the bpmn_xml_output element.");
            }}
        }}

        function setupBpmn() {{
            console.log("Setting up BPMN components...");
            
            // Initialize modeler first
            initializeBpmnModeler();
            
            // Then setup the watcher
            setTimeout(() => {{
                setupBpmnWatcher();
            }}, 500);
        }}

        // Try multiple initialization approaches
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', () => {{
                setTimeout(setupBpmn, 1000);
            }});
        }} else {{
            setTimeout(setupBpmn, 1000);
        }}

        // Fallback initialization
        setTimeout(() => {{
            if (!isModelerInitialized) {{
                console.log("Fallback initialization triggered");
                setupBpmn();
            }}
        }}, 3000);
    </script>
</head>
"""

# --- Gradio UI and Backend Logic ---

def get_bpmn_from_gemini_internal(chat_history, chat_state, current_xml):
    """
    Internal function that interacts with the Gemini API to generate or modify BPMN.
    """
    user_prompt = chat_history[-1][0]

    if not GEMINI_API_AVAILABLE or not client:
        error_message = "Google API key not found. Please create a .env file and add your GOOGLE_API_KEY."
        # Update the last message with the error
        chat_history[-1] = (user_prompt, error_message)
        return chat_history, initial_bpmn_xml, None

    # Determine if this is the first turn or a follow-up
    is_first_turn = chat_state is None

    if is_first_turn:
        instructional_prompt = """
        You are an expert in Business Process Model and Notation (BPMN) diagram creation.
        
        Based on the user's request, you can perform one of two actions:
        
        1. **CREATE**: Generate a new BPMN diagram from a business process description
        2. **MODIFY**: Update an existing BPMN diagram based on requested changes
        
        CRITICAL XML REQUIREMENTS:
        - Generate ONLY the raw XML code. No explanations, text, or markdown code fences.
        - XML MUST start with <?xml version="1.0" encoding="UTF-8"?>
        - Include all required namespaces in bpmn:definitions:
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" 
          xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
          xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
          xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
        - Every process element MUST have unique ID attributes
        - Include complete BPMNDiagram section with proper coordinates
        - Use appropriate BPMN elements: startEvent, endEvent, task, userTask, serviceTask, exclusiveGateway, parallelGateway, sequenceFlow, etc.
        - Ensure proper layout with realistic coordinates for visual clarity
        """
        # Create a new chat session for the first turn
        chat = client.chats.create(model="gemini-2.5-pro")
        # Send the initial instructions
        chat.send_message(instructional_prompt)
        # The message to send is the user's initial prompt
        message_to_send = user_prompt
    else:
        # Use the existing chat session for follow-up requests
        chat = chat_state
        # Provide the previous XML as context for modifications or analysis
        message_to_send = f"""
        Current BPMN XML:
        ```xml
        {current_xml}
        ```
        
        User request: "{user_prompt}"
        
        Based on this request, determine whether to:
        - MODIFY the existing diagram with the requested changes
        - CREATE a completely new diagram if requested
        
        Return the complete, updated BPMN 2.0 XML. Remember to only output the raw XML code.
        """

    try:
        # Send the user's message (either initial prompt or modification request)
        response = chat.send_message(message_to_send)
        generated_xml = response.text if response.text else ""
        
        # Log the raw response from the model
        print("="*80)
        print("MODEL RESPONSE:")
        print(generated_xml)
        print("="*80)

        # Clean up any potential markdown formatting and whitespace
        if generated_xml:
            # Remove markdown code fences
            xml_match = re.search(r'```(?:xml)?\s*(.*?)\s*```', generated_xml, re.DOTALL)
            if xml_match:
                generated_xml = xml_match.group(1).strip()
                print("EXTRACTED XML (after cleaning markdown):")
                print(generated_xml)
                print("="*80)
            else:
                # Clean up any leading/trailing whitespace
                generated_xml = generated_xml.strip()
            
            # Ensure it starts with XML declaration
            if generated_xml and not generated_xml.startswith('<?xml'):
                print("WARNING: XML doesn't start with declaration, adding one...")
                generated_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + generated_xml
                
            # Basic XML validation
            if '<bpmn:definitions' not in generated_xml:
                print("WARNING: Generated XML doesn't contain BPMN definitions")
                generated_xml = initial_bpmn_xml

        # Set appropriate response message based on request type
        response_message = "Here is the updated BPMN diagram based on your request:"
            
        chat_history[-1] = (user_prompt, response_message)
        return chat_history, generated_xml if generated_xml else initial_bpmn_xml, chat

    except Exception as e:
        error_response = f"An error occurred with the Gemini API: {str(e)}"
        print(f"ERROR: {error_response}")
        # Update the last message with the error
        chat_history[-1] = (user_prompt, error_response)
        return chat_history, initial_bpmn_xml, chat_state

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
            
            # Add a button to download the BPMN XML
            download_btn = gr.Button("📥 Download BPMN XML", variant="secondary")
            
            # Add a JavaScript snippet to handle downloading
            gr.HTML("""
            <script>
                // Add event listener to download button
                document.addEventListener('DOMContentLoaded', function() {
                    setTimeout(function() {
                        // Find the download button by traversing the DOM structure
                        const buttons = document.querySelectorAll('button');
                        let downloadBtn = null;
                        
                        for (const btn of buttons) {
                            if (btn.textContent.includes('Download BPMN XML')) {
                                downloadBtn = btn;
                                break;
                            }
                        }
                        
                        if (downloadBtn) {
                            console.log('Download button found, adding event listener');
                            downloadBtn.addEventListener('click', function() {
                                // Get the current XML from the BPMN modeler instead of the hidden field
                                if (window.bpmnModeler) {
                                    window.bpmnModeler.saveXML({ format: true })
                                        .then(function(result) {
                                            const xml = result.xml;
                                            const blob = new Blob([xml], {type: 'application/xml'});
                                            const url = URL.createObjectURL(blob);
                                            const a = document.createElement('a');
                                            a.href = url;
                                            a.download = 'bpmn-diagram.bpmn';
                                            document.body.appendChild(a);
                                            a.click();
                                            document.body.removeChild(a);
                                            URL.revokeObjectURL(url);
                                        })
                                        .catch(function(err) {
                                            alert('Failed to export BPMN diagram: ' + err.message);
                                        });
                                } else {
                                    alert('BPMN modeler not initialized');
                                }
                            });
                        } else {
                            console.error('Download button not found');
                        }
                    }, 2000);
                });
            </script>
            """)

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
        fn=get_bpmn_from_gemini_internal,
        inputs=[chatbot, chat_state, bpmn_xml_output],
        outputs=[chatbot, bpmn_xml_output, chat_state]
    )

    submit_btn.click(
        fn=lambda u, c: (c + [[u, None]], ""),
        inputs=[user_input, chatbot],
        outputs=[chatbot, user_input],
        queue=False
    ).then(
        fn=get_bpmn_from_gemini_internal,
        inputs=[chatbot, chat_state, bpmn_xml_output],
        outputs=[chatbot, bpmn_xml_output, chat_state]
    )

if __name__ == "__main__":
    # To run this app on your local computer:
    # 1. Create a file named .env in the same directory as this script.
    # 2. Add your Google API key to the .env file like this:
    #    GOOGLE_API_KEY="your_actual_api_key"
    # 3. Run the script from your terminal: python your_script_name.py
    if not GEMINI_API_AVAILABLE:
        print("="*80)
        print("WARNING: GOOGLE_API_KEY could not be loaded.")
        print("The application will run, but the chatbot will not connect to the Gemini API.")
        print("Please create a .env file and add your key.")
        print("="*80)
        
    demo.launch()
