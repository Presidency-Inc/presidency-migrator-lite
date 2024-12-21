import os
import requests
from flask import Flask, jsonify
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import re
import json

app = Flask(__name__)

load_dotenv()
tr_session = os.getenv('TESTRAIL_SESSION')
tr_rememberme = os.getenv('TESTRAIL_REMEMBERME')

headers = {
    'cookie': f'tr_session={tr_session}; tr_rememberme={tr_rememberme};'
}

def extract_suite_number(string):
    # Use regex to find digits following "overview/"
    match = re.search(r'view/(\d+)', string)
    if match:
        return match.group(1)
    else:
        return None 

def extract_number(string):
    # Use regex to find digits following "overview/"
    match = re.search(r'overview/(\d+)', string)
    if match:
        return match.group(1)
    else:
        return None 

def get_web_content(url):
    suite_url_regex = r"https:\/\/[^\/]+\/index\.php\?\/suites\/view\/\d+"
    project_url_regex = r"https:\/\/[^\/]+\/index\.php\?\/suites\/overview\/\d+"

    try:
        extraction_mode = None
        if re.match(suite_url_regex, url):
            extraction_mode = "suite"
        elif re.match(project_url_regex, url):
            extraction_mode = "project"

        if extraction_mode is None:
            return {
                "details": "Unsopported URL",
                "url": url
            }

        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()  # Raise an exception for bad status codes

        html_content = response.content
        # print(f"Response content: {html_content}")

        soup = BeautifulSoup(html_content, 'html.parser')

        # Find the <a> tag with the specific id
        link_tag = soup.find('a', id='navigation-project') # Only for version 8.0
        # link_tag = soup.select_one('div.top-section a.link-noline') # Only for version 5.4

        if extraction_mode == "suite":
            # Extract the href attribute and the text content
            if link_tag:
                href_value = link_tag['href']
                text_value = link_tag.get_text()  # or link_tag.string

                suit_name_div = soup.select_one('div.content-header-title')

                if not suit_name_div:
                    print("Tag with id 'content-header-title' not found.")
                    return {
                        "details": "Unsopported URL - Tag with id 'content-header-title' not found.",
                        "url": url
                    }

                span = suit_name_div.find('span')
                content = None
                if span:
                    # If a <span> exists, get its text
                    content = span.get_text(strip=True)
                else:
                    # If no <span> exists, get the text of the div itself
                    content = suit_name_div.get_text(strip=True)

                return {
                    "project_id": extract_number(href_value),
                    "project_name": text_value,
                    "suite_id": extract_suite_number(url),
                    "suite_name": content,
                    "extraction_mode": extraction_mode,
                    "url": url
                }
            else:
                print("Tag with id 'navigation-project' not found.")
        else:
            if link_tag:
                href_value = link_tag['href']
                text_value = link_tag.get_text()  # or link_tag.string
            else:
                return {
                    "details": "Unsopported URL - Tag with id 'navigation-project' not found.",
                    "url": url
                }
    
            return {
                "project_id": extract_number(url),
                "project_name": text_value,
                "suite_id": "all_suites",
                "extraction_mode": extraction_mode,
                "url": url
            }
    except requests.RequestException as e:
        print(f"Error downloading content: {e}")
        return None

# @app.route('/get_web_content', methods=['GET'])
def main():
    extraction_list = []
    with open('linksList.json') as f:
        data = json.load(f)
        extraction_list = data

    print(f"Length of extraction_list: {len(extraction_list)}")

    extracted_data = []
    for url in extraction_list:
        print("-" * 50)
        print("URL:", url)
        htmlContent = get_web_content(url)
        extracted_data.append(htmlContent)

    if extracted_data:
        with open('results.json', 'w') as f:
            json.dump({"message": "Extraction done successfully", "content": extracted_data}, f, indent=4)
    else:
        print(f"Error: Extraction failed.")

if __name__ == '__main__':
    main()
