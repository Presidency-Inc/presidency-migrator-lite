"""TestRail API Client.

Based on the official TestRail API binding for Python 3.x.
"""

import os
import base64
import json
import requests
import logging
import re

from datetime import datetime
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
        self.logs_dir = "logs"

        # Create necessary cookies
        self.tr_session = os.getenv('TESTRAIL_SESSION')
        self.tr_rememberme = os.getenv('TESTRAIL_REMEMBERME')

        os.makedirs(self.attachment_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # Setup logging
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging for the TestRail client."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(self.logs_dir, f'testrail_client_{timestamp}.log')
        
        # Configure logging format and settings
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('TestRailClient')
        self.logger.info('TestRail Client initialized')

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
        self.logger.info(f'Sending {method} request to {url}')

        auth = str(
            base64.b64encode(
                bytes('%s:%s' % (self.username, self.password), 'utf-8')
            ),
            'ascii'
        ).strip()
        headers = {'Authorization': 'Basic ' + auth}

        try:
            if method == 'POST':
                if uri[:14] == 'add_attachment':    # add_attachment API method
                    self.logger.info(f'Uploading attachment: {data}')
                    files = {'attachment': (open(data, 'rb'))}
                    response = requests.post(url, headers=headers, files=files, verify=False)
                    files['attachment'].close()
                else:
                    headers['Content-Type'] = 'application/json'
                    payload = bytes(json.dumps(data), 'utf-8')
                    self.logger.debug(f'POST payload: {json.dumps(data)}')
                    response = requests.post(url, headers=headers, data=payload, verify=False)
            else:
                headers['Content-Type'] = 'application/json'
                response = requests.get(url, headers=headers, verify=False)

            if response.status_code > 201:
                try:
                    error = response.json()
                except:     # response.content not formatted as JSON
                    error = str(response.content)
                error_msg = f'TestRail API returned HTTP {response.status_code} ({error})'
                self.logger.error(error_msg)
                raise APIError(error_msg)
            else:
                if uri[:15] == 'attachments/':   # Expecting file, not JSON
                    try:
                        open(data, 'wb').write(response.content)
                        self.logger.info(f'Successfully saved attachment to {data}')
                        return data
                    except Exception as e:
                        error_msg = f'Error saving attachment: {str(e)}'
                        self.logger.error(error_msg)
                        return "Error saving attachment."
                else:
                    try:
                        result = response.json()
                        self.logger.debug(f'API response: {json.dumps(result)}')
                        return result
                    except:  # Nothing to return
                        return {}
        except Exception as e:
            error_msg = f'Error in API request: {str(e)}'
            self.logger.error(error_msg)
            raise APIError(error_msg)

    def __send_attachment_request(self, uri, file_section):
        """Send request to TestRail API.
            Args:
                uri: API method URI
        """
        url = self.base_url + uri

        try:
            headers = {
                'cookie': (
                    'tr_session={}; '.format(self.tr_session) +
                    'tr_rememberme={}; '.format(self.tr_rememberme)
                ),
            }

            # Make the request
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()  # Raise an exception for bad status codes

            # Create downloads directory if it doesn't exist
            download_dir = os.path.join(os.path.dirname(__file__), 'attachmentFiles')

            # Use the session to download the file
            # response = session.get(url, verify=False)
                
            if response.status_code > 201:
                try:
                    error = response.json()
                except:     # response.content not formatted as JSON
                    error = str(response.content)
                error_msg = f'TestRail API returned HTTP {response.status_code} ({error})'
                self.logger.error(error_msg)
                raise APIError(error_msg)
            else:
                try:
                    file_path = os.path.join(self.attachment_dir, os.path.basename(uri))
                    os.makedirs(download_dir, exist_ok=True)

                    # Generate filename with timestamp
                    current_datetime = datetime.now()
                    milliseconds = int(current_datetime.timestamp() * 1000)
                    filename = f'{file_section}_tr_{milliseconds}.png'
                    filepath = os.path.join(download_dir, filename)

                    # Save the image
                    with open(filepath, 'wb') as f:
                        f.write(response.content)

                    self.logger.info(f'Successfully saved attachment to {file_path}')
                    return filename
                except Exception as e:
                    error_msg = f'Error saving attachment: {str(e)}'
                    self.logger.error(error_msg)
                    return "Error saving attachment."
                
        except Exception as e:
            error_msg = f'Error in API request: {str(e)}'
            self.logger.error(error_msg)
            raise APIError(error_msg)

    def get_projects(self):
        """Get all available projects"""
        return self.send_get('get_projects')['projects'] # TR version 5.4 returns a list
        # return self.send_get('get_projects')

    def get_users(self, project_id=None):
        """Get all active users from TestRail, optionally filtered by project.
        
        Args:
            project_id (int, optional): Project ID to filter users
            
        Returns:
            list: List of active user dictionaries
        """
        try:
            if project_id:
                uri = f'get_users'
                self.logger.info(f'Fetching users for project {project_id}')
            else:
                uri = 'get_users'
                self.logger.info('Fetching all users')
                
            response = self.send_get(uri)
            
            if isinstance(response, dict):
                all_users = response.get('users', [])
            elif isinstance(response, list):
                all_users = response
            else:
                self.logger.warning(f'Unexpected response format: {type(response)}')
                return []
            
            # Filter only active users
            active_users = [user for user in all_users if user.get('is_active', False)]
            
            self.logger.info(f'Found {len(active_users)} active users out of {len(all_users)} total users')
            return active_users
            
        except Exception as e:
            self.logger.error(f'Error getting users: {str(e)}')
            return []

    def get_user(self, user_id):
        """Get a specific user by ID from TestRail.
        
        Args:
            user_id (int): The ID of the user to retrieve
            
        Returns:
            dict: User information including email, name, and role
        """
        try:
            self.logger.info(f'Fetching user details for ID: {user_id}')
            response = self.send_get(f'get_user/{user_id}')
            self.logger.info(f'User details response: {json.dumps(response, indent=2)}')
            if not response:
                self.logger.info(f'No data returned for user ID {user_id}')
                return None
            return response
        except Exception as e:
            self.logger.error(f'Error getting user with ID {user_id}: {str(e)}')
            return None

    def get_user_by_email(self, email):
        """Get user details by email from TestRail.
        
        Args:
            email (str): The email address of the user
            
        Returns:
            dict: User information including id, name, and role
        """
        try:
            self.logger.info(f'Looking up user by email: {email}')
            # Note: The API expects the email parameter in the query string
            response = self.send_get('get_user_by_email', {'email': email})
            self.logger.info(f'Email lookup response: {json.dumps(response, indent=2)}')
            return response
        except Exception as e:
            self.logger.error(f'Error getting user with email {email}: {str(e)}')
            return None

    def get_all_user_details(self, project_id=None):
        """Get detailed information for all users."""
        try:
            self.logger.info("\nGetting basic user list...")
            users = self.get_users(project_id)
            if not users:
                self.logger.info("No users found in basic list")
                return []
                
            self.logger.info(f"\nFetching detailed information for {len(users)} users...")
            detailed_users = []
            
            for i, user in enumerate(users, 1):
                if isinstance(user, dict) and 'id' in user:
                    self.logger.info(f"Fetching details for user {i}/{len(users)} (ID: {user['id']})...")
                    user_details = self.get_user(user['id'])
                    if user_details:
                        detailed_users.append(user_details)
                        self.logger.info(f"Successfully got details for user {user.get('name', user['id'])}")
                    else:
                        self.logger.info(f"Could not get details for user {user['id']}")
                else:
                    self.logger.info(f"Invalid user format: {user}")
            
            self.logger.info(f"\nSuccessfully retrieved details for {len(detailed_users)} users")
            return detailed_users
        except Exception as e:
            self.logger.error(f"Error getting all user details: {str(e)}")
            return []

    def get_user_email_mapping(self, project_id=None):
        """Build a mapping of user IDs to email addresses."""
        try:
            self.logger.info("\nBuilding user email mapping...")
            users = self.get_users(project_id)
            email_mapping = {}
            
            for user in users:
                if isinstance(user, dict) and 'id' in user:
                    self.logger.info(f"Processing user ID: {user['id']}...")
                    if 'email' not in user:
                        self.logger.info(f"Fetching additional details for user {user['id']}...")
                        user_details = self.get_user(user['id'])
                        if user_details and 'email' in user_details:
                            email_mapping[str(user['id'])] = user_details['email']
                            self.logger.info(f"Added email mapping for user {user['id']}")
                    else:
                        email_mapping[str(user['id'])] = user['email']
                        self.logger.info(f"Added email mapping for user {user['id']}")
            
            self.logger.info(f"\nCreated email mapping for {len(email_mapping)} users")
            return email_mapping
        except Exception as e:
            self.logger.error(f"Error building user email mapping: {str(e)}")
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
        # return response
        return response.get('cases', []) # TR version 5.4 returns a list

    def get_all_test_cases(self, project_id, suite_id=None):
        """Get all test cases for a project"""
        all_cases = []
        if isinstance(suite_id, list):
            for suite in suite_id:
                if isinstance(suite, dict):
                    suite_id = suite.get('id')
                else:
                    suite_id = suite
                offset = 0
                limit = 250

                while True:
                    test_cases = self.get_test_cases(project_id, suite_id, offset, limit)
                    if not test_cases:
                        break
                    all_cases.extend(test_cases)
                    self.logger.info(f"Fetched {len(test_cases)} test cases. Total: {len(all_cases)}")
                    if len(test_cases) < limit:
                        break
                    offset += limit
        else:
            offset = 0
            limit = 250

            while True:
                test_cases = self.get_test_cases(project_id, suite_id, offset, limit)
                if not test_cases:
                    break
                all_cases.extend(test_cases)
                self.logger.info(f"Fetched {len(test_cases)} test cases. Total: {len(all_cases)}")
                if len(test_cases) < limit:
                    break
                offset += limit

        return all_cases

    def attachment_lookup(self, test_case):
        """Lookup attachments for a test case"""
        attachments = []
        required_fields = ['custom_preconds', 'custom_steps', 'custom_expected', 'custom_mission', 'custom_goals']
        try:
            attachments = []
            for field in required_fields:
                value = test_case.get(field)
                if value and 'index.php?/attachments/get/' in value:
                    # Extract the specific substring using a regular expression
                    # match = re.search(r'index\.php\?/attachments/get/\S+', value)
                    matches = re.findall(r'index\.php\?/attachments/get/\S+', value)
                    if matches:
                        matches_list = []
                        for match in matches:
                            attachment_value = match
                            attachment_value = attachment_value.replace(')', '')
                            matches_list.append(attachment_value)
                            self.logger.info(f"Extracted attachment for test case {test_case.get('id')}: {attachment_value}")

                        attachments.append({
                            "field": field,
                            "paths": matches_list
                        })
                        self.logger.info(f"Extracted attachment for test case {test_case.get('id')}: {attachment_value}")
                else:
                    self.logger.info(f"Test case {test_case.get('id')} does not have an attachment in field {field}")
            
            if not attachments:
                self.logger.info(f"No attachments found for test case {test_case.get('id')}")
                return None

            return attachments
        except Exception as e:
            self.logger.error(f"Error extracting attachments (attachment_lookup) for test case {test_case.get('id')}: {e}")
            return None

    def get_attachments_for_test_cases(self, test_cases):
        """Get and download attachments for multiple test cases"""
        if not test_cases:
            raise ValueError('test_cases is required')
            
        attachment_metadata = []
        
        for test_case in test_cases:
            case_id = test_case.get('id')
            case_title = test_case.get('title')
            if case_id is None:
                self.logger.info(f"Skipping test case {test_case} as it doesn't have an ID")
                continue
            
            self.logger.info(f"\nProcessing test case ID: {case_id}")
            
            try:
                attachments = self.attachment_lookup(test_case)

                self.logger.info('-' * 100)

                if attachments:
                    self.logger.info(f"Attachments found for case ID: {case_id}: {attachments}")

                self.logger.info('-' * 100)
                
                if not attachments:
                    self.logger.info(f"No attachments found for case ID: {case_id}")
                    continue
                
                stored_data = []
                for attachment in attachments:
                    saved_files = []
                    for file_path in attachment.get('paths', []):
                        self.logger.info(f"\nDownloading: {file_path}")
                        
                        saved_file_name = self.__send_attachment_request(file_path, attachment.get('field'))
                        self.logger.info(f"Saved to: ./attachmentFiles")
                        
                        stored_data.append({
                            'file_path': file_path,
                            'field': attachment.get('field'),
                            'stored_file_name': saved_file_name
                        })
                        
                        saved_files.append(saved_file_name)                     

                attachment_metadata.append({
                    'case_id': case_id,
                    'case_title': case_title,
                    'stored_data': stored_data
                })
                
            except Exception as e:
                self.logger.error(f"Error processing case {case_id}: {str(e)}")
                continue
        
        if not attachment_metadata:
            self.logger.info(f"No attachments found for any test cases")
            return None
        
        self.save_data(attachment_metadata, 'test_cases_attachment_files.json')
        self.logger.info(f"\nSaved attachment metadata to {os.path.join(self.output_dir, 'test_cases_attachment_files.json')}")
        
        return attachment_metadata

    # Deprecated method - Only for TR version 5.7 and above
    # def get_attachments_for_test_cases(self, test_cases):
    #     """Get and download attachments for multiple test cases"""
    #     if not test_cases:
    #         raise ValueError('test_cases is required')
            
    #     attachment_metadata = []
        
    #     for test_case in test_cases:
    #         case_id = test_case.get('id')
    #         if case_id is None:
    #             self.logger.info(f"Skipping test case {test_case} as it doesn't have an ID")
    #             continue
            
    #         self.logger.info(f"\nProcessing test case ID: {case_id}")
            
    #         try:
    #             attachments = self.send_get(f'get_attachments_for_case/{case_id}').get('attachments', [])
                
    #             if not attachments:
    #                 self.logger.info(f"No attachments found for case ID: {case_id}")
    #                 continue
                
    #             for attachment in attachments:
    #                 attachment_id = attachment['id']
    #                 filename = attachment['filename']
                    
    #                 # Download attachment
    #                 file_path = os.path.join(self.attachment_dir, filename)
    #                 self.logger.info(f"\nDownloading: {filename}")
                    
    #                 self.send_get(f'get_attachment/{attachment_id}', file_path)
    #                 self.logger.info(f"Saved to: {file_path}")
                    
    #                 attachment_metadata.append({
    #                     'case_id': case_id,
    #                     'attachment_id': attachment_id,
    #                     'file_name': filename,
    #                     'file_path': file_path
    #                 })
                
    #         except Exception as e:
    #             self.logger.error(f"Error processing case {case_id}: {str(e)}")
    #             continue
        
    #     if not attachment_metadata:
    #         self.logger.info(f"No attachments found for any test cases")
    #         return None
        
    #     self.save_data(attachment_metadata, 'test_cases_attachment_files.json')
    #     self.logger.info(f"\nSaved attachment metadata to {os.path.join(self.output_dir, 'test_cases_attachment_files.json')}")
        
    #     return attachment_metadata

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
    
    # Save suites data to JSON
    client.save_data(suites, 'suites.json')
    print(f"\nSaved {len(suites)} suites to data/output/suites.json")
        
    print("\nAvailable Test Suites:")
    for suite in suites:
        print(f"ID: {suite['id']}, Name: {suite['name']}")
        
    while True:
        suite_id_input = input("\nEnter the Suite ID you want to select (or 'get_all' for all suites): ").strip()
        if suite_id_input.isdigit():
            suite_id = int(suite_id_input)
            if any(suite['id'] == suite_id for suite in suites):
                return suite_id
            else:
                print("Invalid Suite ID. Please try again.")
        elif suite_id_input.lower() == "get_all":
            print("\nSelecting all suites...")
            suite_ids = [suite['id'] for suite in suites]
            client.logger.info(f"Selected all suite IDs: {suite_ids}")
            return suite_ids
        else:
            print("Please enter a numeric Suite ID or 'get_all' for all suites.")


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

        # Deprecated fetching attachments for test cases
        # print("\nFetching attachments for test cases...")
        client.get_attachments_for_test_cases(all_test_cases)
    else:
        print("No test cases were fetched. Please check your project configuration and permissions.")

    # Fetch and save sections
    print("\nFetching sections...")
    sections = []
    if isinstance(suite_id, list):
        for suite in suite_id:
            print(f"Fetching sections for suite {suite}...")
            

            if not isinstance(suite, int):
                print(f"Invalid suite_id {suite}. Skipping...")
                continue
            response = client.get_sections(project_id, suite) # client.get_sections returns a list in v5.4
            sections_data = response.get('sections', [])
            print(f"Response for suite {suite}: {response}")
            sections.extend(sections_data) # client.get_sections returns a list in v5.4
            # sections.extend(response)
    else:
        sections = client.get_sections(project_id, suite_id) # client.get_sections returns a list in v5.4
    client.save_data(sections, 'sections.json')
    num_sections = len(sections)
    # num_sections = len(sections.get('sections', []))
    print(f"Saved {num_sections} sections to data/output/sections.json")
    
    # Deprecated user extraction
    # # Save users list for the specific project
    # print("\nFetching users list...")
    # users = client.get_users(project_id)
    # if users:
    #     print(f"Found {len(users)} users")
    #     client.save_data(users, 'users_list.json')
    #     print(f"Saved users list to data/output/users_list.json")
    
    # # Save detailed user information
    # print("\nFetching detailed user information...")
    # detailed_users = client.get_all_user_details(project_id)
    # if detailed_users:
    #     print(f"Retrieved details for {len(detailed_users)} users")
    #     client.save_data(detailed_users, 'users_detailed.json')
    #     print(f"Saved detailed user information to data/output/users_detailed.json")
    
    # # Create email mapping
    # print("\nCreating user email mapping...")
    # email_mapping = client.get_user_email_mapping(project_id)
    # if email_mapping:
    #     print(f"Created email mapping for {len(email_mapping)} users")
    #     client.save_data(email_mapping, 'user_email_mapping.json')
    #     print(f"Saved user email mapping to data/output/user_email_mapping.json")


if __name__ == "__main__":
    main()
