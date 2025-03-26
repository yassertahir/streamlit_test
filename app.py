import streamlit as st
import time
import os
from openai import OpenAI
from utils import create_assistant, create_thread, create_message, get_response
import json
import speech_recognition as sr

def transcribe_speech():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.write("Speak something...")
        audio_data = r.listen(source)
        return r.recognize_google(audio_data)
# Set page configuration
st.set_page_config(page_title="VC Assistant", layout="wide")
# File to store IDs
# STORAGE_FILE = "assistant_data.json"
# Initialize API client
OPENAI_API_KEY = st.secrets["openai_api_key"]
client = OpenAI(api_key=OPENAI_API_KEY)

# File to store IDs - use absolute path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_FILE = os.path.join(BASE_DIR, "assistant_data.json")

# Show the file path
st.sidebar.info(f"Storage file location: {STORAGE_FILE}")

# Function to load or create assistant and thread
def get_or_create_assistant_and_thread():
    # Default values
    assistant_id = None
    thread_id = None
    
    # Check if storage file exists
    try:
        if os.path.exists(STORAGE_FILE):
            with open(STORAGE_FILE, "r") as f:
                data = json.load(f)
                
                # Verify the assistant still exists
                try:
                    assistant = client.beta.assistants.retrieve(data.get("assistant_id", ""))
                    assistant_id = data["assistant_id"]
                    st.sidebar.info(f"Using existing assistant: {assistant_id}")
                except Exception as e:
                    st.sidebar.warning(f"Assistant retrieval error: {e}")
                    assistant_id = None
                    
                # Verify the thread still exists
                try:
                    thread = client.beta.threads.retrieve(data.get("thread_id", ""))
                    thread_id = data["thread_id"]
                except Exception as e:
                    st.sidebar.warning(f"Thread retrieval error: {e}")
                    thread_id = None
    except Exception as e:
        st.sidebar.warning(f"Storage file error: {e}")
        assistant_id = None
        thread_id = None
    
    # Create new assistant if needed
    if assistant_id is None:
        try:
            assistant_id = create_assistant(client)
            st.sidebar.success(f"Created new assistant: {assistant_id}")
        except Exception as e:
            st.sidebar.error(f"Failed to create assistant: {e}")
            return None, None
    
    # Create new thread if needed
    if thread_id is None:
        try:
            thread_id = create_thread(client)
        except Exception as e:
            st.sidebar.error(f"Failed to create thread: {e}")
            return assistant_id, None
    
    # Save IDs
    try:
        os.makedirs(os.path.dirname(STORAGE_FILE), exist_ok=True)
        with open(STORAGE_FILE, "w") as f:
            json.dump({
                "assistant_id": assistant_id,
                "thread_id": thread_id
            }, f)
        st.sidebar.success("Assistant data saved successfully!")
    except Exception as e:
        st.sidebar.error(f"Failed to save assistant data: {e}")
    
    return assistant_id, thread_id
# Add this function BEFORE it's used in the file upload section
def wait_for_active_runs(client, thread_id, max_wait_seconds=60):
    """Check for and wait for any active runs to complete with timeout"""
    start_time = time.time()
    
    while True:
        # Check if we've waited too long
        elapsed_time = time.time() - start_time
        if elapsed_time > max_wait_seconds:
            st.sidebar.warning(f"Timed out after waiting {max_wait_seconds} seconds for run to complete")
            return False
        
        # List runs for the thread
        runs = client.beta.threads.runs.list(thread_id=thread_id)
        
        # Filter for active runs
        active_runs = [run for run in runs.data if run.status in ["queued", "in_progress"]]
        requires_action_runs = [run for run in runs.data if run.status == "requires_action"]
        
        # No runs at all, we can continue
        if not active_runs and not requires_action_runs:
            return True
            
        # If there are runs requiring action, don't wait for them here
        if requires_action_runs:
            st.sidebar.info("Run requires action - continuing with function calling...")
            return True
        
        # Only wait for queued or in_progress runs
        if active_runs:
            status = active_runs[0].status
            st.sidebar.info(f"Waiting for active run to complete ({status})... {int(elapsed_time)}s elapsed")
            time.sleep(1)
# Get or create assistant and thread
assistant_id, thread_id = get_or_create_assistant_and_thread()
st.session_state.assistant_id = assistant_id
st.session_state.thread_id = thread_id
if os.path.exists(STORAGE_FILE):
    st.sidebar.success("Assistant configuration saved!")
else:
    st.sidebar.error("Failed to save assistant configuration!")
