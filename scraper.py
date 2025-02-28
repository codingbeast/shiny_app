import requests
from bs4 import BeautifulSoup
from mycolorlogger.mylogger import log
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.oauth2 import service_account
import io, re
import csv
import re
from urllib.parse import urlparse
import unicodedata
from urllib.parse import urlparse
logger = log.logger



from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io, os
import csv, json

class DriveManager:
    def __init__(self):
        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        SERVICE_ACCOUNT_FILE = 'doc/service_account.json'

        # Store folder IDs as instance variables
        self.CSV_FOLDER_ID = "1NrmVf1DfAAqxkg72nFLCd4hwGciVVFbJ"
        self.HTML_FOLDER_ID = "11Rm4t0tlYweXXxNjoYuXB7L0rVd-fILj"

        secret_key_str = os.getenv("MY_SECRET_KEY")
        # Authenticate and build the Drive service
        if secret_key_str:
            secret_key = json.loads(secret_key_str)
            self.creds = service_account.Credentials.from_service_account_info(
            secret_key, scopes=SCOPES)
        else:
            self.creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        
        
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        super().__init__()

    def write_text_to_drive(self, file_name, content, folder_id=None):
        """
        Creates a text file on Google Drive and writes content to it.
        If folder_id is not provided, it defaults to the HTML folder.
        """
        if folder_id is None:
            folder_id = self.HTML_FOLDER_ID  # Default folder is HTML folder

        file_metadata = {
            'name': file_name,
            'mimeType': 'text/plain',
            'parents': [folder_id]
        }
        media = MediaIoBaseUpload(io.BytesIO(content.encode("utf-8")), mimetype='text/plain')

        file = self.drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logger.info(f"html file '{file_name}' created successfully! File ID: {file.get('id')}")
        return file.get('id')

    def write_csv_to_drive(self, file_name, data_list, folder_id=None, append=False):
        """
        Creates or appends to a CSV file on Google Drive and writes a list of dictionaries to it.
        If folder_id is not provided, it defaults to the CSV folder.

        Args:
            file_name (str): Name of the CSV file.
            data_list (list): List of dictionaries to write to the CSV.
            folder_id (str, optional): ID of the folder to store the file. Defaults to CSV_FOLDER_ID.
            append (bool, optional): If True, appends to an existing file. Defaults to False.

        Returns:
            str: File ID of the created/updated CSV file.
        """
        if not data_list:
            logger.warning("Data list is empty. Cannot create or update CSV file.")
            return None

        if folder_id is None:
            folder_id = self.CSV_FOLDER_ID  # Default folder is CSV folder

        # Extract headers from the first dictionary
        headers = data_list[0].keys()

        # Check if the file already exists
        file_id = None
        if append:
            file_id = self._get_file_id(file_name, folder_id)

            if file_id:
                # Download the existing file
                existing_csv = self._download_file(file_id)
                existing_data = list(csv.DictReader(io.StringIO(existing_csv)))

                # Append new data to existing data
                data_list = existing_data + data_list

        # Write CSV to an in-memory file
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=headers)
        # Write header and rows
        writer.writeheader()
        writer.writerows(data_list)

        # Prepare file metadata
        file_metadata = {
            'name': file_name,
            'mimeType': 'text/csv',
            'parents': [folder_id]
        }

        # Upload the file
        media = MediaIoBaseUpload(io.BytesIO(csv_buffer.getvalue().encode("utf-8")), mimetype='text/csv')
        if file_id:
            # Update the existing file
            file = self.drive_service.files().update(fileId=file_id, media_body=media, fields='id').execute()
            logger.info(f"CSV file '{file_name}' updated successfully! File ID: {file.get('id')}")
        else:
            # Create a new file
            file = self.drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            logger.info(f"CSV file '{file_name}' created successfully! File ID: {file.get('id')}")

        return file.get('id')
    def _get_file_id(self, file_name, folder_id):
        """
        Get the file ID of an existing file in Google Drive.

        Args:
            file_name (str): Name of the file.
            folder_id (str): ID of the folder to search in.

        Returns:
            str: File ID if found, otherwise None.
        """
        query = f"name = '{file_name}' and '{folder_id}' in parents and trashed = false"
        response = self.drive_service.files().list(q=query, spaces='drive', fields='files(id)').execute()
        files = response.get('files', [])

        if files:
            return files[0]['id']
        return None

    def _download_file(self, file_id):
        """
        Download the content of a file from Google Drive.

        Args:
            file_id (str): ID of the file to download.

        Returns:
            str: Content of the file.
        """
        request = self.drive_service.files().get_media(fileId=file_id)
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        return file.getvalue().decode("utf-8")

    def get_all_files_from_html_folder(self):
        """
        Fetches all file names from the HTML folder and returns them as a list.
        """
        query = f"'{self.HTML_FOLDER_ID}' in parents and trashed=false"
        results = self.drive_service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])

        if not files:
            logger.info("No files found in the HTML folder.")
            return []

        file_names = [file['name'] for file in files]
        return file_names

