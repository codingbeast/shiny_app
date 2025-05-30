import re
import os
import pandas as pd
from typing import Optional, List
from dateutil.parser import parse
from datetime import datetime, timedelta
import spacy
from pandarallel import pandarallel

class OSACDateParser:
    def __init__(self):
        # Load spaCy model for NER
        self.nlp = spacy.load("en_core_web_sm")
    def extract_month(self, text: str) -> Optional[int]:
        """
        Extract the month (as an integer 1–12) from a date text.
        Returns None if not found.
        """
        months = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12
        }
        text = text.lower()
        for month_name, month_num in months.items():
            if month_name in text:
                return month_num
        return None
    def parse_date(self, text: str, osac_date: str = '') -> str:
        """
        Extract and validate dates from text.
        Uses year from osac_date when available for dates without year.
        Returns comma-separated string of found dates in YYYY-MM-DD format.
        """
        if not text or not isinstance(text, str):
            return ''

        # Parse osac_date to get default year and datetime object
        default_date = None
        default_year = None
        if osac_date:
            try:
                default_date = parse(osac_date)
                default_year = default_date.year
            except:
                pass

        doc = self.nlp(text)
        dates = []

        for ent in doc.ents:
            if ent.label_ == "DATE":
                mentioned_month = self.extract_month(ent.text)
                if mentioned_month and default_date and mentioned_month < default_date.month:
                    adjusted_year = default_date.year + 1
                else:
                    adjusted_year = default_date.year
                parsed_dates = self.preprocess_and_parse_dates([ent.text], default_date=default_date, default_year=adjusted_year)
                for date in parsed_dates:
                    str_date = date.strftime('%d/%m/%Y')
                    if str_date not in dates:
                        dates.append(str_date)  # Format as string

        return ", ".join(dates)

    def preprocess_and_parse_dates(self, date_strings: List[str], default_date: Optional[datetime] = None, default_year: Optional[int] = None) -> List[datetime]:
        """
        Preprocess and parse date strings into datetime objects.
        Args:
            date_strings: List of date strings to parse.
            default_date: Default datetime to use for relative dates (e.g., "today").
            default_year: Default year to use for dates without a year.
        Returns:
            List of parsed datetime objects.
        """
        parsed_dates = []
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

        for date_str in date_strings:
            original_str = date_str.strip()
            cleaned_str = original_str.lower()

            # Handle relative dates
            if cleaned_str == 'today':
                if default_date:
                    parsed_dates.append(default_date)
                continue
            elif cleaned_str == 'tomorrow':
                if default_date:
                    parsed_dates.append(default_date + timedelta(days=1))
                continue
            elif cleaned_str == 'yesterday':
                if default_date:
                    parsed_dates.append(default_date - timedelta(days=1))
                continue

            # Handle weekday prefixes (e.g., "Sunday, August 4" -> "August 4")
            # or standalone weekdays (e.g., "Sunday" -> next Sunday from default_date)
            weekday_match = re.match(r'^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)[,\s]*', cleaned_str)
            if weekday_match:
                weekday = weekday_match.group(1)
                remaining_str = cleaned_str[weekday_match.end():].strip()
                if not remaining_str:
                    # Standalone weekday (e.g., "Sunday")
                    if default_date:
                        weekday_idx = weekdays.index(weekday)
                        current_weekday = default_date.weekday()  # Monday=0, Sunday=6
                        days_ahead = (weekday_idx - current_weekday) % 7
                        if days_ahead == 0:
                            days_ahead = 7  # Next week
                        parsed_date = default_date + timedelta(days=days_ahead)
                        parsed_dates.append(parsed_date)
                    continue
                else:
                    # Weekday prefix with date (e.g., "Sunday, August 4")
                    cleaned_str = remaining_str

            # Extract the first date part (e.g., "August 4-5" -> "August 4")
            first_part = re.split(r'[-–—,;&]|\s+(?:and|&|to)\s+', cleaned_str)[0].strip()

            # Remove non-date text (e.g., "October 1 National Day" -> "October 1")
            date_match = re.search(r'([a-z]+\.?\s+\d{1,2}|[a-z]+\.?)', first_part)
            if date_match:
                date_part = date_match.group(0)
                try:
                    # Use default_year if provided, else use default_date's year
                    if default_year:
                        parsed_date = parse(date_part, default=datetime(default_year, 1, 1))
                    elif default_date:
                        parsed_date = parse(date_part, default=datetime(default_date.year, 1, 1))
                    else:
                        parsed_date = parse(date_part)
                    parsed_dates.append(parsed_date)
                except:
                    continue

        return parsed_dates


class OSACDateCSVProcessor(OSACDateParser):
    def __init__(self, df: pd.DataFrame):
        super().__init__()
        pandarallel.initialize()
        self.df = df.copy()
        self.df.columns = self.df.columns.str.strip()
    
    @property
    def extract(self) -> pd.DataFrame:
        if 'date' not in self.df.columns:
            self.df['date'] = None
            
        needs_processing = self.df['date'].isna() | (self.df['date'] == '')
        
        if needs_processing.any():
            # Parallel apply for processing
            self.df.loc[needs_processing, 'date'] = (
                self.df.loc[needs_processing]
                .parallel_apply(
                    lambda row: self.parse_date(row['OSAC_Title'], row['OSAC_Date']),
                    axis=1
                )
            )
        
        return self.df
        
# if __name__ == "__main__":
    
#     df_with_dates = OSACDateCSVProcessor().extract
#     print(df_with_dates)
