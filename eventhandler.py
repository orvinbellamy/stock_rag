from typing_extensions import override
from openai import AssistantEventHandler
 
# First, we create a EventHandler class to define
# how we want to handle the events in the response stream.
 
class EventHandler(AssistantEventHandler):    
	@override
	def on_text_created(self, text) -> None:
		print(f"\nassistant > ", end="", flush=True)
      
	@override
	def on_text_delta(self, delta, snapshot):
		print(delta.value, end="", flush=True)
      
	def on_tool_call_created(self, tool_call):
		print(f"\nassistant > {tool_call.type}\n", flush=True)
  
	def on_tool_call_delta(self, delta, snapshot):
		if delta.type == 'code_interpreter':
			if delta.code_interpreter.input:
				print(delta.code_interpreter.input, end="", flush=True)
			if delta.code_interpreter.outputs:
				print(f"\n\noutput >", flush=True)
				for output in delta.code_interpreter.outputs:
					if output.type == "logs":
						print(f"\n{output.logs}", flush=True)

class ThreadManager():
	def __init__(self, client, messages: list):
		# self.thread_id = thread_id
		
		self._client = client
		self.dic_thread = []
		self.thread = self.client.beta.threads.create(messages=messages)
		self.thread_id = self.thread.id

		# Get the first message stored
		message = client.beta.threads.messages.list(thread_id=self.thread_id)
		message_data = message.data[0]

		message_id = message_data.id
		assistant_id = message_data.assistant_id
		created_at = message_data.created_at
		file_ids = message_data.attachments
		role = message_data.role
		run_id = message_data.run_id
		message_text = message_data.content[0].text.value

		dic_message = {
			'assistant_id': assistant_id, 
			'created_at': created_at, 
			'file_ids': file_ids, 
			'role': role, 
			'run_id': run_id,
			'message_text': message_text
			}
		
		self.dic_thread[message_id] = dic_message

	def get_last_message(self):
		messages = self._client.beta.threads.messages.list(thread_id=self.thread_id)
		
		# Get the list of messages in the thread
		messages_data = messages.data

		# For now this records multiple messages from assistant separately
		# Need to combine them together to make them one single string
		for message in messages_data:
			
			if message.id in self.dic_thread.keys():
				break
			else:
				message_id = message.id
				assistant_id = message.assistant_id
				created_at = message.created_at
				file_ids = message.attachments
				role = message.role
				run_id = message.run_id
				message_text = message.content[0].text.value # this needs to be fixed because there can be multiple contents

				dic_message = {
					'assistant_id': assistant_id, 
					'created_at': created_at,
					'file_ids': file_ids,
					'role': role, 
					'run_id': run_id,
					'message_text': message_text
					}

				self.dic_thread[message_id] = dic_message

		# return dic_message
	
	def run_thread(self, assistant_id : str, message : list = None):
		
		with self._client.beta.threads.runs.stream(
			thread_id=self.thread_id,
			assistant_id=assistant_id,
			event_handler=EventHandler(),
			additional_messages=message,
		) as stream:
			stream.until_done()

		self.get_last_message()
	
	def delete_thread(self):

		self._client.beta.threads.delete(thread_id=self.thread_id)
		print(f"thread: {self.thread_id} has been deleted.")