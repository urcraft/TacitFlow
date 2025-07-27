# Frontend constants and HTML/JS code for BPMN Chatbot

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
