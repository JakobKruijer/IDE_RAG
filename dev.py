import string
import fitz
import os
import torch
import pandas as pd
from transformers import TableTransformerForObjectDetection, DetrImageProcessor
from pdf2image import convert_from_path
from PIL import Image
import layoutparser as lp

data_path = r"C:\Users\JKRUIJER\OneDrive - Capgemini\Documents\Training\Python\IDE RAG\Data"
test = r"C:\Users\JKRUIJER\OneDrive - Capgemini\Documents\Training\Python\IDE RAG\Data\OVS60040-2-V005.pdf"

''' extract OVS & eis/regel
instruction = 'Vul in volgens OVS60040-2 regel 310.'
def OVS_en_eis_retriever(instruction):
    if "OVS" in instruction:
        words = instruction.split()
        for word in words:
            if "OVS" in word:
                OVS_file_name = word 
        if 'eis' in instruction:
            # retrieve the eis number
            index = words.index('eis')
            eis = words[index+1] 
            #eis = eis.translate(str.maketrans('', '', string.punctuation)) 
        elif 'regel' in instruction:
            # retrieve the regel number
            index = words.index('regel')
            regel = words[index+1] 
            #regel = regel.translate(str.maketrans('', '', string.punctuation)) 
        else:
            print("Geen regel of eis gevonden bij:", OVS_file_name)
        pdf_info = extract_requirement_text(OVS_file_name, eis)
        return instruction, OVS_file_name, pdf_info
'''

''' get instruction for an object from a file using string logic
# function to get instruction for an object
def extract_requirement_text(ovs_name, eis_number):
    """Searches for the given requirement (eis XYZ) in the PDF and extracts relevant text."""
    dir_list = os.listdir("Data")
    ovs_file = [file for file in dir_list if ovs_name in file][0] #identify the file in the data folder and return the first match
    pdf_path = data_path + '\\' + ovs_file
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text = page.get_text("text")
            if eis_number in text:
                # extract relevant paragraph containing the requirement
                blocks = text.split("\n \n")  
                for paragraph in blocks:
                    if eis_number in paragraph:              
                        return paragraph
    return f"Geen specifieke informatie gevonden voor {eis_number} in het PDF."
print(extract_requirement_text('OVS60040-2', '310.'))
'''

''' get instruction for an object from a file using a library
import pdfplumber

file_path = r"C:\Users\JKRUIJER\OneDrive - Capgemini\Documents\Training\Python\IDE RAG\Data\OVS60040-2-V005.pdf"
eis_number = "310."


with pdfplumber.open(file_path) as pdf:
    pages = pdf.pages
    for page in pages:
        text = page.extract_text_simple(x_tolerance=3, y_tolerance=3)       
        if eis_number in text:
            page_num = page
            tables = page.extract_tables()
            for table in tables:
                if eis_number in table[0][1]:
                    print(table)
'''

''' #identify objects from query
import pandas as pd
#from rapidfuzz import process
from thefuzz import fuzz
from thefuzz import process

# Lees de objectenlijst in
df = pd.read_excel(r"C:\Users\JKRUIJER\OneDrive - Capgemini\Documents\Training\Python\IDE RAG\Index_invulinstructies\data\invulinstructies_formatted_test.xlsx")
object_list = df["Object"].astype(str).tolist()
object_list = [obj.lower() for obj in object_list]

def find_best_matches(user_query, object_list):
    user_query.lower()
    user_query_words = user_query.split()
    matched = []
    for word in user_query_words:
        match = process.extract(word, object_list, limit=1)
        if match[0][1] >= 95:
            matched.append(match[0][0])
    return matched

# User input
user_query = "Wat is de invulinstructie voor puic"
best_matches = find_best_matches(user_query, object_list)

print(f"Gevonden objecten: {best_matches}")
'''

