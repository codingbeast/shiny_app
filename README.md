# shiny_app

## python installation

This guide will help you install Python on your system to run this project.

### Prerequisites

- A computer running Windows, macOS, or Linux
- Administrator/root privileges (for some installation steps)

### Installation Instructions

#### Windows

1. Download the latest Python installer from [python.org](https://www.python.org/downloads/windows/)
2. Run the installer
3. Check "Add Python to PATH" at the bottom of the first page
4. Click "Install Now"
5. After installation completes, verify by opening Command Prompt and running:

   ```cmd
   python --version

#### Linux

1. Update package list:

   ```bash
   sudo apt update
   sudo apt-get install python3

## script installation

### Google Service Account Setup (for Google Drive Storage)

#### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Create Project"
3. Enter a project name and click "Create"

#### 2. Enable Google Drive API

1. In your project dashboard, go to "APIs & Services" > "Library"
2. Search for "Google Drive API"
3. Click "Enable"

#### 3. Create Service Account

1. Go to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Enter:
   - Service account name
   - Service account ID
   - Description (optional)
4. Click "Create and Continue"
5. Assign "Service Account Token Creator" role
6. Click "Continue" then "Done"

#### 4. Generate Credentials

1. In your service account list, click the account you created
2. Go to "Keys" tab
3. Click "Add Key" > "Create new key"
4. Select JSON format and click "Create"
5. The JSON key file will download automatically - keep this secure!

#### 5. Share Google Drive Folder

1. Create a folder in your Google Drive
2. Right-click the folder and select "Share"
3. Add your service account email (found in the JSON file as "client_email")
4. Set permission to "Editor"

#### 6. Add Credentials to Your Project

1. Place the downloaded JSON file in your project's secure location
2. Add to `.gitignore`:
    In your Python code, authenticate with:
3. update the scraper.py file to access the json file from correct location

```python
SERVICE_ACCOUNT_FILE = 'doc/service_account.json'
```

### Google Drive Folder Structure Setup & update drive folder id

1. first take the client email from service_account.json
2. <drive-upload@projectalfa-abcd.iam.gserviceaccount.com> is your client email

```json
{
  "type": "service_account",
  "project_id": "abcd-abcd",
  "private_key_id": "abcd",
  "private_key": "abcd",
  "client_email": "drive-upload@projectalfa-abcd.iam.gserviceaccount.com",
  "client_id": "abcd",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "abcd",
  "universe_domain": "googleapis.com"
}
```

#### 1. Create Base Folder

1. Go to [Google Drive](https://drive.google.com)
2. Click "+ New" → "Folder"
3. Name it "osac" (or your preferred base name)

#### 2. Share the Base Folder

1. Right-click the "osac" folder
2. Select "Share"
3. Add your service account's client email (from the JSON credentials)
4. Set permission to "Editor"
5. Click "Send"

#### 3. Create Subfolders

1. Open the "osac" folder
2. Create two new folders inside it:
   - One named "html"
   - One named "csv"

#### 4. Final Folder Structure

The structure should look like this:

```bash
osac/
├── html/
└── csv/
```

1. take the ids from both html and csv folder url example <https://drive.google.com/drive/u/0/folders/1JnNAo9No8etBRoNKIFvviuiBXAZEeDzH>
2. 1JnNAo9No8etBRoNKIFvviuiBXAZEeDzH is your id.
3. update the scraper.py to use new google drive folder id

```bash
CSV_FOLDER_ID_DRIVE = "1NrmVf1DfAAqxkg72nFLCd4hwGciVVFbJ"
HTML_FOLDER_ID_DRIVE = "1JnNAo9No8etBRoNKIFvviuiBXAZEeDzH"
```

### Requirements Installation

#### 1. Prerequisites

- Python 3.10+ installed
- pip package manager (comes with Python 3.4+)
- Access to command line/terminal

#### 2. Recommended: Using Virtual Environment (optional)

```bash
# Create virtual environment
python -m venv venv

# Activate environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

#### 3. Basic Installation

```bash
# Navigate to your project directory
cd path/to/your/project

# Install all required packages
pip install -r requirements.txt
```

### Run main script

```bash
python scraper.py




