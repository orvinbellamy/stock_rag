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
	def __init__(self, client, thread_id: str):
		self.thread_id = thread_id
		self._client = client
		self.dic_thread = {}

		# Get the first message stored
		message = client.beta.threads.messages.list(thread_id=thread_id)
		message_data = message.data[0]

		message_id = message_data.id
		assistant_id = message_data.assistant_id
		created_at = message_data.created_at
		file_ids = message_data.attachments
		role = message_data.role
		run_id = message_data.run_id
		message_text = message_data.content[0].text.value

		dic_message = {'message_id': message_id, 'assistant_id': assistant_id, 
						'created_at': created_at, 'file_ids': file_ids, 'role': role, 'run_id': run_id,
						'message_text': message_text}
		
		self.dic_thread['0'] = dic_message
		

	def get_last_message(self):
		message = self._client.beta.threads.messages.list(thread_id=self.thread_id)
		message_data = message.data[0]

		message_id = message_data.id
		assistant_id = message_data.assistant_id
		created_at = message_data.created_at
		file_ids = message_data.attachments
		role = message_data.role
		run_id = message_data.run_id
		message_text = message_data.content[0].text.value

		dic_message = {'message_id': message_id, 'assistant_id': assistant_id, 
						'created_at': created_at, 'file_ids': file_ids, 'role': role, 'run_id': run_id,
						'message_text': message_text}

		max_key = max(int(key) for key in self.dic_thread.keys())

		self.dic_thread[max_key] = dic_message

		return dic_message