from llama_index.core import SimpleDirectoryReader, ListIndex, VectorStoreIndex, TreeIndex
import os
from dotenv import load_dotenv

# load environment variable
load_dotenv("C:/Users/JKRUIJER/OneDrive - Capgemini/Documents/Training/Python/IDE RAG/devcontainer.env")
api_key = os.getenv('OPENAI_API_KEY')

#OpenAI key
os.environ["OPENAI_API_KEY"] = api_key

# Laad invulinstructies data
data_kenmerken = SimpleDirectoryReader(r"C:\Users\JKRUIJER\OneDrive - Capgemini\Documents\Training\Python\IDE RAG\Index_subset\data").load_data()

# Voeg of wijzig metadata
for doc in data_kenmerken:
    doc.metadata.update({
        "filename": "<Subset>",
        "category": "BID manager",
        "doc_type": "pdf",
        "tags": ["Kemnerk", "Object", "Invullen", "Invulinstructie",],
        "language": "Dutch",
        "summary": "Dit document beschrijft de subsets."
    })
    
# Maak een index voor kenmerken
index = TreeIndex.from_documents(data_kenmerken)

# Sla de kenmerkenindex op
index.storage_context.persist(persist_dir="Index_subset/storage")

