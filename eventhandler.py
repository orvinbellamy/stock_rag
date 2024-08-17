from typing_extensions import override
from openai import AssistantEventHandler, OpenAI
from agenthandler import AgentHandler
 
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
	def __init__(self, client : OpenAI, messages : list):
		# self.thread_id = thread_id
		
		self._client = client
		self.dic_thread = {}
		self.thread = self._client.beta.threads.create(messages=messages)
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

		for content in message_data.content:
			
			if content.type == 'text':
				message_text = content.text.value

			elif content.type == 'image_file':
				file_id = content.image_file.file_id
				file = self._client.files.content(file_id)
				file.write_to_file(f'images/{file_id}.png')
				message_text = f'Image generated: {file_id}'
				print(f'Image generated: {file_id}')
			
			else:
				message_text = 'Unidentified content type'
		

		dic_message = {
			'assistant_id': assistant_id, 
			'created_at': created_at, 
			'file_ids': file_ids, 
			'role': role, 
			'run_id': run_id,
			'message_text': message_text
			}
		
		self.dic_thread[message_id] = dic_message
		self.last_message = message_text

	def get_last_message(self):
		messages = self._client.beta.threads.messages.list(thread_id=self.thread_id)
		
		# Get the list of messages in the thread
		messages_data = messages.data

		messages_combined = []

		# For now this records multiple messages from assistant separately
		# Need to combine them together to make them one single string
		for message in messages_data:
			
			# If message already exists in dic_thread
			if message.id in self.dic_thread.keys():
    
				# If there is no new message, return
				if messages_combined == []:
					print('No new message unrecorded.')
					return
				
				# If there is at least one new message, then proceed normally
				else:
					break
			
			# If message doesn't exist in dic_thread, we add them
			else:
				for content in message.content:
			
					if content.type == 'text':
						message_text = content.text.value

					elif content.type == 'image_file':
						file_id = content.image_file.file_id
						file = self._client.files.content(file_id)
						file.write_to_file(f'images/{file_id}.png')
						message_text = f'Image generated: {file_id}'
						print(f'Image generated: {file_id}')
					
					else:
						message_text = 'Unidentified content type'

					messages_combined += [message_text]
					message_id = message.id
					assistant_id = message.assistant_id
					created_at = message.created_at
					file_ids = message.attachments
					role = message.role
					run_id = message.run_id

		messages_combined_string = '\n'.join(messages_combined)

		dic_message = {
			'assistant_id': assistant_id, 
			'created_at': created_at,
			'file_ids': file_ids,
			'role': role, 
			'run_id': run_id,
			'message_text': messages_combined_string
			}

		self.dic_thread[message_id] = dic_message
		self.last_message = messages_combined_string

		# return dic_message
	
	def run_thread(self, assistant: AgentHandler, prompt:list = None, attachments:list = None):
		
		if prompt is None and attachments is not None:
			raise ValueError('Attachment is provided without prompt')

		attachment_list = []

		# Format all file_ids provided in attachments
		for file in attachments:
			list_plc = [
				{
					'file_id': file,
					'tools': [{'type': 'code_interpreter'}]
				}
			]

			# Add it to attachment_list
			attachment_list += list_plc

		message = [
			{
				'role': 'user',
				'content': prompt,
				'attachments': attachment_list
			}
		]

		with self._client.beta.threads.runs.stream(
			thread_id=self.thread_id,
			assistant_id=assistant.assistant_id,
			event_handler=EventHandler(),
			additional_messages=message,
		) as stream:
			stream.until_done()

		self.get_last_message()
	
	def delete_thread(self):

		self._client.beta.threads.delete(thread_id=self.thread_id)
		print(f"thread: {self.thread_id} has been deleted.")