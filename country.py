import re
import os
from collections import defaultdict
from functools import lru_cache
from rapidfuzz import process, fuzz
import pandas as pd
from pandarallel import pandarallel
from typing import Optional

ISO_COUNTRY_NAME_PATH = "ISO_country_names.txt"

class OSACCountryParser:
    def __init__(self):
        self.iso_country = self._load_country_data()
        self._build_fuzzy_index()
        
    def _load_country_data(self):
        """Load and preprocess country data"""
        with open(ISO_COUNTRY_NAME_PATH, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
            
    def _build_fuzzy_index(self):
        """Build comprehensive index with all name variants"""
        self.fuzzy_index = defaultdict(list)
        self.all_variants = []
        
        for line in self.iso_country:
            # Split variants and clean them
            variants = [v.strip().lower() for v in re.split(r",|\|", line)]
            primary = variants[0]
            
            # Add all variants to index
            for variant in variants:
                clean_variant = self._normalize_text(variant)
                self.fuzzy_index[clean_variant].append(primary)
                self.all_variants.append(clean_variant)
                
            # Add common abbreviations
            if primary == "United States of America":
                self._add_abbreviation("usa", primary)
                self._add_abbreviation("us", primary)
            elif primary == "United Kingdom":
                self._add_abbreviation("uk", primary)
            # Add more abbreviations as needed
    
    def _add_abbreviation(self, abbr: str, primary: str):
        """Helper to add common abbreviations"""
        self.fuzzy_index[abbr].append(primary)
        self.all_variants.append(abbr)
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching"""
        return re.sub(r"[^\w\s]", "", text.lower()).strip()
    
    @lru_cache(maxsize=10_000)
    def parse_country(self, text: str, threshold: int = 75) -> Optional[str]:
        """Improved country matching with multiple fallback strategies"""
        if not text or not isinstance(text, str):
            return None
            
        text_lower = self._normalize_text(text)
        
        # Strategy 1: Check for exact substring matches
        for variant, primaries in self.fuzzy_index.items():
            if len(variant) > 3 and variant in text_lower:
                return primaries[0]
        
        # Strategy 2: Check for word boundaries (more flexible)
        words = set(text_lower.split())
        for variant, primaries in self.fuzzy_index.items():
            if variant in words:
                return primaries[0]
        
        # Strategy 3: Fuzzy match with adjusted scorer
        result = process.extractOne(
            text_lower,
            self.all_variants,
            scorer=fuzz.WRatio,  # Weighted ratio works better for partial matches
            score_cutoff=threshold
        )
        
        if result:
            return self.fuzzy_index[result[0]][0]
        
        # Strategy 4: Try matching individual words
        for word in text_lower.split():
            if len(word) > 3:  # Skip short words
                result = process.extractOne(
                    word,
                    self.all_variants,
                    scorer=fuzz.QRatio,
                    score_cutoff=threshold
                )
                if result:
                    return self.fuzzy_index[result[0]][0]
        
        return None

class OSACCountryProcessor(OSACCountryParser):
    def __init__(self, df: pd.DataFrame):
        super().__init__()
        pandarallel.initialize()
        self.df = df.copy()
        
    @property
    def extract(self) -> pd.DataFrame:
        # Initialize country column if it doesn't exist
        if 'country' not in self.df.columns:
            self.df['country'] = ''
        
        # Create mask for rows needing processing
        needs_processing = self.df['country'].isna() | (self.df['country'] == '')
        
        # Only process the rows that need it
        if needs_processing.any():
            self.df.loc[needs_processing, 'country'] = (
                self.df.loc[needs_processing, 'OSAC_Title']
                .parallel_apply(lambda x: self.parse_country(x) or "")
            )
        
        return self.df  # Returns complete DataFrame with all data