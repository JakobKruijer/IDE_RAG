import os
from dotenv import load_dotenv
import httpx
from pyImxOtl import OtlImx
from pyImxOtl.otl.generic import OtlReleaseStage
from pyImxOtl.otl.uitwisselscopes import OtlUitwisselscope
import json
import httpx
import xml.etree.ElementTree as ET
import pandas as pd 

# Load environment variables from the .env file
load_dotenv()

# Retrieve the API key
api_key_uitwisselscope = os.getenv("API_KEY_UITWISSELSCOPES")
api_key_OTL= os.getenv("API_KEY_OTL")

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
    
print(uitwisselscope("Signal"))