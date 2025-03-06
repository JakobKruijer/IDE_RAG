import os
from dotenv import load_dotenv
import streamlit as st
from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.query_engine import SubQuestionQueryEngine
from llama_index.agent.openai import OpenAIAgent
from llama_index.llms.openai import OpenAI

# Load secrets
api_key = st.secrets["openai"]["api_key"]

# Set OpenAI API key and settings
os.environ["OPENAI_API_KEY"] = api_key
Settings.llm = OpenAI(model="gpt-3.5-turbo", temperature=0, max_tokens=200)

# Streamlit app settings
st.set_page_config(page_title="BID Manager Assistant", page_icon="🤖", layout="centered")
st.title("BID Manager Assistent")
st.info("LET OP: dit is een demoversie, verstrekte informatie kan onjuist zijn. Raadpleeg altijd de [BID manager](https://prorail.moxio.com/central/#sso/v1/authenticate/aHR0cHM6Ly9wcm9yYWlsLm1veGlvLmNvbS9iaWQvYXV0aC9zc28vdjEvcmVjZWl2ZV90b2tlbg==) voor nauwkeurige en actuele informatie.", icon="ℹ️")

# Function to load indices and create tools
@st.cache_resource(show_spinner=True)
def initialize_agent():
    # Load indices
    list_storage_context = StorageContext.from_defaults(persist_dir="Index_kenmerken/storage")
    keyword_storage_context = StorageContext.from_defaults(persist_dir="Index_objectstructuur/storage")

    list_index = load_index_from_storage(list_storage_context)
    keyword_index = load_index_from_storage(keyword_storage_context)

    # Create query engines
    list_engine = list_index.as_query_engine(similarity_top_k=1)
    keyword_engine = keyword_index.as_query_engine(similarity_top_k=1)

    # Define tools
    tools = [
        QueryEngineTool(
            query_engine=list_engine,
            metadata=ToolMetadata(
                name="Kenmerken",
                description="Geeft informatie over definities, invulinstructies en de (keuzes van) kenmerken bij objecten."
            )
        ),
        QueryEngineTool(
            query_engine=keyword_engine,
            metadata=ToolMetadata(
                name="Objectstructuur",
                description="Geeft informatie over de definities en locaties van objecten en hun bovenliggende en onderliggende equipments."
            )
        )
    ]

    # Create sub-question query engine #ADD return_direct=True
    query_engine = SubQuestionQueryEngine.from_defaults(query_engine_tools=tools)
    agent = OpenAIAgent.from_tools(tools + [
        QueryEngineTool(
            query_engine=query_engine,
            metadata=ToolMetadata(
                name="sub_question_query_engine",
                description="Wordt gebruikt bij vragen over de BID manager."
            )
        )
    ])
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

        