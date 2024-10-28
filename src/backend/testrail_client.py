import os
import time
import json
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TESTRAIL_URL = os.getenv('TESTRAIL_URL')
TESTRAIL_USER = os.getenv('TESTRAIL_USER')
TESTRAIL_API_KEY = os.getenv('TESTRAIL_API_KEY')

auth = HTTPBasicAuth(TESTRAIL_USER, TESTRAIL_API_KEY)
headers = {'Content-Type': 'application/json'}


def send_get(uri, params=None):
    url = f"{TESTRAIL_URL}index.php?/api/v2/{uri}"
    try:
        response = requests.get(url, auth=auth, headers=headers, params=params)
        response.raise_for_status()  # This will raise an exception for HTTP errors
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', '60'))
            print(f"Rate limit exceeded. Retrying after {retry_after} seconds.")
            time.sleep(retry_after)
            return send_get(uri, params)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error occurred while making request to {url}: {str(e)}")
        print(f"Response content: {response.text}")
        raise
    except json.JSONDecodeError:
        print(f"Error decoding JSON response from {url}")
        print(f"Response content: {response.text}")
        raise


def get_projects():
    try:
        projects = send_get('get_projects')
        print(f"Debug: get_projects() returned: {projects}")
        return projects['projects']  # Return the 'projects' list directly
    except Exception as e:
        print(f"Error in get_projects(): {str(e)}")
        raise


def select_project():
    projects = get_projects()
    print(f"Debug: Type of projects: {type(projects)}")
    print(f"Debug: Content of projects: {projects}")
    
    if not projects:
        print("No projects available.")
        return None

    print("Available Projects:")
    for project in projects:
        print(f"Debug: Type of project: {type(project)}")
        print(f"Debug: Content of project: {project}")
        status = 'Completed' if project['is_completed'] else 'Active'
        print(f"ID: {project['id']}, Name: {project['name']}, Status: {status}")
    
    while True:
        project_id_input = input("Enter the Project ID you want to select (or 'q' to quit): ").strip().lower()
        if project_id_input == 'q':
            return None
        if project_id_input.isdigit():
            project_id = int(project_id_input)
            if any(project['id'] == project_id for project in projects):
                return project_id
            else:
                print("Invalid Project ID. Please try again.")
        else:
            print("Please enter a numeric Project ID or 'q' to quit.")


def get_project(project_id):
    return send_get(f'get_project/{project_id}')


def get_suites(project_id):
    return send_get(f'get_suites/{project_id}')


def select_suite(project_id):
    suites = get_suites(project_id)
    if not suites:
        print("No test suites found for this project.")
        return None  # For single-suite projects
    print("Available Test Suites:")
    for suite in suites:
        print(f"ID: {suite['id']}, Name: {suite['name']}")
    while True:
        suite_id_input = input("Enter the Suite ID you want to select: ").strip()
        if suite_id_input.isdigit():
            suite_id = int(suite_id_input)
            if any(suite['id'] == suite_id for suite in suites):
                return suite_id
            else:
                print("Invalid Suite ID. Please try again.")
        else:
            print("Please enter a numeric Suite ID.")


def get_sections(project_id, suite_id):
    if suite_id:
        uri = f'get_sections/{project_id}&suite_id={suite_id}'
    else:
        uri = f'get_sections/{project_id}'
    return send_get(uri)


def get_test_cases(project_id, suite_id, offset=0, limit=250):
    params = {'offset': offset, 'limit': limit}
    if suite_id:
        params['suite_id'] = suite_id
    response = send_get(f'get_cases/{project_id}', params=params)
    return response.get('cases', [])


def get_all_test_cases(project_id, suite_id):
    all_cases = []
    offset = 0
    limit = 250
    max_retries = 3
    retry_delay = 5  # seconds

    while True:
        for attempt in range(max_retries):
            try:
                print(f"Fetching test cases: offset {offset}, limit {limit}")
                test_cases = get_test_cases(project_id, suite_id, offset, limit)
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Error fetching test cases: {str(e)}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print(f"Failed to fetch test cases after {max_retries} attempts. Last error: {str(e)}")
                    return all_cases

        if not test_cases:
            break
        all_cases.extend(test_cases)
        print(f"Fetched {len(test_cases)} test cases. Total: {len(all_cases)}")
        if len(test_cases) < limit:
            break
        offset += limit

    return all_cases


def save_data(data, filename):
    output_dir = os.path.join(os.path.dirname(__file__), '../../data/output')
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def main():
    # Select project
    project_id = select_project()
    if not project_id:
        print("No project selected. Exiting.")
        return
    project = get_project(project_id)
    suite_mode = project['suite_mode']

    # Determine 'suite_id' based on 'suite_mode'
    if suite_mode == 1:
        # Single Suite Mode
        suite_id = None
        print("Project is in Single Suite Mode.")
    elif suite_mode == 2:
        # Single Suite + Baselines Mode
        suite_id = get_suites(project_id)[0]['id']
        print("Project is in Single Suite + Baselines Mode.")
    elif suite_mode == 3:
        # Multiple Suites Mode
        print("Project is in Multiple Suites Mode.")
        suite_id = select_suite(project_id)
    else:
        print("Unknown suite mode.")
        return

    # Fetch and save test cases
    print("Fetching test cases...")
    all_test_cases = get_all_test_cases(project_id, suite_id)
    if all_test_cases:
        save_data(all_test_cases, 'test_cases.json')
        print(f"Saved {len(all_test_cases)} test cases to data/output/test_cases.json")
    else:
        print("No test cases were fetched. Please check your project configuration and permissions.")

    # Fetch and save sections
    print("Fetching sections...")
    sections = get_sections(project_id, suite_id)
    save_data(sections, 'sections.json')
    num_sections = len(sections.get('sections', []))  # Get length of the 'sections' array
    print(f"Saved {num_sections} sections to data/output/sections.json")


if __name__ == "__main__":
    main()
