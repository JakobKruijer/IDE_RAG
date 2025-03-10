import os
import pandas as pd
from dotenv import load_dotenv
from llama_index.core import Settings, VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.llms.openai import OpenAI
from llama_index.agent.openai import OpenAIAgent
from llama_index.core.schema import Document
from llama_index.core.tools import FunctionTool
import fitz
import string
from thefuzz import process
import pdfplumber

# load environment variable
load_dotenv("C:/Users/JKRUIJER/OneDrive - Capgemini/Documents/Training/Python/IDE RAG/devcontainer.env")
api_key = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = api_key
Settings.llm = OpenAI(model="gpt-3.5-turbo", temperature=0, max_tokens=200) # low temperature for exact answers

# load object instruction data from an Excel file
excel_path = r"C:\Users\JKRUIJER\OneDrive - Capgemini\Documents\Training\Python\IDE RAG\Index_invulinstructies\data\invulinstructies_formatted.xlsx"
df = pd.read_excel(excel_path)
df["Object"] = df["Object"].str.lower()

# import pdf data path
data_path = "C:/Users/JKRUIJER/OneDrive - Capgemini/Documents/Training/Python/IDE RAG/Data"

''' Convert Excel rows into structured LlamaIndex documents & create and store Index in Index_agent_invulinstructies/storage
# Convert Excel rows into structured LlamaIndex documents
documents = []
for _, row in df.iterrows():
    object_name = row["Object"].strip()
    instruction_text = row["Invulinstructie"].strip()
    
    # Ensure each document is clearly labeled by object
    doc = Document(
        text=f"Object: {object_name}\nInvulinstructie: {instruction_text}",
        metadata={"Object": object_name}
    )
    documents.append(doc)

# Create index with structured documents
index = VectorStoreIndex.from_documents(documents)

# store index
index.storage_context.persist(persist_dir="Index_agent_invulinstructies/storage")
'''

# set storage path
index_storage_context = StorageContext.from_defaults(persist_dir="Index_invulinstructies/storage")

# retrieve index
index = load_index_from_storage(index_storage_context)

# create retriever and query engine
retriever = VectorIndexRetriever(index=index, similarity_top_k=1)  # Top 1 match
query_engine = RetrieverQueryEngine(retriever=retriever)

# Lees de objectenlijst in
df_objecten = pd.read_excel(r"C:\Users\JKRUIJER\OneDrive - Capgemini\Documents\Training\Python\IDE RAG\Index_invulinstructies\data\invulinstructies_formatted_test.xlsx")
object_list = df_objecten["Object"].astype(str).tolist()
object_list = [obj.lower() for obj in object_list]

# function to extract objects from query 
def find_objects(user_query, object_list):
    user_query.lower()
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
                        df = pd.DataFrame(table, columns=['Index', 'Waarde']).set_index('Index')
                        return df, page_num
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
                df2, page_num = extract_requirement_text(OVS_file_name, eis)
                return instruction, OVS_file_name, df2, page_num      
            else:
                return instruction
        else:
            return "Object gevonden, maar geen instructie beschikbaar."

    return "Geen overeenkomend object gevonden."

# function to add two numbers
def add_numbers(a: int, b: int) -> int:
    """Adds two numbers and returns the result."""
    return a + b

# setting up the tools
instruction_tool = FunctionTool.from_defaults(fn=get_instruction, return_direct=True)
add_tool = FunctionTool.from_defaults(fn=add_numbers, return_direct=True)

# initializing agent
agent = OpenAIAgent.from_tools([add_tool, instruction_tool])

# example query
# standStillDetectionInterval
# permissionToDriveTimer
# puic
#query = "Wat is de invulinstructie voor standStillDetectionInterval?"
#instruction = get_instruction(query)

instruction = agent.query("Wat is de invulinstructie voor standStillDetectionInterval?")
print("Instructie:", instruction)