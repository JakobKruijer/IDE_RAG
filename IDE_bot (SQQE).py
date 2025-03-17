import os
import pandas as pd
from dotenv import load_dotenv
from llama_index.core import Settings, VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.llms.openai import OpenAI
from llama_index.agent.openai import OpenAIAgent
from llama_index.core.schema import Document
from llama_index.core.tools import FunctionTool, QueryEngineTool, ToolMetadata
from thefuzz import process
import pdfplumber
import httpx
from pyImxOtl import OtlImx
from pyImxOtl.otl.generic import OtlReleaseStage
from pyImxOtl.otl.uitwisselscopes import OtlUitwisselscope
from llama_index.core.query_engine import SubQuestionQueryEngine, CustomQueryEngine

# load environment variables from the .env file
load_dotenv()

# retrieve the API keys
api_key_uitwisselscope = os.getenv("API_KEY_UITWISSELSCOPES")
api_key_OTL= os.getenv("API_KEY_OTL")
api_key_openai = os.getenv("OPENAI_API_KEY")

# setup chatgpt
Settings.llm = OpenAI(model="gpt-3.5-turbo", temperature=0, max_tokens=200, api_key=api_key_openai) # low temperature for exact answers

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
                        return table, page_num
        return f"Geen specifieke informatie gevonden voor eis/regel {eis_number} in {ovs_file}."

# function to retrieve the instruction and referenced file name (if applicable)
def get_instruction(query):
    """Takes a kenmerk as input and returns the correct fill-in instruction, including consulting the PDF if needed."""
    response = find_objects(query, object_list)
    #response = query
    if response:
        matched_object = response.strip().lower()
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

# function to return the uitwisselscope for an object
def uitwisselscope(object):
    "Takes an object name as an input argument and returns the uitwisselscope for that object as a pandas dataframe."
    with httpx.Client() as httpx_client:

        otl_imx = OtlImx(OtlReleaseStage.versies)
        imx_versions = otl_imx.get_versions(httpx_client)
        imx_versie = imx_versions[7].versienummer  ## 5.0.0

        otl_uitwisselscope = OtlUitwisselscope(OtlReleaseStage.kandidaatversies)
        versions = otl_uitwisselscope.get_versions(httpx_client)
        # awesome we have a leading zero on the uitwisselscope versions not on the imx versions  :-/
        uitwissel_scope_versions = [item for item in versions if "05.0.0" in item.naam]
        # use latest within the version
        otl_uitwisselscope.set_imx_version(httpx_client, uitwissel_scope_versions[-1])

        # use object iri as entry point
        iri = "http://www.prorail.nl/IMSpoor#" + object + "_element" 
        print(iri)
        # query otl object
        object_of_intrest = otl_imx.get_concept(httpx_client, imx_versie, iri)

        # use otl object iri to get uitwisselscope
        eigenschappen_scope = otl_uitwisselscope.get_klasse(httpx_client, object_of_intrest.iri)

        # Fetch IMX versions
        headers = {"Authorization": f"Bearer {api_key_uitwisselscope}"}  
        response = httpx.get("https://otl.prorail.nl/uitwisselscopes/scopes/api/rest/v1/kandidaatversies/05.0.0-v4/klassen/http%3A%2F%2Fwww.prorail.nl%2FIMSpoor%23Signal_element", headers=headers)  

        try:
            data = response.json()  # JSON-data ophalen
            # Haal de relevante data uit de dictionary en maak een lijst van dictionaries
            eigenschappen = data['data']['eigenschappen']

            # Stap 1: Verzamel unieke kenmerk_naam en scope
            kenmerk_naam_lijst = []
            scope_lijst = set()

            for key, value in eigenschappen.items():
                kenmerk_naam = value['naam']
                kenmerk_naam_lijst.append(kenmerk_naam)
                
                scopes = value.get('in scopes', {})  # Zorgt ervoor dat None niet crasht

                if isinstance(scopes, dict):
                    for scope_key, scope_value in scopes.items():
                        scope_lijst.add(scope_value['naam'])

            # **Stap 2: Maak een DataFrame met standaard 0**
            scope_lijst = sorted(list(scope_lijst))  # Geordende lijst van unieke scopes
            df = pd.DataFrame(0, index=kenmerk_naam_lijst, columns=scope_lijst)

            # **Stap 3: Vul de DataFrame met 1 als de scope aanwezig is**
            for key, value in eigenschappen.items():
                kenmerk_naam = value['naam']
                scopes = value.get('in scopes', {})  # Hier opnieuw ophalen!

                if isinstance(scopes, dict):
                    for scope_key, scope_value in scopes.items():
                        scope = scope_value['naam']
                        df.loc[kenmerk_naam, scope] = 1

            df = df.sort_index()
            df = df.reset_index()
            df = df.rename(columns={'index': 'Kenmerk'})
            return df
        except Exception as e:
            return "Error decoding JSON:", e

# function to add two numbers
def add_numbers(a: int, b: int) -> int:
    """Adds two numbers and returns the result."""
    return a + b

# setting up the tools
class ToolQueryEngine(CustomQueryEngine):
    """Custom query engine that wraps a FunctionTool."""

    function_tool: FunctionTool

    def __init__(self, fn):
        # Initialize the FunctionTool first
        function_tool_instance = FunctionTool.from_defaults(fn=fn, return_direct=True)
        
        # Pass it explicitly to CustomQueryEngine
        super().__init__(function_tool=function_tool_instance)

    def custom_query(self, *args, **kwargs):
        """Executes the function tool using provided arguments."""
        return self.function_tool.fn(*args, **kwargs)

add_tool = ToolQueryEngine(fn=add_numbers)
uitwisselscope_tool = ToolQueryEngine(fn=uitwisselscope)
instruction_tool = ToolQueryEngine(fn=get_instruction)

query_engine_tools = [
    QueryEngineTool(
        query_engine=add_tool,
        metadata=ToolMetadata(
            name='Add numbers', 
            description="Takes as input two numbers and returns their sum.")
    ),
    QueryEngineTool(
        query_engine=uitwisselscope_tool,
        metadata=ToolMetadata(
            name='Uitwisselscope', 
            description="Takes as input an object name and returns its uitwisselscope.")
    ),
    QueryEngineTool(
        query_engine=instruction_tool,
        metadata=ToolMetadata(
            name='Invulinstructie', 
            description="Takes as input an feature name and returns its fill-in instructions.")
    ),
]

# maak de Sub Question Query Engines
query_engine = SubQuestionQueryEngine.from_defaults( # of RouterQueryEngine
    query_engine_tools=query_engine_tools
    )

# Maak de Chatbot Agent
query_engine_tool = QueryEngineTool(
    query_engine=query_engine,
    metadata=ToolMetadata(
        name="sub_question_query_engine",
        description=(
            "Wordt gebruikt bij vragen over de BID manager."
        ),
    ),
)

tools = query_engine_tools + [query_engine_tool]

# initializing agent
agent = OpenAIAgent.from_tools(tools)

# example kenmerken voor invulinstructies
# standStillDetectionInterval
# permissionToDriveTimer
# puic
#instruction = agent.query("hoe vul ik puic in?")

instruction = query_engine.query("hoe vul ik puic in?")
print(instruction)