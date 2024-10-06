import time
import pandas as pd
import yfinance as yf
from typing import Literal
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains

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
	
	def _get_news_links(self, dic_urls:dict, max_links:int=100, scroll_amount:int=1000, scroll_limit:int=10, pause_time:int=5):

		# Set up driver, this will open a Google Chrome
		# We can automatically close this later
		driver = webdriver.Chrome()

		dic_links = {}

		for stock in dic_urls:

			driver.get(dic_urls[stock])

			news_links = []

			# Go to the bottom of the screen as a first action
			ActionChains(driver).scroll_by_amount(0, 10000).perform()

			for _ in range(scroll_limit):

				if len(news_links) >= max_links:
					
					return news_links[0:100]
				else:
					# print(f'loop:{_}')
					# Scroll down in smaller steps
					ActionChains(driver).scroll_by_amount(0, scroll_amount).perform()
					
					# Wait for new content to load
					time.sleep(pause_time)

					# Parse the page source with BeautifulSoup
					soup = BeautifulSoup(driver.page_source, 'html.parser')

					# Find all news links on the page
					articles = soup.find_all('a', href=True)  # Update class name as needed
					for article in articles:
						link = article['href']
						if "/news/" in link:
							link = f"https://finance.yahoo.com{link}"  # Complete the URL
						if link not in news_links:  # Avoid duplicates
							news_links.append(link)

			dic_links[stock] = news_links[0:100]

		# Close driver, we don't need it anymore
		driver.quit()

		return dic_links

	def get_stock_news(self):
		
		dic_urls = {}

		for stock in self.stock_list:
			
			dic_urls[stock] = f'https://finance.yahoo.com/quote/{stock}/news/'

		dic_links = self._get_news_links(dic_urls=dic_urls)

		return dic_links