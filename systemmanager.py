### For managing multiple agents together ###

from agenthandler import AgentHandler
from eventhandler import ThreadManager

class MultiSystemManager():

	def __init__(self):
		pass


class ProcessEntity():
	
	def __init__(self, name, entity_type='Test', role=None):

		self.name = name
		self.entity_type = entity_type  # "individual" or "team"
		self.role = role
		self.sub_entities = []

	def add_sub_entity(self, sub_entity):

		self.sub_entities.append(sub_entity)