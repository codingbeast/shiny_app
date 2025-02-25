import requests
from bs4 import BeautifulSoup
from mycolorlogger.mylogger import log
from datetime import datetime, timedelta

logger = log.logger

class OsacScraper:
    def __init__(self):
        self.s = requests.Session()  # Session object for making requests
        self._cookies = None  # Private variable for cookies
        self._verification_code = None  # Private variable for verification code
        self._api_url = "https://www.osac.gov/Content/Search"
        self.page_links_container = []
        self.twelve_months_buffer_period = datetime.today() - timedelta(days=365)

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

            if page_number > 5:  # todo: Stop after 10 pages for debug
                logger.info("page is more then 5 stopped ")
                break
            page_number += 1
if __name__ == "__main__":
    osac_scraper = OsacScraper()
    osac_scraper.set_cookie_from_home_page()
    osac_scraper.get_advisories()
    with open("links.txt","w") as writer:
        writer.write("\n".join(osac_scraper.page_links_container))