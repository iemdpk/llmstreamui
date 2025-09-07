
import streamlit as st
import requests
import time
import urllib.parse

# --- Configuration ---
# The two API endpoints provided by the user.
INSERT_API_URL = "https://nodejsllm-1.onrender.com/insert"
STREAM_API_URL = "https://nodejsllm-1.onrender.com/true"

# The name of the bot for the chat interface.
BOT_NAME = "API Chatbot"

# A brief explanation of the bot.
st.title(BOT_NAME)
st.markdown("A simple chatbot powered by your custom APIs.")

# --- Session State Initialization ---
# This ensures that the chat history is preserved across reruns.
# It stores messages as a list of dictionaries.
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Helper Functions ---

def get_chatbot_response_stream(prompt: str):
    """
    Submits a task to the 'insert' API and then polls the 'true' API
    for streaming output.

    Args:
        prompt (str): The user's input message.

    Yields:
        str: Chunks of the chatbot's generated response.
    """
    try:
        # 1. Prepare and send the request to the 'insert' API.
        params = {
            "task": prompt,
            "context": "general chatbot conversation",
            "required": "short answer only answer which is asked,dont answer anything else"
        }
        encoded_params = urllib.parse.urlencode(params)
        insert_url = f"{INSERT_API_URL}?{encoded_params}"
        
        insert_response = requests.get(insert_url)
        insert_response.raise_for_status()
        
        insert_data = insert_response.json()
        if not insert_data.get("success"):
            yield "Error: Failed to insert task. The API returned an error."
            return
        
        # 2. Poll the 'true' API for the generated output.
        # This is the polling loop.
        
        poll_count = 0
        max_polls = 60  # Increased limit for longer responses
        poll_interval = 0.5  # Reduced interval for faster streaming effect
        
        last_output = ""
        
        while poll_count < max_polls:
            poll_response = requests.get(STREAM_API_URL)
            poll_response.raise_for_status()
            poll_data = poll_response.json()

            # Handle the case where the API returns a list of JSON objects
            if isinstance(poll_data, list) and poll_data:
                last_data = poll_data[-1]
            else:
                last_data = poll_data

            # Check if the generation is complete
            current_output = last_data.get("output", "")
            
            # Yield new characters since the last poll
            new_chars = current_output[len(last_output):]
            if new_chars:
                yield new_chars
                
            last_output = current_output
            
            if last_data.get("status"):
                break
            
            # Wait before the next poll
            time.sleep(poll_interval)
            poll_count += 1
        
        # if poll_count >= max_polls:
        #     yield "\n\nSorry, the API timed out while generating a response."
    
    except requests.exceptions.RequestException as e:
        yield f"An API request error occurred: {e}"
    except Exception as e:
        yield f"An unexpected error occurred: {e}"

# --- Main Chatbot Logic ---

# Display existing messages in the chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle user input from the chat box
if prompt := st.chat_input("Ask something..."):
    # Add user message to chat history and display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get the chatbot's response in a streaming fashion
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        for response_chunk in get_chatbot_response_stream(prompt):
            full_response += response_chunk
            message_placeholder.markdown(full_response + "▌") # Add a blinking cursor effect
        
        # Once streaming is done, display the final response
        message_placeholder.markdown(full_response)
        
        # Add the final full response to the session state
        st.session_state.messages.append({"role": "assistant", "content": full_response})
