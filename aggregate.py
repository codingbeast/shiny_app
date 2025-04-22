import pandas as pd
from dateutil.parser import parse
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
            return parse(x, fuzzy=True)
        except Exception:
            return pd.NaT

    def get_all_country_dates(self, countries, start_date, end_date):
        # Create a full date range
        full_dates = pd.date_range(start=start_date, end=end_date, freq='D')
        # Cartesian product between countries and full date range
        full_index = pd.MultiIndex.from_product(
            [countries, full_dates],
            names=['country', 'date']
        )
        return pd.DataFrame(index=full_index).reset_index()

    @property
    def extract_daily_data(self) -> pd.DataFrame:
        df = self.df[['country', 'date', 'protest', 'suppression', 'anticipated']].copy()
        df.replace('', pd.NA, inplace=True)
        df.dropna(subset=['country', 'date'], how='any', inplace=True)
        df['date'] = df['date'].apply(self.safe_parse)
        df = df.dropna(subset=['date'])

        indicators = ['protest', 'suppression', 'anticipated']
        df[indicators] = df[indicators].fillna(0).astype(int)

        # Group actual data
        grouped = df.groupby(['country', 'date'])[indicators].max().reset_index()

        # Get full date range
        start_date = pd.Timestamp('2004-01-01')
        end_date = pd.Timestamp.today().normalize()
        countries = grouped['country'].unique()
        full_dates_df = self.get_all_country_dates(countries, start_date, end_date)

        # Merge and fill missing with 0
        full_daily = full_dates_df.merge(grouped, on=['country', 'date'], how='left')
        full_daily[indicators] = full_daily[indicators].fillna(0).astype(int)

        return full_daily

    @property
    def extract_monthly_data(self) -> pd.DataFrame:
        daily = self.extract_daily_data.copy()
        daily['month'] = daily['date'].dt.to_period('M').astype(str)
        monthly = daily.groupby(['country', 'month'])[['protest', 'suppression', 'anticipated']].max().reset_index()
        return monthly
