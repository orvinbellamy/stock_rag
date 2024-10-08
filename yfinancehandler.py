import time
import pandas as pd
import re
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
	
	def _get_news_links(self, dic_urls:dict, driver=None, max_links:int=10, scroll_amount:int=1000, scroll_limit:int=10, pause_time:int=5):

		"""
		This method is to get links from Yahoo news page.
		It's specifically designed only for Yahoo news page.
		It uses selenium to load the webpage with a Chrome driver (other drivers possible too).
		And then beautifulsoup to parse the HTML of the webpage.
		By default it returns 10 links.
		This method is to be used in conjunction with _get_articles()
		"""

		# If driver isn't given, we define it here and then close it at the end of the method
		if driver is None:
			driver = webdriver.Chrome()

		# Set up empty dictionary to store links later
		dic_links = {}

		# Loop through each stock
		# Each stock will have its own news webpage
		for stock in dic_urls:
			
			# Load the news webpage on the Chrome driver
			driver.get(dic_urls[stock])

			# Set empty list to store the links later
			news_links = []

			# Go to the bottom of the screen as a first action
			# This is done to load more news. Yahoo news is infinite scrolling
			ActionChains(driver).scroll_by_amount(0, 10000).perform()

			# Scroll limit is the maximum number of scrolls we do
			# This is a measure against Yahoo News' infinite scrolling
			# Either we get the max number of links we need or we scroll the maximum number of times
			for _ in range(scroll_limit):
				
				# If we have the max number of links, we exit the loop
				if len(news_links) >= max_links:
					break

				# Scroll down in smaller steps
				ActionChains(driver).scroll_by_amount(0, scroll_amount).perform()
				
				# Wait for new content to load
				time.sleep(pause_time)

				# Parse the page source with BeautifulSoup
				soup = BeautifulSoup(driver.page_source, 'html.parser')

				# Example: Select elements with the class "stream-items"
				stream_items = soup.select('ul[class^="stream-items"]')

				# Iterate through each <ul> element found
				for ul in stream_items:
					# Find all <a> elements where class starts with "subtle-link fin-size-small titles"
					links = ul.find_all('a', class_=re.compile(r'^subtle-link fin-size-small titles'))

					# Extract the href from each <a> element
					for link in links:

						news_links.append(link.get('href'))

			dic_links[stock] = news_links[0:max_links]

		if driver is None:
			# Close driver, we don't need it anymore
			driver.quit()

		return dic_links
	
	def _get_articles(self, dic_links:dict, driver=None, pause_time:int=3):
		
		if driver is None:
			driver = webdriver.Chrome()

		dic_html = {}
		
		for stock_links in dic_links:
			
			dic_html[stock_links] = []

			for link in dic_links[stock_links]:

				driver.get(link)

				time.sleep(pause_time)
			
				soup = BeautifulSoup(driver.page_source, 'html.parser')

				# Find the <div> with class starting with "body-wrap%"
				body_wrap = soup.find('div', class_=re.compile(r'^body-wrap'))

				# If the first body-wrap is found, look inside for <div class="body%">
				if body_wrap:
					body_content = body_wrap.find('div', class_=re.compile(r'^body'))

					# If body-content is found, extract all <p> tags inside it
					# if body_content:
					paragraphs = body_content.find_all('p')

					# Collect the article text
					article_text = "\n".join([p.get_text() for p in paragraphs])

					# Store the article text by the link in the dictionary
					dic_html[stock_links].append(article_text)

		if driver is None:
			driver.quit()

		return dic_html

	def get_stock_news(self, max_news:int=10):
		
		dic_urls = {}
		driver = webdriver.Chrome()

		for stock in self.stock_list:
			
			dic_urls[stock] = f'https://finance.yahoo.com/quote/{stock}/news/'

		dic_links = self._get_news_links(dic_urls=dic_urls, driver=driver, max_links=max_news)

		dic_articles = self._get_articles(dic_links=dic_links, driver=driver)

		driver.quit()

		return dic_links, dic_articles