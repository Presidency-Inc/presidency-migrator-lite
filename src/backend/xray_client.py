import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from jira_client import JiraClient
import re

class XrayAPIError(Exception):
    """Custom exception for Xray API errors"""
    def __init__(self, message, status_code=None, response=None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)

def setup_logging():
    """Configure logging with both file and console handlers"""
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'xray_import_{timestamp}.log')
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Setup logger
    logger = logging.getLogger('xray_client')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Initialize logger
logger = setup_logging()

class XrayClient:
    def __init__(self):
        load_dotenv()
        self.client_id = os.getenv('XRAY_CLIENT_ID')
        self.client_secret = os.getenv('XRAY_CLIENT_SECRET')
        self.base_url = os.getenv('XRAY_CLOUD_BASE_URL', 'https://xray.cloud.getxray.app')
        self.api_url = f"{self.base_url}/api/v2"
        self.project_id = os.getenv('JIRA_PROJECT_ID')
        self._token = None
        self._gql_client = None
        
        # Validate environment variables
        missing_vars = []
        if not self.client_id:
            missing_vars.append('XRAY_CLIENT_ID')
        if not self.client_secret:
            missing_vars.append('XRAY_CLIENT_SECRET')
        if not self.base_url:
            missing_vars.append('XRAY_CLOUD_BASE_URL')
        if not self.project_id:
            missing_vars.append('JIRA_PROJECT_ID')
        
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info("XrayClient initialized with base URL: %s", self.api_url)
        # Authenticate immediately upon initialization
        self.authenticate()

    def _get_gql_client(self):
        """Initialize or return existing GraphQL client"""
        if not self._gql_client:
            if not self._token:
                logger.warning("No authentication token found. Authenticating first...")
                self.authenticate()
                
            transport = RequestsHTTPTransport(
                url=f"{self.base_url}/api/v2/graphql",
                headers={
                    'Authorization': f'Bearer {self._token}',
                    'Content-Type': 'application/json',
                }
            )
            self._gql_client = Client(transport=transport, fetch_schema_from_transport=True)
        return self._gql_client

    def authenticate(self):
        """Authenticate with Xray API"""
        try:
            logger.debug("Attempting authentication with Xray API")
            url = f"{self.api_url}/authenticate"
            logger.debug("Authentication URL: %s", url)
            
            response = requests.post(
                url,
                json={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
            )
            
            if response.status_code == 200:
                self._token = response.text.strip('"')
                logger.info("Successfully authenticated with Xray API")
                # Recreate GraphQL client with new token
                self._gql_client = None  # Force recreation of client with new token
                return True
            else:
                logger.error(f"Authentication failed. Status code: {response.status_code}")
                logger.debug(f"Response content: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False

    def import_tests(self, tests, project_key=None):
        """Import tests in bulk to Xray"""
        try:
            # Ensure we have a valid token
            if not self._token:
                logger.warning("No authentication token found. Authenticating first...")
                self.authenticate()

            url = f"{self.api_url}/import/test/bulk"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self._token}'
            }
            
            # Log the request payload
            logger.debug("Import tests request payload: %s", json.dumps(tests, indent=2))
            
            response = requests.post(url, headers=headers, json=tests)
            
            if response.status_code == 200:
                job_id = response.json().get('jobId')
                logger.info("Import job created successfully with ID: %s", job_id)
                return job_id
            
            error_msg = f"Failed to import tests. Status code: {response.status_code}"
            logger.error(error_msg)
            logger.debug("Response content: %s", response.text)
            
            raise XrayAPIError(
                error_msg,
                status_code=response.status_code,
                response=response.text
            )
            
        except requests.exceptions.RequestException as e:
            logger.error("Network error during test import: %s", str(e))
            raise XrayAPIError(f"Network error: {str(e)}")

    def check_import_status(self, job_id, polling_interval=30, max_retries=12):
        """Check the status of an import job with retry logic"""
        if not self._token:
            logger.warning("No authentication token found. Authenticating first...")
            self.authenticate()

        url = f"{self.api_url}/import/test/bulk/{job_id}/status"
        headers = {'Authorization': f'Bearer {self._token}'}
        
        logger.info("Starting to monitor import job: %s", job_id)
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers)
                
                if response.status_code == 200:
                    status_data = response.json()
                    status = status_data.get('status')
                    
                    logger.info("Job %s status: %s", job_id, status)
                    if 'progress' in status_data:
                        for progress_msg in status_data['progress']:
                            logger.debug("Progress: %s", progress_msg)
                    
                    if status in ['successful', 'failed', 'partially_successful']:
                        if status != 'successful':
                            logger.warning("Import completed with status: %s", status)
                            if 'result' in status_data:
                                logger.debug("Import result: %s", 
                                    json.dumps(status_data['result'], indent=2))
                            
                            # Add time estimate updates for successfully created tests
                            if status_data.get('result', {}).get('test_issues'):
                                for test_issue in status_data['result']['test_issues']:
                                    issue_key = test_issue.get('key')
                                    if issue_key:
                                        self.update_time_estimate(issue_key, test_issue.get('originalEstimate'))
                    
                        return status_data
                    
                elif response.status_code == 404:
                    logger.error("Import job not found: %s", job_id)
                    raise XrayAPIError("Import job not found", 
                        status_code=404, response=response.text)
                else:
                    logger.error("Error checking job status. Status code: %d", 
                        response.status_code)
                    logger.debug("Response content: %s", response.text)
            
            except requests.exceptions.RequestException as e:
                logger.error("Network error checking job status: %s", str(e))
            
            time.sleep(polling_interval)
        
        raise XrayAPIError(f"Timeout waiting for import job {job_id} to complete")

    def create_test_repository_folder(self, folder_path, project_key=None):
        """Create a test repository folder in Xray using GraphQL"""
        try:
            client = self._get_gql_client()
            
            # Check if folder exists
            check_folder_query = gql("""
                query getFolder($projectId: String!, $path: String!) {
                    getFolder(projectId: $projectId, path: $path) {
                        name
                        path
                        testsCount
                        folders
                    }
                }
            """)
            
            variables = {
                "projectId": self.project_id,
                "path": folder_path
            }
            
            logger.debug(f"Checking if folder exists: {folder_path}")
            try:
                result = client.execute(check_folder_query, variable_values=variables)
                if result.get('getFolder'):
                    logger.info(f"Folder already exists: {folder_path}")
                    return True
            except Exception as e:
                logger.debug(f"Folder does not exist: {str(e)}")
            
            # Create folder if it doesn't exist
            create_folder_mutation = gql("""
                mutation createFolder($projectId: String!, $path: String!) {
                    createFolder(
                        projectId: $projectId,
                        path: $path
                    ) {
                        folder {
                            name
                            path
                            testsCount
                        }
                        warnings
                    }
                }
            """)
            
            logger.debug(f"Creating folder: {folder_path}")
            result = client.execute(create_folder_mutation, variable_values=variables)
            
            if result.get('createFolder', {}).get('folder'):
                logger.info(f"Successfully created folder: {folder_path}")
                return True
            else:
                logger.error(f"Failed to create folder. Response: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating folder {folder_path}: {str(e)}")
            return False

    def verify_folder_structure(self, project_key):
        """Verify the folder structure in Xray"""
        try:
            if not self._token:
                self.authenticate()
                
            url = f"{self.base_url}/graphql"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self._token}'
            }
            
            query = {
                "query": """
                query {
                    getFolder(projectId: "%s", path: "/") {
                        name
                        path
                        testsCount
                        folders
                    }
                }
                """ % project_key
            }
            
            logger.info("Verifying folder structure")
            logger.debug("GraphQL query: %s", json.dumps(query, indent=2))
            
            response = requests.post(url, headers=headers, json=query)
            if response.status_code == 200:
                result = response.json()
                logger.debug("Folder structure: %s", json.dumps(result, indent=2))
                return True
            return False
                
        except Exception as e:
            logger.error(f"Error verifying folder structure: {str(e)}")
            return False

    def create_folder_structure(self, sections_data, project_key):
        """Create the complete folder structure from sections data"""
        logger.info("Creating folder structure in Xray")
        created_folders = set()
        
        # First, create the project root folder
        root_folder = 'TestRail'
        self.create_test_repository_folder(root_folder, project_key)
        created_folders.add(root_folder)
        
        try:
            # Get unique suite IDs directly from sections array
            suite_ids = {section.get('suite_id') for section in sections_data if section.get('suite_id')}
            
            # Create suite folders first
            for suite_id in suite_ids:
                suite_name = self.get_suite_name(suite_id)
                if suite_name:
                    suite_path = f"{root_folder}/{suite_name}"
                    if suite_path not in created_folders:
                        if self.create_test_repository_folder(suite_path, project_key):
                            created_folders.add(suite_path)
            
            # Sort sections by depth to create parent folders first
            sorted_sections = sorted(sections_data, 
                                key=lambda x: x.get('depth', 0))
            
            # Create section folders
            for section in sorted_sections:
                folder_path = self.build_folder_path(section['id'], sections_data)
                if folder_path and folder_path not in created_folders:
                    # Create each level of the folder hierarchy
                    path_parts = folder_path.split('/')
                    for i in range(2, len(path_parts) + 1):  # Start from 2 to skip root folder
                        partial_path = '/'.join(path_parts[:i])
                        if partial_path not in created_folders:
                            if self.create_test_repository_folder(partial_path, project_key):
                                created_folders.add(partial_path)
                            else:
                                logger.warning(f"Failed to create folder: {partial_path}")
            
            # Verify the folder structure
            return self.verify_folder_structure(project_key)
            
        except Exception as e:
            logger.error(f"Error creating folder structure: {str(e)}")
            return False

    def build_folder_path(self, section_id, sections_data):
        """Build the full folder path from section hierarchy"""
        if not section_id:
            return None
        
        path_parts = ['TestRail']

        if isinstance(sections_data, dict):
            sections_data = sections_data.get('sections', [])

        # Convert section_id to int if it's a string
        if isinstance(section_id, str):
            section_id = int(section_id)
        
        logger.debug(f"Starting build_folder_path with section_id={section_id}")
        
        try:
            # Find the section in the array
            current = next((section for section in sections_data 
                        if section['id'] == section_id), None)
            
            if not current:
                logger.warning(f"Section {section_id} not found in sections data")
                return None
                
            logger.debug(f"Found section: {current}")
                
            # Collect all parts of the path (we'll reverse them later)
            section_parts = []
            
            # First, get the suite name if available
            if 'suite_id' in current and current['suite_id']:
                suite_name = self.get_suite_name(current['suite_id'])
                if suite_name:
                    path_parts.append(suite_name)
                    logger.debug(f"Appended suite_name: {suite_name}")
                else:
                    logger.warning(f"Suite name for suite_id {current['suite_id']} not found")
            
            # Then build the section hierarchy from current section up to root
            while current:
                section_parts.append(current['name'])
                logger.debug(f"Appended section name: {current['name']}")
                
                parent_id = current.get('parent_id')
                if parent_id:
                    logger.debug(f"Current parent_id: {parent_id}")
                    # Find parent section in the array
                    current = next((section for section in sections_data 
                                    if section['id'] == parent_id), None)
                    if current:
                        logger.debug(f"Found parent section: {current}")
                    else:
                        logger.warning(f"Parent section {parent_id} not found")
                        break
                else:
                    logger.debug("No parent_id found, reached top of hierarchy")
                    break
            
            # Add sections in reverse order (from root to leaf)
            path_parts.extend(reversed(section_parts))
            
            built_path = '/'.join(path_parts)
            logger.debug(f"Built folder path: {built_path}")
            return built_path
            
        except Exception as e:
            logger.error(f"Error building folder path for section {section_id}: {str(e)}")
            return None

    def create_precondition_graphql(self, precondition_data):
        """Create a precondition in Xray using GraphQL"""
        try:
            client = self._get_gql_client()
            create_precondition_mutation = gql("""
                mutation createPrecondition(
                    $preconditionType: UpdatePreconditionTypeInput!,
                    $definition: String!,
                    $jira: JSON!
                ) {
                    createPrecondition(
                        preconditionType: $preconditionType,
                        definition: $definition,
                        jira: $jira
                    ) {
                        precondition {
                            issueId
                            preconditionType {
                                name
                            }
                            definition
                            jira(fields: ["key"])
                        }
                        warnings
                    }
                }
            """)

            precondition_type = precondition_data.get('precondition_type', 'Generic')

            variables = {
                "preconditionType": {"name": precondition_type},
                "definition": precondition_data.get('custom_preconds', ''),
                "jira": {
                    "fields": {
                        "summary": precondition_data.get('title', ''),
                        "project": {"key": os.getenv('JIRA_PROJECT_KEY')}
                    }
                }
            }
            logger.debug(f"Creating precondition for test: {precondition_data.get('title')}")
            result = client.execute(create_precondition_mutation, variable_values=variables)
            logger.debug(f"Precondition creation result: {json.dumps(result, indent=2)}")
            return result
        except Exception as e:
            logger.error(f"Error creating precondition: {str(e)}")
            return None

    def get_suite_name(self, suite_id):
        """Retrieve the suite name given a suite ID"""
        try:
            # Load the suites data
            with open('data/output/suites.json', 'r', encoding='utf-8') as f:
                suites_data = json.load(f)
            
            # Find the suite in the data
            suite = next((suite for suite in suites_data if suite['id'] == suite_id), None)
            
            if suite:
                logger.debug(f"Found suite: {suite}")
                return suite['name']
            else:
                logger.warning(f"Suite {suite_id} not found in suites data")
                return None
                
        except Exception as e:
            logger.error(f"Error getting suite name for suite_id {suite_id}: {str(e)}")
            return None

