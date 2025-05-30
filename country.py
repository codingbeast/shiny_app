import re
import pandas as pd
from pandarallel import pandarallel
from typing import Optional
from functools import lru_cache

ISO_COUNTRY_NAME_PATH = "ISO_country_names.txt"

class OSACCountryParser:
    def __init__(self):
        self.iso_country = self._load_country_data()
        self._build_index()

    def _load_country_data(self):
        """Load and preprocess country data"""
        with open(ISO_COUNTRY_NAME_PATH, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]

    def _build_index(self):
        """Build index from normalized variant → primary country"""
        self.variant_index = {}

        for line in self.iso_country:
            variants_raw = [v.strip() for v in line.split(",,")]
            primary = variants_raw[0]
            for variant in variants_raw:
                normalized_variant = self._normalize_text(variant)
                self.variant_index[normalized_variant] = primary

    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching"""
        return re.sub(r"[^\w\s]", "", text.lower()).strip()

    @lru_cache(maxsize=10_000)
    def parse_country(self, text: str) -> Optional[str]:
        """Check if a known country or variant is present in the title"""
        if not text or not isinstance(text, str):
            return None

        normalized_text = self._normalize_text(text)
        
        words = set(normalized_text.split())

        # Strategy 1: Exact word match
        for word in words:
            if word in self.variant_index:
                return self.variant_index[word]

        # Strategy 2: Substring match for longer variant phrases
        for variant, primary in self.variant_index.items():
            if len(variant) > 1 and variant in normalized_text:
                return primary

        return None


class OSACCountryProcessor(OSACCountryParser):
    def __init__(self, df: pd.DataFrame):
        super().__init__()
        pandarallel.initialize()
        self.df = df.copy()

    @property
    def extract(self) -> pd.DataFrame:
        """Fill in the 'country' column by extracting from OSAC_Title"""
        if 'country' not in self.df.columns:
            self.df['country'] = ''

        needs_processing = self.df['country'].isna() | (self.df['country'] == '')

        if needs_processing.any():
            self.df.loc[needs_processing, 'country'] = (
                self.df.loc[needs_processing, 'OSAC_Title']
                .parallel_apply(lambda x: self.parse_country(x) or "")
            )

        return self.df