# Initialize message history
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Fetch messages from thread
    messages = client.beta.threads.messages.list(thread_id=st.session_state.thread_id)
    for msg in reversed(messages.data):  # Reversed to show oldest messages first
        role = msg.role
        # Extract content from message parts
        content = ""
        for part in msg.content:
            if part.type == "text":
                content += part.text.value
        st.session_state.messages.append({"role": role, "content": content})

# Display chat history
st.title("VC Assistant")
st.markdown("""
This assistant evaluates startup proposals like a venture capitalist. 
Submit your business idea to get feedback and a score.
""")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Add this code at the BEGINNING of your sidebar section, before the file upload code:
with st.sidebar:
    st.subheader("Conversation")
    
    # Add a prominent button to start a new conversation
    if st.button("Start New Conversation", type="primary"):  # Using 'primary' type for emphasis
        # Create a new thread
        new_thread_id = create_thread(client)
        
        # Update the storage file
        try:
            with open(STORAGE_FILE, "r") as f:
                data = json.load(f)
            
            data["thread_id"] = new_thread_id
            
            with open(STORAGE_FILE, "w") as f:
                json.dump(data, f)
            
            # Update session state
            st.session_state.thread_id = new_thread_id
            st.session_state.messages = []
            st.session_state.processed_files = set()
            
            st.sidebar.success("Started a new conversation!")
            st.rerun()  # Using rerun instead of experimental_rerun
        except Exception as e:
            st.sidebar.error(f"Error starting new conversation: {e}")
    
    st.divider()  # Add a visual separator
    
    # Continue with the existing file upload section
    st.subheader("Upload Documents")
    
    # Create a set for processed files
    if "processed_files" not in st.session_state:
        st.session_state.processed_files = set()
        
    # Track files pending analysis
    if "pending_files" not in st.session_state:
        st.session_state.pending_files = []

    # Allow multiple files
    uploaded_files = st.file_uploader(
        "Upload files...", 
        accept_multiple_files=True,
        type=["pdf", "csv", "xlsx", "docx", "txt"]
    )
    
    # Show what files are ready to be analyzed
    if uploaded_files:
        st.write("Files ready for analysis:")
        for uploaded_file in uploaded_files:
            if uploaded_file.name in st.session_state.processed_files:
                st.write(f"✅ {uploaded_file.name} (already processed)")
            else:
                st.write(f"📄 {uploaded_file.name}")
    
    # Add a button to process all uploaded files
    if uploaded_files and any(file.name not in st.session_state.processed_files for file in uploaded_files):
        if st.button("Analyze All Files"):
            file_ids = []
            file_names = []
            
            # First, upload all files to OpenAI
            for uploaded_file in uploaded_files:
                if uploaded_file.name not in st.session_state.processed_files:
                    # Build a full path based on the current file's directory
                    temp_file_path = os.path.join(BASE_DIR, f"{uploaded_file.name}")
                    # print(temp_file_path)
                    # Write the file to that path
                    with open(temp_file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    try:
                        # Upload file to OpenAI
                        file = client.files.create(
                            file=open(temp_file_path, "rb"),
                            purpose="assistants"  # This is critical
                        )
                        
                        # Add to our tracking lists
                        file_ids.append({
                            "file_id": file.id, 
                            "file_name": uploaded_file.name
                        })
                        file_names.append(uploaded_file.name)
                        st.sidebar.success(f"File uploaded: {uploaded_file.name}")
                        
                        # Clean up temp file
                        os.remove(temp_file_path)
                        
                        # Mark as processed
                        st.session_state.processed_files.add(uploaded_file.name)
                        
                    except Exception as e:
                        st.sidebar.error(f"Error uploading {uploaded_file.name}: {e}")
            
            # If we have files to process
            if file_ids:
                # Wait for any active runs
                wait_for_active_runs(client, st.session_state.thread_id)
                
                
                # Separate CSV files from other files for appropriate handling
                csv_files = [f for f in file_ids if f["file_name"].lower().endswith('.csv')]
                non_csv_files = [f for f in file_ids if not f["file_name"].lower().endswith('.csv')]
                
                # Create attachments list for file_search-compatible files
                attachments = []
                for file_info in non_csv_files:
                    attachments.append({
                        "file_id": file_info["file_id"],
                        "tools": [{"type": "file_search"}]
                    })
                
                # Create attachments list for CSV files that need code_interpreter
                csv_attachments = []
                for file_info in csv_files:
                    csv_attachments.append({
                        "file_id": file_info["file_id"],
                        "tools": [{"type": "code_interpreter"}]  # CSV files need code_interpreter
                    })
                
                # Create a message with all attachments
                message_text = f"I've uploaded {len(file_ids)} files for analysis: {', '.join(file_names)}. "
                
                if csv_files:
                    message_text += f"The following are CSV files that need code_interpreter: {', '.join(f['file_name'] for f in csv_files)}. "
                
                message_text += "Please analyze all files together for a comprehensive evaluation."
                
                # Create message with all attachments
                message = client.beta.threads.messages.create(
                    thread_id=st.session_state.thread_id,
                    role="user",
                    content=[{
                        "type": "text",
                        "text": message_text
                    }],
                    attachments=attachments + csv_attachments  # Combine all attachments
                )
                st.sidebar.write(f"Attaching files: {[a['file_id'] for a in attachments]}")
                # run = client.beta.threads.runs.create(
                # thread_id=thread_id,
                # assistant_id=assistant_id)
                # Wait for any active runs that message might create
                wait_for_active_runs(client, st.session_state.thread_id)
                time.sleep(5)  # Give OpenAI time to process the file
                # Create a run to analyze all files
                with st.spinner("Analyzing files..."):
                    has_csv = any(file.endswith('.csv') for file in file_names)
                    has_pdf = any(file.endswith('.pdf') for file in file_names)
                    
                    # Build dynamic instructions
                    instructions = "Please analyze all the uploaded files together to provide a comprehensive evaluation. "

                    if has_csv:
                        instructions += "For CSV files, use the code_interpreter tool to analyze the data. "

                    if has_pdf and has_csv:
                        instructions += "Use both the business plan in the PDF and analyze the competitive data in the CSV files. "

                    instructions += (
                        "Use your VC evaluation framework and the configured functions to evaluate the startup proposal. "
                    )

                    # Append final, more detailed section
                    instructions += """
                    Please provide a comprehensive evaluation of the attached startup proposal. 
                    Follow the structure below and ensure each bullet is explained in multiple sentences or paragraphs:

                    1. Summary of the proposal
                    2. Strengths 
                    3. Areas for improvement
                    4. Team assessment (with LinkedIn profiles and a detailed table of team members if CVs are provided)
                    5. Competitive analysis
                    6. Overall score (1-10)
                    7. Final recommendation

                    At the end, always provide a Team Table with columns:
                    - Experience Summary
                    - Contact Details from CV

                    Remember to reference all attached files (PDFs, CSVs, etc.) during the analysis.
                    """

                    # Use this combined instructions string when creating the run
                    run = client.beta.threads.runs.create(
                        thread_id=st.session_state.thread_id,
                        assistant_id=st.session_state.assistant_id,
                        instructions=instructions
                    )
                    
                    # Wait for the run to complete
                    wait_for_active_runs(client, st.session_state.thread_id)
                    
                    # Add message to chat history
                    st.session_state.messages.append({
                        "role": "user", 
                        "content": message_text #f"I've uploaded {len(file_names)} files for analysis: {', '.join(file_names)}"
                    })
                    
                    # Get the response
                    response_content = get_response(client, st.session_state.thread_id, st.session_state.assistant_id)
                    
                    # Add to chat history
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": response_content
                    })
                
                # Force rerun to refresh UI
                st.rerun()
    

