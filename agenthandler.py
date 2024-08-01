import pandas as pd
import openai
from openai import OpenAI
import json
from eventhandler import ThreadManager

class AgentHandler():
	def __init__(self, client, assistant_id: str, thread: ThreadManager):
		self._client = client
		self.assistant_id