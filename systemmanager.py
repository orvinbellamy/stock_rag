### For managing multiple agents together ###

from openai import OpenAI
from agenthandler import AgentHandler
from eventhandler import ThreadManager

class SystemNode:

	# As a start each Node will have 2 or 3 agents (models)
	# 1 agent will always be the reviewer
	# The other agent(s) will do the actual work

	def __init__(self, client:OpenAI, name:str, main_agent:AgentHandler, sub_agents:list[AgentHandler], child_nodes:list=None):
		self.name = name
		self.main_agent = main_agent
		self.sub_agents = sub_agents
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
		
	def delete_thread(self):
		self.thread.delete_thread()

	def _check_for_instruction(self):

		if "Start work:" in self.thread.last_message:
			return True
		else:
			return False
		
	def _give_instruction_to_sub_agents(self):

		prompt = self.thread.last_message

		for agent in self.sub_agents:
			self.thread.run_thread(
				assistant=agent,
				prompt=prompt
			)

		### TODO: Need to figure out how to parse the responses and for the manager to review each response
		### TODO: Need to figure out how to trigger a run input in child nodes from an output in parent node
	
	def input_prompt(self, prompt:str):
		self.thread.run_thread(
			assistant=self.main_agent,
			prompt=prompt
		)

		if self._check_for_instruction():

			self._give_instruction_to_sub_agents()

class MultiSystemManager():

	def __init__(self, head_node:SystemNode):
		self.head_node = head_node

	def input_message(self, prompt:str):

		self.head_node.thread.run_thread(
			assistant=self.head_node.agents['reviewer'],
			prompt=prompt)