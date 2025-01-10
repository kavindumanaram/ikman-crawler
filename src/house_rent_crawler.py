from google.oauth2.service_account import Credentials
from bs4 import BeautifulSoup
import math
from utils import URL_PREFIX
from utils import get_spreadsheet, extract_json_data, read_config
import pandas as pd
from openpyxl import load_workbook
# from utils import URL_PREFIX
# from utils import get_spreadsheet, extract_json_data, read_config


MAX_PAGES_THRESHOLD = 10
 
def get_last_house_urls(house_data_sheet):
    """
    Reads the 'Sale' sheet and retrieves the last house URLs.
    Replace this with your custom logic to parse house URLs.
    """
    data = house_data_sheet  # Pandas DataFrame
    if "URL" in data.columns:
        return data["URL"].tolist()[-5:]  # Get last 5 URLs
    return []
 

def append_house_data(file_path, sheet_name, data):
    # Ensure sheet_name is a string
    # if not isinstance(sheet_name, str):
    #     raise ValueError(f"Expected sheet_name to be a string, got {type(sheet_name).__name__}.")

    # Load the workbook
    try:
        wb = load_workbook(file_path)
        # Check if the sheet exists
        #print(f"wb.sheetnames={wb.sheetnames}")
        #if sheet_name in wb.sheetnames:
        ws = wb["Sale"]
        #else:
            # Create the sheet if it doesn't exist
        #ws = wb.create_sheet(sheet_name)
    except FileNotFoundError:
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    # Append each row of data to the sheet
    for row_data in data:
        ws.append(row_data)

    # Save the workbook
    wb.save(file_path)
    print(f"Appended data to sheet '{sheet_name}' in file '{file_path}'.")



def extract_url_data(spreadsheet):
    url_data = []

    # Check if spreadsheet is already a DataFrame
    if isinstance(spreadsheet, pd.DataFrame):
        config_sheet = spreadsheet
    else:
        # Parse the "Config" sheet from the Excel file
        config_sheet = spreadsheet.parse(sheet_name="Config")

    # Iterate over the rows of the DataFrame
    for _, row in config_sheet.iterrows():  # Use iterrows() for pandas DataFrame
        key = row['Key']  # Column name in the sheet
        value = row['Value']  # Column name in the sheet
        if key == "House" and pd.notna(value):  # Check for "House" keys and non-NaN values
            url_parts = value.split('/')
            if len(url_parts) > 5:
                city = url_parts[5].replace('-', ' ').title()
                url_data.append([city, value])

    return url_data


def handler(event, context):
    # Step 1: Get the spreadsheet
    spreadsheet = get_spreadsheet()

    # Step 2: Read the config sheet
    config = read_config(spreadsheet)

    # Step 3: Extract URL data from the config
    url_data = extract_url_data(config)

    # Step 4: Read the "Sale" sheet
    house_data_sheet = spreadsheet.parse(sheet_name="Sale")  # Load "Sale" sheet into a DataFrame

    # Optional Step: Backup the sheet (commented)
    # backup_sheet(spreadsheet, house_data_sheet)

    # Step 5: Retrieve the last house URLs
    last_house_urls = get_last_house_urls(house_data_sheet)

    print("Configuration Data:")
    print(config)

    print("\nExtracted URL Data:")
    print(url_data)

    print("\nLast House URLs:")
    print(last_house_urls) 

    return_data = []
    for url_index in range(len(url_data)):
        print(f"url_index = {url_index}")
        city = url_data[url_index][0]
        print(f"Fetching data location: {city}")
        url = url_data[url_index][1]
        max_page_number = -1
        for page_no in range(1, MAX_PAGES_THRESHOLD + 1):
            final_url = f"{url}&page={page_no}"
            data = extract_json_data(final_url)
            #print(f"data={data}")
            ads = data['serp']['ads']['data']['ads']   
            #print(f"ads={ads}")         
            
            if max_page_number < 0:
                pagination = data['serp']['ads']['data']['paginationData']
                max_page_number = math.ceil(pagination['total'] / pagination['pageSize'])
                print(f"max_page_number: {max_page_number}")

            for ad in ads:
                price = ad['price'].split('Rs ')[1]
                size = ad['details']
                ad_url = f"{URL_PREFIX}{ad['slug']}"
                consider, note, description = "", "", ""
                if ad_url not in last_house_urls:
                    return_data.append([
                        ad['title'],
                        city,
                        size,
                        price,
                        f"{URL_PREFIX}{ad['slug']}",
                        consider,
                        note
                    ])                 

            if page_no == max_page_number:
                print("breaking")
                break
            else:
                print("continue")

    append_house_data("test.xlsx",house_data_sheet, return_data)
    
    
handler({}, {})