def parse_steps(steps_separated):
    """Parse test steps and expected results from TestRail format to Xray format.
    Args:
        Args fields:
            custom_steps_separated (list): A list of step dictionaries (with keys content, additional_info and expected)
        
    Returns:
        list: A list of step dictionaries in Xray format
    """
    if not steps_separated:
        return []
        
    steps = []
    for step in steps_separated:
        steps.append({
            'action': step['content'],
            'data': '',
            'result': step['expected']
        })
    
    return steps

def parse_time_estimate(estimate_str):
    """Convert TestRail time estimate (e.g., '8m', '1h 30m') to seconds"""
    if not estimate_str:
        return None
    
    total_seconds = 0
    # Remove any whitespace and convert to lowercase
    estimate_str = estimate_str.lower().strip()
    
    # Handle hours
    if 'h' in estimate_str:
        hours_part = estimate_str.split('h')[0]
        try:
            total_seconds += int(float(hours_part)) * 3600
        except ValueError:
            pass
        estimate_str = estimate_str.split('h')[1]
    
    # Handle minutes
    if 'm' in estimate_str:
        minutes_part = estimate_str.split('m')[0]
        try:
            total_seconds += int(float(minutes_part)) * 60
        except ValueError:
            pass
    
    return total_seconds

def format_bdd_scenarios(scenarios_data):
    """Format BDD scenarios with proper structure and numbering.
    
    Args:
        scenarios_data (list): List of dictionaries containing scenario data
            Each dictionary has a 'content' key with the scenario text
        
    Returns:
        str: Formatted scenario text with proper numbering and structure
    """
    logger.info("Starting BDD scenario formatting")
    logger.debug(f"Input scenarios data: {scenarios_data}")
    
    if not scenarios_data:
        logger.warning("No scenarios data provided")
        return None
    
    formatted_scenarios = []
    scenario_count = 0
    
    try:
        # Process each scenario in the list
        for scenario in scenarios_data:
            scenario_content = scenario.get('content', '')
            logger.debug(f"Processing scenario content:\n{scenario_content}")
            
            if not scenario_content:
                continue
                
            # Split the content into lines and process each line
            lines = [line.strip() for line in scenario_content.split('\n') if line.strip()]
            logger.debug(f"Scenario lines: {lines}")
            
            if lines:
                # Start new scenario
                scenario_count += 1
                if scenario_count > 1:
                    # Add spacing between scenarios
                    formatted_scenarios.append('')
                    formatted_scenarios.append('')
                
                # Add scenario header
                formatted_scenarios.append(f'# Scenario {scenario_count}:')
                formatted_scenarios.append('')  # Empty line after header
                
                # Add each line of the scenario
                formatted_scenarios.extend(lines)
        
        result = '\n'.join(formatted_scenarios).strip()
        logger.info(f"BDD formatting complete, generated {scenario_count} scenarios")
        logger.debug(f"Final formatted output:\n{result}")
        return result
        
    except Exception as e:
        logger.error(f"Error formatting BDD scenarios: {str(e)}")
        return None

