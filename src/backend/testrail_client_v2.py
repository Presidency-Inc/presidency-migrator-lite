"""TestRail API Client.

Based on the official TestRail API binding for Python 3.x.
"""

import os
import base64
import json
import requests
from dotenv import load_dotenv

class APIError(Exception):
    pass

class TestRailClient:
    def __init__(self, base_url=None, username=None, password=None):
        load_dotenv()
        
        self.base_url = base_url or os.getenv('TESTRAIL_URL')
        self.username = username or os.getenv('TESTRAIL_USER')
        self.password = password or os.getenv('TESTRAIL_PWD')
        
        if not all([self.base_url, self.username, self.password]):
            raise ValueError("Missing required credentials. Please provide them or set in .env file")
            
        if not self.base_url.endswith('/'):
            self.base_url += '/'
        self.__url = self.base_url + 'index.php?/api/v2/'
        
        # Create necessary directories
        self.attachment_dir = "./attachmentFiles"
        self.output_dir = "data/output"
        os.makedirs(self.attachment_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def send_get(self, uri, filepath=None):
        """Issue a GET request (read) against the API.

        Args:
            uri: The API method to call including parameters, e.g. get_case/1.
            filepath: The path and file name for attachment download; used only
                for 'get_attachment/:attachment_id'.

        Returns:
            A dict containing the result of the request.
        """
        return self.__send_request('GET', uri, filepath)

    def send_post(self, uri, data):
        """Issue a POST request (write) against the API.

        Args:
            uri: The API method to call, including parameters, e.g. add_case/1.
            data: The data to submit as part of the request as a dict; strings
                must be UTF-8 encoded. If adding an attachment, must be the
                path to the file.

        Returns:
            A dict containing the result of the request.
        """
        return self.__send_request('POST', uri, data)

    def __send_request(self, method, uri, data):
        """Send request to TestRail API.

        Args:
            method: HTTP method to use (GET or POST)
            uri: API method URI
            data: Request data (for POST) or filepath (for GET attachment)

        Returns:
            Response data (JSON decoded or file path for attachments)
        """
        url = self.__url + uri

        auth = str(
            base64.b64encode(
                bytes('%s:%s' % (self.username, self.password), 'utf-8')
            ),
            'ascii'
        ).strip()
        headers = {'Authorization': 'Basic ' + auth}

        if method == 'POST':
            if uri[:14] == 'add_attachment':    # add_attachment API method
                files = {'attachment': (open(data, 'rb'))}
                response = requests.post(url, headers=headers, files=files, verify=False)
                files['attachment'].close()
            else:
                headers['Content-Type'] = 'application/json'
                payload = bytes(json.dumps(data), 'utf-8')
                response = requests.post(url, headers=headers, data=payload, verify=False)
        else:
            headers['Content-Type'] = 'application/json'
            response = requests.get(url, headers=headers, verify=False)

        if response.status_code > 201:
            try:
                error = response.json()
            except:     # response.content not formatted as JSON
                error = str(response.content)
            raise APIError('TestRail API returned HTTP %s (%s)' % (response.status_code, error))
        else:
            if uri[:15] == 'get_attachment/':   # Expecting file, not JSON
                try:
                    open(data, 'wb').write(response.content)
                    return data
                except:
                    return "Error saving attachment."
            else:
                try:
                    return response.json()
                except: # Nothing to return
                    return {}

    def get_projects(self):
        """Get all available projects"""
        return self.send_get('get_projects')

    def get_users(self, project_id=None):
        """Get all users from TestRail, optionally filtered by project.
        
        Args:
            project_id (int, optional): Project ID to filter users
            
        Returns:
            list: List of user dictionaries
        """
        try:
            # For non-admin users or when filtering by project
            if project_id:
                uri = f'get_users'  # Remove project_id from URI
            else:
                uri = 'get_users'
                
            print(f"Fetching users with URI: {uri}")
            response = self.send_get(uri)
            print(f"Raw API Response: {json.dumps(response, indent=2)}")
            
            # Handle different response formats
            if isinstance(response, dict):
                if 'users' in response:
                    users = response['users']
                else:
                    users = []
            elif isinstance(response, list):
                users = response
            else:
                print(f"Unexpected response format: {type(response)}")
                return []
                
            # Additional debugging
            if not users:
                print("No users found in response")
            else:
                print(f"Found {len(users)} users in response")
                for user in users:
                    print(f"User found: ID={user.get('id')}, Name={user.get('name')}")
            
            return users
        except Exception as e:
            print(f"Error getting users: {str(e)}")
            print(f"Exception type: {type(e)}")
            if hasattr(e, 'response'):
                print(f"Response status code: {e.response.status_code}")
                print(f"Response content: {e.response.text}")
            return []

    def get_user(self, user_id):
        """Get a specific user by ID from TestRail.
        
        Args:
            user_id (int): The ID of the user to retrieve
            
        Returns:
            dict: User information including email, name, and role
        """
        try:
            print(f"Fetching user details for ID: {user_id}")
            response = self.send_get(f'get_user/{user_id}')
            print(f"User details response: {json.dumps(response, indent=2)}")
            if not response:
                print(f"No data returned for user ID {user_id}")
                return None
            return response
        except Exception as e:
            print(f"Error getting user with ID {user_id}: {str(e)}")
            if hasattr(e, 'response'):
                print(f"Response status code: {e.response.status_code}")
                print(f"Response content: {e.response.text}")
            return None

    def get_user_by_email(self, email):
        """Get user details by email from TestRail.
        
        Args:
            email (str): The email address of the user
            
        Returns:
            dict: User information including id, name, and role
        """
        try:
            print(f"Looking up user by email: {email}")
            # Note: The API expects the email parameter in the query string
            response = self.send_get('get_user_by_email', {'email': email})
            print(f"Email lookup response: {json.dumps(response, indent=2)}")
            return response
        except Exception as e:
            print(f"Error getting user with email {email}: {str(e)}")
            if hasattr(e, 'response'):
                print(f"Response status code: {e.response.status_code}")
                print(f"Response content: {e.response.text}")
            return None

    def get_all_user_details(self, project_id=None):
        """Get detailed information for all users."""
        try:
            print("\nGetting basic user list...")
            users = self.get_users(project_id)
            if not users:
                print("No users found in basic list")
                return []
                
            print(f"\nFetching detailed information for {len(users)} users...")
            detailed_users = []
            
            for i, user in enumerate(users, 1):
                if isinstance(user, dict) and 'id' in user:
                    print(f"Fetching details for user {i}/{len(users)} (ID: {user['id']})...")
                    user_details = self.get_user(user['id'])
                    if user_details:
                        detailed_users.append(user_details)
                        print(f"Successfully got details for user {user.get('name', user['id'])}")
                    else:
                        print(f"Could not get details for user {user['id']}")
                else:
                    print(f"Invalid user format: {user}")
            
            print(f"\nSuccessfully retrieved details for {len(detailed_users)} users")
            return detailed_users
        except Exception as e:
            print(f"Error getting all user details: {str(e)}")
            return []

    def get_user_email_mapping(self, project_id=None):
        """Build a mapping of user IDs to email addresses."""
        try:
            print("\nBuilding user email mapping...")
            users = self.get_users(project_id)
            email_mapping = {}
            
            for user in users:
                if isinstance(user, dict) and 'id' in user:
                    print(f"Processing user ID: {user['id']}...")
                    if 'email' not in user:
                        print(f"Fetching additional details for user {user['id']}...")
                        user_details = self.get_user(user['id'])
                        if user_details and 'email' in user_details:
                            email_mapping[str(user['id'])] = user_details['email']
                            print(f"Added email mapping for user {user['id']}")
                    else:
                        email_mapping[str(user['id'])] = user['email']
                        print(f"Added email mapping for user {user['id']}")
            
            print(f"\nCreated email mapping for {len(email_mapping)} users")
            return email_mapping
        except Exception as e:
            print(f"Error building user email mapping: {str(e)}")
            return {}

    def get_project(self, project_id):
        """Get a specific project by ID"""
        return self.send_get(f'get_project/{project_id}')

    def get_suites(self, project_id):
        """Get all test suites for a project"""
        return self.send_get(f'get_suites/{project_id}')

    def get_sections(self, project_id, suite_id=None):
        """Get all sections for a project and suite"""
        uri = f'get_sections/{project_id}'
        if suite_id:
            uri += f'&suite_id={suite_id}'
        return self.send_get(uri)

    def get_test_cases(self, project_id, suite_id=None, offset=0, limit=250):
        """Get test cases with pagination"""
        params = f'get_cases/{project_id}'
        if suite_id:
            params += f'&suite_id={suite_id}'
        if offset:
            params += f'&offset={offset}'
        if limit:
            params += f'&limit={limit}'
        response = self.send_get(params)
        return response.get('cases', [])

    def get_all_test_cases(self, project_id, suite_id=None):
        """Get all test cases for a project"""
        all_cases = []
        offset = 0
        limit = 250

        while True:
            test_cases = self.get_test_cases(project_id, suite_id, offset, limit)
            if not test_cases:
                break
            all_cases.extend(test_cases)
            print(f"Fetched {len(test_cases)} test cases. Total: {len(all_cases)}")
            if len(test_cases) < limit:
                break
            offset += limit

        return all_cases

    def get_attachments_for_test_cases(self, test_cases):
        """Get and download attachments for multiple test cases"""
        if not test_cases:
            raise ValueError('test_cases is required')
            
        attachment_metadata = []
        
        for test_case in test_cases:
            case_id = test_case.get('id')
            if case_id is None:
                print(f"Skipping test case {test_case} as it doesn't have an ID")
                continue
            
            print(f"\nProcessing test case ID: {case_id}")
            
            try:
                attachments = self.send_get(f'get_attachments_for_case/{case_id}').get('attachments', [])
                
                if not attachments:
                    print(f"No attachments found for case ID: {case_id}")
                    continue
                
                for attachment in attachments:
                    attachment_id = attachment['id']
                    filename = attachment['filename']
                    
                    # Download attachment
                    file_path = os.path.join(self.attachment_dir, filename)
                    print(f"\nDownloading: {filename}")
                    
                    self.send_get(f'get_attachment/{attachment_id}', file_path)
                    print(f"Saved to: {file_path}")
                    
                    attachment_metadata.append({
                        'case_id': case_id,
                        'attachment_id': attachment_id,
                        'file_name': filename,
                        'file_path': file_path
                    })
                
            except Exception as e:
                print(f"Error processing case {case_id}: {str(e)}")
                continue
        
        if not attachment_metadata:
            print(f"No attachments found for any test cases")
            return None
        
        self.save_data(attachment_metadata, 'test_cases_attachment_files.json')
        print(f"\nSaved attachment metadata to {os.path.join(self.output_dir, 'test_cases_attachment_files.json')}")
        
        return attachment_metadata

    def save_data(self, data, filename):
        """Save data to JSON file"""
        file_path = os.path.join(self.output_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)


def select_project(client):
    """Interactive project selection"""
    projects = client.get_projects()
    
    if not projects:
        print("No projects available.")
        return None

    print("\nAvailable Projects:")
    for project in projects:
        status = 'Completed' if project['is_completed'] else 'Active'
        print(f"ID: {project['id']}, Name: {project['name']}, Status: {status}")
    
    while True:
        project_id_input = input("\nEnter the Project ID you want to select (or 'q' to quit): ").strip().lower()
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


def select_suite(client, project_id):
    """Interactive suite selection"""
    suites = client.get_suites(project_id)
    if not suites:
        print("No test suites found for this project.")
        return None
        
    print("\nAvailable Test Suites:")
    for suite in suites:
        print(f"ID: {suite['id']}, Name: {suite['name']}")
        
    while True:
        suite_id_input = input("\nEnter the Suite ID you want to select: ").strip()
        if suite_id_input.isdigit():
            suite_id = int(suite_id_input)
            if any(suite['id'] == suite_id for suite in suites):
                return suite_id
            else:
                print("Invalid Suite ID. Please try again.")
        else:
            print("Please enter a numeric Suite ID.")

def main():
    # Initialize TestRail client
    client = TestRailClient()
    
    # Select project
    project_id = select_project(client)
    if not project_id:
        print("No project selected. Exiting.")
        return
        
    project = client.get_project(project_id)
    suite_mode = project['suite_mode']

    # Determine suite_id based on suite_mode
    if suite_mode == 1:
        suite_id = None
        print("Project is in Single Suite Mode.")
    elif suite_mode == 2:
        suite_id = client.get_suites(project_id)[0]['id']
        print("Project is in Single Suite + Baselines Mode.")
    elif suite_mode == 3:
        print("Project is in Multiple Suites Mode.")
        suite_id = select_suite(client, project_id)
    else:
        print("Unknown suite mode.")
        return

    # Fetch and save test cases
    print("\nFetching test cases...")
    all_test_cases = client.get_all_test_cases(project_id, suite_id)

    if all_test_cases:
        client.save_data(all_test_cases, 'test_cases.json')
        print(f"Saved {len(all_test_cases)} test cases to data/output/test_cases.json")

        print("\nFetching attachments for test cases...")
        client.get_attachments_for_test_cases(all_test_cases)
    else:
        print("No test cases were fetched. Please check your project configuration and permissions.")

    # Fetch and save sections
    print("\nFetching sections...")
    sections = client.get_sections(project_id, suite_id)
    client.save_data(sections, 'sections.json')
    num_sections = len(sections.get('sections', []))
    print(f"Saved {num_sections} sections to data/output/sections.json")
    
    # Save users list for the specific project
    print("\nFetching users list...")
    users = client.get_users(project_id)
    if users:
        print(f"Found {len(users)} users")
        client.save_data(users, 'users_list.json')
        print(f"Saved users list to data/output/users_list.json")
    
    # Save detailed user information
    print("\nFetching detailed user information...")
    detailed_users = client.get_all_user_details(project_id)
    if detailed_users:
        print(f"Retrieved details for {len(detailed_users)} users")
        client.save_data(detailed_users, 'users_detailed.json')
        print(f"Saved detailed user information to data/output/users_detailed.json")
    
    # Create email mapping
    print("\nCreating user email mapping...")
    email_mapping = client.get_user_email_mapping(project_id)
    if email_mapping:
        print(f"Created email mapping for {len(email_mapping)} users")
        client.save_data(email_mapping, 'user_email_mapping.json')
        print(f"Saved user email mapping to data/output/user_email_mapping.json")


if __name__ == "__main__":
    main()
