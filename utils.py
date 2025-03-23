import time
from openai import OpenAI
import json
def create_assistant(client):
    """Create a new assistant"""
    function_tools = [
        {
            "type": "function",
            "function": {
                "name": "find_linkedin_profiles",
                "description": "Find LinkedIn profiles for startup team members based on their names and company details",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "team_members": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "Full name of the team member"
                                    },
                                    "role": {
                                        "type": "string",
                                        "description": "Role or title of the team member"
                                    },
                                    "company": {
                                        "type": "string",
                                        "description": "Company or startup name"
                                    }
                                }
                            },
                            "description": "List of team members to find LinkedIn profiles for"
                        }
                    },
                    "required": ["team_members"]
                }
            }
         }
         ,
        {
            "type": "function",
            "function": {
                "name": "find_similar_startups",
                "description": "Find similar startups based on the business description and industry",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "business_description": {
                            "type": "string",
                            "description": "Brief description of the startup's business model or product"
                        },
                        "industry": {
                            "type": "string",
                            "description": "Industry or sector of the startup"
                        },
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Keywords related to the startup's product or service"
                        }
                    },
                    "required": ["business_description"]
                }
            }
        }
    ]
    
    assistant = client.beta.assistants.create(
        name="VC Assistant",
        instructions="""
        You are a venture capitalist evaluating startup proposals.
        Analyze business ideas, provide constructive feedback, and score them on a scale of 1-10.
        Consider factors like market potential, innovation, team, business model, and scalability.
        
        For team analysis:
        1. Extract team member names and roles from the document
        2. Use the find_linkedin_profiles function to research team backgrounds
        3. Evaluate the team's experience and fit for the venture
        
        For market analysis:
        1. Identify the startup's industry and key business model elements
        2. Use the find_similar_startups function to identify competitors
        3. Evaluate the competitive landscape and market opportunity
        
        Structure your response as follows:
        1. Summary of the proposal
        2. Strengths
        3. Areas for improvement
        4. Team assessment (including LinkedIn profiles if found)
        5. Competitive analysis (with similar startups)
        6. Overall score (1-10)
        7. Final recommendation
        
        When analyzing uploaded files, extract key information and provide feedback based on the content.
        """,
        model="gpt-3.5-turbo",  # Use GPT-4o for better function calling capabilities
        tools=[
            {"type": "file_search"},
            {"type": "code_interpreter"}
        ] + function_tools,
        temperature=0.2,  # Lower for more consistent/reliable outputs
        top_p=0.9        # Slightly constrained but allows some flexibility
    )
    
    return assistant.id

def create_thread(client):
    """Create a new thread for conversation"""
    thread = client.beta.threads.create()
    return thread.id

def create_message(client, thread_id, content):
    """Add a user message to a thread"""
    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=content
    )
    return message.id

