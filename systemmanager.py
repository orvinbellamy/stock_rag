### For managing multiple agents together ###

import pandas as pd
from typing import Union
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

	# TODO: Need to write a function that takes outputs from the sub agents
	# TODO: and then gives it back to the main agent

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
		self.last_run_messages = {}

		# This will label messages in thread.df_messages in node_run_id column
		# run_id labels messages per ThreadManager.run_thread()
		# node_run_id labels messages per self.input_prompt()
		self._node_run_counter = 0 

		prompt_start = 'Ignore this sentence, this is only to begin the thread.'
		self.thread = ThreadManager(client=client, prompt=prompt_start)
		
	def delete_thread(self):
		self.thread.delete_thread()

	def _check_for_instruction(self, message:str, keyword:str) -> bool:

		if keyword in message:
			return True
		else:
			return False
		
	def _get_latest_message_from_agents(self) -> pd.DataFrame:

		# Get the last location (index) of each assistant_id
		df_max_loc = self.thread.df_messages.groupby('assistant_id').agg({'_msg_loc': 'max'}).reset_index()

		# Inner join with df_messages to get the latest message
		df_last_messages = pd.merge(df_max_loc, self.thread.df_messages[['assistant_id', '_msg_loc', 'message_text']], how='inner', on=['assistant_id', '_msg_loc'])

		return df_last_messages
	
	def _get_latest_node_run_message_from_agents(self) -> pd.DataFrame:

		# Get the last location (index) of each assistant_id
		df_max_loc = self.thread.df_messages.groupby('assistant_id').agg({'node_run_id': 'max'}).reset_index()

		# Inner join with df_messages to get the latest message
		df_last_messages = pd.merge(df_max_loc, self.thread.df_messages[['assistant_id', 'node_run_id', 'message_text']], how='inner', on=['assistant_id', 'node_run_id'])

		return df_last_messages
		
	def _give_instruction_to_sub_agents(self) -> dict:

		# This is under the assumption that all sub agents will receive the same instruction from the main agent

		message_output = {}

		prompt = self.thread.last_message

		# Loop through list of sub agents
		for agent in self.sub_agents:
			

			print(f'Giving instructions to {agent.assistant_name}')
			
			self.thread.run_thread(
				assistant=agent,
				prompt=prompt,
				node_run_id=self._node_run_counter
			)

			message_output[agent] = self.thread.last_message
		
		print('Giving instructions to sub agents done')

		return message_output
	
	def input_prompt(self, prompt:str) -> dict:

		"""
		The format of the output, message_output is
		{
			agent: "last_message",
			agent: "last_message",
			agent: "last_message"
		}
		"""

		message_output = {}

		print(f'Input prompt: running thread with main agent: {self.main_agent.assistant_name}')

		self.thread.run_thread(
			assistant=self.main_agent,
			prompt=prompt,
			node_run_id=self._node_run_counter
		)

		message_output[self.main_agent] = self.thread.last_message

		print(f'Input prompt: running thread done')
		print('Input prompt: checking for instructions')

		if self._check_for_instruction(message=self.thread.last_message, keyword='Start work:'):
			
			print('Input prompt: instructions found, giving instruction to sub agents')
			
			# Give instructions to sub agents
			# Returns their output from the instructions given
			message_output_sub_agents = self._give_instruction_to_sub_agents()

			# Combine message_output and message_output_sub_agents
			# message_output now has outputs from all agents which were given a prompt
			message_output.update(message_output_sub_agents)
		
		else:
			print('Input prompt: no instructions found')

		print('Input prompt: done')

		# each time input_prompt() is called, increase _node_run_counter by 1 permanently
		self._node_run_counter += 1

		self.last_run_messages = message_output

		return message_output
	
	def report_to_main_agent(self) -> dict:

		# TODO: finish this function

		last_node_run_messages = self._get_latest_node_run_message_from_agents()

