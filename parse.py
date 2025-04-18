
import pandas as pd
import os
from date import OSACDateCSVProcessor
from country import OSACCountryProcessor
from protest import OSACProtestProcessor
from suppression import OSACSuppressionProcessor
from anticipation import OSACDateAnticipationProcessor
from aggregate import OSACAggregateProcessor
from scraper import DriveManager,EXTRACTED_DETAILS_CSV_FILE_NAME


class DataParser(DriveManager):
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
    
    def save_df(self, df : pd.DataFrame, filename:str= None) -> None:
        #df = df[['OSAC_Title', "country"]]
        if filename == None:
            filename = self.csv_output_path
        df.to_csv(filename,index=False, encoding='utf-8')
    def upload_to_drive(self, df : pd.DataFrame, filename =None):
        if filename == None:
            filename = EXTRACTED_DETAILS_CSV_FILE_NAME
        csv_data = df.to_dict(orient="records")
        self.write_csv_to_drive(file_name=filename, data_list=csv_data, append=False)

if __name__ == "__main__":
    data_parser = DataParser("osac.csv","OSAC_parsed.csv")
    df = data_parser.get_df
    df_with_date = OSACDateCSVProcessor(df).extract
    df_with_country = OSACCountryProcessor(df_with_date).extract
    df_with_protest = OSACProtestProcessor(df_with_country).extract
    df_with_suppression = OSACSuppressionProcessor(df_with_protest).extract
    df_with_aniticipation = OSACDateAnticipationProcessor(df_with_suppression).extract
    data_parser.save_df(df_with_aniticipation)
    data_parser.upload_to_drive(df_with_aniticipation, filename="OSAC_parsed.csv")
    
    aggregate_parser = OSACAggregateProcessor("OSAC_parsed.csv") #input the parseed csv file
    df_with_daily_data = aggregate_parser.extract_daily_data
    df_with_monthly_data = aggregate_parser.extract_monthly_data
    data_parser.save_df(df_with_daily_data, "OSAC_daily.csv")
    data_parser.upload_to_drive(df_with_daily_data, filename="OSAC_daily.csv")
    data_parser.save_df(df_with_monthly_data,"OSAC_monthly.csv")
    data_parser.upload_to_drive(df_with_monthly_data, filename="OSAC_monthly.csv")
    

    




        