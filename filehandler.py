import pandas as pd
import openai
from openai import OpenAI
import json

class FileHandler:
    def __init__(self, df: pd.DataFrame, dic_file: dict, dic_file_name: str, file_name: str, client: OpenAI, file_path:str='openai_upload_files/'):
        
        self._client = client
        self._dic_file = dic_file
        self.df = df
        self.file_name = file_name
        self.file_path = file_path

        try:
            # That means the file already exists
            dic_file['df_balance_sheet.csv']

            self.file_id = dic_file[file_name]

        except KeyError:
            print("Note: File doesn't exist yet")     
            self.file_id = ''
       
        self._dic_file_name = dic_file_name

        # Make sure the csv is always updated
        df.to_csv(f"{file_path}{file_name}", index=False)

    # Delete the file from openai and 
    def update_openai_file(self):
        
        # Try deleting file from openai
        try:
            self._client.files.delete(self.file_id)
            print(f"file name: {self.file_name}, file id: {self.file_id} has been deleted")
        # If file already doesn't exist
        except:
            print(f"file name: {self.file_name}, file id: {self.file_id} doesn't exist or is already deleted")

        openai_file = self._client.files.create(
            file=open(f"{self.file_path}{self.file_name}", 'rb'),
            purpose='assistants'
        )

        self._dic_file[self.file_name] = openai_file.id
        self.file_id = openai_file.id

        print(f"file name: {self.file_name} is uploaded, new file id: {self.file_id}")

        self.df.to_csv(f"{self.file_path}{self.file_name}", index=False)

        self._dic_file[self.file_name] = self.file_id
    
        with open(f"{self.file_path}{self._dic_file_name}", 'w') as json_file:
            json.dump(self._dic_file, json_file, indent='\t')
            print(f"{self.file_path}{self._dic_file_name} file has been updated")