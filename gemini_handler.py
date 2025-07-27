import re
from frontend import initial_bpmn_xml

def get_bpmn_from_gemini_internal(chat_history, chat_state, current_xml, client, gemini_api_available):
    """
    Internal function that interacts with the Gemini API to generate or modify BPMN.
    """
    user_prompt = chat_history[-1][0]

    if not gemini_api_available or not client:
        error_message = "Google API key not found. Please create a .env file and add your GEMINI_API_KEY."
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
        
        IMPORTANT DESIGN PRINCIPLES:
        - Create ONLY what the user explicitly describes - do not add extra steps, decisions, or processes
        - Use the simplest BPMN elements that accurately represent the described process
        - If the user mentions specific roles, systems, or decision points, include those; otherwise keep it minimal
        - Stick to the linear flow described unless the user explicitly mentions parallel paths or complex logic
        - Do not assume additional business rules, validations, or error handling unless mentioned
        
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
