import pandas as pd
import yfinance as yf

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

    def import_cashflow(self):

        df = pd.DataFrame(columns=dict(self.schemas['cashflow']))

        for stock in self.stock_list:

            df_plc = self.stocks.tickers[stock].cashflow.T.reset_index()
            df_plc.rename(columns={'index': 'Date'},inplace=True)
            df_plc['Ticker'] = stock

            df = pd.concat([df, df_plc], ignore_index=True)
        
        return df
    
    def import_income_stmt(self):
        
        df = pd.DataFrame(columns=dict(self.schemas['income_stmt']))

        for stock in self.stock_list:

            df_plc = self.stocks.tickers[stock].income_stmt.T.reset_index()
            df_plc.rename(columns={'index': 'Date'},inplace=True)
            df_plc['Ticker'] = stock

            df = pd.concat([df, df_plc], ignore_index=True)

        return df