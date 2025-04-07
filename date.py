import re, os
import pandas as pd
from typing import Optional

class OSACDateParser:
    """Flexible date parser that can work with any data source"""
    def __init__(self):
        months = [
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december"
        ]
        self.months_pattern = re.compile(
            r"\b(" + "|".join(months) + r")\b",
            flags=re.IGNORECASE
        )
    def parse_date(self, title: str, osac_date: str) -> Optional[str]:
        if self.months_pattern.search(title):
            return ""
        else:
            return ''
    
    # [Keep all other methods from previous implementation]

class OSACDateCSVProcessor(OSACDateParser):
    """Adds CSV handling while keeping date parsing logic separate"""
    
    def __init__(self, csv_path: str):
        super().__init__()
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        self.df = pd.read_csv(csv_path)
        self.df.columns = self.df.columns.str.strip()
        
    
    def process_csv(self) -> pd.DataFrame:
        """Processes the loaded CSV and adds date column"""
        self.df['date'] = self.df.apply(
            lambda row: self.parse_date(row['OSAC_Title'], row['OSAC_Date']),
            axis=1
        )
        return self.df

if __name__ == "__main__":
    processor = OSACDateCSVProcessor("osac.csv")
    df_with_dates = processor.process_csv()
    print(df_with_dates)
