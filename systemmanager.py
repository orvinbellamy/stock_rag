### For managing multiple agents together ###

from openai import OpenAI
from agenthandler import AgentHandler
from eventhandler import ThreadManager
# import logging as log

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

	def _check_for_instruction(self, keyword:str):

		if keyword in self.thread.last_message:
			return True
		else:
			return False
		
	def _give_instruction_to_sub_agents(self):

		prompt = self.thread.last_message

		for agent in self.sub_agents:

			print(f'Giving instructions to {agent.assistant_name}')
			self.thread.run_thread(
				assistant=agent,
				prompt=prompt
			)

			# Check to see if there's any instruction from the output of the last sub agent
			if not self._check_for_instruction(keyword='Start work:'):
				
				print('No instruction found')

			# If there is instruction
			# Check to see if sub agent is a main agent in a child node
			elif self.child_nodes is not None:
				
				print(f'Instruction found, and sub agent is a main agent in a child node')

				for node in self.child_nodes:
					if node.main_agent == agent:

						# This is a mutual recursion
						# It won't create infinite loop
						# The limit is the depth of the child nodes
						node.input_prompt(prompt=self.thread.last_message)
					break
			else:
				print('Instruction found, but sub agent is not a main agent in a child node')
				

		### TODO: Need to figure out how to parse the responses and for the manager to review each response
		### TODO: Need to figure out how to trigger a run input in child nodes from an output in parent node
	
	def input_prompt(self, prompt:str):

		print(f'Input prompt: running thread with main agent: {self.main_agent.assistant_name}')

		self.thread.run_thread(
			assistant=self.main_agent,
			prompt=prompt
		)

		print(f'Input prompt: running thread done')
		print('Input prompt: checking for instructions')

		if self._check_for_instruction(keyword='Start work:'):
			
			print('Input prompt: instructions found, giving instruction to sub agents')
			self._give_instruction_to_sub_agents()
		
		else:
			print('Input prompt: no instructions found')

		print('Input prompt: done')

class MultiSystemManager():

	def __init__(self, head_node:SystemNode):
		self.head_node = head_node

	def input_message(self, prompt:str):

		self.head_node.thread.run_thread(
			assistant=self.head_node.agents['reviewer'],
			prompt=prompt)