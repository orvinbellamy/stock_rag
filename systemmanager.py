### For managing multiple agents together ###

from agenthandler import AgentHandler
from eventhandler import ThreadManager

class Staff:
    def __init__(self, name: str, title: str, salary: float, subordinates: list[str]):
        self.name = name
        self.title = title
        self.salary = salary
        self.subordinates = subordinates

    def add_subordinate(self, subordinate: str):
        self.subordinates.append(subordinate)

    def remove_subordinate(self, subordinate: str):
        self.subordinates.remove(subordinate)

class MultiSystemManager():

	def __init__(self, staff_list: list[Staff]):
		self.staff_list = staff_list

	def fire(self, staff: Staff):
		self.staff_list.remove(staff)
