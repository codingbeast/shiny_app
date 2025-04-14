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
        # Expanded protest-related patterns (fixed version)
        default_patterns = [
            # General protest terms
            r"\bprotest(?:ers?|ing|s)?\b",
            r"\bdemonstrat(?:ion|ors?|ing|e)\b",
            r"\brall(?:y|ies|ied|ying)\b",
            r"\bstrike(?:rs?|s)?\b",
            r"\bmarch(?:es|ed|ing)?\b",
            r"\bwalk[- ]?out(?:s)?\b",
            r"\bsit[- ]?in(?:s)?\b",
            r"\bpicket(?:ing|ers?|s)?\b",
            
            # Types of protests
            r"\b(?:hunger|labor|general|wildcat) strike\b",
            r"\b(?:student|teacher|worker|union) protest\b",
            r"\b(?:mass|street|public) gathering\b",
            r"\b(?:peaceful|violent) demonstration\b",
            r"\b(?:anti|pro)[-\s]\w+ (?:protest|rally)\b",
            
            # Protest actions
            r"\b(?:block(?:ade|ing)|occup(?:ation|y|ying)|barricad(?:e|ing))\b",
            r"\bclash(?:es|ed)? with (?:police|authorities)\b",
            r"\b(?:police|riot) dispers(?:al|ed|ing)\b",
            r"\b(?:tear gas|water cannon|rubber bullets)\b",
            r"\b(?:chant(?:ing|ed)|slogan(?:s)?|placard(?:s)?)\b",
            
            # Civil unrest terms
            r"\bcivil unrest\b",
            r"\b(?:social|political) movement\b",
            r"\b(?:mass|public) mobiliz(?:ation|ing)\b",
            r"\b(?:urban|popular) uprising\b",
            r"\b(?:riot(?:s|ers?|ing)?|civil disobedience)\b",
            
            # Labor actions
            r"\b(?:labor|union) action\b",
            r"\b(?:work(?:ers?)?|general) stoppage\b",
            r"\b(?:go[ -]?slow|work[ -]?to[ -]?rule)\b",
            r"\b(?:boycott(?:ing|s)?|industrial action)\b",
            
            # Other related terms
            r"\b(?:gather(?:ing|ed)|assembl(?:y|ies))\b",
            r"\b(?:activis(?:ts?|m)|dissident(?:s)?)\b",
            r"\b(?:resistance|opposition) movement\b",
            r"\b(?:human[ -]?chain|die[ -]?in)\b",
            r"\b(?:vigil(?:s)?|candlelight (?:rally|protest))\b",
            
            # International terms
            r"\b(?:huelga|manifestación|protesta)\b",  # Spanish
            r"\b(?:grève|manifestation)\b",  # French
            r"\b(?:protesto|sciopero)\b",  # Italian
            r"\b(?:Streik|Demonstration)\b"  # German
            # Removed Arabic pattern as it might cause issues in some environments
        ]
        
        patterns = patterns or default_patterns
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