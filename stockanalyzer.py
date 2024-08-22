import json
from openai import OpenAI
from yfinancehandler import YFHandler
from filehandler import FileHandler
from agenthandler import AgentHandler
from eventhandler import ThreadManager

# There has to be a better way of doing this
with open('config/dataframe_schemas.json', 'r') as f:
    schemas = json.load(f)

def analyze_stock(client: OpenAI, ticker: list):
	
	yf_handler = YFHandler(stock_list=ticker, schemas=schemas)

	df_stocks = yf_handler.import_stocks()
	df_cashflow = yf_handler.import_cashflow()
	df_income_stmt = yf_handler.import_income_stmt()

	# Write to CSV
	# Technically this will be done by the FileHandler but just to be safe
	df_stocks.to_csv('openai_upload_files/df_stocks.csv', index=False)
	df_cashflow.to_csv('openai_upload_files/df_cashflow.csv', index=False)
	df_income_stmt.to_csv('openai_upload_files/df_income_stmt.csv', index=False)

	file_stocks = FileHandler(
		df=df_stocks,
		dic_file=dic_files,
		file_name='df_stocks.csv',
		dic_file_name=OPENAI_DIC_FILE_NAME,
		file_path=FILE_PATH,
		dic_file_path=FILE_PATH,
		client=client
	)

	file_cashflow = FileHandler(
		df=df_cashflow,
		dic_file=dic_files,
		file_name='df_cashflow.csv',
		dic_file_name=OPENAI_DIC_FILE_NAME,
		file_path=FILE_PATH,
		dic_file_path=FILE_PATH,
		client=client
	)

	file_income_stmt = FileHandler(
		df=df_income_stmt,
		dic_file=dic_files,
		file_name='df_income_stmt.csv',
		dic_file_name=OPENAI_DIC_FILE_NAME,
		file_path=FILE_PATH,
		dic_file_path=FILE_PATH,
		client=client
	)

	# Update files on OpenAI
	file_stocks.update_openai_file(dic_file=dic_files)
	file_cashflow.update_openai_file(dic_file=dic_files)
	file_income_stmt.update_openai_file(dic_file=dic_files)

	# Have to manually update the tool_resources because the file_id can change
	dic_assistants['fin_analyst']['tool_resources'] = {
		'code_interpreter': {'file_ids': [dic_files['df_stocks.csv']]}
	}

	with open('config/assistants.json', 'w') as json_file:
		json.dump(dic_assistants, json_file)
		print(f'assistants.json file has been updated')

	fin_analyst = AgentHandler(
		client = client, 
		new=False,
		assistant_name = 'fin_analyst',
		dic_file = dic_assistants,
		dic_file_name = 'assistants.json',
		dic_file_path='config/'
		)

	fin_consultant = AgentHandler(
		client = client,
		new=False,
		assistant_name = 'fin_consultant',
		dic_file = dic_assistants,
		dic_file_name = 'assistants.json',
		dic_file_path='config/'
		)
	
	# prompt_start = f"This is your client. I want you to advice me on the stocks I list below.\
	# 	I want to know the stocks' performance, if they're overvalued or undervalued, and whether or not they'll be a good investment.\
	# 	I am looking for a long term (5+ years) investment and I have a relatively high risk tolerance.\
	# 	Stocks: {ticker}"

	prompt_start = f"This is the financial consultant.\
		The client wants advice on the following stocks.\
		I need you to provide me your analysis on these stocks so I can provide the appropriate recommendations.\
		You will be provided with the data of these stocks, use them as you see fit.\
		Stocks: {ticker}"

	thread = ThreadManager(
		client=client,
		prompt=prompt_start
	)

	thread.run_thread(
		assistant=fin_analyst,
		prompt=prompt_start,
		attachments=[file_stocks.file_id, file_cashflow.file_id, file_income_stmt.file_id]
	)

	next_prompt = thread.last_message

	thread.run_thread(
		assistant=fin_consultant,
		prompt=next_prompt
	)

	thread.delete_thread()

	return thread.last_message