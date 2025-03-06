from llama_index.core import SimpleDirectoryReader, ListIndex, VectorStoreIndex
import os
from dotenv import load_dotenv

# load environment variable
load_dotenv("C:/Users/JKRUIJER/OneDrive - Capgemini/Documents/Training/Python/IDE RAG/devcontainer.env")
api_key = os.getenv('OPENAI_API_KEY')

#OpenAI key
os.environ["OPENAI_API_KEY"] = api_key

# Laad invulinstructies data
data_kenmerken = SimpleDirectoryReader(r"C:\Users\JKRUIJER\OneDrive - Capgemini\Documents\Training\Python\IDE RAG\Index_invulinstructies\data").load_data()

# Voeg of wijzig metadata
for doc in data_kenmerken:
    doc.metadata.update({
        "filename": "<Invulinstructies>",
        "category": "BID manager",
        "doc_type": "excel",
        "tags": ["Kemnerk", "Object", "Invullen", "Invulinstructie",],
        "language": "Dutch",
        "summary": "Dit document beschrijft de invulinstructies die bij objecten horen. Per kenmerk wordt beschreven hoe deze moet worden ingevuld."
    })
    
# Maak een index voor kenmerken
index = VectorStoreIndex.from_documents(data_kenmerken)

# Sla de kenmerkenindex op
index.storage_context.persist(persist_dir="Index_invulinstructies/storage")

