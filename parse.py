
import pandas as pd
import os
from date import OSACDateCSVProcessor
from country import OSACCountryProcessor


class DataParser:
    def __init__(self, csv_path : str, csv_output_path : str):
        super().__init__()
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        self.df = pd.read_csv(csv_path)
        self.df.columns = self.df.columns.str.strip()
        self.csv_output_path = csv_output_path
    
    @property
    def get_df(self, ) -> pd.DataFrame:
        return self.df
    
    def save_df(self, df : pd.DataFrame) -> None:
        #df = df[['OSAC_Title', "country"]]
        df.to_csv(self.csv_output_path,index=False, encoding='utf-8')

if __name__ == "__main__":
    data_parser = DataParser("osac.csv","osac_test.csv")
    df = data_parser.get_df
    df_with_date = OSACDateCSVProcessor(df).extract
    df_with_country = OSACCountryProcessor(df_with_date).extract
    data_parser.save_df(df_with_country)

    




        