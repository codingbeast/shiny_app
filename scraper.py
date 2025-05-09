import requests
from bs4 import BeautifulSoup
from mycolorlogger.mylogger import log
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.oauth2 import service_account
import io, re
import multiprocessing
import csv, time, sys
import glob
import multiprocessing
from functools import partial
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from urllib.parse import urlparse
import unicodedata
from urllib.parse import urlparse
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io, os
import csv, json

SCRAPED_LOG_FILE_NAME = "already_scraped_links.txt"
UPLOADED_DRIVE_LOG_FILE_NAME = "uploaded_to_drive.txt"
DOWNLOADED_LINKS_FROM_PAGINATION_LOG_FILE_NAME = "links.txt"
EXTRACTED_DETAILS_CSV_FILE_NAME = "osac.csv"
LOG_FILE_NAME_FOR_DRIVE_FLAG = "error.txt"
HTML_OUTPUT_DIR = "output"
CSV_FOLDER_ID_DRIVE = "1NrmVf1DfAAqxkg72nFLCd4hwGciVVFbJ"
HTML_FOLDER_ID_DRIVE = "1JnNAo9No8etBRoNKIFvviuiBXAZEeDzH"
SERVICE_ACCOUNT_FILE = 'doc/service_account.json'

logger = log.logger

class DriveManager:
    def __init__(self): 
        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        Path(HTML_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        # Store folder IDs as instance variables
        self.CSV_FOLDER_ID = CSV_FOLDER_ID_DRIVE
        self.HTML_FOLDER_ID = HTML_FOLDER_ID_DRIVE
        
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
        self.uploaded_to_drive_log(file_name)
        return file.get('id')
    def find_file_in_drive(self, file_name, folder_id=None):
            """
            Searches for a file by name in the specified Google Drive folder.
            Returns the file ID if found, else None.
            """
            if folder_id is None:
                folder_id = self.CSV_FOLDER_ID

            query = f"name = '{file_name}' and '{folder_id}' in parents and trashed = false"
            response = self.drive_service.files().list(q=query, fields="files(id)").execute()
            files = response.get("files", [])
            return files[0]["id"] if files else None

    def write_or_replace_text_to_drive(self, file_name, content, folder_id=None):
        """
        Writes a text file to Google Drive, replacing it if it already exists.
        """
        if folder_id is None:
            folder_id = self.CSV_FOLDER_ID

        existing_file_id = self.find_file_in_drive(file_name, folder_id)
        if existing_file_id:
            self.drive_service.files().delete(fileId=existing_file_id).execute()
            logger.info(f"Existing file '{file_name}' deleted successfully.")

        return self.write_text_to_drive(file_name, content, folder_id)
    def get_text_from_drive(self, file_name, folder_id=None):
            """
            Retrieves the content of a text file from Google Drive by name.
            Returns the content as a string or None if the file is not found.
            """
            if folder_id is None:
                folder_id = self.CSV_FOLDER_ID

            file_id = self.find_file_in_drive(file_name, folder_id)
            if not file_id:
                logger.warning(f"File '{file_name}' not found in Drive.")
                return None

            request = self.drive_service.files().get_media(fileId=file_id)
            file_stream = io.BytesIO()
            downloader = MediaIoBaseUpload(file_stream, mimetype='text/plain')
            request.execute()
            file_stream.seek(0)
            return file_stream.read().decode("utf-8")  # Return content as a string
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
        file_id = self._get_file_id(file_name, folder_id)
        if append and file_id:
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
        media = MediaIoBaseUpload(io.BytesIO(csv_buffer.getvalue().encode("utf-8")), mimetype='text/csv', resumable=True)
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

    # def get_all_files_from_html_folder(self):
    #     """
    #     Fetches all file names from the HTML folder and returns them as a list.
    #     """
    #     query = f"'{self.HTML_FOLDER_ID}' in parents and trashed=false"
    #     results = self.drive_service.files().list(q=query, fields="files(id, name)").execute()
    #     files = results.get('files', [])

    #     if not files:
    #         logger.info("No files found in the HTML folder.")
    #         return []

    #     file_names = [file['name'] for file in files]
    #     return file_names
    def uploaded_to_drive_log(self, filename) -> None:
        with open(UPLOADED_DRIVE_LOG_FILE_NAME,"a", encoding="utf-8") as f:
            f.write(f"{os.path.basename(filename)}\n")
    def get_all_uploaded_to_drive_log(self) -> list:
        if os.path.exists(UPLOADED_DRIVE_LOG_FILE_NAME):
            with open(UPLOADED_DRIVE_LOG_FILE_NAME,"r", encoding='utf-8') as f:
                files = [i.strip() for i in f.readlines()]
        else:
            files = []
        return files

class OsacScraper(DriveManager):
    def __init__(self):
        self.s = requests.Session()  # Session object for making requests
        self._cookies = None  # Private variable for cookies
        self._verification_code = None  # Private variable for verification code
        self._api_url = "https://www.osac.gov/Content/Search"
        self.page_links_container = []
        self.total_results_found = 29115
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
        email = ""
        password = ""
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
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "lxml")
        # Extract cookies and verification code
        cookies_dict = requests.utils.dict_from_cookiejar(res.cookies)
        verification_code = soup.find("input", {"name": "__RequestVerificationToken"}).get("value")
        try:
            total_results = soup.find("span",{"data-pager" : "totalNumber"}).get("data-value")
            self.total_results_found = int(total_results)
        except:
            pass
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
Content-Disposition: form-data; name="TotalCount"

