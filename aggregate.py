import pandas as pd
from dateutil import parser
from datetime import datetime

class OSACAggregateProcessor:
    def __init__(self, parsed_file_name: str):
        self.parsed_file_name = parsed_file_name
        try:
            self.df = pd.read_csv(self.parsed_file_name, encoding='utf-8')
        except Exception:
            raise FileNotFoundError(f"File not found: {self.parsed_file_name}")

    def safe_parse(self, x):
        if isinstance(x, datetime):
            return x
        try:
            return parser.parse(x, fuzzy=True)
        except Exception:
            return pd.NaT

    @property
    def extract_daily_data(self) -> pd.DataFrame:
        df = self.df[['country', 'date', 'protest', 'suppression', 'anticipated']].copy()
        df.replace('', pd.NA, inplace=True)
        df.dropna(subset=['country', 'date'], how='any', inplace=True)
        df['date'] = df['date'].apply(self.safe_parse)
        df = df.dropna(subset=['date'])

        indicators = ['protest', 'suppression', 'anticipated']
        df[indicators] = df[indicators].fillna(0).astype(int)

        daily = df.groupby(['country', 'date'])[indicators].max().reset_index()
        return daily

    @property
    def extract_monthly_data(self) -> pd.DataFrame:
        daily = self.extract_daily_data.copy()
        daily['month'] = daily['date'].dt.to_period('M').astype(str)
        monthly = daily.groupby(['country', 'month'])[['protest', 'suppression', 'anticipated']].max().reset_index()
        return monthly
