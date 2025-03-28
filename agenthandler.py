import pandas as pd
import openai
from openai import OpenAI
import json
from typing import Literal

class AgentHandler():

	# NOTE: assistants.json() will no longer have file_ids
	# If we want to assign a file, we have to do it manually
	def __init__(
			self,
			client:OpenAI, 
			new:bool,
			dic_file:dict,
			assistant_name:str,
			instructions:str = None,
			model:str = None,
			tools:list = [],
			tool_resources: dict = {},
			files:list = [],
			dic_file_name:str='assistants.json',
			dic_file_path:str='config/'
			):
		
		self._client = client
		self.assistant_name = assistant_name
		self._dic_file_name = dic_file_name
		self._dic_file_path = dic_file_path
		self.files = files
		
		# If creating a new assistant/agent
		if new:
			if instructions is None or model is None:
				raise ValueError('Assistant property is incomplete for creating a new assistant.')

			self.assistant = client.beta.assistants.create(
				name=assistant_name,
				instructions=instructions,
				model=model,
				tools=tools,
				tool_resources=tool_resources
			)

			print(f'New assistant has been created, name: {assistant_name}, id: {self.assistant.id}')

			self.assistant_id = self.assistant.id

			dic_file[assistant_name] = {}
			dic_file[assistant_name]['id'] = self.assistant_id
			dic_file[assistant_name]['instructions'] = instructions
			dic_file[assistant_name]['model'] = model
			dic_file[assistant_name]['tools'] = tools
			dic_file[assistant_name]['tool_resources'] = tool_resources

			self._dic_agent = dic_file

			with open(f"{self._dic_file_path}{self._dic_file_name}", 'w') as json_file:
				json.dump(self._dic_agent, json_file, indent='\t')
				print(f"{self._dic_file_path}{self._dic_file_name} file has been updated")

		# If using an existing assistant/agent
		else:
			self._dic_agent = dic_file
			self.assistant_id = dic_file[assistant_name]['id']
			self.assistant = client.beta.assistants.update(
				assistant_id=dic_file[assistant_name]['id'], 
				instructions=dic_file[assistant_name]['instructions'],
				model=dic_file[assistant_name]['model'],
				tools=dic_file[assistant_name]['tools'],
				tool_resources={} 
			)

			print(f'Assistant has been updated, name: {assistant_name}, id: {self.assistant.id}')
  
	def update_agent(self, instructions:str=None, model:str=None, tools:list=None, agent_files:list=None):

		if instructions is None:
			instructions = self._dic_agent[self.assistant_name]['instructions']
		else:
			self.dic_agent['instructions'] = instructions
   
		if model is None:
			model = self._dic_agent[self.assistant_name]['model']
		else:
			self.dic_agent['model'] = model
   
		if tools is None:
			tools = self._dic_agent[self.assistant_name]['tools']
		else:
			self.dic_agent['tools'] = tools
   
		if agent_files is None:
			tool_resources = {}
		else:
			tool_resources = {
				'code_interpreter': {
					'file_ids': agent_files
				}
			}

			self.files = agent_files
		
		self.assistant = self._client.beta.assistants.update(
			assistant_id = self.assistant_id,
			instructions = instructions,
			model = model,
			tools = tools,
			tool_resources = tool_resources
		)

		print(f"assistant_id: {self.assistant_id} has been updated.")
  
		# dic_file[assistant_name] = self._dic_agent
  
		print(f"{self.assistant_name} properties in main dictionary has been updated.")

		with open(f"{self._dic_file_path}{self._dic_file_name}", 'w') as json_file:
			json.dump(self._dic_agent, json_file, indent='\t')
			print(f"{self._dic_file_path}{self._dic_file_name} file has been updated")