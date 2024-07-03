import pandas as pd
import openai
from openai import OpenAI

class FileHandler:
    def __init__(self, df: pd.DataFrame):
        
        self.df = df