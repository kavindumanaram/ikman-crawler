import requests
import json
from bs4 import BeautifulSoup
import os
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Google Sheets Authentication
SERVICE_ACCOUNT_FILE = "seek-452514-34d51d780268.json"
SPREADSHEET_NAME = "Job Listings"
SPREADSHEET_ID = "1H0dKBxunJCj-6DHCObqXRVxJZ6cQxbHv9g4Y0BtZguY"  # Your existing Google Sheet ID
RECIPIENT_EMAIL = "kavinduxyz@gmail.com"

# Gmail SMTP Credentials
EMAIL_SENDER = "devkavindu91@gmail.com"
EMAIL_PASSWORD = "hmqp myqh nohm eutl"  # Use Google App Password

# Set up Google Sheets authentication
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
client = gspread.authorize(creds)

def get_existing_spreadsheet():
    """Open an existing Google Spreadsheet using its ID."""
    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        print(f"✅ Using existing spreadsheet: {SPREADSHEET_NAME}")
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"❌ Error: Unable to find the spreadsheet with ID {SPREADSHEET_ID}. Make sure it's shared with the service account.")
        return None, None

    # Get the first worksheet
    sheet = spreadsheet.get_worksheet(0)

    # Get Google Sheet URL
    sheet_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
    
    return sheet, sheet_url

def extract_jobs_and_session_id(url):
    """Scrapes job listings from SEEK and returns (title, job_id) pairs."""
    try:
        headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        data = response.text.split("window.SEEK_REDUX_DATA =")[1].split("window.SEEK_APP_CONFIG =")[0].strip()
        if data.endswith(';'):
            data = data[:-1]

        redux_data = json.loads(data)
        jobs = redux_data.get('results', {}).get('results', {}).get('jobs', [])

        if not jobs:
            print("⚠️ No jobs found.")
        else:
            print(f"✅ Extracted {len(jobs)} jobs.")

        return [(job.get('title'), job.get('id')) for job in jobs if 'title' in job and 'id' in job]
    except Exception as e:
        print(f"❌ Error extracting job data: {e}")
        return []

def fetch_job_description(job_id):
    """Fetches job description from SEEK and filters relevant keywords."""
    try:
        job_url = f"https://www.seek.com.au/job/{job_id}?type=standout&ref=search-standalone"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        response = requests.get(job_url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        description = " ".join(p.get_text(strip=True) for p in paragraphs)

        have_phrases = ["visa", "482", "sponsor", "relocation"]
        if not any(phrase.lower() in description.lower() for phrase in have_phrases):
            return ""

        return description
    except Exception as e:
        print(f"❌ Error fetching job description for Job ID {job_id}: {e}")
        return ""

def save_to_google_sheets(sheet, data):
    """Saves job data to Google Sheets while avoiding duplicate job listings."""
    try:
        existing_rows = sheet.get_all_values()
        job_ids_in_sheet = {row[1] for row in existing_rows[1:]} if existing_rows else set()

        new_data = []
        for title, job_id, job_url, keyword, domain in data:
            if job_id not in job_ids_in_sheet:
                new_data.append([title, job_id, job_url, keyword, domain])

        if new_data:
            sheet.append_rows(new_data)
            print(f"✅ Added {len(new_data)} new job listings to Google Sheets.")
        else:
            print("ℹ️ No new job listings to add.")
    except Exception as e:
        print(f"❌ Error saving to Google Sheets: {e}")

def send_email(sheet_url):
    """Sends an email with the Google Sheet link."""
    try:
        subject = "Your Job Listings Google Sheet is Ready!"
        body = f"Hi,\n\nYour job listings have been updated.\n\n🔗 Google Sheet: {sheet_url}\n\nBest regards,\nYour Python Script"

        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = RECIPIENT_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, RECIPIENT_EMAIL, msg.as_string())
        server.quit()

        print(f"📧 Email sent to {RECIPIENT_EMAIL} with Google Sheet link.")
    except Exception as e:
        print(f"❌ Error sending email: {e}")

if __name__ == "__main__":
    enriched_job_details = []
    now = datetime.now()

    keywords = ["visa-sponsorship"]
    keywordsNZ = ["visa sponsorship"]
    domainList = ["www.seek.com.au", "www.seek.co.nz"]

    sheet, sheet_url = get_existing_spreadsheet()
    if not sheet:
        print("❌ Exiting script.")
        exit()

    for domain in domainList:
        if domain == "www.seek.co.nz":
            keywords = keywordsNZ
        for keyword in keywords:
            URL = f"https://{domain}/{keyword.replace(' ', '-')}-jobs-in-information-communication-technology?sortmode=ListedDate"
            job_details = extract_jobs_and_session_id(URL)

            if job_details:
                for title, job_id in job_details:
                    job_url = f"https://{domain}/job/{job_id}"
                    description = fetch_job_description(job_id)
                    if description:
                        enriched_job_details.append((title, job_id, job_url, keyword, domain.split('.')[3]))

    save_to_google_sheets(sheet, enriched_job_details)
    if enriched_job_details:
        send_email(sheet_url)
