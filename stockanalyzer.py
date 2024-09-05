import json
import openai
from typing import Literal
from openai import OpenAI
from yfinancehandler import YFHandler
from filehandler import FileHandler
from agenthandler import AgentHandler
from eventhandler import ThreadManager

# There has to be a better way of doing this
with open('config/dataframe_schemas.json', 'r') as f:
    schemas = json.load(f)

def stock_data_setup(client: OpenAI, ticker: list, type: Literal['price', 'cash', 'income'], dic_files: dict):

	FILE_PATH = 'openai_upload_files/'
	OPENAI_DIC_FILE_NAME = 'openai_files.json'

	yf_handler = YFHandler(stock_list=ticker, schemas=schemas)

	if type == 'price':
		df = yf_handler.import_stocks()
		stock_data_file_name = 'df_stocks.csv'
		
	elif type == 'cash':
		df = yf_handler.import_cashflow()
		stock_data_file_name = 'df_cashflow.csv'

	elif type == 'income':
		df = yf_handler.import_income_stmt()
		stock_data_file_name = 'df_income_stmt.csv'

	else:
		raise ValueError('Stock data type is not properly defined.')
	
	# Write to CSV
	# Technically this will be done by the FileHandler but just to be safe
	df.to_csv(f'openai_upload_files/{stock_data_file_name}', index=False)

	file_stock_data = FileHandler(
		df=df,
		dic_file=dic_files,
		file_name=stock_data_file_name,
		dic_file_name=OPENAI_DIC_FILE_NAME,
		file_path=FILE_PATH,
		dic_file_path=FILE_PATH,
		client=client
	)
	
	file_stock_data.update_openai_file(dic_file=dic_files)
		
	return file_stock_data

def analyze_stock(ticker: list, dic_files: dict, dic_assistants: dict):
	
	client = OpenAI()

	file_stocks = stock_data_setup(client=client, ticker=ticker, type='price', dic_files=dic_files)
	file_cashflow = stock_data_setup(client=client, ticker=ticker, type='cash', dic_files=dic_files)
	file_income_stmt = stock_data_setup(client=client, ticker=ticker, type='income', dic_files=dic_files)

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