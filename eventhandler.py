from typing_extensions import override
from openai import AssistantEventHandler, OpenAI
from openai.types.beta.threads.message import Message
from agenthandler import AgentHandler
import time
import pandas as pd
 
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
	def __init__(
			self, 
			client:OpenAI, 
			prompt:str,
			# assistants:list[AgentHandler]=[], # maybe this is better with **kwargs?
			attachments:list=[]):
		
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

		self.messages = []
		self._client = client
		self.thread = self._client.beta.threads.create(messages=message)
		self.thread_id = self.thread.id

		df_schema = {
			'message_id': 'str',
			'assistant_id': 'str',
			'created_at': 'int',
			'file_ids': 'str',
			'role': 'str',
			'run_id': 'str',
			'message_text': 'str',
			'_msg_loc': 'int',
			'node_run_id': 'int'
		}
		self.df_messages = pd.DataFrame({col: pd.Series(dtype=dt) for col, dt in df_schema.items()})

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
				# file.write_to_file(f'images/{file_id}.png')
				message_text = f'Image generated: {file_id}'
				print(f'Image generated: {file_id}')
			
			else:
				message_text = 'Unidentified content type'
		

		dic_message = {
			'message_id': message_id,
			'assistant_id': assistant_id, 
			'created_at': created_at, 
			'file_ids': file_ids, 
			'role': role, 
			'run_id': run_id,
			'message_text': message_text,
			'_msg_loc': 0
			}
		self.messages += [dic_message]
		
		df_append = pd.DataFrame([dic_message])
		self.df_messages =  pd.concat([self.df_messages, df_append], ignore_index=True)
		
		self.last_message = message_text

	# # Add assistant to link it to the thread
	# def add_assistant(self, assistant:AgentHandler):

	# 	self.manager.link(thread=self, agent=assistant)

	# # Remove assistant from the thread
	# def remove_assistant(self, assistant:AgentHandler):

	# 	self.manager.link(thread=self, agent=assistant)

	def _combine_messages(self, message: pd.Series, messages_combined: list, index: str):
		messages_combined_string = '\n'.join(messages_combined)

		dic_message = {
			'message_id': message['message_id'],
			'assistant_id': message['assistant_id'], 
			'created_at': message['created_at'],
			'file_ids': message['file_ids'],
			'role': message['role'], 
			'run_id': message['run_id'],
			'message_text': messages_combined_string,
			'_msg_loc': message['_msg_loc']
			}
		
		return dic_message
	
	def get_last_message(self, node_run_id:int=None) -> str:
		
		#### Note assistant_id can be None

		print('get_last_message initiated')

		messages = self._client.beta.threads.messages.list(thread_id=self.thread_id).data
		# Reverse the list order because we want to use _msg_loc to filter
		messages = messages[::-1]
		# Filter for new messages only
		max_loc = self.df_messages['_msg_loc'].max()+1
		messages = messages[max_loc:]

		if len(messages) > 0:
			messages_combined = []
			messages_append_placeholder = []
			previous_index = max_loc
			# Set assistant_id
			asst_id = '' 

			dic_new_messages = [
				{
					'message_id': message.id,
					'assistant_id': message.assistant_id,
					'created_at': message.created_at,
					'file_ids': message.attachments,
					'role': message.role,
					'run_id': message.run_id,
					'message_text': message.content[0].text.value,
					'_msg_loc': index + max_loc,
					'node_run_id': node_run_id
				} for index, message in enumerate(messages)]
			
			df_new_messages = pd.DataFrame(dic_new_messages)

			# For now this records multiple messages from assistant separately
			# Need to combine them together to make them one single string
			for index, row in df_new_messages.iterrows():

				row_assistant_id, row_message_text = row[['assistant_id', 'message_text']]

				# if asst_id is blank that means it's the first loop
				if asst_id == '':
					print('asst_id = blank')
					asst_id = row_assistant_id

					# print(f'new_message: {message_text}')
					messages_combined.append(row_message_text)

				# Message is still by the same entity, keep collecting message
				elif row_assistant_id == asst_id:
					
					print('message.assistant_id == asst_id, proceed normally to collect message')

					# print(f'new_message: {message_text}')
					messages_combined.append(row_message_text)

				# Message is by another entity, add the combined message of the last entity
				# and start a new round of messages
				else: # message.assistant_id != asst_id
					
					print('message.assistant_id != asst_id, record previous message first')
					# If there is no new message, return
					if messages_combined == []:
						print('No new message unrecorded.')
					
					# If there is at least one new message, then proceed normally
					else:
						
						# Reverse the order so that first message comes first
						# messages_combined = messages_combined[::-1]
						# print(messages_combined)
						# We use previous message because the current loop is the new message
						dic_message = self._combine_messages(message=previous_message, messages_combined=messages_combined, index=previous_index)
						# print(dic_message)
						# Add message by the previous entity to the list first
						messages_append_placeholder.append(dic_message)

						self.messages += messages_append_placeholder

						df_append = pd.DataFrame([dic_message])
						self.df_messages =  pd.concat([self.df_messages, df_append], ignore_index=True)

						# Reset messages_combined to empty list to prepare for the next entity's messages
						messages_combined = []
						# print(messages_combined)

						# Update asst_id to the new entity (note user role will have None assistant_id)
						asst_id = row_assistant_id

						# print(f'new_message: {row_message_text}')
						messages_combined.append(row_message_text)
						# print(messages_combined)
				
				# Set message as previous_message for the next loop
				previous_message = row
				previous_index = index + max_loc

			# messages_combined = messages_combined[::-1]
			dic_message = self._combine_messages(message=previous_message, messages_combined=messages_combined, index=previous_index)

			messages_append_placeholder.append(dic_message)
			self.messages += messages_append_placeholder

			df_append = pd.DataFrame([dic_message])
			self.df_messages =  pd.concat([self.df_messages, df_append], ignore_index=True)

			self.last_message = dic_message['message_text']

			return dic_message['message_text']
		else:
			print('No new message')

			return None
	
	def run_thread(self, assistant:AgentHandler, prompt:str=None, attachments:list=[], node_run_id:int=None, end_pause:int=5):
		
		if prompt is None and len(attachments) > 0:
			raise ValueError('Attachment is provided without prompt')
		
		elif prompt is None:

			stream = self._client.beta.threads.runs.create(
				thread_id=self.thread_id,
				assistant_id=assistant.assistant_id,
				stream=True
				# event_handler=EventHandler()
			) 
			# as stream:
			# 	stream.until_done()

			for event in stream:
				print(event, end='\r')
		
		elif prompt is not None:
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

			stream = self._client.beta.threads.runs.create(
				thread_id=self.thread_id,
				assistant_id=assistant.assistant_id,
				additional_messages=message,
				stream=True
			) 
			# as stream:
			# 	stream.until_done()

			for event in stream:
				print(event, end='\r')

		# Buffer maybe we need to wait after thread run is done for data to update
		time.sleep(1)

		self.get_last_message(node_run_id=node_run_id)

		# Sleep for 5 seconds in anticipation that there will be multiple consecutive runs
		time.sleep(5)

		return self.last_message
	
	def delete_thread(self):

		self._client.beta.threads.delete(thread_id=self.thread_id)
		print(f"thread: {self.thread_id} has been deleted.")

	
	def clear_and_delete(self):

		"""
		Delete thread and self to free up memory
		"""

		self.delete_thread()
		
		self.messages = None
		self.df_messages = None

		# Delete the instance by removing references to itself
		del self


