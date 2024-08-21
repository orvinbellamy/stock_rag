README

TODO:
- Success multiple assistants can interach in the same thread
- Time to refine the assistants
- Fix this
	# Have to manually update the tool_resources because the file_id can change
dic_assistants['fin_analyst']['tool_resources'] = {
    'code_interpreter': {'file_ids': [dic_files['df_stocks.csv']]}
}
- We're not using dic_thread for ThreadManager() anymore, we're just using 
	self.messages = self._client.beta.threads.messages.list(thread_id=self.thread_id).data
	Or do we? We have the self.last_message