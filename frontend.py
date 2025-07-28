# Frontend constants and HTML/JS code for BPMN Chatbot
# -------------------------------------------------------------------
# (only the head_html string changed – everything else is untouched)

initial_bpmn_xml = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                  xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                  xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
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

# -------------------------------------------------------------------
# Everything below lives in <head>.  The CSS additions and new JS
# sections are clearly marked with  >>> NEW <<< comments.
# -------------------------------------------------------------------
head_html = f"""
<head>
    <!-- bpmn-js Modeler CSS -->
    <link rel="stylesheet" href="https://unpkg.com/bpmn-js@18.6.2/dist/assets/bpmn-js.css">
    <link rel="stylesheet" href="https://unpkg.com/bpmn-js@18.6.2/dist/assets/diagram-js.css">
    <link rel="stylesheet" href="https://unpkg.com/bpmn-js@18.6.2/dist/assets/bpmn-font/css/bpmn.css">

    <!-- bpmn-js Modeler JS -->
    <script src="https://unpkg.com/bpmn-js@18.6.2/dist/bpmn-modeler.development.js"></script>

    <style>
        /* -----------------------------------------------------------------
           Existing styling
        ------------------------------------------------------------------*/
        .bpmn-container {{ height: 600px; border: 1px solid #eee; border-radius: 8px; background-color: #f9f9f9; }}
        #chatbot        {{ height: 560px; overflow-y: auto; }}
        .bpmn-error     {{ color: red; padding: 10px; background-color: #ffe6e6; border-radius: 4px; margin: 10px 0; }}
        .bpmn-buttons   {{ padding: 10px; display: flex; gap: 10px; }}
        .bpmn-button    {{
            padding: 8px 16px;
            background-color: #1976d2;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }}
        .bpmn-button:hover {{ background-color: #1565c0; }}

        /* >>> NEW <<<  — overlay styling lifted from modeler.html */
        .diagram-note {{
            background-color: rgba(66,180,21,.7);
            color: #fff;
            border-radius: 5px;
            font-family: Arial, sans-serif;
            font-size: 12px;
            padding: 4px 6px;
            min-height: 16px;
            width: 120px;
            text-align: center;
            pointer-events: auto;
            white-space: normal;
        }}
        .needs-discussion:not(.djs-connection) .djs-visual > :nth-child(1) {{
            stroke: rgba(66,180,21,.7) !important;
        }}
    </style>

    <script>
        /* -----------------------------------------------------------------
           1.  Globals
        ------------------------------------------------------------------*/
        let bpmnModeler;
        let isModelerInitialized = false;

        // >>> NEW <<< : overlay bookkeeping
        let pendingOverlaySpecs = [];   // specs waiting for a diagram to load
        const currentOverlayIds  = [];  // overlay handles so we can remove them

        /* -----------------------------------------------------------------
           2.  Utility — add / refresh overlays
        ------------------------------------------------------------------*/
        function applyOverlays(specs = []) {{
            if (!bpmnModeler) return;
            const overlays = bpmnModeler.get('overlays');
            const canvas   = bpmnModeler.get('canvas');

            // Remove previous note overlays & markers
            currentOverlayIds.forEach(id => overlays.remove(id));
            currentOverlayIds.length = 0;  // reset array

            canvas.removeMarker && canvas._eventBus && canvas._eventBus.fire; // keep tree-shakers happy :-)

            specs.forEach(spec => {{
                if (!spec || !spec.id) return;
                const html       = `<div class="diagram-note">${{spec.text || 'Note'}}</div>`;
                const position   = spec.position || {{ bottom:0, right:0 }};
                const overlayId  = overlays.add(spec.id, 'note', {{ position, html }});
                currentOverlayIds.push(overlayId);

                if (spec.markerClass)
                    canvas.addMarker(spec.id, spec.markerClass);
            }});
        }}

        /* -----------------------------------------------------------------
           3.  Render BPMN
        ------------------------------------------------------------------*/
        async function renderBpmn(xml) {{
            if (!bpmnModeler || !xml?.trim()) return;
            try {{
                await bpmnModeler.importXML(xml);
                bpmnModeler.get('canvas').zoom('fit-viewport');

                // >>> NEW <<<  — now (re)apply overlays
                applyOverlays(pendingOverlaySpecs);
            }} catch (err) {{
                console.error('Error rendering BPMN XML:', err);
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

        /* -----------------------------------------------------------------
           4.  Modeler setup (unchanged except final call to renderBpmn)
        ------------------------------------------------------------------*/
        function initializeBpmnModeler() {{
            try {{
                bpmnModeler = new BpmnJS({{ container: '#bpmn-canvas' }});
                isModelerInitialized = true;

                // Render initial XML
                const textarea = document.querySelector('#bpmn_xml_output textarea');
                if (textarea?.value?.trim()) renderBpmn(textarea.value);
            }} catch (err) {{
                console.error("Failed to initialize BPMN Modeler:", err);
            }}
        }}

        /* -----------------------------------------------------------------
           5.  MutationObservers
        ------------------------------------------------------------------*/
        function setupBpmnWatcher() {{
            const xmlBox     = document.getElementById('bpmn_xml_output');
            const overlayBox = document.getElementById('overlay_specs');

            if (xmlBox) {{
                const obs = new MutationObserver(() => {{
                    const val = xmlBox.querySelector('textarea')?.value;
                    if (val?.trim() && isModelerInitialized) renderBpmn(val);
                }});
                obs.observe(xmlBox, {{ childList:true, subtree:true, attributes:true }});
            }}

            // >>> NEW <<<  — watch overlay specs
            if (overlayBox) {{
                const obs2 = new MutationObserver(() => {{
                    const raw = overlayBox.querySelector('textarea')?.value;
                    try {{
                        pendingOverlaySpecs = raw ? JSON.parse(raw) : [];
                    }} catch (e) {{
                        console.warn("Overlay JSON parse error:", e);
                        pendingOverlaySpecs = [];
                    }}
                    if (isModelerInitialized) applyOverlays(pendingOverlaySpecs);
                }});
                obs2.observe(overlayBox, {{ childList:true, subtree:true, attributes:true }});
            }}
        }}

        /* -----------------------------------------------------------------
           6.  Boot sequence
        ------------------------------------------------------------------*/
        function setupBpmn() {{
            initializeBpmnModeler();
            setTimeout(setupBpmnWatcher, 500);    // allow DOM to settle
        }}

        if (document.readyState === 'loading')
            document.addEventListener('DOMContentLoaded', () => setTimeout(setupBpmn, 1000));
        else
            setTimeout(setupBpmn, 1000);
    </script>
</head>
"""
