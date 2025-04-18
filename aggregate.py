import pandas as pd
from dateutil import parser
from datetime import datetime

class OSACAggregateProcessor:
    def __init__(self, parsed_file_name: str):
        """
        Initializes the OSACAggregateProcessor with the path to the CSV file.
        Attempts to read the file into a DataFrame.
        Raises a FileNotFoundError if the file cannot be found.
        """
        self.parsed_file_name = parsed_file_name
        try:
            # Read the CSV file into a DataFrame with UTF-8 encoding
            self.df = pd.read_csv(self.parsed_file_name, encoding='utf-8')
        except Exception as e:
            # Raise an error if file is not found
            raise FileNotFoundError(f"File not found: {self.parsed_file_name}")

    def safe_parse(self, x):
        """
        Safely parses a string into a datetime object. If the input is already
        a datetime object, it returns it as-is. If parsing fails, returns pd.NaT.
        """
        if isinstance(x, datetime):
            return x
        try:
            # Try to parse the string into a datetime object
            return parser.parse(x, fuzzy=True)
        except Exception:
            # Return Not-a-Time (pd.NaT) if parsing fails
            return pd.NaT

    @property
    def extract_monthly_data(self) -> pd.DataFrame:
        """
        Extracts and processes the monthly data. 
        - Handles missing values by replacing empty strings with NaN and dropping rows with all NaN values.
        - Parses the 'date' column into datetime format and extracts the month.
        - Removes the original 'date' column and returns the processed DataFrame.
        """
        OSAC_monthly = self.df[['country', 'date']].copy()
        
        # Replace empty strings with NaN
        OSAC_monthly.replace('', pd.NA, inplace=True)
        
        # Drop rows where all values are NaN
        OSAC_monthly.dropna(how='all', inplace=True)
        
        # Parse the 'date' column safely
        OSAC_monthly['date'] = OSAC_monthly['date'].apply(self.safe_parse)
        
        # Extract the month from the 'date' column and handle missing values (fill NaN with 0)
        OSAC_monthly['month'] = OSAC_monthly['date'].dt.month.fillna(0).astype(int)
        
        # Drop the 'date' column since it's no longer needed
        OSAC_monthly.drop(columns=['date'], inplace=True)
        
        return OSAC_monthly

    @property
    def extract_daily_data(self) -> pd.DataFrame:
        """
        Extracts and processes the daily data.
        - Handles missing values by replacing empty strings with NaN and dropping rows with all NaN values.
        - Returns the 'country' and 'date' columns without any additional processing.
        """
        OSAC_daily = self.df[['country', 'date']].copy()
        
        # Replace empty strings with NaN
        OSAC_daily.replace('', pd.NA, inplace=True)
        
        # Drop rows where all values are NaN
        OSAC_daily.dropna(how='all', inplace=True)
        
        return OSAC_daily
