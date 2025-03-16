### For managing multiple agents together ###

import pandas as pd
from typing import Union, Tuple
from openai import OpenAI
from agenthandler import AgentHandler
from eventhandler import ThreadManager
# import logging as log

# Check to see if assistant is already assigned to this thread
# We only allow running thread against assigned assistant
# This is so that we can always trace assistant to agent and vice versa

class AgentThreadManager():
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

	# TODO: We don't need to worry giving data mid run. All data should be set first and assigned to the agents/assistants
	# TODO: User input (stock ticker) -> runs stock_data_setup -> run the multi node system

	def __init__(
			self, 
			client:OpenAI, 
			name:str, 
			main_agent:AgentHandler, 
			sub_agents:list[AgentHandler],
			agent_thread_manager:AgentThreadManager
			):
		self.name = name
		self.agent_thread_manager = agent_thread_manager
		self.main_agent = main_agent
		self.sub_agents = sub_agents
		self.last_run_messages = {} # This is also message_output, # TODO: naming inconsistency

		# This will label messages in thread.df_messages in node_run_id column
		# run_id labels messages per ThreadManager.run_thread()
		# node_run_id labels messages per self.input_prompt()
		self._node_run_counter = 0 

		prompt_start = 'Ignore this sentence, this is only to begin the thread.'
		self.thread = ThreadManager(client=client, prompt=prompt_start)

		# Link main agent to thread
		self.agent_thread_manager.link(thread=self.thread, agent=self.main_agent)

		# Link sub agents to thread
		for sub_agent in self.sub_agents:

			self.agent_thread_manager.link(thread=self.thread, agent=sub_agent)
		
	def delete_thread(self):
		self.thread.delete_thread()

	def _check_for_instruction(self, message:str, keyword:str) -> bool:

		if keyword in message:
			return True
		else:
			return False
		
	def _get_latest_message_from_agents(self, main_agent:bool=True) -> pd.DataFrame:

		# Get the last location (index) of each assistant_id
		df_max_loc = self.thread.df_messages.groupby('assistant_id').agg({'_msg_loc': 'max'}).reset_index()

		# Inner join with df_messages to get the latest message
		df_last_messages = pd.merge(df_max_loc, self.thread.df_messages[['assistant_id', '_msg_loc', 'message_text']], how='inner', on=['assistant_id', '_msg_loc'])

		# If main_agent is False, means we want to exclude the main agent's last messages.
		if not main_agent:

			# Filter out main_agent
			df_last_messages = df_last_messages.loc[df_last_messages['assistant_id']!=self.main_agent.assistant_id,:]

		return df_last_messages
	
	# We may not need this
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
				node_run_id=self._node_run_counter,
				attachments=agent.files
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
			node_run_id=self._node_run_counter,
			attachments=self.main_agent.files
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

		self.last_run_messages = message_output # TODO: naming inconsistency

		return message_output
	
	def _split_sub_agents_messages(self, message_output:dict, keyword:str) -> dict:

		message_to_concatenate = message_output.copy()

		# Filter out message by main agent
		message_to_concatenate.pop(self.main_agent)

		#
		sub_agents_with_instructions = [key for key, value in message_to_concatenate.items() if keyword in value.lower()]

		# Create a new dictionary with only the specified keys
		message_output_instructions = {agent: message_to_concatenate[agent] for agent in sub_agents_with_instructions if agent in message_to_concatenate}

		# Delete the sub agents that have instructions from message_to_concatenate
		for agent in sub_agents_with_instructions:
			message_to_concatenate.pop(agent, None)

		# So essentially there will be 2 separate message_output dictionaries
		# 1 will not have instructions, meaning they're legitimate outputs from the sub agents
		# Which can be returned to the main agent
		# The other are messages from the sub agents which have instructions
		# which should be forwarded to appropriate child nodes
		dic_output = {
			'message_no_instructions': message_to_concatenate,
			'message_with_instructions': message_output_instructions
		}

		return dic_output

	def run_node(self, prompt:str) -> dict:

		# Input prompt to main agent
		# Then check for instructions, if instructions exists, forward it to sub agents
		# Get message outputs from the run
		# note that agents who don't get input won't be part of the message_output
		message_output = self.input_prompt(prompt=prompt)

		# Get messages for instructions and for feedback (to main agent)
		dic_sub_agent_split_messages = self._split_sub_agents_messages(
			message_output=message_output,
			keyword='Start work:'
			)
		
		return dic_sub_agent_split_messages
	
	# Doing this with **kwargs, but not sure if that's the best way to do it
	# sub_agents:list=None
	def _report_to_main_agent(self, sub_agents:list=None, node_run_id:int=None) -> str:

		"""
		Note that this should be run when all sub agents have their final output,
		because it will get the latest message based on df.messages['_msg_loc'],
		not the self.last_run_messages
		i.e. not outputting instruction and waiting for reply from child node.

		How to use **kwargs (not sure if it's the best way to do this):
		agent = True
		agent_financial_analyst = True
		"""

		df_last_messages = self._get_latest_message_from_agents(main_agent=False)

		# If sub_agents is provided, filter only for sub_agents specified
		if sub_agents:

			list_assistant_id = [agent.assistant_id for agent in sub_agents]

			df_last_messages.loc[df_last_messages['assistant_id'].isin(list_assistant_id),:]

		messages_to_report = '\n'.join(df_last_messages['message_text'])

		message_from_main_agent = self.thread.run_thread(
			assistant=self.main_agent,
			prompt=messages_to_report,
			node_run_id=node_run_id
		)

		return message_from_main_agent
	
	def clear_and_delete(self):

		self.thread.clear_and_delete()

		del self