def map_test_case(test_case, field_mapping, sections_data):
    """Map a TestRail test case to Xray format"""
    # Create an instance of XrayClient for folder path building
    client = XrayClient()
    jiraClient = JiraClient()

    mapped_test = {
        "fields": {
            "project": {"key": os.getenv('JIRA_PROJECT_KEY')},
            "issuetype": {"name": "Test"}
        }
    }
    
    # Map test type
    test_type = field_mapping['test_case_type_mapping'].get(str(test_case.get('template_id')), 'Manual')
    mapped_test['testtype'] = test_type

    # Map basic fields
    mapped_test['fields']['summary'] = test_case.get('title', '')

    mapped_test['fields']['assignee'] = { "name": os.getenv('JIRA_ASSIGNEE_NAME') }
    mapped_test['fields']['components'] = [{"name": field_mapping['automation_type_mapping'].get(str(test_case.get('type_id')), 'Unknown')}]

    # -------- TestRail URL Reference --------
    tr_url_reference = f"{os.getenv('TESTRAIL_URL')}index.php?/cases/view/{test_case['id']}"
    description = mapped_test['fields'].get('description', '')
    mapped_test['fields']['description'] = description + f"\n*TestRail URL Reference:* {tr_url_reference}\n-----------------\n"
    # -------- TestRail URL Reference --------  


    # ------- Attachments -------
    test_cases_attachment_files_data = []
    with open('data/output/test_cases_attachment_files.json', 'r') as f:
        test_cases_attachment_files = json.load(f)
        test_cases_attachment_files_data = test_cases_attachment_files.copy()
    for item in test_cases_attachment_files:
        if test_case.get('id') == item['case_id']:
            stored_data = item["stored_data"]

            self_link = None
            
            # creating confluence page to attach file and get the link
            page_data = jiraClient.create_page(
                space_key=os.getenv('JIRA_SPACE_KEY'),
                title=f"{test_case.get('id')} - {test_case.get('title')}",
                content="<p>This is a test page created via API</p>"
            )

            download_dir = os.path.join(os.path.dirname(__file__), 'attachmentFiles')            

            if page_data:
                for data_item in stored_data:
                    full_file_path = os.path.join(download_dir, data_item['stored_file_name'])
                    if not os.path.exists(full_file_path):
                        logger.warning(f"File not found: {full_file_path}")
                        continue

                    attachment_data = jiraClient.attach_file(
                        content_id=page_data['id'],
                        file_path=full_file_path,
                        comment=f"Attachment in {data_item.get('field')}"
                    )
                # self_link = f"{os.getenv('JIRA_URL')}/wiki{attachment_data['results'][0]['_links']['webui']}"
                self_link = f"{os.getenv('JIRA_URL')}/wiki/pages/viewpageattachments.action?pageId={page_data['id']}"

            description = mapped_test['fields'].get('description', '')
            mapped_test['fields']['description'] = description + f"*Attachment Files Link:* {self_link}\n" + '\n-----------------\n'
            test_cases_attachment_files_data.remove(item)
            break
    

    # Add time tracking directly in fields object according to Xray support's structure
    if test_case.get('estimate'):
        mapped_test['fields']['timetracking'] = {
            "originalEstimate": test_case['estimate'],
            "remainingEstimate": test_case['estimate']
        }
        logger.info(f"Setting time estimate for test case {test_case.get('id')}: {test_case['estimate']}")
    

    precond_data = {}

    # -------- PRECONDITIONS --------
    if 'custom_preconds' in test_case and test_case['custom_preconds'] is not None:
        description = mapped_test['fields'].get('description', '')
        preconditions = test_case.get('custom_preconds', '')
        if preconditions.strip():  # Check if custom_preconds is not just whitespace
            uPrecondsDefinition = '*Preconditions:* \n' + preconditions
            mapped_test['fields']['description'] = description + uPrecondsDefinition + '\n-----------------\n'
    # -------- PRECONDITIONS --------

    
    # Map priority with enhanced debug logging
    priority_id = str(test_case.get('priority_id', '3'))
    original_priority = test_case.get('priority', 'Unknown')
    mapped_priority = field_mapping['priority_mapping'].get(priority_id, 'Low')
    
    logger.info(f"""Priority Mapping for Test Case {test_case.get('id')} - "{test_case.get('title')}":
        TestRail Priority ID: {priority_id}
        TestRail Priority Name: {original_priority}
        Mapped to Xray Priority: {mapped_priority}
    """)
    
    mapped_test['fields']['priority'] = {
        "name": mapped_priority
    }
    
    # Build folder path for test repository
    if test_case.get('section_id'):
        try:
            # Convert section_id to int if it's a string
            section_id = int(test_case['section_id']) if isinstance(test_case['section_id'], str) else test_case['section_id']
            folder_path = client.build_folder_path(section_id, sections_data)
            if folder_path:
                mapped_test['xray_test_repository_folder'] = folder_path
                logger.debug(f"Set folder path for test case {test_case.get('id')}: {folder_path}")
            else:
                logger.warning(f"Could not build folder path for test case {test_case.get('id')} with section_id {section_id}")
        except Exception as e:
            logger.error(f"Error building folder path for test case {test_case.get('id')}: {str(e)}")
            logger.debug(f"Section ID: {test_case.get('section_id')}, Type: {type(test_case.get('section_id'))}")
            logger.debug(f"Sections data sample: {str(sections_data[:1])}")
    
    # Map test steps based on type
    if test_type == 'Manual':
        steps = []
        if test_case.get('custom_steps_separated'):
            steps.extend(parse_steps(test_case['custom_steps_separated']))
        
        if steps:
            mapped_test['steps'] = steps
    elif test_type == 'Generic':
        stepsString = test_case.get('custom_steps') or ''
        uStepsDefinition = '*Steps:* \n'+stepsString if stepsString else ''
        expectedResultsString = test_case.get('custom_expected', '') or ''
        uExpectedResultsDefinition = '*Expected Results:* \n'+expectedResultsString if expectedResultsString else ''
        
        description = mapped_test['fields'].get('description', '') or ''
        if uStepsDefinition:
            description += uStepsDefinition + '\n-----------------\n'
        if uExpectedResultsDefinition:
            description += uExpectedResultsDefinition + '\n-----------------\n'

        mapped_test['fields']['description'] = description
    
    elif test_type == 'Cucumber':
        # Handle BDD/Cucumber scenarios
        logger.info(f"Processing Cucumber test case: {test_case.get('id')} - {test_case.get('title')}")
        
        bdd_scenario = json.loads(test_case.get('custom_testrail_bdd_scenario')) if test_case.get('custom_testrail_bdd_scenario') else None
        if bdd_scenario:
            logger.debug(f"Found BDD scenario content:\n{bdd_scenario}")
            formatted_scenarios = format_bdd_scenarios(bdd_scenario)
            
            if formatted_scenarios:
                mapped_test['gherkin_def'] = formatted_scenarios
                logger.info(f"Successfully mapped BDD scenarios for test case {test_case.get('id')}")
                logger.debug(f"Mapped scenarios:\n{formatted_scenarios}")
            else:
                logger.warning(f"No formatted scenarios generated for test case {test_case.get('id')}")
        else:
            logger.warning(f"No BDD scenario content found for Cucumber test case {test_case.get('id')}")
        
        # Log the complete mapped test case
        logger.debug(f"Complete mapped test case with BDD scenario:\n{json.dumps(mapped_test, indent=2)}")
    
    elif test_type == 'Exploratory':
        # Handle Exploratory test cases
        logger.info(f"Processing Exploratory test case: {test_case.get('id')} - {test_case.get('title')}")

        missionString = test_case.get('custom_mission') or ''
        goalsString = test_case.get('custom_goals') or ''
        
        uMissionDefinition = '*Mission:* '+missionString+'\n' if missionString else ''
        uGoalsDefinition = '*Goals:* '+goalsString+'\n' if goalsString else ''
        
        mapped_test['unstructured_def'] = uMissionDefinition + uGoalsDefinition

    pattern = r'!\[\]\(.*?\)'
    description = re.sub(pattern, '', mapped_test['fields']['description'])

    mapped_test['fields']['description'] = description

    references = test_case.get('refs') or ''
    if references:
        references_list = references.split(',')
        references_list = [f"({jiraClient.base_reference_url}/{ref})" for ref in references_list]
        uReferences = '*References:* \n' + ', '.join(references_list) + '\n' if references else ''
        mapped_test['fields']['description'] = description + uReferences + '\n-----------------\n'

    # Log the mapped test case for debugging
    logger.debug(f"Mapped test case {test_case.get('id')} with time tracking: {json.dumps(mapped_test, indent=2)}")
    
    return mapped_test

