### For managing multiple agents together ###

from openai import OpenAI
from agenthandler import AgentHandler
from eventhandler import ThreadManager
# import logging as log

# Check to see if assistant is already assigned to this thread
# We only allow running thread against assigned assistant
# This is so that we can always trace assistant to agent and vice versa

class ThreadAgentManager():
	def __init__(self):
		self._thread_to_agents={}
		self._agent_to_threads={}

	def link(self, thread:ThreadManager, agent:AgentHandler):
		"""Creates a bidirectional link between a thread and an agent."""
		self._thread_to_agents.setdefault(thread, set()).add(agent)
		self._agent_to_threads.setdefault(agent, set()).add(thread)

	def unlink(self, thread:ThreadManager, agent:AgentHandler):
		"""Removes the bidirectional link between a thread and an agent."""
		if agent in self._thread_to_agents.get(thread, set()):
			self._thread_to_agents[thread].remove(agent)
		if thread in self._agent_to_threads.get(agent, set()):
			self._agent_to_threads[agent].remove(thread)
	
	def get_agents(self, thread:ThreadManager):
		"""Returns a set of agents linked to a thread."""
		return self._thread_to_agents.get(thread, set())

	def get_threads(self, agent:AgentHandler):
		"""Returns a set of threads linked to an agent."""
		return self._agent_to_threads.get(agent, set())
	
	def is_linked(self, thread:ThreadManager, agent:AgentHandler):
		"""Check if a specific agent and thread are linked."""
		return (
			agent in self._thread_to_agents.get(thread, set()) and
			thread in self._agent_to_threads.get(agent, set())
		)

class SystemNode:

	# As a start each Node will have 2 or 3 agents (models)
	# 1 agent will always be the reviewer
	# The other agent(s) will do the actual work

	# TODO: Do we actually need SystemNode? Can't we do this with ThreadManager?

	def __init__(
			self, 
			client:OpenAI, 
			name:str, 
			main_agent:AgentHandler, 
			sub_agents:list[AgentHandler]
			):
		self.name = name
		self.main_agent = main_agent
		self.sub_agents = sub_agents
		self.input_msg = ''
		self.output_msg = ''

		prompt_start = 'Ignore this sentence, this is only to begin the thread.'
		self.thread = ThreadManager(client=client, prompt=prompt_start)

		# TODO: Add an input prompt and output prompt, each node needs to have an input and output
		
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

class MultiNodeManager():

	def __init__(self):
		self.schema = {}

	def _find_main_node(self):

		"""
		Finds the main node in the hierarchy (the node with no parent).
		"""

		all_nodes = set(self.schema.keys())
		child_nodes = {child for children in self.schema.values() for child in children}
		
		main_nodes = list(all_nodes - child_nodes)
		
		if len(main_nodes) != 1:
			raise ValueError("There should be exactly one main node.")
		
		return main_nodes[0]

	def add_node(self, node:SystemNode, **kwargs):

		## TODO: need to make sure: 1. cannot add node that already exists, 2. node hierarchy cannot loop

		# Check if either `parent_node` or `child_node` is provided, but not both
		if 'parent_node' in kwargs and 'child_node' in kwargs:
			raise ValueError("Please provide only one of 'parent_node' or 'child_node', not both.")
		
		elif 'parent_node' in kwargs:
			if not isinstance(kwargs['parent_node'], SystemNode):
				raise TypeError("The 'parent_node' parameter must be a SystemNode object.")
			else:
				self.schema.setdefault(kwargs['parent_node'], set()).add(node)

		elif 'child_node' in kwargs:

			if isinstance(kwargs['child_node'], SystemNode):
				self.schema.setdefault(node, set()).add(kwargs['child_node'])

			elif isinstance(kwargs['child_node'], list) and all(isinstance(item, SystemNode) for item in kwargs['child_node']):
				
				self.schema.setdefault(node, set())

				self.schema[node].update(kwargs['child_node'])

			else:
				raise TypeError("The 'child_node' parameter must be a SystemNode object or a list of SystemNode.")
		else:
			self.schema.setdefault(node, set())
	
	def _check_for_instruction(self, node:SystemNode, keyword:str):

		if keyword in self.thread.last_message:
			return True
		else:
			return False

	# def input_prompt(self, prompt:str):

	# 	print(f'Input prompt: running thread done')
	# 	print('Input prompt: checking for instructions')

	# 	if self._check_for_instruction(keyword='Start work:'):
			
	# 		print('Input prompt: instructions found, giving instruction to sub agents')
	# 		self._give_instruction_to_sub_agents()
		
	# 	else:
	# 		print('Input prompt: no instructions found')

	# 	print('Input prompt: done')