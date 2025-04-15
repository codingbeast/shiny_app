import re
import os
import pandas as pd
from typing import Optional, List
from dateutil.parser import parse
from datetime import datetime, timedelta
import spacy
import regex
from pandarallel import pandarallel

class OSACProtestParser:
    def __init__(self, patterns: Optional[List[str]] = None):
        # Use only the specified patterns
        protest_keywords = ["protest", "demonstration", "demonstrator"]
        
        # Define strike-related patterns
        strike_keywords = [
            r"(worker|union|labor|labour)[^.]+(?<!(air))strike[^.]*\.",
            r"(?<!(air))strike[^.]+(worker|union|labor|labour)[^.]*\."
        ]
        
        # Combine patterns
        protest_pattern = "|".join(protest_keywords)
        strike_pattern = "|".join(strike_keywords)
        full_pattern = protest_pattern + "|" + strike_pattern
        
        # Use the provided patterns or the default ones
        patterns = patterns or [full_pattern]
        self.compiled_patterns = [regex.compile(p, regex.IGNORECASE) for p in patterns]

    def add_pattern(self, pattern: str):
        """Allows adding a new pattern at any time."""
        self.compiled_patterns.append(regex.compile(pattern, regex.IGNORECASE))

    def parse_protest(self, 
                     title: Optional[str] = None,
                     location: Optional[str] = None,
                     events: Optional[str] = None,
                     actions: Optional[str] = None,
                     assistance: Optional[str] = None,
                     other: Optional[str] = None) -> int:
        # Convert all inputs to strings, handling None and NaN values
        title = str(title) if pd.notna(title) else ""
        location = str(location) if pd.notna(location) else ""
        events = str(events) if pd.notna(events) else ""
        actions = str(actions) if pd.notna(actions) else ""
        assistance = str(assistance) if pd.notna(assistance) else ""
        other = str(other) if pd.notna(other) else ""
        
        text = " ".join([title, location, events, actions, assistance, other])
        
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                return 1
        return 0

class OSACProtestProcessor(OSACProtestParser):
    def __init__(self, df: pd.DataFrame):
        super().__init__()
        pandarallel.initialize()
        self.df = df.copy()
        self.df.columns = self.df.columns.str.strip()
        
        # Convert all relevant columns to strings, replacing NaN with empty string
        text_cols = ['OSAC_Title', 'OSAC_Location', 'OSAC_Events', 
                    'OSAC_Actions', 'OSAC_Assistance', 'OSAC_Other']
        for col in text_cols:
            if col in self.df.columns:
                self.df[col] = self.df[col].astype(str).replace('nan', '')
    
    @property
    def extract(self) -> pd.DataFrame:
        if 'protest' not in self.df.columns:
            self.df['protest'] = None
            
        needs_processing = self.df['protest'].isna() | (self.df['protest'] == '')
        
        if needs_processing.any():
            # Parallel apply for processing
            self.df.loc[needs_processing, 'protest'] = (
                self.df.loc[needs_processing]
                .parallel_apply(
                    lambda row: self.parse_protest(row['OSAC_Title'],
                                                row['OSAC_Location'],
                                                row['OSAC_Events'],
                                                row['OSAC_Actions'],
                                                row['OSAC_Assistance'],
                                                row['OSAC_Other']),
                    axis=1
                )
            )
        
        return self.df

if __name__ == "__main__":
    pass