{self.total_results_found}
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

500
--{boundary}
Content-Disposition: form-data; name="actionType"

SearchMore
--{boundary}
Content-Disposition: form-data; name="pageNumber"

{page_number}
--{boundary}--
"""
        return body


    def fetch_page_data(self, page_number):
        """Fetch advisories from a single page with retry and timeout."""
        logger.info(f"Fetching data from page: {page_number}")
        
        url = self.api_url
        headers = self.get_header
        cookies = self.cookies
        data = self.get_boundry_data(page_number=page_number)
        
        max_retries = 3  # Number of retry attempts
        backoff_factor = 2  # Delay factor for retries

        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(url, headers=headers, cookies=cookies, data=data, timeout=60*5)
                response.raise_for_status()  # Raise an exception for HTTP errors

                html = response.json().get("viewHTML", "")
                if not html:
                    logger.warning(f"Page {page_number} returned empty HTML.")
                    return None
                
                soup = BeautifulSoup(html, "lxml")
                page_links = []

                for link_container in soup.find_all("div", {"class": "col-8 col-md-10 mss-content-item-details"}):
                    link = link_container.find("a").get("href", None)
                    date_str = link_container.find("div", {"class": "mss-content-item-datetype"}).get_text(strip=True).split("|")[0].strip()
                    date_obj = datetime.strptime(date_str, "%m/%d/%Y")

                    if date_obj < self.twelve_months_buffer_period:
                        logger.info(f"Page {page_number} contains outdated advisories. Stopping further collection.")
                        return None  # Stop further processing if old data is found.

                    page_links.append(link)

                return page_links

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on page {page_number}, attempt {attempt}/{max_retries}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching page {page_number}: {e}")
                break  # Exit on non-timeout errors

            time.sleep(backoff_factor * attempt)  # Exponential backoff delay

        logger.error(f"Failed to fetch page {page_number} after {max_retries} attempts.")
        return None


    def get_advisories(self) -> bool:
        """Main function to fetch advisories with parallel requests."""

        # Check if links.txt exists and is not older than 1 day
        if os.path.exists(DOWNLOADED_LINKS_FROM_PAGINATION_LOG_FILE_NAME):
            file_age = time.time() - os.path.getmtime(DOWNLOADED_LINKS_FROM_PAGINATION_LOG_FILE_NAME)
            if file_age <= 86400:  # 86400 seconds = 1 day
                with open(DOWNLOADED_LINKS_FROM_PAGINATION_LOG_FILE_NAME, "r", encoding="utf-8") as f:
                    self.page_links_container = [i.strip() for i in f.readlines()]
                return True

        # If file is old or doesn't exist, fetch new advisories
        max_pages = 59  # Adjust as needed
        self.page_links_container = []  # Reset container

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_page = {executor.submit(self.fetch_page_data, page): page for page in range(1, max_pages + 1)}

            for future in as_completed(future_to_page):
                result = future.result()
                if result is None:
                    break  # Stop if outdated advisories are found.
                self.page_links_container.extend(result)

        # Save collected links
        links = list(set(self.page_links_container))
        with open(DOWNLOADED_LINKS_FROM_PAGINATION_LOG_FILE_NAME, "w", encoding="utf-8") as f:
            f.write("\n".join(links))

        return True
    def get_advisories_without_pool(self) -> bool:
        """Main function to fetch advisories sequentially to ensure early stopping."""
        # Check if links.txt exists and is not older than 1 day
        if os.path.exists(DOWNLOADED_LINKS_FROM_PAGINATION_LOG_FILE_NAME):
            file_age = time.time() - os.path.getmtime(DOWNLOADED_LINKS_FROM_PAGINATION_LOG_FILE_NAME)
            if file_age <= 86400:  # 86400 seconds = 1 day
                with open(DOWNLOADED_LINKS_FROM_PAGINATION_LOG_FILE_NAME, "r", encoding="utf-8") as f:
                    self.page_links_container = [i.strip() for i in f.readlines()]
                return True

        # If file is old or doesn't exist, fetch new advisories
        self.page_links_container = []  # Reset container
        page_number = 1
        max_pages = 59  # Adjust based on expected maximum pages

        while page_number <= max_pages:
            result = self.fetch_page_data(page_number)
            if result is None:
                # Stop pagination if outdated advisories are found
                break
            self.page_links_container.extend(result)
            page_number += 1

        # Save collected links
        links = list(set(self.page_links_container))
        with open(DOWNLOADED_LINKS_FROM_PAGINATION_LOG_FILE_NAME, "w", encoding="utf-8") as f:
            f.write("\n".join(links))

        return True
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
    def clean_text_2(self, text):
        text = unicodedata.normalize("NFKC", text).strip()
        clean_text = re.sub(r"[^\x00-\x7F]+", "", text) 
        return clean_text.strip()
    def extract_id(self, url):
        return url.rstrip('/').split('/')[-1]  # Get last part of the URL
    def clean_text(self, text):
        text = unicodedata.normalize("NFKC", text).strip()
        
        # Regex pattern to match and remove the unwanted prefixes
        pattern = r'\s*(?:Locations?|Location|Events?|Event|Actions?\s+to\s+Take|Assistances?)\s*:?\s*'
        
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
    def append_dict_to_csv(self, file_path, data):
        """
        Appends a dictionary to a CSV file.
        
        :param file_path: Path to the CSV file.
        :param data: Dictionary to append (keys as column names).
        """
        file_exists = os.path.isfile(file_path)
        
        with open(file_path, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=data.keys())
            
            # Write header if file is new
            if not file_exists:
                writer.writeheader()
            
            # Write data
            writer.writerow(data)

    def filter_already_scraped_data(self,):
        if os.path.exists(SCRAPED_LOG_FILE_NAME):
            with open(SCRAPED_LOG_FILE_NAME,"r") as file:
                temp_links = [i.strip() for i in file.readlines() if i.strip()]
        else:
            temp_links = []
            
        links = [i for i in self.page_links_container if i not in temp_links]
        self.page_links_container = links
    def extract_words_before_colon(self, text):
        ignore_list = {"https","http","phone","email", "facebook", "twitter","website","emergencies","tel"}
        if ignore_list is None:
            ignore_list = set()  # Default to an empty set if no ignore list is provided

        lines = text.splitlines()  # Split text into separate lines
        extracted_words = []

        for line in lines:
            if ':' in line:  # Ensure colon is present in the line
                # Match up to 3 words before the first colon, keeping the colon in the result
                match = re.match(r'^([\w]+(?:\s+[\w]+){0,2})\s*(:)', line)
                if match:
                    extracted_text = match.group(1)  # Extract matched words before colon
                    if extracted_text.lower() not in ignore_list:  # Check against ignore list
                        extracted_words.append(extracted_text + match.group(2))  # Keep words + colon

        return extracted_words
    def extract_first_matching_keyword(self, extracted_keywords, default_selections):
        # Convert default selections to lowercase for case-insensitive matching
        default_selections_lower = [d.lower() for d in default_selections]

        # Check for a match and return the first matched keyword
        for word in extracted_keywords:
            # Check if any default selection is part of the word (case-insensitive)
            if any(re.search(fr"\b{d}\w*\b", word.lower(), re.IGNORECASE) for d in default_selections_lower):
                return word

        return None  # Return None if no match is found
    def extract_section(self, content_data, start_header, all_headers):
        # Escape all headers for regex
        other_headers = [re.escape(h) for h in all_headers if h != start_header]
        
        # Build the regex pattern
        if other_headers:
            # Pattern to match until next header OR end
            pattern = rf"{re.escape(start_header)}(.*?)(?={'|'.join(other_headers)}|\Z)"
        else:
            # Pattern to match until end only
            pattern = rf"{re.escape(start_header)}(.*?)(?=\Z)"
        
        # Search with DOTALL flag (matches across newlines)
        match = re.search(pattern, content_data, re.DOTALL)
        
        return match.group(1).strip().lstrip(':') .strip() if match else None
    def keyword_extractor(self, soup : BeautifulSoup):
        content_data = soup.find("div", {"class": "mss-content-listitem"})
        content_data = [self.clean_text_2(i.get_text(separator="\n", strip=True)) for i in soup.find_all('p') + soup.find_all('ul') + soup.find_all('strong')]
        extracted_all_text = "\n".join(content_data)
        default_selections = ["location", "event", "Assistance","action",]
        extracted_keyword_before_colon = self.extract_words_before_colon(extracted_all_text)
        matched_keywords = [word for word in extracted_keyword_before_colon if any(re.search(fr"\b{d}\w*\b", word, re.IGNORECASE) for d in default_selections)]
        matched_keywords = list(set(matched_keywords))
        matched_keywords_from_strong = self.extract_keywords_from_strong(soup=soup)
        total_keywords = matched_keywords + matched_keywords_from_strong
        total_keywords = list(set(total_keywords))
        return total_keywords
    def extract_keywords_from_strong(self, soup: BeautifulSoup):
        default_selections = ["location", "event", "assistance", "action"]
        pattern = re.compile(
            r'^(' + '|'.join(default_selections) + r')[s:_-]*', 
            flags=re.IGNORECASE
        )

        from_strong_selection = []
        for strong_tag in soup.find_all("strong"):
            # Check if the parent is a <p> tag and this is the first child
            if strong_tag.parent.name == "p" and strong_tag is strong_tag.parent.find(recursive=False):
                text = strong_tag.get_text(strip=True)
                if pattern.match(text.lower()):
                    from_strong_selection.append(text)
        
        return from_strong_selection
    def extract_details(self,index_, url):
        logger.info(f"{index_} out of {len(self.page_links_container)} : {url}")
        temp={}
        id_ = self.extract_id(url)
        html_filename = f"{id_}.html"
        try:
            soup = self.getSoup(url)
        except Exception as e:
            logger.warning(f"getting error while processing {url} skiped")
            self.error_urls.append({"url" : url})
            self.write_to_log(url)
            return None
        try:
            content_data = soup.find("div", {"class": "mss-content-listitem"})
            content_data = self.clean_text_2(content_data.get_text(separator="\n", strip=True))
            keywords_ = self.keyword_extractor(soup = soup)
        except Exception as e:
            logger.critical("all data not found skiped")
            self.error_urls.append({"url" : url})
            self.write_to_log(url)
            temp['OSAC_ID'] =''
            temp['OSAC_Date'] = ''
            temp['OSAC_Title'] = 'link is protected'
            temp['OSAC_URL'] = url
            temp['OSAC_Location'] = ''
            temp['OSAC_Events'] = ''
            temp['OSAC_Actions'] = ''
            temp['OSAC_Assistance'] = ""
            temp['OSAC_Other'] = ""
            #self.osac_dataset.append(temp)
            self.append_dict_to_csv(file_path = "osac.csv", data=temp)
            return None
        location_keyword = self.extract_first_matching_keyword(keywords_,[ "location"])
        event_keyword = self.extract_first_matching_keyword(keywords_,["event"])
        action_to_take_keyword = self.extract_first_matching_keyword(keywords_, ["action"])
        assistance_keyword = self.extract_first_matching_keyword(keywords_, ["assistance"])
        temp['OSAC_ID'] = self.extract_id(url)
        try:
            temp['OSAC_Date'] = soup.find("div", {"class" : "col-md-12 mss-content-datetype-container"}).get_text(strip=True).split("|")[0].strip()
        except Exception as e:
            logger.warning("date not found setting empty string")
            temp['OSAC_Date'] = ""
        try:
            temp['OSAC_Title'] = soup.find("div",{"class" : "mss-page-title"}).get_text(strip=True)
        except Exception as e:
            logger.warning("title not found skiping ")
            self.error_urls.append({"url" : url})
            self.write_to_log(url)
            temp['OSAC_ID'] =''
            temp['OSAC_Date'] = ''
            temp['OSAC_Title'] = 'link is protected'
            temp['OSAC_URL'] = url
            temp['OSAC_Location'] = ''
            temp['OSAC_Events'] = ''
            temp['OSAC_Actions'] = ''
            temp['OSAC_Assistance'] = ""
            temp['OSAC_Other'] = ""
            #self.osac_dataset.append(temp)
            self.append_dict_to_csv(file_path = "osac.csv", data=temp)
            return None
        
        temp['OSAC_URL'] = url
        sections_to_remove = []
        try:
            location = self.extract_section(content_data, location_keyword, keywords_)
            temp['OSAC_Location'] = location
            sections_to_remove.append(f"{location_keyword}{location}")
        except Exception as e:
            logger.warning("location not found set empty string")
            temp['OSAC_Location'] =  ""
        try:
            events = self.extract_section(content_data, event_keyword, keywords_)
            temp['OSAC_Events'] = events
            sections_to_remove.append(f"{event_keyword}{events}")
        except Exception as e:
            logger.warning("events not found set empty string .")
            temp['OSAC_Events']  = ""

        try:
            actions_to_take = self.extract_section(content_data, action_to_take_keyword, keywords_)
            temp['OSAC_Actions'] = actions_to_take
            sections_to_remove.append(f"{action_to_take_keyword}{actions_to_take}")
        except Exception as e:
            logger.warning("actions not found set empty string .")
            temp['OSAC_Actions']  = ""
        try:
            assistance = self.extract_section(content_data, assistance_keyword, keywords_)
            temp['OSAC_Assistance'] = assistance
            sections_to_remove.append(f"{assistance_keyword}{assistance}")
        except Exception as e:
            logger.warning("assitance not found set empty string.")
            temp['OSAC_Assistance'] = ""
        
        # Create OSAC_Others by removing captured sections from full content
        others_content = content_data
        for section in sections_to_remove:
            others_content = others_content.replace(section, "")
        
        # Clean up the remaining content
        others_content = self.clean_text_2(others_content)
        
        # Remove the title if it appears in the content
        if 'OSAC_Title' in temp:
            others_content = others_content.replace(temp['OSAC_Title'], "")
        
        # Remove multiple newlines and trim
        others_content = re.sub(r'\n+', '\n', others_content).strip()
        
        temp['OSAC_Other'] = others_content if others_content else ""
        #store to a dataset
        #self.osac_dataset.append(temp)
        self.append_dict_to_csv(file_path = EXTRACTED_DETAILS_CSV_FILE_NAME, data=temp)
        #extract string from soup : add this in end to avoid other link extraction set preprocess to true if you want remove unwnatext text
        html_str = self.get_html_data(soup, preprocess = True)
        self.write_to_file(file_name=html_filename,content=html_str)
        self.write_to_log(url)
        #break
    def extract_details_runner(self):
        total_length = len(self.page_links_container)
        logger.info(f"total links are {total_length}") 
        for index_, url in enumerate(self.page_links_container,start=1):
            self.extract_details(index_=index_, url=url)
    def extract_details_worker(self, args):
        """Helper function to unpack arguments and call extract_details."""
        self, index_, url = args
        self.extract_details(index_=index_, url=url)

    def extract_details_runner(self):
        total_length = len(self.page_links_container)
        logger.info(f"Total links are {total_length}")

        with multiprocessing.Pool(processes=5) as pool:
            pool.map(self.extract_details_worker, [(self, index_, url) for index_, url in enumerate(self.page_links_container, start=1)])
    def write_to_file(self, file_name, content) -> None:
        filename_path = os.path.join("output", file_name)
        with open(filename_path, "w", encoding="utf-8") as f:
            f.write(content)
    def write_to_log(self, url) -> bool:
        with open(SCRAPED_LOG_FILE_NAME,"a", encoding="utf-8") as f:
            f.write(f"{url}\n")
        return True

    def upload_single_file(self, file_path, write_text_to_drive):
        """Helper function to upload a single file to Google Drive."""
        try:
            with open(file_path, "r", encoding="utf-8") as reader:
                content = reader.read()
            self.write_text_to_drive(file_name=os.path.basename(file_path), content=content)
            return f"Uploaded: {file_path}"
        except Exception as e:
            return f"Error uploading {file_path}: {e}"
        
    def upload_data_to_drive(self) -> bool:
        not_uploaded_files = self.filter_already_scraped_data_from_drive()
        logger.info(f"Starting upload for {len(not_uploaded_files)} files")
        
        with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
            upload_func = partial(self.upload_single_file, write_text_to_drive=self.write_text_to_drive)
            results = pool.map(upload_func, not_uploaded_files)
        
        for result in results:
            logger.info(result)
        
        return True
    def filter_already_scraped_data_from_drive(self,):
        all_files = self.get_all_uploaded_to_drive_log()
        all_html_files_from_local = [i for i in glob.glob("output/*html")]
        not_upload_html_files = [i for i in all_html_files_from_local if os.path.basename(i) not in all_files]
        logger.info(f"filtering only links that is not  stored in database. {len(not_upload_html_files)}")
        return not_upload_html_files
    
    def save_csv_to_drive(self,) -> None:
        df = pd.read_csv(EXTRACTED_DETAILS_CSV_FILE_NAME)
        csv_data = df.to_dict(orient="records")
        self.write_csv_to_drive(file_name=EXTRACTED_DETAILS_CSV_FILE_NAME, data_list=csv_data, append=False)
        #self.write_csv_to_drive(file_name="errors.csv", data_list=self.error_urls, append=True)
        
if __name__ == "__main__":
    
    osac_scraper = OsacScraper()
    
    args = sys.argv[1:]
    if len(args) > 0:
        if args[0] == "check":
            content = osac_scraper.get_text_from_drive(LOG_FILE_NAME_FOR_DRIVE_FLAG)
            if content != None and len(content) > 1:
                assert False, "Error detected while running"
            else:
                sys.exit()
    error_logger = []

    #set extract cookies from home to request api
    try:
        osac_scraper.set_cookie_from_home_page()
    except Exception as e:
        error_logger.append(e)
        
    #get all links from search page (12 months buffer time)
    try:
        osac_scraper.get_advisories_without_pool()
    except Exception as e:
        error_logger.append(e)
    #check if already data availble inside our drive folder and remove links if already available 
    try:
        osac_scraper.filter_already_scraped_data()
    except Exception as e:
        error_logger.append(e)
    #extract details and save html in drive
    try:
        osac_scraper.extract_details_runner()
    except Exception as e:
        error_logger.append(e)

    try:
        osac_scraper.upload_data_to_drive()
    except Exception as e:
        error_logger.append(e)
    try:
        osac_scraper.save_csv_to_drive()
    except Exception as e:
        error_logger.append(e)
    final_error = "\n".join(error_logger)
    
    osac_scraper.write_or_replace_text_to_drive(file_name=LOG_FILE_NAME_FOR_DRIVE_FLAG,content=final_error )