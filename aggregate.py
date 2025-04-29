import pandas as pd
from dateutil.parser import parse
from datetime import datetime

class OSACAggregateProcessor:
    def __init__(self, parsed_file_name: str, iso_country_file: str):
        self.parsed_file_name = parsed_file_name
        self.iso_country_file = iso_country_file
        try:
            self.df = pd.read_csv(self.parsed_file_name, encoding='utf-8')
            # Load all ISO countries
            with open(iso_country_file, 'r') as f:
                self.all_countries = [line.strip() for line in f if line.strip()]
        except Exception as e:
            raise FileNotFoundError(f"File not found: {e}")

    def safe_parse(self, x):
        if isinstance(x, datetime):
            return x
        try:
            return parse(x, fuzzy=True)
        except Exception:
            return pd.NaT

    def get_all_country_dates(self, start_date, end_date):
        # Create a full date range using ALL ISO countries
        full_dates = pd.date_range(start=start_date, end=end_date, freq='D')
        # Cartesian product between all countries and full date range
        full_index = pd.MultiIndex.from_product(
            [self.all_countries, full_dates],
            names=['country', 'date']
        )
        return pd.DataFrame(index=full_index).reset_index()

    @property
    def extract_daily_data(self) -> pd.DataFrame:
        # Step 1: Load and clean alert data
        df = self.df[['country', 'date', 'protest', 'suppression', 'anticipated']].copy()
        df.replace('', pd.NA, inplace=True)
        df.dropna(subset=['country', 'date'], how='any', inplace=True)
        
        # Convert dates and ensure consistent format
        df['date'] = pd.to_datetime(df['date'].apply(self.safe_parse)).dt.normalize()
        df = df.dropna(subset=['date'])
        
        # Convert indicators to integers
        indicators = ['protest', 'suppression', 'anticipated']
        df[indicators] = df[indicators].fillna(0).astype(int)

        # Step 2: Create complete date range
        #start_date = df['date'].min()
        start_date = pd.to_datetime("2004-01-01")
        end_date = df['date'].max()
        full_dates_df = self.get_all_country_dates(start_date, end_date)
        full_dates_df['date'] = pd.to_datetime(full_dates_df['date']).dt.normalize()

        # Step 3: Standardize country names before merge
        # Create a mapping from alert country names to ISO codes if needed
        # (This assumes you have a way to map them - may need additional logic)
        country_map = {c: c for c in df['country'].unique()}  # Default 1:1 mapping
        
        grouped = (
            df.assign(country_iso=df['country'].map(country_map))
            .groupby(['country_iso', 'date'])[indicators]
            .max()
            .reset_index()
        )

        # Step 4: Perform merge with proper columns
        full_daily = (
            full_dates_df
            .merge(grouped, 
                  left_on=['country', 'date'],
                  right_on=['country_iso', 'date'],
                  how='left')
            .drop(columns=['country_iso'])
        )
        
        # Fill missing values
        full_daily[indicators] = full_daily[indicators].fillna(0).astype(int)
        
        return full_daily

    @property
    def extract_monthly_data(self) -> pd.DataFrame:
        daily = self.extract_daily_data.copy()
        daily['month'] = daily['date'].dt.to_period('M').astype(str)
        monthly = daily.groupby(['country', 'month'])[['protest', 'suppression', 'anticipated']].max().reset_index()
        return monthly