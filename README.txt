README

TODO:
- Success multiple assistants can interach in the same thread
- Time to refine the assistants
- Fix this
	# Have to manually update the tool_resources because the file_id can change
dic_assistants['fin_analyst']['tool_resources'] = {
    'code_interpreter': {'file_ids': [dic_files['df_stocks.csv']]}
}
- need to work on stockanalyzer.py