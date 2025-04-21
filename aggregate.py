import pandas as pd
from dateutil.parser import parse
from datetime import datetime

class OSACAggregateProcessor:
    def __init__(self, parsed_file_name: str):
        # Store the file name
        self.parsed_file_name = parsed_file_name
        try:
            # Read the CSV file into a DataFrame using UTF-8 encoding
            self.df = pd.read_csv(self.parsed_file_name, encoding='utf-8')
        except Exception:
            # If file not found or can't be read, raise a helpful error
            raise FileNotFoundError(f"File not found: {self.parsed_file_name}")

    def safe_parse(self, x):
        """
        Safely parses a date string into a datetime object.
        If it's already a datetime, just return it.
        If parsing fails, return NaT (Not a Time).
        """
        if isinstance(x, datetime):
            return x
        try:
            return parse(x, fuzzy=True)
        except Exception:
            return pd.NaT

    @property
    def extract_daily_data(self) -> pd.DataFrame:
        """
        Processes and returns daily aggregated data by country and date.
        Each row indicates whether any of the events (protest, suppression, anticipated)
        happened on a given day in a country.
        """
        # Keep only necessary columns
        df = self.df[['country', 'date', 'protest', 'suppression', 'anticipated']].copy()

        # Replace empty strings with actual NaN values
        df.replace('', pd.NA, inplace=True)

        # Drop rows where 'country' or 'date' is missing
        df.dropna(subset=['country', 'date'], how='any', inplace=True)

        # Parse 'date' strings into datetime objects
        df['date'] = df['date'].apply(self.safe_parse)

        # Drop rows where 'date' parsing failed
        df = df.dropna(subset=['date'])

        # Fill NaNs in event columns with 0 and convert to integers
        indicators = ['protest', 'suppression', 'anticipated']
        df[indicators] = df[indicators].fillna(0).astype(int)

        # Group by 'country' and 'date', and take max of each event column
        # (so if any event occurred that day, it will be marked as 1)
        daily = df.groupby(['country', 'date'])[indicators].max().reset_index()

        return daily

    @property
    def extract_monthly_data(self) -> pd.DataFrame:
        """
        Aggregates the daily data to a monthly level.
        Each row shows if any protest, suppression, or anticipation event occurred
        in that month for a country.
        """
        # First, get the cleaned daily data
        daily = self.extract_daily_data.copy()

        # Extract 'month' in YYYY-MM format from 'date'
        daily['month'] = daily['date'].dt.to_period('M').astype(str)

        # Group by 'country' and 'month', taking max to see if any event happened
        monthly = daily.groupby(['country', 'month'])[['protest', 'suppression', 'anticipated']].max().reset_index()

        return monthly