class MultiNodeManager():

	# TODO: We likely need a separate class or a way to keep track of messages to transfer between nodes

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
			
			self.hierarchy = self._check_hierarchy(schema=schema, depth=schema_depth)
			self.schema = schema.copy()
			self._main_node = self._find_main_node(schema=self.schema)

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

	def _find_main_node(self, schema:dict):

		"""
		Finds the main node in the hierarchy (the node with no parent).
		"""

		all_nodes = set(schema.keys())
		child_nodes = {child for children in schema.values() for child in children}
		
		main_nodes = list(all_nodes - child_nodes)
		
		if len(main_nodes) != 1:
			raise ValueError("There should be exactly one main node.")
		
		return main_nodes[0]
	
	def set_schema(self, schema:dict, schema_depth:int=20):

		# Check if schema is valid first before assigning to self.schema
		# _check_hierarchy() will raise error if the schema is not valid
		self.hierarchy = self._check_hierarchy(schema=schema, depth=schema_depth)
		self.schema = schema.copy()
		self._main_node = self._find_main_node(schema=self.schema)

	# Not sure if this is necessary since there's already validation in add_node()
	def _check_hierarchy(self, schema:dict, depth:int=20):

		## First make sure all nodes inside the sets exist as a key
		
		# Get all nodes in the sets
		all_nodes = set().union(*schema.values())

		# Get all nodes in the keys
		schema_keys = set(schema.keys())

		# Nodes in sets must be a subset of nodes in keys
		if not all_nodes.issubset(schema_keys):
			raise ValueError("All nodes must be a key in the schema dictionary")

		hierarchy = {}

		schema_main_node = self._find_main_node(schema=schema)

		# Get the current schema in hierarchical order
		for i in range(1,depth): # Max limit of 100

			# First hierarchy which is the main node has to be done manually
			if i == 1:
				hierarchy[1] = [schema_main_node]
				hierarchy[2] = list(schema[schema_main_node])
			
			else:

				# Create next hierarchy
				hierarchy[i+1] = []

				# Loop through nodes in the existing hierarchy and find their child nodes
				for node in hierarchy[i]:

					# Add child nodes to the next hierarchy
					hierarchy[i+1] += list(schema[node])
			
				# If there is no mode child node, end the loop
				if hierarchy[i+1] == []:

					hierarchy.pop(i+1,None)
					break

		# Combine all lists in the dictionary into a single list
		hierarchy_nodes = [item for sublist in hierarchy.values() for item in sublist]

		if len(hierarchy_nodes) != len(set(hierarchy_nodes)):
			raise ValueError('At least one node exists in multiple hierarchy.')
		else:
			return hierarchy

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
		self._main_node = self._find_main_node(schema=self.schema)
	
	def _check_for_instruction(self, message:str, keyword:str):

		if keyword in message:
			return True
		else:
			return False
	
	# run downward as in we give an input from the top (main node)
	# and then it gives instructions downstream (downward)
	def _run_nodes_downward(self, prompt:str):

		"""
		The structure of the node_message_tracker is this
		{
			1: {main_node: main_node_message_output},
			2: {node1: node1_message_output, node2: node2_message_output},
			3: {node3: node3_message_output, node4: node4W_message_output},
		}
		"""

		print('Inputting prompt to main agent of main node')

		# Dictionary to store instructions
		dic_nodes_message_outputs = {}

		# Loop through each hierarchy level
		# From 1 (the top most, where the main node is) to the bottom
		# Each loop is a hierarchy {1: [list of nodes]}
		for depth in range(1,len(self.hierarchy)+1):
			
			if depth == 1:

				# Get a dataframe of the last message from all agent in node
				# message_output structure is
				# message_output = {agent:'last_message', agent:'last_message',}
				dic_sub_agent_split_messages = self._main_node.run_node(prompt=prompt)

				dic_nodes_message_outputs[self._main_node] = dic_sub_agent_split_messages
				
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
									
									prompt = last_node.last_run_messages[last_node.main_agent]
									dic_sub_agent_split_messages = child_node.run_node(prompt=prompt)

									dic_nodes_message_outputs[child_node] = dic_sub_agent_split_messages
		
		# Structure of dic_nodes_message_outputs
		# {
		# node: dic_output = {
		#	'message_no_instructions': {agent1: message, agent2: message},
		#	'message_with_instructions': {agent3: message, agent4: message}
		# 	}
		# }
		return dic_nodes_message_outputs

	# This should only be run after _run_nodes_downward
	def _run_nodes_upward(self, nodes_messages:dict):

		# Initialize the two new dictionaries
		dic_message_no_instructions = {}
		dic_message_with_instructions = {}

		# Split the original dictionary into two
		for key, messages in nodes_messages.items():
			dic_message_no_instructions[key] = messages['message_no_instructions']
			dic_message_with_instructions[key] = messages['message_with_instructions']

		# We loop from the hierarchy from bottom-up this time
		for depth in range(len(self.hierarchy),0,-1):
			
			# Get all nodes in this hierarchy
			list_of_nodes = self.hierarchy[depth]

			# Loop through each node in the hierarchy
			for node in list_of_nodes:

				# Get message from main agent of the node
				node_message_output = node._report_to_main_agent()

				# If not at the highest hierarchy
				if depth > 1:

					for parent_node, child_nodes in self.schema.items():
						
						if node in child_nodes:
							
							# NOTE: this is under the assumption there is no feedback loop
							# i.e. in this method the output of the main agent will never have an instruction
							# Run this input_prompt on parent_node
							# Technically we can run it using run_node as well
							# We do this just so that the latest message is stored in the node object, we don't have to fetch the message output here
							parent_node.input_prompt(prompt=node_message_output)

							# Exit the loop
							break
		
		# This will be the node_message_output from hierarchy=1
		# i.e. the main node
		return node_message_output
	
	def run(self, prompt:str):

		dic_nodes_messages_output = self._run_nodes_downward(prompt=prompt)

		node_message_output = self._run_nodes_upward(nodes_messages=dic_nodes_messages_output)

		return node_message_output