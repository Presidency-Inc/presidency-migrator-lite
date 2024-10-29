import os
import time
import json
import requests
from requests.auth import HTTPBasicAuth

class TestRailClient:
    def __init__(self, base_url, username, api_key):
        self.base_url = base_url.rstrip('/')
        self.auth = HTTPBasicAuth(username, api_key)
        self.headers = {'Content-Type': 'application/json'}

    def _send_get(self, uri, params=None):
        url = f"{self.base_url}/index.php?/api/v2/{uri}"
        try:
            response = requests.get(url, auth=self.auth, headers=self.headers, params=params)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', '60'))
                print(f"Rate limit exceeded. Retrying after {retry_after} seconds.")
                time.sleep(retry_after)
                return self._send_get(uri, params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error occurred while making request to {url}: {str(e)}")
            print(f"Response content: {response.text}")
            raise
        except json.JSONDecodeError:
            print(f"Error decoding JSON response from {url}")
            print(f"Response content: {response.text}")
            raise

    def get_projects(self):
        try:
            response = self._send_get('get_projects')
            projects = response.get('projects', [])
            return projects
        except Exception as e:
            print(f"Error in get_projects(): {str(e)}")
            raise

    def get_project(self, project_id):
        return self._send_get(f'get_project/{project_id}')

    def get_suites(self, project_id):
        return self._send_get(f'get_suites/{project_id}')

    def get_sections(self, project_id, suite_id=None):
        params = {}
        if suite_id:
            params['suite_id'] = suite_id
        response = self._send_get(f'get_sections/{project_id}', params=params)
        return response.get('sections', [])

    def get_test_cases(self, project_id, suite_id=None, offset=0, limit=250):
        params = {'offset': offset, 'limit': limit}
        if suite_id:
            params['suite_id'] = suite_id
        response = self._send_get(f'get_cases/{project_id}', params=params)
        return response

    def get_all_test_cases(self, project_id, suite_id=None):
        all_cases = []
        offset = 0
        limit = 250
        max_retries = 3
        retry_delay = 5  # seconds

        while True:
            for attempt in range(max_retries):
                try:
                    print(f"Fetching test cases: offset {offset}, limit {limit}")
                    test_cases = self.get_test_cases(project_id, suite_id, offset, limit)
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

    def save_data(self, data, filename):
        output_dir = os.path.join(os.path.dirname(__file__), '../../data/output')
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