class OsacScraper(DriveManager):
    def __init__(self):
        self.s = requests.Session()  # Session object for making requests
        self._cookies = None  # Private variable for cookies
        self._verification_code = None  # Private variable for verification code
        self._api_url = "https://www.osac.gov/Content/Search"
        self.page_links_container = []
        self.osac_dataset = []
        self.error_urls = []
        self.twelve_months_buffer_period = datetime.today() - timedelta(days=365)
        super().__init__()

    @property
    def get_header(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Referer": "https://www.osac.gov/Content/Browse/Report?subContentTypes=Alerts%2CTravel%20Advisories",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "multipart/form-data; boundary=----geckoformboundary6777d4edf039c309ea1f3ca47bf6aaa9",
            "Origin": "https://www.osac.gov",
            "DNT": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-GPC": "1",
            "Priority": "u=0",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "TE": "trailers",
        }
    @property
    def api_url(self) -> str:
        return self._api_url
    @property
    def cookies(self):
        """Getter for cookies."""
        return self._cookies

    @cookies.setter
    def cookies(self, value):
        """Setter for cookies."""
        self._cookies = value

    @property
    def verification_code(self):
        """Getter for verification code."""
        return self._verification_code

    @verification_code.setter
    def verification_code(self, value):
        """Setter for verification code."""
        self._verification_code = value

    def set_login_from_home_page(self,) -> None:
        url = "https://www.osac.gov/UserAccount/Login"
        email = "advrter%40gmail.com"
        password = "Raj29956"
        payload = f"__RequestVerificationToken={self.verification_code}&ReturnUrl=&Username={email}&Password={password}&RememberMe=true&RememberMe=false&X-Requested-With=XMLHttpRequest"
        res = self.s.post(url, headers={
            'Host': 'www.osac.gov',
            'Content-Length': '258',
            'Sec-Ch-Ua': '"Not;A=Brand";v="24", "Chromium";v="128"',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Ch-Ua-Mobile': '?0',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.6613.120 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept': '*/*',
            'X-Requested-With': 'XMLHttpRequest',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Origin': 'https://www.osac.gov',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://www.osac.gov/',
            'Accept-Encoding': 'gzip, deflate, br',
            'Priority': 'u=1, i',
            }, cookies=self.cookies,data=payload)
        print(res.text)

    def set_cookie_from_home_page(self):
        """Method to fetch cookies and verification code from the home page."""
        logger.info("getting cookies and verification code from osac home page..")
        url = "https://www.osac.gov/Content/Browse/Report?subContentTypes=Alerts%2CTravel%20Advisories"
        res = self.s.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.osac.gov/Content/Browse/Report?subContentTypes=Alerts%2CTravel%20Advisories",
            "Origin": "https://www.osac.gov",
            "DNT": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-GPC": "1",
            "Priority": "u=0",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "TE": "trailers",
        })
        soup = BeautifulSoup(res.text, "lxml")
        # Extract cookies and verification code
        cookies_dict = requests.utils.dict_from_cookiejar(res.cookies)
        verification_code = soup.find("input", {"name": "__RequestVerificationToken"}).get("value")

        # Use setters to update the values
        self.cookies = cookies_dict
        self.verification_code = verification_code
        logger.info("cookies and verification code is stored.")
        logger.info("login and storing session.")
        #self.set_login_from_home_page()
    def get_boundry_data(self, page_number: int, ) -> str:
        # Multipart form-data body
        boundary = "----geckoformboundary6777d4edf039c309ea1f3ca47bf6aaa9"
        body = f"""
--{boundary}
Content-Disposition: form-data; name="__RequestVerificationToken"

{self.verification_code}
--{boundary}
Content-Disposition: form-data; name="SortOrderCode"

0
--{boundary}
Content-Disposition: form-data; name="CurrentPageNumber"

{page_number}
--{boundary}
Content-Disposition: form-data; name="ContentTypeIds"

5
--{boundary}
Content-Disposition: form-data; name="AscendingSortOrder"

false
--{boundary}
Content-Disposition: form-data; name="SubContentTypeIds"

1
--{boundary}
Content-Disposition: form-data; name="SubContentTypeIds"

6
--{boundary}
Content-Disposition: form-data; name="Featured"

false
--{boundary}
Content-Disposition: form-data; name="PageSize"

20
--{boundary}
Content-Disposition: form-data; name="actionType"

SearchMore
--{boundary}--
"""
        return body

    def get_advisories(self,) -> bool:
        # Send the request
        page_number = 1
        while True:
            logger.info(f"gettting data from page : {page_number}")
            response = requests.post(self.api_url, headers=self.get_header, cookies=self.cookies, data=self.get_boundry_data(page_number=page_number))
            response.raise_for_status()
            # Print the response
            html = response.json()['viewHTML']
            soup = BeautifulSoup(html,"lxml")
            for link_container in soup.find_all("div", {"class" : "col-8 col-md-10 mss-content-item-details"}):
                link = link_container.find("a").get("href",None)
                date_str = link_container.find("div", {"class" : "mss-content-item-datetype"}).get_text(strip=True).split("|")[0].strip()
                date_obj = datetime.strptime(date_str, "%m/%d/%Y")
                # Check if the date is older than 12 months
                if date_obj < self.twelve_months_buffer_period:
                    logger.info("data is older then buffer period ( 12 months) stopping the link collection.")
                    return False  # Stop processing if date is older than 12 months
                else:
                    self.page_links_container.append(link)  # Add link to the container

            if page_number > 0:  # todo: Stop after 10 pages for debug
                logger.info("page is more then 5 stopped ")
                with open("links.txt","w") as f:
                    f.write("\n".join(self.page_links_container))
                break
            page_number += 1

    def extract_id(self, url):
        return url.rstrip('/').split('/')[-1]  # Get last part of the URL
    def getSoup(self,url) -> BeautifulSoup:
        res = self.s.get(url)
        res.raise_for_status()
        soup = BeautifulSoup(res.text,"lxml")
        return soup
    def get_html_data(self,  soup : BeautifulSoup, preprocess = True) -> str:
        if preprocess == False:
            return str(soup)
        elements_to_remove = [
            {"id": "sessionTimeoutModal"},
            {"id": "LayoutLoading"},
            {"class": "mss-topmenu-list"},
            {"class": "mss-topmenu-navbar mss-topmenu-navbar-user"},
            {"class": "dropdown mss-display-inlineblock mss-btn-share-container"},
            {"class": "mss-printheader-text"},
            {"input": {"value": "Print"}},
            "footer",
            {"section": {"id": "printFooter"}},
            ]
        # Remove elements
        for element in elements_to_remove:
            if isinstance(element, dict):
                # Handle cases where the element is a dictionary (e.g., {"id": "sessionTimeoutModal"})
                for tag, attrs in element.items():
                    found = soup.find(tag, attrs)
                    if found:
                        found.decompose()
            else:
                # Handle cases where the element is a string (e.g., "footer")
                found = soup.find(element)
                if found:
                    found.decompose() if isinstance(found, str) else found  
        return str(soup)
    
    def extract_id(self, url):
        return url.rstrip('/').split('/')[-1]  # Get last part of the URL
    def clean_text(self, text):
        text = unicodedata.normalize("NFKC", text).strip()
        
        # Regex pattern to match and remove the unwanted prefixes
        pattern = r'^(?:Locations?|Events?|Actions?\s+to\s+Take|Assistances?)\s*:?\s*'
        
        return re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
    def extract_text_from_tag(self, start_tag):
        """Extracts text after the given start tag until the next <strong> tag or closing </section> tag."""
        if not start_tag:
            return ""

        content = []
        current_element = start_tag.find_next()
        content.append(start_tag.find_parent("p").get_text(strip=True))
        while current_element:
            # Stop at the next <strong> tag or when reaching the closing </section> tag
            if current_element.name == "strong" or (hasattr(current_element, "find") and current_element.find("strong")):
                if "Assistance" not in start_tag.find_parent("p").get_text(strip=True):
                    break
            if current_element.name == "section":  # Stop at the closing </section>
                break

            # Extract only text content
            if isinstance(current_element, str):
                content.append(current_element.strip())
            elif hasattr(current_element, "get_text"):
                content.append(current_element.get_text(strip=True))

            current_element = current_element.find_next()

        return self.clean_text(" ".join(content))

    def extract_details(self)-> None:

        total_length = len(self.page_links_container)
        for index_, url in enumerate(self.page_links_container, start=1):
            logger.info(f"{index_} out of {total_length} : {url}")
            temp={}
            id_ = self.extract_id(url)
            html_filename = f"{id_}.html"
            try:
                soup = self.getSoup(url)
            except Exception as e:
                logger.warning(f"getting error while processing {url} skiped")
                self.error_urls.append({"url" : url})
                continue
            try:
                content_data = soup.find("div", {"class" :"mss-content-listitem"}).get_text(separator=" ",strip=True)
                content_data = self.clean_text(content_data)
            except Exception as e:
                logger.critical("all data not found skiped")
                self.error_urls.append({"url" : url})
                temp['OSAC_ID'] =''
                temp[' OSAC_Date'] = ''
                temp['OSAC_Title'] = 'link is protected'
                temp['OSAC_URL'] = url
                temp['OSAC_Location'] = ''
                temp['OSAC_Events'] = ''
                temp['OSAC_Actions'] = ''
                temp['OSAC_Assistance'] = ""
                self.osac_dataset.append(temp)
                continue
            temp['OSAC_ID'] = self.extract_id(url)
            try:
                temp[' OSAC_Date'] = soup.find("div", {"class" : "col-md-12 mss-content-datetype-container"}).get_text(strip=True).split("|")[0].strip()
            except Exception as e:
                logger.warning("date not found setting empty string")
                temp['OSAC_Date'] = ""
            try:
                temp['OSAC_Title'] = soup.find("div",{"class" : "mss-page-title"}).get_text(strip=True)
            except Exception as e:
                logger.warning("title not found skiping ")
                self.error_urls.append({"url" : url})
                temp['OSAC_ID'] =''
                temp[' OSAC_Date'] = ''
                temp['OSAC_Title'] = 'link is protected'
                temp['OSAC_URL'] = url
                temp['OSAC_Location'] = ''
                temp['OSAC_Events'] = ''
                temp['OSAC_Actions'] = ''
                temp['OSAC_Assistance'] = ""
                self.osac_dataset.append(temp)
                continue
            
            temp['OSAC_URL'] = url
            
            try:
                location = self.extract_text_from_tag(soup.find("strong",string=re.compile(r"Locations?\s*:?", re.I)))
                if len(location) < 1:
                    logger.warning("location not found set empty string")
                temp['OSAC_Location'] = location
            except Exception as e:
                logger.warning("location not found set empty string")
                temp['OSAC_Location'] =  ""
            try:
                events = self.extract_text_from_tag(soup.find("strong", string=re.compile(r"Events?\s*:?", re.I)))
                if len(events) < 1:
                    logger.warning("events not found set empty string .")
                temp['OSAC_Events'] = events
            except Exception as e:
                logger.warning("events not found set empty string .")
                temp['OSAC_Events']  = ""

            try:
                actions_to_take = self.extract_text_from_tag(soup.find("strong", string=re.compile(r"Actions?\s*to\s*Take\s*:?", re.I)))
                if len(actions_to_take) < 1:
                    logger.warning("actions not found set empty string .")
                temp['OSAC_Actions'] = actions_to_take
            except Exception as e:
                logger.warning("actions not found set empty string .")
                temp['OSAC_Actions']  = ""
            try:
                assistance = self.extract_text_from_tag(soup.find("strong", string=re.compile(r"Assistance\s*:?", re.I)))
                if len(assistance) < 1:
                    logger.warning("assitance not found set empty string.")
                temp['OSAC_Assistance'] = assistance
            except Exception as e:
                logger.warning("assitance not found set empty string.")
                temp['OSAC_Assistance'] = ""
            #store to a dataset
            self.osac_dataset.append(temp)
            #extract string from soup : add this in end to avoid other link extraction set preprocess to true if you want remove unwnatext text
            html_str = self.get_html_data(soup, preprocess = True)
            self.write_text_to_drive(file_name=html_filename,content=html_str)
            #break
    def filter_already_scraped_data(self,):
        all_files = self.get_all_files_from_html_folder()
        all_ids = [i.replace(".html","") for i in all_files]
        logger.info("filtering only links that is not  stored in database.")
        links_container_dataset = []
        for url in self.page_links_container:
            id_ = self.extract_id(url)
            if not id_ in all_ids:
                links_container_dataset.append(url)
        self.page_links_container = links_container_dataset
        
    def save_csv_to_drive(self,) -> None:
        csv_data = self.osac_dataset
        self.write_csv_to_drive(file_name="osac.csv", data_list=csv_data, append=True)
        self.write_csv_to_drive(file_name="errors.csv", data_list=self.error_urls, append=True)
if __name__ == "__main__":
    osac_scraper = OsacScraper()
    #set extract cookies from home to request api
    osac_scraper.set_cookie_from_home_page()

    #get all links from search page (12 months buffer time)
    osac_scraper.get_advisories()

    #check if already data availble inside our drive folder and remove links if already available 
    osac_scraper.filter_already_scraped_data()

    #extract details and save html in drive
    osac_scraper.extract_details()

    #save extracted data to drive in csv format.
    osac_scraper.save_csv_to_drive()