class MultiNodeManager():

	## TODO: input_prompt can send prompts from main_node to the very bottom node
	## TODO: now need to code how to get the output from the very bottom child node up 
	## TODO: to the main node again

	## This way if the validation failed, it will not update the current schema

	# Exclude self._nodes_unique for now, don't think we need it since we have self._check_hierarchy()

	def __init__(self, schema:dict={}, schema_depth:int=20):

		"""
		The schema has to be in this format:
		schema = {
			node1: set([node2, node3]),
			node2: set([node4, node5]),
			node3: set([node6]),
			node4: set([]),
			node5: set([]),
			node5: set([])
		}

		Hierarchy has the following format:
		{
			1: [nodes],
			2: [nodes],
			3: [nodes],
		}
		"""

		if schema != {}:
			
			self.hierarcy = self._check_hierarchy(schema=schema, depth=schema_depth)
			self.schema = schema.copy()
			self._main_node = self._find_main_node()

			# need to add self._nodes_unique here
			# 		
		else:

			self.hierarchy = {}
			self.schema = schema.copy()
			self._main_node = None

			# This set contains all unique nodes inside this object
			# All node must be unique, there cannot be any duplicate
			# self._nodes_unique = set()

	# This function checks whether a node already exists in this object
	# If it doesn't exist, add them
	# def _add_nodes_unique(self, nodes:Union[SystemNode,list]):

	# 	if isinstance(nodes, SystemNode) and nodes not in self._nodes_unique:
			
	# 		self._nodes_unique.add(nodes)

	# 	elif isinstance(nodes, list):

	# 		for item in nodes:

	# 			if isinstance(nodes, SystemNode) and nodes not in self._nodes_unique:
	# 				self._nodes_unique.add(nodes)
	# 			else:
	# 				raise ValueError('This node already exists in the object. All nodes in object must be unique.')
	# 	else:
	# 		raise ValueError('This node already exists in the object. All nodes in object must be unique.')

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
	
	def set_schema(self, schema:dict, schema_depth:int=20):

		# Check if schema is valid first before assigning to self.schema
		# _check_hierarchy() will raise error if the schema is not valid
		self.hierarcy = self._check_hierarchy(schema=schema, depth=schema_depth)
		self.schema = schema.copy()
		self._main_node = self._find_main_node()

	# Not sure if this is necessary since there's already validation in add_node()
	def _check_hierarchy(self, schema:dict, depth:int=20):

		hierarchy = {}

		# Get the current schema in hierarchical order
		for i in range(1,depth): # Max limit of 100

			# First hierarchy which is the main node has to be done manually
			if i == 1:
				hierarchy[1] = [self._main_node]
				hierarchy[2] = list(schema[self._main_node])
			
			else:

				# Create next hierarchy
				hierarchy[i+1] = []

				# Loop through nodes in the existing hierarchy and find their child nodes
				for node in hierarchy[i]:

					# Add child nodes to the next hierarchy
					hierarchy[i+1] += list(schema[node])
			
			# If there is no mode child node, end the loop
			if hierarchy[i+1] == []:
				break

		# Combine all lists in the dictionary into a single list
		hierarchy_nodes = [item for sublist in hierarchy.values() for item in sublist]

		if len(hierarchy_nodes) != len(set(hierarchy_nodes)):
			raise ValueError('At least one node exists in multiple hierarchy.')
		else:
			return hierarchy_nodes

	def add_node(self, node:SystemNode, depth:int=20, **kwargs):

		# Use a copy of schema as a staging
		# So that if there's an error it will not update the schema attribute
		schema_stg = self.schema.copy()

		# Check if either `parent_node` or `child_node` is provided, but not both
		if 'parent_node' in kwargs and 'child_node' in kwargs:
			raise ValueError("Please provide only one of 'parent_node' or 'child_node', not both.")
		
		elif 'parent_node' in kwargs:
			if not isinstance(kwargs['parent_node'], SystemNode):
				raise TypeError("The 'parent_node' parameter must be a SystemNode object.")
			else:
				# self._add_nodes_unique(nodes=node)
				schema_stg.setdefault(kwargs['parent_node'], set()).add(node)

		elif 'child_node' in kwargs:

			if isinstance(kwargs['child_node'], SystemNode):
				# self._add_nodes_unique(nodes=kwargs['child_node'])
				schema_stg.setdefault(node, set()).add(kwargs['child_node'])

			elif isinstance(kwargs['child_node'], list) and all(isinstance(item, SystemNode) for item in kwargs['child_node']):
				
				schema_stg.setdefault(node, set())

				# self._add_nodes_unique(nodes=kwargs['child_node'])
				schema_stg[node].update(kwargs['child_node'])

			else:
				raise TypeError("The 'child_node' parameter must be a SystemNode object or a list of SystemNode.")
		else:
			schema_stg.setdefault(node, set())

		self.hierarchy = self._check_hierarchy(schema=schema_stg, depth=depth)

		self.schema = schema_stg.copy()

		# Set the main node
		self._main_node = self._find_main_node()
	
	def _check_for_instruction(self, message:str, keyword:str):

		if keyword in message:
			return True
		else:
			return False
 
	def input_prompt(self, prompt:str):

		"""
		The structure of the node_message_tracker is this
		{
			1: {main_node: main_node_message_output},
			2: {node1: node1_message_output, node2: node2_message_output},
			3: {node3: node3_message_output, node4: node4W_message_output},
		}
		"""

		print('Inputting prompt to main agent of main node')

		# Get the depth of the schema's hierarchy
		hierarchy_depth = len(self.hierarchy)

		# Loop through each hierarchy level
		# From 1 (the top most, where the main node is) to the bottom
		# Each loop is a hierarchy {1: [list of nodes]}
		for depth in range(1,hierarchy_depth+1):
			
			if depth == 1:

				# Get a dataframe of the last message from all agent in node
				# message_output structure is
				# message_output = {agent:'last_message', agent:'last_message',}
				message_output = self._main_node.input_prompt(prompt=prompt)
				
				# Store dataframe in the message tracker
				# node_message_tracker[1]= {self._main_node: message_output}
			
			else:
				
				# Check the last message of each sub_agent in all message_output from the previous depth

				# Get the list of nodes in the previous hierarchy
				list_last_nodes = self.hierarchy[depth-1]

				# Loop through each last node
				for last_node in list_last_nodes:

					# Get child nodes of the last node (if it exists)
					child_nodes_of_last_node = self.schema[last_node]

					# Check if the last node has child nodes
					# If not then skip, this node has no child node in current hierarchy
					if len(child_nodes_of_last_node)==0:
						continue

					# Check the last messages/output of each agent from the last run (in previous hierarchy) 
					# last_node.last_run_messages structure
					# {agent:"last_mesage_output", agent:"last_mesage_output"}
					for agent in last_node.last_run_messages:
						
						if agent == last_node.main_agent:
							continue

						# We only want to check messages from sub agents
						# because main agent will not give instructions to child nodes
						# also need to check if there is instruction
						elif self._check_for_instruction(message=last_node.last_run_messages[agent], keyword='Start work:'):
							
							# Loop through each child node (current hierarchy)
							# of the last node (previous hierarchy)
							for child_node in child_nodes_of_last_node:
								
								# Check if the sub agent from the last node is a main agent in one of the child nodes
								if agent == child_node.main_agent:
									
									prompt = last_node.last_run_messages[agent]
									message_output = child_node.input_prompt(prompt=prompt)

				

	# def input_prompt(self, prompt:str):

	# 	print(f'Input prompt: running thread done')
	# 	print('Input prompt: checking for instructions')

	# 	if self._check_for_instruction(keyword='Start work:'):
			
	# 		print('Input prompt: instructions found, giving instruction to sub agents')
	# 		self._give_instruction_to_sub_agents()
		
	# 	else:
	# 		print('Input prompt: no instructions found')

	# 	print('Input prompt: done')