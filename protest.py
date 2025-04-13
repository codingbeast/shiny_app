import re
import os
import pandas as pd
from typing import Optional, List
from dateutil.parser import parse
from datetime import datetime, timedelta
import spacy
from pandarallel import pandarallel

class OSACProtestParser:
    def __init__(self):
        pass
    def parse_protest(self, 
                      title: str = None,
                      events : str= None,
                      actions : str= None,
                      assistance : str= None,
                      other : str= None,
                      location : str = None
                      ) -> str:
        pass
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