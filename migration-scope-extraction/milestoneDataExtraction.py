import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import re
import json
from urllib.parse import urljoin

# Load environment variables
load_dotenv()
tr_session = os.getenv('TESTRAIL_SESSION')
tr_rememberme = os.getenv('TESTRAIL_REMEMBERME')

BASE_URL = 'https://a1neashore.testrail.io'

headers = {
    'cookie': f'tr_session={tr_session}; tr_rememberme={tr_rememberme};'
}

def extract_id_from_url(url, pattern):
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_test_case_ids_from_json(json_path):
    """Read test case IDs from JSON file."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            test_cases = json.load(f)
            return [case['ID'] for case in test_cases]
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return []

def get_web_content(url):
    try:
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except requests.RequestException as e:
        print(f"Error downloading content from {url}: {e}")
        return None

def extract_case_info(test_case_id):
    # Step 2: Create test case URL
    test_case_url = f"{BASE_URL}/index.php?/tests/view/{test_case_id}"
    
    # Get the test case page
    soup = get_web_content(test_case_url)
    if not soup:
        return None

    # Step 3: Find "ViewCase" button
    view_case_button = soup.select_one('a.toolbar-button')
    if not view_case_button:
        print(f"View Case button not found for test case {test_case_id}")
        return None

    # Step 4: Get the case view URL
    case_view_href = view_case_button.get('href')
    case_view_url = urljoin(BASE_URL, case_view_href)

    # Get the case view page
    case_soup = get_web_content(case_view_url)
    if not case_soup:
        return None

    # Step 5: Extract suite and project information
    # Find suite information
    breadcrumb = case_soup.select_one('div.content-breadcrumb')
    suite_link = breadcrumb.select_one('a') if breadcrumb else None
    
    if not suite_link:
        print(f"Suite information not found for test case {test_case_id}")
        return None

    suite_href = suite_link.get('href')
    suite_id = extract_id_from_url(suite_href, r'/suites/view/(\d+)')
    suite_name = suite_link.text.strip()

    # Find project information
    project_link = case_soup.select_one('a#navigation-project')
    if not project_link:
        print(f"Project information not found for test case {test_case_id}")
        return None

    project_href = project_link.get('href')
    project_id = extract_id_from_url(project_href, r'/projects/overview/(\d+)')
    project_name = project_link.text.strip()

    return {
        "test_case_id": test_case_id,
        "project_id": project_id,
        "project_name": project_name,
        "suite_id": suite_id,
        "suite_name": suite_name,
        "url": test_case_url,
        "extraction_mode": "suite"
    }

def main():
    # Step 1: Get test case IDs from JSON
    test_case_ids = get_test_case_ids_from_json('milestone_data_extraction.json')
    
    extracted_data = []
    for test_case_id in test_case_ids:
        print(f"Processing test case ID: {test_case_id}")
        case_info = extract_case_info(test_case_id)
        if case_info:
            extracted_data.append(case_info)

    if extracted_data:
        with open('milestoneResults.json', 'w') as f:
            json.dump({
                "message": "Extraction completed successfully",
                "content": extracted_data
            }, f, indent=4)
        print(f"Successfully processed {len(extracted_data)} test cases")
    else:
        print("Error: No data was extracted")

if __name__ == '__main__':
    main()