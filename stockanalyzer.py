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

def stock_data_setup(
	client: OpenAI, 
	ticker: list,
	config:dict, 
	dic_files:dict=None
	):

	OPENAI_DIC_FILE_NAME = 'openai_files.json'
	dic_data_collection = {}
	yf_handler = YFHandler(stock_list=ticker, schemas=schemas)

	# Mapping of data types to file names and handler methods
	data_mapping = {
		'price': {
			'file_name': 'df_stocks.csv',
			'method': 'import_stocks'
		},
		'cashflow': {
			'file_name': 'df_cashflow.csv',
			'method': 'import_cashflow'
		},
		'income_statement': {
			'file_name': 'df_income_stmt.csv',
			'method': 'import_income_stmt'
		},
		'balance_sheet': {
			'file_name': 'df_balance_sheet.csv',
			'method': 'import_balance_sheet'
		}
	}

	# Loop each data requested (i.e. stock price, cashflow, income statement)
	for data_requested, data_config in config.items():

		# If it exists in data_mapping (i.e. it's a valid data from yfinance)
		if data_requested in data_mapping.keys():
			
			# Get the right method from YFHandler
			import_method = getattr(yf_handler, data_mapping[data_requested]['method'])

			# Execute the method to get the data
			df_data = import_method(period=data_config['period'])

			# Create a FileHandler object
			file_handler = FileHandler(
				df=df_data,
				dic_file=dic_files,
				file_name=data_mapping[data_requested]['file_name'],
				dic_file_name=OPENAI_DIC_FILE_NAME,
				client=client
			)

			file_handler.update_openai_file()

			# Store the file handler in the collection
			dic_data_collection[data_requested] = file_handler

	return dic_data_collection

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