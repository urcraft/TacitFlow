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
<bpmn:definitions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" targetNamespace="http://bpmn.io/schema/bpmn" id="Definitions_1">
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

        async function saveXML() {{
            try {{
                const result = await bpmnModeler.saveXML({{ format: true }});
                console.log("Current BPMN XML:", result.xml);
                
                // Update the hidden textarea with the new XML
                const xmlOutputElement = document.getElementById('bpmn_xml_output');
                if (xmlOutputElement && xmlOutputElement.querySelector('textarea')) {{
                    const textarea = xmlOutputElement.querySelector('textarea');
                    textarea.value = result.xml;
                    
                    // Trigger change event so Gradio recognizes the change
                    const event = new Event('input', {{ bubbles: true }});
                    textarea.dispatchEvent(event);
                    
                    console.log("XML updated in the hidden field");
                }}
                
                alert("Diagram saved!");
            }} catch (err) {{
                console.error("Error saving BPMN XML:", err);
                alert("Failed to save diagram: " + err.message);
            }}
        }}

        function initializeBpmnModeler() {{
            try {{
                console.log("Initializing BPMN Modeler...");
                bpmnModeler = new BpmnJS({{
                    container: '#bpmn-canvas'
                }});
                isModelerInitialized = true;
                console.log("BPMN Modeler initialized successfully");
                
                // Add buttons to the container
                const container = document.getElementById('bpmn-container');
                const buttonsDiv = document.createElement('div');
                buttonsDiv.className = 'bpmn-buttons';
                
                const saveButton = document.createElement('button');
                saveButton.className = 'bpmn-button';
                saveButton.textContent = 'Save Diagram';
                saveButton.onclick = saveXML;
                buttonsDiv.appendChild(saveButton);
                
                container.parentNode.insertBefore(buttonsDiv, container.nextSibling);
                
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

def get_bpmn_from_gemini(user_prompt, chat_history):
    """
    Interacts with the Gemini API to generate BPMN and update the chat.
    """
    if not GEMINI_API_AVAILABLE or not client:
        error_message = "Google API key not found. Please create a .env file and add your GOOGLE_API_KEY."
        chat_history.append((user_prompt, error_message))
        return chat_history, initial_bpmn_xml

    instructional_prompt = """
    You are an expert in Business Process Model and Notation (BPMN).
    Your task is to take a user's description of a business process and convert it into a valid BPMN 2.0 XML format.
    
    CRITICAL REQUIREMENTS:
    1. Generate ONLY the raw XML code. Do not include any other text, explanations, or markdown code fences.
    2. The XML MUST start with <?xml version="1.0" encoding="UTF-8"?>
    3. The XML MUST contain a bpmn:definitions element as the root, with all required namespaces:
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" 
       xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
       xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
       xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
    4. Every process element MUST have a unique ID attribute
    5. Every shape MUST have proper coordinates with dc:Bounds elements
    6. Include a complete BPMNDiagram section with BPMNPlane and BPMNShape elements
    
    The final XML should be fully compatible with bpmn-js modeler for editing.
    """

    try:
        # Create a chat session
        chat = client.chats.create(model="gemini-2.5-flash")
        
        # Send the instructional prompt first
        chat.send_message(instructional_prompt)
        
        # Send the user's process description
        response = chat.send_message(user_prompt)
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

        chat_history.append((user_prompt, "Here is the BPMN diagram based on your description:"))
        return chat_history, generated_xml if generated_xml else initial_bpmn_xml

    except Exception as e:
        error_response = f"An error occurred with the Gemini API: {str(e)}"
        print(f"ERROR: {error_response}")
        chat_history.append((user_prompt, error_response))
        return chat_history, initial_bpmn_xml

# Define the Gradio interface
with gr.Blocks(head=head_html, title="BPMN Chatbot") as demo:
    gr.Markdown("# 🤖 BPMN Generation Chatbot")
    gr.Markdown("Describe a business process, and the AI will generate a BPMN diagram for you.")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## 💬 Chat")
            chatbot = gr.Chatbot(
                elem_id="chatbot",
                value=[(None, "Hello! How can I help you design a business process today?")]
            )
            user_input = gr.Textbox(
                show_label=False,
                placeholder="e.g., A customer places an order for a pizza, we check availability of ingredients and allergy specifications, then bake, package and deliver the product. The customer can opt to pay when the pizza is delivered or during the online ordering process itself.",
            )
            submit_btn = gr.Button("Send", variant="primary")

        with gr.Column(scale=2):
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

    def clear_input_and_get_bpmn(user_prompt, chat_history):
        chat_history, bpmn_xml = get_bpmn_from_gemini(user_prompt, chat_history)
        return chat_history, bpmn_xml, ""

    submit_btn.click(
        fn=clear_input_and_get_bpmn,
        inputs=[user_input, chatbot],
        outputs=[chatbot, bpmn_xml_output, user_input]
    )
    user_input.submit(
        fn=clear_input_and_get_bpmn,
        inputs=[user_input, chatbot],
        outputs=[chatbot, bpmn_xml_output, user_input]
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