def get_response(client, thread_id, assistant_id):
    """Create a run and wait for completion to get assistant's response"""
    # First check if a run already exists
    runs = client.beta.threads.runs.list(thread_id=thread_id)
    if len(runs.data) > 0 and runs.data[0].status in ["queued", "in_progress", "requires_action"]:
        run = runs.data[0]  # Use the existing run
    else:
        # Create a new run only if needed
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )
    
    # Poll for run completion or function calls
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        
        if run_status.status == "completed":
            # Get messages
            messages = client.beta.threads.messages.list(
                thread_id=thread_id
            )
            # Return the latest assistant message
            for message in messages.data:
                if message.role == "assistant" and message.run_id == run.id:
                    # Extract content from message parts
                    content = ""
                    for part in message.content:
                        if part.type == "text":
                            content += part.text.value
                    return content
            
            return "No response found."
        
        elif run_status.status == "requires_action":
            # Handle function calling
            try:
                tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    
                    
                    # if function_name == "find_linkedin_profiles":
                    #     def find_linkedin_profiles_impl(team_members):
                    #         import requests
                    #         import os
                            
                    #         # Get API key from environment variable
                    #         api_key = os.environ.get("LINKEDIN_API_KEY")
                    #         if not api_key:
                    #             return {"error": "LinkedIn API key not configured", "profiles": []}
                            
                    #         profiles = []
                            
                    #         for member in team_members:
                    #             name = member.get("name", "").strip()
                    #             role = member.get("role", "").strip()
                    #             company = member.get("company", "").strip()
                                
                    #             if not name:
                    #                 continue
                                    
                    #             try:
                    #                 # Using a service like People Data Labs, Apollo.io, or Hunter.io
                    #                 # This is an example with a hypothetical API
                    #                 url = "https://api.peopledatalabs.com/v5/person/search"
                    #                 headers = {
                    #                     "X-API-Key": api_key,
                    #                     "Content-Type": "application/json"
                    #                 }
                    #                 payload = {
                    #                     "name": name,
                    #                     "company": company,
                    #                     "title": role,
                    #                     "include_linkedin_url": True
                    #                 }
                                    
                    #                 response = requests.post(url, json=payload, headers=headers)
                    #                 data = response.json()
                                    
                    #                 if data.get("status") == 200 and data.get("data"):
                    #                     person = data["data"][0]  # Get first match
                    #                     profiles.append({
                    #                         "name": name,
                    #                         "role": role,
                    #                         "company": company,
                    #                         "linkedin_url": person.get("linkedin_url", ""),
                    #                         "profile_summary": person.get("bio", "No bio available"),
                    #                         "experience": person.get("experience", [])
                    #                     })
                    #                 else:
                    #                     # Fallback to simulated data
                    #                     profiles.append({
                    #                         "name": name,
                    #                         "role": role,
                    #                         "company": company,
                    #                         "linkedin_url": f"https://linkedin.com/in/{name.lower().replace(' ', '-')}",
                    #                         "profile_summary": "Profile not found - this is a placeholder URL",
                    #                         "note": "Real API search returned no results."
                    #                     })
                                        
                    #             except Exception as e:
                    #                 # Error handling with fallback
                    #                 print(f"Error searching for {name}: {e}")
                    #                 profiles.append({
                    #                     "name": name,
                    #                     "role": role,
                    #                     "company": company,
                    #                     "linkedin_url": "#",
                    #                     "profile_summary": f"Error retrieving profile: {str(e)}",
                    #                     "note": "API error occurred."
                    #                 })
                            
                    #         return {"profiles": profiles}
                        
                    #     team_members = function_args.get("team_members", [])
                    #     result = find_linkedin_profiles_impl(team_members)
                        
                    # elif function_name == "find_similar_startups":
                    #     def find_similar_startups_impl(business_description, industry=None, keywords=None):
                    #         # Get API key from environment variable
                    #         api_key = os.environ.get("CRUNCHBASE_API_KEY")
                    #         if not api_key:
                    #             return {"error": "Crunchbase API key not configured", "similar_startups": []}
                            
                    #         import requests
                    #         import os
                            
                    #         try:
                    #             # Build query from industry and keywords
                    #             query = industry if industry else ""
                    #             if keywords:
                    #                 query += " " + " ".join(keywords)
                    #             if not query and business_description:
                    #                 # Extract key terms from business description
                    #                 import re
                    #                 # Simple extraction of nouns over 4 letters
                    #                 words = re.findall(r'\b[A-Za-z]{4,}\b', business_description)
                    #                 query = " ".join(words[:5])  # Take first 5 words
                                
                    #             # Using Crunchbase API
                    #             url = "https://api.crunchbase.com/api/v4/searches/organizations"
                    #             headers = {
                    #                 "X-CB-USER-KEY": api_key,
                    #                 "Content-Type": "application/json"
                    #             }
                    #             payload = {
                    #                 "field_ids": ["name", "short_description", "website_url", "categories"],
                    #                 "query": [
                    #                     {
                    #                         "type": "predicate",
                    #                         "field_id": "facet_ids",
                    #                         "operator_id": "includes",
                    #                         "values": ["company"]
                    #                     },
                    #                     {
                    #                         "type": "predicate", 
                    #                         "field_id": "description",
                    #                         "operator_id": "contains",
                    #                         "values": [query]
                    #                     }
                    #                 ],
                    #                 "limit": 5
                    #             }
                                
                    #             response = requests.post(url, json=payload, headers=headers)
                    #             data = response.json()
                                
                    #             startups = []
                    #             if "entities" in data:
                    #                 for entity in data["entities"]:
                    #                     properties = entity.get("properties", {})
                    #                     startups.append({
                    #                         "name": properties.get("name", "Unknown"),
                    #                         "website": properties.get("website_url", "#"),
                    #                         "description": properties.get("short_description", "No description available"),
                    #                         "categories": properties.get("categories", [])
                    #                     })
                                    
                    #                 return {
                    #                     "similar_startups": startups,
                    #                     "detected_industry": industry or "Based on query: " + query
                    #                 }
                    #             else:
                    #                 # Fallback to our mock implementation if API fails
                    #                 return print(f"Error finding similar startups: {e}") #find_similar_startups_mock(business_description, industry, keywords)                                    
                    #         except Exception as e:
                    #             # print(f"Error finding similar startups: {e}")
                    #             # Fallback to mock implementation
                    #             return {"error": f"Error finding similar startups: {str(e)}", "similar_startups": []}
                            

                    #     business_description = function_args.get("business_description", "")
                    #     industry = function_args.get("industry", None)
                    #     keywords = function_args.get("keywords", [])
                    #     result = find_similar_startups_impl(business_description, industry, keywords)
                        
                    # else:
                    result = {"error": "Function not implemented"}
                    
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": json.dumps(result)
                    })
                
                # Submit the outputs back
                client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
            except Exception as e:
                print(f"Error in function calling: {e}")
                return f"Error in processing functions: {e}"
            
        elif run_status.status in ["failed", "expired", "cancelled"]:
            return f"Error: Run ended with status {run_status.status}"
        
        time.sleep(1)  # Avoid rate limiting