## Manually checking run status of a thread
## Primivite, not needed
def check_run_status(client, thread_id: str, run_id: str, n_tries: int, wait_time):
	
	## Wait until status is completed
	for i in range(0, n_tries):

		# Retrieve the latest run
		run_retrieve = client.beta.threads.runs.retrieve(
			thread_id=thread_id,
			run_id=run_id
		)

		# Get the run status
		run_status = run_retrieve.status

		# Check run status
		if run_status == 'completed':
			print('Run is completed')
			return f'Run is completed (run_id: {run_id}, thread_id {thread_id})'
		elif run_status == 'in_progress':
			print('Run is in progress')
			pass
		elif run_status == 'queued':
			print('Run is queued')
			pass
		elif run_status == 'cancelling':
			print('Run is cancelling')
			pass
		elif run_status == 'cancelled':
			raise ValueError(f'Error: run is cancelled (run_id: {run_id}, thread_id {thread_id})')
		elif run_status == 'failed':
			raise ValueError(f'Error: run has failed (run_id: {run_id}, thread_id {thread_id})')
		elif run_status == 'expired':
			raise ValueError(f'Error: run has expired (run_id: {run_id}, thread_id {thread_id})')
		elif run_status == 'requires_action':
			print('Action is required')
			return f'Action required (run_id: {run_id}, thread_id {thread_id})'

		# Sleep to give time for the run to process
		time.sleep(wait_time)