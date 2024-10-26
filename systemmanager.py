### For managing multiple agents together ###

from openai import OpenAI
from agenthandler import AgentHandler
from eventhandler import ThreadManager

class SystemNode:

	# As a start each Node will have 2 or 3 agents (models)
	# 1 agent will always be the reviewer
	# The other agent(s) will do the actual work

	def __init__(self, client:OpenAI, name:str, agents:list[AgentHandler], child_nodes:list=None):
		self.name = name
		self.agents = agents
		self.child_nodes = child_nodes
		self.input_msg = ''
		self.output_msg = ''

		prompt_start = 'Ignore this sentence, this is only to begin the thread.'
		self.thread = ThreadManager(client=client, prompt=prompt_start)

		# TODO: Add a code to verify that there is at least one reviewer agent
		# TODO: Add an input prompt and output prompt, each node needs to have an input and output

	def add_child_nodes(self, node):
		
		if isinstance(node, SystemNode):
			self.child_nodes.append(node)
		else:
			raise ValueError("Child node must be a SystemNode object.")

	def remove_child_nodes(self, node):
		
		if isinstance(node, SystemNode):
			self.child_nodes.remove(node)
		else:
			raise ValueError("Child node must be a SystemNode object.")

class MultiSystemManager():

	def __init__(self, head_node:SystemNode):
		self.head_node = head_node

	def input_message(self, prompt:str):

		self.head_node.thread.run_thread(
			assistant=self.head_node.agents['reviewer'],
			prompt=prompt)