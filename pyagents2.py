import openai
import os
import requests
import re
import json
from colorama import Fore, Style, init
from serpapi import GoogleSearch
from datetime import datetime
from bs4 import BeautifulSoup
from googleapiclient.discovery import build

# Initialize colorama
init()

def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()

def save_file(filepath, content):
    with open(filepath, 'a', encoding='utf-8') as outfile:
        outfile.write(content)

api_key = open_file('openaiapikey2.txt')

mailgun_api_key = open_file('mgapikey.txt')

# Read the Google API key and Custom Search Engine ID from files
GOOGLE_SEARCH_API_KEY = open_file('googleapikey.txt')
GOOGLE_SEARCH_CX = open_file('googlecx.txt') 

conversation1 = []
conversation2 = []

chatbot1 = open_file('chatbot11.txt')
chatbot2 = open_file('chatbot10.txt')

def get_organic_results(query):
    params = {
      "engine": "google",
      "q": query,
      "num": "5",
      "api_key": "your key"
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    organic_results = results["organic_results"]
    return organic_results
    
def google_s(query):  # Accept the 'query' parameter
    search_engine = build("customsearch", "v1", developerKey=GOOGLE_SEARCH_API_KEY)
    results = search_engine.cse().list(q=query, cx=GOOGLE_SEARCH_CX, num=7).execute()

    # Extract the titles and snippets
    try:
        s_items = [{'title': result['title'], 'snippet': result['snippet']} for result in results['items']]
    except KeyError:
        s_items = []
        print("No items found for this search query.")
        
    return s_items      

def scrape_website(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    
    # If the GET request is successful, the status code will be 200
    if response.status_code == 200:
        # Get the content of the response
        page_content = response.content
        
        # Create a BeautifulSoup object and specify the parser
        soup = BeautifulSoup(page_content, 'html.parser')
        
        # Now you can use soup object to find data in the webpage
        # For example, let's say you want to scrape all text inside paragraph tags <p>
        paragraphs = soup.find_all('p')
        
        # Extract text from the paragraph tags
        scraped_data = [p.get_text() for p in paragraphs]
        
        return scraped_data
    else:
        print("Failed to retrieve the webpage")
        return []
        
def send_email(recipient, subject, body, attachment=None):
    data = {
        "from": "YOU",
        "to": recipient,
        "subject": subject,
        "text": body,
    }

    if attachment:
        with open(attachment, 'rb') as f:
            files = {'attachment': (os.path.basename(attachment), f)}
            response = requests.post(
                "https://api.eu.mailgun.net/v3/allabtai.com/messages",
                auth=("api", mailgun_api_key),
                data=data,
                files=files
            )
    else:
        response = requests.post(
            "https://api.eu.mailgun.net/v3/allabtai.com/messages",
            auth=("api", mailgun_api_key),
            data=data
        )

    if response.status_code != 200:
        raise Exception("Failed to send email: " + str(response.text))

    print("Email sent successfully.")

def chatgpt(api_key, conversation, chatbot, user_input, temperature=0, frequency_penalty=0.2, presence_penalty=0, max_turns=10):
    openai.api_key = api_key
    conversation.append({"role": "user","content": user_input})

    # Only use the last max_turns turns of the conversation
    if len(conversation) > max_turns * 2:
        conversation = conversation[-max_turns * 2:]

    messages_input = conversation.copy()
    prompt = [{"role": "system", "content": chatbot}]
    messages_input.insert(0, prompt[0])

    functions=[
         
        {
            "name": "google_s",
            "description": "Get the organic search results for a specific query",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for which to fetch the organic results",
                    }
                },
                "required": ["query"],
            },
        },
        {
            "name": "scrape_website",
            "description": "Scrape data from a specific website",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL of the website to scrape",
                    }
                },
                "required": ["url"],
            },
        },
        {
            "name": "save_file",
            "description": "Save the provided content to a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file where the content will be saved",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to be saved in the file",
                    },
                },
                "required": ["filepath", "content"],
            },
        },
        {
            "name": "open_file",
            "description": "Open a file and return its content",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file to be opened",
                    },
                },
                "required": ["filepath"],
            },
        },
        {
            "name": "send_email",
            "description": "Send an email using the Mailgun API",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient": {
                        "type": "string",
                        "description": "Email address of the recipient",
                    },
                    "subject": {
                        "type": "string",
                "description": "Subject of the email",
                    },
                    "body": {
                        "type": "string",
                            "description": "Body of the email",
                    },
                    "attachment": {
                        "type": "string",
                        "description": "Path to the file to be attached",
                    },
                },
                "required": ["recipient", "subject", "body"],
            },
        }
    ]

    completion = openai.ChatCompletion.create(
        model="gpt-4-0613",
        temperature=temperature,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        messages=messages_input,
        functions=functions,
        function_call="auto"
    )
    
    chat_response = completion['choices'][0]['message']['content']

    function_info = {}  
    response = ""  # Initialize response to an empty string

    if 'function_call' in completion.choices[0].message:
        function_info = completion.choices[0].message['function_call']
        if 'name' in function_info:
            # This regular expression matches all control characters
            control_chars = re.compile('[\x00-\x1f\x7f-\x9f]')

            # Use it to replace control characters with an empty string
            clean_json_string = control_chars.sub('', function_info['arguments'])

            if function_info['name'] == 'google_s':
                response = google_s(**json.loads(clean_json_string))
            elif function_info['name'] == 'scrape_website':
                response = scrape_website(**json.loads(clean_json_string))
            elif function_info['name'] == 'save_file':
                response = save_file(**json.loads(clean_json_string))
            elif function_info['name'] == 'open_file':
                response = open_file(**json.loads(clean_json_string))
            elif function_info['name'] == 'send_email':  # Add this condition
                response = send_email(**json.loads(clean_json_string))

    if chat_response is None:
        chat_response = ""
    chat_response = chat_response + '\n' + str(response)
    
    conversation.append({"role": "assistant", "content": chat_response})

    return chat_response

def print_colored(agent, text):
    agent_colors = {
        "Ms.Python:": Fore.YELLOW,
        "Mr.PyDev:": Fore.CYAN,
    }
    color = agent_colors.get(agent, "")
    print(color + f"{agent}: {text}" + Style.RESET_ALL, end="")

num_turns = 15

user_message = "Hello Mr.PyDev. I am Ms.Python. I'll be starting my assignment now."

for i in range(num_turns):
    print_colored("Ms.Python:", f"{user_message}\n\n")
    save_file("ChatLog.txt", "Ms.Python: " + user_message + "\n\n")
    response = chatgpt(api_key, conversation1, chatbot1, user_message)
    user_message = response

    print_colored("Mr.PyDev:", f"{user_message}\n\n")
    save_file("ChatLog.txt", "Mr.PyDev: " + user_message + "\n\n")
    response = chatgpt(api_key, conversation2, chatbot2, user_message)
    user_message = response
