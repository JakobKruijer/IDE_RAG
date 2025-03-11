import os
import streamlit as st
from llama_index.core import Settings
import pandas as pd
from llama_index.llms.openai import OpenAI
from llama_index.agent.openai import OpenAIAgent
from llama_index.core.tools import FunctionTool
from thefuzz import process
import pdfplumber

# Load secrets
api_key = st.secrets["openai"]["api_key"]

# Set OpenAI API key and settings
os.environ["OPENAI_API_KEY"] = api_key
Settings.llm = OpenAI(model="gpt-3.5-turbo", temperature=0, max_tokens=200)

# Streamlit app settings
st.set_page_config(page_title="BID Manager Assistant", page_icon="🤖", layout="centered")
st.title("BID Manager Assistent")
st.info("LET OP: dit is een demoversie, verstrekte informatie kan onjuist zijn. Raadpleeg altijd de [BID manager](https://prorail.moxio.com/central/#sso/v1/authenticate/aHR0cHM6Ly9wcm9yYWlsLm1veGlvLmNvbS9iaWQvYXV0aC9zc28vdjEvcmVjZWl2ZV90b2tlbg==) voor nauwkeurige en actuele informatie.", icon="ℹ️")

# load object instruction data from an Excel file
excel_path = "Index_invulinstructies/data/invulinstructies_formatted.xlsx"
df = pd.read_excel(excel_path)
df["Object"] = df["Object"].str.lower()

# import pdf data path
data_path = "Data"

# Lees de objectenlijst in
df_objecten = pd.read_excel("Index_invulinstructies/data/invulinstructies_formatted_test.xlsx")
object_list = df_objecten["Object"].astype(str).tolist()
object_list = [obj.lower() for obj in object_list]

# function to extract objects from query 
def find_objects(user_query, object_list):
    user_query = user_query.lower()
    user_query_words = user_query.split()
    matched = []
    for word in user_query_words:
        match = process.extract(word, object_list, limit=1)
        if match[0][1] >= 90:
            matched.append(match[0][0])
    return matched[0]

# function to get instruction for an object from a referenced file
def extract_requirement_text(ovs_name, eis_number):
    """Searches for the given requirement (eis XYZ) in the PDF and extracts relevant text.
    First identifies the correct file based on {ovs_name} and then searches the text in pdf associated with {eis_number}."""
    dir_list = os.listdir("Data") # retreive all directories for all files in the data folder
    ovs_file = [file for file in dir_list if ovs_name in file][0] # identify the file in the data folder and return the first match
    pdf_path = data_path + '/' + ovs_file # set the correct file directory
    # return the text in {ovs_file} associated with {eis_number}
    with pdfplumber.open(pdf_path) as pdf:
        pages = pdf.pages
        for page in pages:
            text = page.extract_text_simple(x_tolerance=3, y_tolerance=3)       
            if eis_number in text:
                page_num = page
                tables = page.extract_tables()
                for table in tables:
                    if eis_number in table[0][1]:
                        return table, page_num
        return f"Geen specifieke informatie gevonden voor eis/regel {eis_number} in {ovs_file}."

# function to retrieve the instruction and referenced file name (if applicable)
def get_instruction(query):
    """Retrieves the correct fill-in instruction, including consulting the PDF if needed."""
    #query = f"Geef alleen de naam van het object voor de volgende vraag en niets anders: {query}"
    #response = query_engine.query(query)
    response = find_objects(query, object_list)

    if response:
        matched_object = response.strip()
        print(f"Matched Object: {matched_object}") 

        # fetch instruction from the DataFrame
        result = df.loc[df["Object"] == matched_object, "Invulinstructie"]

        if not result.empty:
            instruction = result.iloc[0]
            
            # if instruction references a rule in documentation, retrieve documentation and the specific rule
            if "OVS" in instruction:
                words = instruction.split()
                for word in words:
                    if "OVS" in word:
                        OVS_file_name = word
                        if 'eis' in instruction:
                            # retrieve the eis number
                            index_eis = words.index('eis')
                            eis = words[index_eis+1] 
                        elif 'regel' in instruction:
                            # retrieve the regel number
                            index_regel = words.index('regel')
                            eis = words[index_regel+1] 
                        else:
                            print("Geen regel of eis gevonden bij:", OVS_file_name)
                pdf_info = extract_requirement_text(OVS_file_name, eis)
                return instruction, OVS_file_name, pdf_info      
            else:
                return instruction
        else:
            return "Object gevonden, maar geen instructie beschikbaar."

    return "Geen overeenkomend object gevonden."

# function to add two numbers
def add_numbers(a: int, b: int) -> int:
    """Adds two numbers and returns the result."""
    return a + b


# Function to load indices and create tools
@st.cache_resource(show_spinner=True)
def initialize_agent():
    # Define tools
    instruction_tool = FunctionTool.from_defaults(fn=get_instruction, return_direct=True)
    add_tool = FunctionTool.from_defaults(fn=add_numbers, return_direct=True)
    agent = OpenAIAgent.from_tools([add_tool, instruction_tool])
    return agent

# Initialize the agent
agent = initialize_agent()

# Initialize the chat messages history
if "messages" not in st.session_state.keys():  
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hallo! Ik ben de BID manager assistent. Stel een vraag over BID178 om te beginnen.",
        }
    ]

# Initialize the chat agent
if "chat_engine" not in st.session_state.keys():
    st.session_state.chat_engine = agent

# Prompt for user input and save to chat history
if prompt := st.chat_input(
    "Ask a question"
):  
    st.session_state.messages.append({"role": "user", "content": prompt})

# Write message history to UI
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# If last message is not from assistant, generate a new response
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        response_stream = st.session_state.chat_engine.stream_chat(prompt)
        st.write_stream(response_stream.response_gen)
        message = {"role": "assistant", "content": response_stream.response}
        # Add response to message history
        st.session_state.messages.append(message)

        