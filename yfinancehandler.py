import pandas as pd
import yfinance as yf
from typing import Literal

class YFHandler():
	def __init__(self, stock_list: list, schemas: dict):
		
		self.stocks = yf.Tickers(stock_list)
		self.stock_list = stock_list
		self.schemas = schemas
	
	def import_stocks(self):

		df = pd.DataFrame(columns=dict(self.schemas['stocks']))

		for stock in self.stock_list:

			df_plc = self.stocks.tickers[stock].history(period='max').reset_index()
			df_plc['Ticker'] = stock

			df = pd.concat([df, df_plc], ignore_index=True)

		return df

	def import_cashflow(self, period:Literal['year', 'quarter']='quarter'):

		df = pd.DataFrame(columns=dict(self.schemas['cashflow']))

		if period=='year':
			for stock in self.stock_list:

				df_plc = self.stocks.tickers[stock].cashflow.T.reset_index()
				df_plc.rename(columns={'index': 'Date'},inplace=True)
				df_plc['Ticker'] = stock

				df = pd.concat([df, df_plc], ignore_index=True)
		elif period=='quarter':
			for stock in self.stock_list:

				df_plc = self.stocks.tickers[stock].quarterly_cashflow.T.reset_index()
				df_plc.rename(columns={'index': 'Date'},inplace=True)
				df_plc['Ticker'] = stock

				df = pd.concat([df, df_plc], ignore_index=True)
		else:
			raise ValueError("period argument has to be either 'year' or 'quarter'")
		
		return df
	
	def import_income_stmt(self, period:Literal['year', 'quarter']='quarter'):
		
		df = pd.DataFrame(columns=dict(self.schemas['income_stmt']))

		if period=='year':
			for stock in self.stock_list:
				
				df_plc = self.stocks.tickers[stock].income_stmt.T.reset_index()
				df_plc.rename(columns={'index': 'Date'},inplace=True)
				df_plc['Ticker'] = stock

				df = pd.concat([df, df_plc], ignore_index=True)

		elif period=='quarter':
			for stock in self.stock_list:
				
				df_plc = self.stocks.tickers[stock].quarterly_income_stmt.T.reset_index()
				df_plc.rename(columns={'index': 'Date'},inplace=True)
				df_plc['Ticker'] = stock

				df = pd.concat([df, df_plc], ignore_index=True)
		else:
			raise ValueError("period argument has to be either 'year' or 'quarter'")

		return df
	
	def import_balance_sheet(self, period:Literal['year', 'quarter']='quarter'):
		
		df = pd.DataFrame(columns=dict(self.schemas['balance_sheet']))

		if period=='year':
			for stock in self.stock_list:
				
				df_plc = self.stocks.tickers[stock].balance_sheet.T.reset_index()
				df_plc.rename(columns={'index': 'Date'},inplace=True)
				df_plc['Ticker'] = stock

				df = pd.concat([df, df_plc], ignore_index=True)

		elif period=='quarter':
			for stock in self.stock_list:
				
				df_plc = self.stocks.tickers[stock].quarterly_balance_sheet.T.reset_index()
				df_plc.rename(columns={'index': 'Date'},inplace=True)
				df_plc['Ticker'] = stock

				df = pd.concat([df, df_plc], ignore_index=True)
		else:
			raise ValueError("period argument has to be either 'year' or 'quarter'")

		return df
	
	def import_actions(self):

		df = pd.DataFrame(columns=dict(self.schemas['actions']))

		for stock in self.stock_list:

			df_plc = self.stocks.tickers[stock].actions.reset_index()
			df_plc['Ticker'] = stock

			df = pd.concat([df, df_plc], ignore_index=True)

		return df
	
	def import_shares_count(self, start_date:str, end_date:str=None):

		df = pd.DataFrame(columns=dict(self.schemas['shares_count']))

		for stock in self.stock_list:

			df_plc = self.stocks.tickers[stock].get_shares_full(start=start_date, end=end_date).reset_index()
			df_plc.rename(columns={'index': 'Date', '0': 'Shares Count'},inplace=True)
			df_plc['Ticker'] = stock

			df = pd.concat([df, df_plc], ignore_index=True)

		return df