def get_xray_issue_type(test_case):
    """Determine Xray issue type based on test case attributes"""
    if test_case.get('custom_preconds'):
        return "Precondition"
    return "Test"

def get_nested_value(obj, path):
    """Get a value from a nested dictionary using dot notation.
    
    Args:
        obj (dict): The dictionary to search in
        path (str): The path to the value using dot notation (e.g., 'fields.summary')
    
    Returns:
        The value if found, None otherwise
    """
    try:
        parts = path.split('.')
        current = obj
        for part in parts:
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current
    except Exception:
        return None

def validate_test_case(mapped_test):
    """Validate required fields for Xray import"""
    required_fields = {
        'testtype': 'Test Type',
        'fields.summary': 'Summary'
    }
    
    missing_fields = []
    for field, name in required_fields.items():
        if not get_nested_value(mapped_test, field):
            missing_fields.append(name)
    
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

def build_repository_path(test_case, sections_data):
    """Build Xray test repository folder path from TestRail section"""
    section_id = test_case.get('section_id')
    if not section_id:
        return None
        
    # Collect sections from leaf to root
    sections = []
    current_section = sections_data.get(str(section_id))
    
    while current_section:
        sections.append(current_section['name'])
        parent_id = current_section.get('parent_id')
        current_section = sections_data.get(str(parent_id)) if parent_id else None
    
    # Build path from root to leaf
    path_parts = ['TestRail'] + sections[::-1]  # Reverse the sections list
    return '/'.join(path_parts) if path_parts else None

