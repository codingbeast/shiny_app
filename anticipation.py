from datetime import datetime
from typing import Optional
import pandas as pd
from dateutil.parser import parse

class OSACDateAnticipationProcessor:
    def __init__(self, df: pd.DataFrame, columns_to_return=None):
        super().__init__()
        self.df = df.copy()
        self.df.columns = self.df.columns.str.strip()
        self.columns_to_return = columns_to_return or ["OSAC_ID", "country", "date", "protest", "suppression", "anticipated"]  # If no columns are specified, return all

    def safe_parse(self, date_str: str, format: str = "%Y-%m-%d") -> Optional[datetime]:
        try:
            return datetime.strptime(date_str.strip(), format)
        except Exception:
            try:
                return parse(date_str,fuzzy=True)  # Fallback to flexible parsing
            except Exception:
                return pd.NaT


    @property
    def extract(self) -> pd.DataFrame:
        # Apply safe parsing to the date columns
        # self.df['OSAC_Date'] = self.df['OSAC_Date'].apply(self.safe_parse)
        # self.df['date'] = self.df['date'].apply(self.safe_parse)
        self.df['OSAC_Date'] = self.df['OSAC_Date'].apply(lambda x: self.safe_parse(x, format="%m/%d/%Y"))
        self.df['date'] = self.df['date'].apply(lambda x: self.safe_parse(x, format="%d/%m/%Y"))

        
        # Create the 'anticipated' column
        self.df['anticipated'] = (self.df['date'] > self.df['OSAC_Date']).astype(int)
        
        # Return only the specified columns, or all columns if none specified
        if self.columns_to_return:
            return self.df[self.columns_to_return]
        else:
            return self.df
