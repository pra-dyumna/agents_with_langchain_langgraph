from langchain_google_genai import GoogleGenerativeAI
from dotenv import load_dotenv
import os 

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")

class llm_model_config:
    def __init__(self, model_name:str, temperature:float):
        self.model_name = model_name
        self.temperature = temperature
        self.api_key = API_KEY

    def get_llm(self):
        return GoogleGenerativeAI(model=self.model_name, temperature=self.temperature, api_key=self.api_key)
    

llm = llm_model_config(model_name="gemini-2.5-flash", temperature=0.7).get_llm()