def main():
    try:
        logger.info("Starting Xray test import process")
        
        # Initialize Xray client
        client = XrayClient()
        
        # Load field mapping configuration
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'field_mapping.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            field_mapping = json.load(f)
            logger.info("Loaded field mapping configuration")
            logger.debug("Field mapping: %s", json.dumps(field_mapping, indent=2))

        # Load sections data - keep as array
        sections_file = os.path.join(os.path.dirname(__file__), '../../data/output/sections.json')
        with open(sections_file, 'r', encoding='utf-8') as f:
            sections_data = json.load(f)  # Keep as array, don't convert to dict
            logger.info("Loaded sections data")
            
        # Load test cases
        input_file = os.path.join(os.path.dirname(__file__), '../../data/output/test_cases.json')
        with open(input_file, 'r', encoding='utf-8') as f:
            test_cases = json.load(f)
            logger.info(f"Loaded {len(test_cases)} test cases")

        # Map test cases to Xray format
        mapped_tests = []
        for idx, test_case in enumerate(test_cases, 1):
            try:
                # Map the test case
                mapped_test = map_test_case(test_case, field_mapping, sections_data)
                
                # Add repository path using class method
                if test_case.get('section_id'):
                    folder_path = client.build_folder_path(test_case['section_id'], sections_data)
                    if folder_path:
                        mapped_test['xray_test_repository_folder'] = folder_path
                
                # Validate required fields
                validate_test_case(mapped_test)
                
                mapped_tests.append(mapped_test)
                
            except Exception as e:
                logger.error(f"Error mapping test case {idx}: {str(e)}")
                continue

        # Get project key from environment
        project_key = os.getenv('JIRA_PROJECT_KEY')
        logger.info(f"Using JIRA project key: {project_key}")

        if not mapped_tests:
            logger.error("No test cases were successfully mapped")
            return

        # Create folder structure before import
        try:
            logger.info("Creating folder structure in Xray")
            client.create_folder_structure(sections_data, client.project_id)  # Pass array directly
        except Exception as e:
            logger.warning(f"Failed to create folder structure: {str(e)}")
            # Continue with import even if folder creation fails
        
        # Import tests
        job_id = client.import_tests(mapped_tests, project_key)
        # logger.info(f"Import job created with ID: {job_id}")

        # Monitor import status
        final_status = client.check_import_status(job_id)
        logger.info(f"Import completed with status: {final_status.get('status')}")
        
    except Exception as e:
        logger.error(f"Import process failed: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    main()
