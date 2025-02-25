import requests
from bs4 import BeautifulSoup
from mycolorlogger.mylogger import log
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io, re
import csv
from urllib.parse import urlparse
logger = log.logger



from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io
import csv

class DriveManager:
    def __init__(self):
        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        SERVICE_ACCOUNT_FILE = 'doc/service_account.json'

        # Store folder IDs as instance variables
        self.CSV_FOLDER_ID = "1NrmVf1DfAAqxkg72nFLCd4hwGciVVFbJ"
        self.HTML_FOLDER_ID = "11Rm4t0tlYweXXxNjoYuXB7L0rVd-fILj"

        # Authenticate and build the Drive service
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
        print(f"Text file '{file_name}' created successfully! File ID: {file.get('id')}")
        return file.get('id')

    def write_csv_to_drive(self, file_name, data_list, folder_id=None):
        """
        Creates a CSV file on Google Drive and writes a list of dictionaries to it.
        If folder_id is not provided, it defaults to the CSV folder.
        """
        if not data_list:
            print("Data list is empty. Cannot create CSV file.")
            return None

        if folder_id is None:
            folder_id = self.CSV_FOLDER_ID  # Default folder is CSV folder

        # Extract headers from the first dictionary
        headers = data_list[0].keys()

        # Write CSV to an in-memory file
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data_list)

        file_metadata = {
            'name': file_name,
            'mimeType': 'text/csv',
            'parents': [folder_id]
        }
        media = MediaIoBaseUpload(io.BytesIO(csv_buffer.getvalue().encode("utf-8")), mimetype='text/csv')

        file = self.drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"CSV file '{file_name}' created successfully! File ID: {file.get('id')}")
        return file.get('id')

    def get_all_files_from_html_folder(self):
        """
        Fetches all file names from the HTML folder and returns them as a list.
        """
        query = f"'{self.HTML_FOLDER_ID}' in parents and trashed=false"
        results = self.drive_service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])

        if not files:
            print("No files found in the HTML folder.")
            return []

        file_names = [file['name'] for file in files]
        print("Files in HTML Folder:", file_names)
        return file_names

class OsacScraper(DriveManager):
    def __init__(self):
        self.s = requests.Session()  # Session object for making requests
        self._cookies = None  # Private variable for cookies
        self._verification_code = None  # Private variable for verification code
        self._api_url = "https://www.osac.gov/Content/Search"
        self.page_links_container = []
        self.osac_dataset = []
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

    def set_cookie_from_home_page(self):
        """Method to fetch cookies and verification code from the home page."""
        logger.info("getting cookies and verification code from osac home page..")
        url = "https://www.osac.gov/Content/Browse/Report?subContentTypes=Alerts%2CTravel%20Advisories"
        res = self.s.get(url)
        soup = BeautifulSoup(res.text, "lxml")

        # Extract cookies and verification code
        cookies_dict = requests.utils.dict_from_cookiejar(res.cookies)
        verification_code = soup.find("input", {"name": "__RequestVerificationToken"}).get("value")

        # Use setters to update the values
        self.cookies = cookies_dict
        self.verification_code = verification_code
        logger.info("cookies and verification code is stored.")
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

3
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

500
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
                break
            page_number += 1

    def extract_id(self, url):
        return url.rstrip('/').split('/')[-1]  # Get last part of the URL
    def getSoup(self,url) -> BeautifulSoup:
        res = requests.get(url)
        res.raise_for_status()
        soup = BeautifulSoup(res.text,"lxml")
        return soup
    def get_html_data( soup : BeautifulSoup, preprocess = True) -> str:
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
    def extract_details(self)-> None:
        for url in self.page_links_container:
            id_ = self.extract_id(url)
            html_filename = f"{id_}.html"
            try:
                soup = self.getSoup(url)
            except Exception as e:
                logger.warning(f"getting error while processing {url} skiped")
                continue
            #extract string from soup : add this in end to avoid other link extraction set preprocess to true if you want remove unwnatext text
            html_str = self.get_html_data(soup, preprocess = True)
if __name__ == "__main__":
    osac_scraper = OsacScraper()
    osac_scraper.set_cookie_from_home_page()
    osac_scraper.get_advisories()
    with open("links.txt","w") as writer:
        writer.write("\n".join(osac_scraper.page_links_container))