# Button to record audio
transcribed_text = ""
if st.button("Start Recording"):
    try:
        transcribed_text = transcribe_speech()
        st.write("Transcription:")
        st.write(transcribed_text)
    except Exception as e:
        st.error(f"Transcription error: {e}")

# Chat input
text_input = st.chat_input("Enter your startup proposal or question")

# If the user didn't type anything, but did record audio, use the transcribed text
if not text_input and transcribed_text:
    text_input = transcribed_text

if text_input:
    # Optionally add a note to the input for guardrails
    final_user_input = f"{text_input}\n\n(Please follow the VC evaluation framework and refuse irrelevant requests)."

    # Display user message
    with st.chat_message("user"):
        st.write(text_input)

    # Create message in your thread
    create_message(client, st.session_state.thread_id, final_user_input)

    # Get assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response_content = get_response(client, st.session_state.thread_id, st.session_state.assistant_id)
            st.write(response_content)   
# # User input area
# user_input = st.chat_input("Enter your startup proposal or question")

# if user_input:
#     # Add user message to chat history
#     final_user_input = f"{user_input}\n\n(Please follow the VC evaluation framework and refuse irrelevant requests)."

#     # Add user message to chat history
#     st.session_state.messages.append({"role": "user", "content": final_user_input})
    
#     # Display user message
#     with st.chat_message("user"):
#         st.write(user_input)
    
#     # Create message in thread

#     create_message(client, st.session_state.thread_id, user_input)
    
#     # Get assistant response
#     with st.chat_message("assistant"):
#         with st.spinner("Thinking..."):
#             response_content = get_response(client, st.session_state.thread_id, st.session_state.assistant_id)
#             st.write(response_content)
    
#     # Add assistant response to chat history
#     st.session_state.messages.append({"role": "assistant", "content": response_content})

