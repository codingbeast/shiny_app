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
        # Default protest-related patterns
        default_patterns = [
            r"\bprotest\b",
            r"\bdemonstration\b",
            r"\brally\b",
            r"\bstrike\b",
            r"\bmarch\b",
            r"civil unrest",
            r"labor action",
            r"\bwalkout\b",
            r"sit[- ]?in",
            r"picketing",
            r"mass gathering"
        ]
        
        patterns = patterns or default_patterns
        self.compiled_patterns = [regex.compile(p, regex.IGNORECASE) for p in patterns]

    def add_pattern(self, pattern: str):
        """Allows my lord to add a new pattern at any time."""
        self.compiled_patterns.append(regex.compile(pattern, regex.IGNORECASE))

    def parse_protest(self, 
                      title: Optional[str] = None,
                      location: Optional[str] = None,
                      events: Optional[str] = None,
                      actions: Optional[str] = None,
                      assistance: Optional[str] = None,
                      other: Optional[str] = None,

                      ) -> int:
        text = " ".join(filter(None, [title, events, actions, assistance, other, location]))
        
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

if __name__=="__main__":
    pass