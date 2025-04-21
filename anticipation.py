from datetime import datetime
import pandas as pd
from dateutil.parser import parse

class OSACDateAnticipationProcessor:
    def __init__(self, df: pd.DataFrame, columns_to_return=None):
        super().__init__()
        self.df = df.copy()
        self.df.columns = self.df.columns.str.strip()
        self.columns_to_return = columns_to_return or ["OSAC_ID", "country", "date", "protest", "suppression", "anticipated"]  # If no columns are specified, return all

    @staticmethod
    def safe_parse(x):
        if isinstance(x, datetime):
            return x
        try:
            return parse(x, fuzzy=True)
        except Exception:
            return pd.NaT

    @property
    def extract(self) -> pd.DataFrame:
        # Apply safe parsing to the date columns
        self.df['OSAC_Date'] = self.df['OSAC_Date'].apply(self.safe_parse)
        self.df['date'] = self.df['date'].apply(self.safe_parse)
        
        # Create the 'anticipated' column
        self.df['anticipated'] = (self.df['date'] > self.df['OSAC_Date']).astype(int)
        
        # Return only the specified columns, or all columns if none specified
        if self.columns_to_return:
            return self.df[self.columns_to_return]
        else:
            return self.df
