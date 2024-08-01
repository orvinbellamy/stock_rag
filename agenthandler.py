import pandas as pd
import openai
from openai import OpenAI
import json
from eventhandler import ThreadManager

class AgentHandler():
	def __init__(self, client, assistant_id: str, thread: ThreadManager, dic_agent: dict):
		self._client = client
		self.assistant_id = assistant_id
		self.dic_agent = dic_agent
		self.assistant = client.beta.assistants.update(
			assistant_id=dic_agent['fin_analyst']['id'], 
			instructions=dic_agent['fin_analyst']['instructions'],
			model=dic_agent['fin_analyst']['model'],
			tools=dic_agent['fin_analyst']['tools'],
			tool_resources=['fin_analyst']['tool_resources']
		)
  
	def update_agent(self, dic_file : dict, assistant_name : str, instructions : str = None, model : str = None, tools : list = None, tool_resources : dict = None):
		
		if instructions is None:
			instructions = self.dic_agent['instructions']
		else:
			self.dic_agent['instructions'] = instructions
   
		if model is None:
			model = self.dic_agent['model']
		else:
			self.dic_agent['model'] = model
   
		if tools is None:
			tools = self.dic_agent['tools']
		else:
			self.dic_agent['tools'] = tools
   
		if tool_resources is None:
			tool_resources = self.dic_agent['tool_resources']
		else:
			self.dic_agent['tool_resources'] = tool_resources
		
		self.assistant = self.client.beta.assistants.update(
			assistant_id = self.assistant_id,
			instructions = instructions,
			model = model,
			tools = tools,
			tool_resources = tool_resources
		)

		print(f"assistant_id: {self.assistant_id} has been updated.")
  
		dic_file[assistant_name] = self.dic_agent
  
		print(f"{assistant_name} properties in main dictionary has been updated.")
  