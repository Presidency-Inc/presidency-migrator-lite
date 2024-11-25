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

    def check_import_status(self, job_id, polling_interval=5, max_retries=60):
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
        
        # Sort sections by depth to create parent folders first
        sorted_sections = sorted(sections_data['sections'], key=lambda x: x['depth'])
        
        for section in sorted_sections:
            folder_path = self.build_folder_path(section, sections_data)
            if folder_path and folder_path not in created_folders:
                if self.create_test_repository_folder(folder_path, project_key):
                    created_folders.add(folder_path)
                else:
                    logger.warning(f"Failed to create folder: {folder_path}")
        
        # Verify the folder structure
        self.verify_folder_structure(project_key)

    def build_folder_path(self, section, sections_data):
        """Build the full folder path for a section"""
        path_parts = ['TestRail']
        current = section
        
        while current:
            path_parts.insert(1, current['name'])
            if current.get('parent_id'):
                parent_id = str(current['parent_id'])
                current = next((s for s in sections_data['sections'] if str(s['id']) == parent_id), None)
            else:
                break
        
        return '/'.join(path_parts)

    def create_precondition(self, precondition_data):
        """Create a precondition in Xray using GraphQL"""
        try:
            client = self._get_gql_client()
            
            create_precondition_mutation = gql("""
                mutation createPrecondition(
                    $preconditionType: UpdatePreconditionTypeInput!,
                    $definition: String!,
                    $folderPath: String!,
                    $jira: JSON!
                ) {
                    createPrecondition(
                        preconditionType: $preconditionType,
                        definition: $definition,
                        folderPath: $folderPath,
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
            
            variables = {
                "preconditionType": {"name": "Generic"},
                "definition": precondition_data.get('custom_preconds', ''),
                "folderPath": f"TestRail/{precondition_data.get('section_path', '')}",
                "jira": {
                    "fields": {
                        "project": {"key": os.getenv('JIRA_PROJECT_KEY')},
                        "summary": f"Precondition for: {precondition_data.get('title', '')}",
                        "issuetype": {"name": "Precondition"}
                    }
                }
            }
            
            logger.debug(f"Creating precondition for test: {precondition_data.get('title')}")
            result = client.execute(create_precondition_mutation, variable_values=variables)
            logger.debug(f"Precondition creation result: {json.dumps(result, indent=2)}")
            
            if result.get('createPrecondition', {}).get('precondition'):
                return result['createPrecondition']['precondition']['issueId']
            return None
            
        except Exception as e:
            logger.error(f"Error creating precondition: {str(e)}")
            return None

    def link_precondition_to_test(self, test_issue_id, precondition_issue_id):
        """Link a precondition to a test using GraphQL"""
        try:
            client = self._get_gql_client()
            
            add_precondition_mutation = gql("""
                mutation addPreconditionsToTest(
                    $issueId: String!,
                    $preconditionIssueIds: [String]!
                ) {
                    addPreconditionsToTest(
                        issueId: $issueId,
                        preconditionIssueIds: $preconditionIssueIds
                    ) {
                        addedPreconditions
                        warning
                    }
                }
            """)
            
            variables = {
                "issueId": test_issue_id,
                "preconditionIssueIds": [precondition_issue_id]
            }
            
            logger.debug(f"Linking precondition {precondition_issue_id} to test {test_issue_id}")
            result = client.execute(add_precondition_mutation, variable_values=variables)
            logger.debug(f"Precondition linking result: {json.dumps(result, indent=2)}")
            
            return bool(result.get('addPreconditionsToTest', {}).get('addedPreconditions'))
            
        except Exception as e:
            logger.error(f"Error linking precondition to test: {str(e)}")
            return False

    def process_preconditions(self, test_cases):
        """Process preconditions for all test cases"""
        try:
            precondition_mapping = {}  # TestRail ID -> Xray Issue ID
            
            for test in test_cases:
                if test.get('is_deleted') or not test.get('custom_preconds'):
                    continue
                    
                precondition_id = self.create_precondition(test)
                if precondition_id:
                    precondition_mapping[test['id']] = precondition_id
                    logger.info(f"Created precondition for test {test['id']}")
            
            return precondition_mapping
            
        except Exception as e:
            logger.error(f"Error processing preconditions: {str(e)}")
            return {}

def build_folder_path(section_id, sections_data):
    """Build the full folder path from section hierarchy"""
    if not section_id:
        return None
        
    path_parts = []
    current = sections_data.get(str(section_id))
    
    while current:
        path_parts.insert(0, current['name'])
        if current.get('parent_id'):
            current = sections_data.get(str(current['parent_id']))
        else:
            break
            
    return '/'.join(['TestRail'] + path_parts)

def map_test_steps(test_case):
    """Map TestRail test steps to Xray format"""
    if test_case.get('custom_steps_separated'):
        return [{
            'action': step.get('content', ''),
            'data': step.get('additional_info', ''),
            'result': step.get('expected', '')
        } for step in test_case['custom_steps_separated']]
    elif test_case.get('custom_steps'):
        return [{
            'action': test_case['custom_steps'],
            'data': '',
            'result': test_case.get('custom_expected', '')
        }]
    return None

def map_test_case(test_case, field_mapping, sections_data):
    """Map a TestRail test case to Xray format"""
    mapped_test = {
        "fields": {
            #"project": {"key": "${JIRA_PROJECT_KEY}"},
            "project": {"key": "XSP"},
            "issuetype": {"name": "Test"}
        }
    }
    
    # Map test type
    test_type = field_mapping['test_case_type_mapping'].get(str(test_case.get('type_id')), 'Manual')
    mapped_test['testtype'] = test_type
    
    # Map basic fields
    mapped_test['fields']['summary'] = test_case.get('title', '')
    
    # Map priority
    priority_id = str(test_case.get('priority_id', '3'))
    mapped_test['fields']['priority'] = {
        "name": field_mapping['priority_mapping'].get(priority_id, 'Medium')
    }
    
    # Map description/goals
    if test_case.get('custom_goals'):
        mapped_test['fields']['description'] = test_case['custom_goals']
    
    # Build folder path for test repository
    if test_case.get('section_id'):
        folder_path = build_folder_path(test_case['section_id'], sections_data)
        if folder_path:
            mapped_test['xray_test_repository_folder'] = folder_path
    
    # Map test steps based on type
    if test_type == 'Manual':
        steps = []
        if test_case.get('custom_steps'):
            # Handle combined steps format
            steps.extend(parse_steps(test_case['custom_steps'], test_case.get('custom_expected', '')))
        elif test_case.get('custom_steps_separated'):
            # Handle separated steps format
            steps.extend(test_case['custom_steps_separated'])
        
        if steps:
            mapped_test['steps'] = steps
    
    # Map Cucumber/Gherkin scenarios
    elif test_type == 'Cucumber' and test_case.get('custom_testrail_bdd_scenario'):
        mapped_test['gherkin_def'] = test_case['custom_testrail_bdd_scenario']
    
    return mapped_test

def get_xray_test_type(testrail_type_id):
    """Map TestRail type ID to Xray test type"""
    mapping = {
        1: "Manual",
        2: "Generic",  # For automated tests
        3: "Generic",
        4: "Cucumber",
        7: "Manual",
        10: "Generic"
    }
    return mapping.get(str(testrail_type_id), "Manual")

def get_xray_issue_type(test_case):
    """Determine Xray issue type based on test case attributes"""
    if test_case.get('custom_preconds'):
        return "Precondition"
    return "Test"

def validate_test_case(mapped_test):
    """Validate required fields for Xray import"""
    required_fields = {
        'testtype': 'Test Type',
        'fields.summary': 'Summary',
        '__xray_testId': 'Test ID'
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
        
    path_parts = []
    current_section = sections_data.get(str(section_id))
    
    while current_section:
        path_parts.insert(0, current_section['name'])
        parent_id = current_section.get('parent_id')
        current_section = sections_data.get(str(parent_id)) if parent_id else None
    
    return '/'.join(path_parts) if path_parts else None

def import_test_cases(test_cases, sections_data):
    """Import test cases to Xray with proper validation and mapping"""
    client = XrayClient()
    
    # Authenticate first
    client.authenticate()
    
    # First, create all preconditions and store their IDs
    logger.info("Processing preconditions...")
    precondition_mapping = client.process_preconditions(test_cases)
    logger.info(f"Created {len(precondition_mapping)} preconditions")
    
    # Load mapping configuration
    with open('config/field_mapping.json', 'r') as f:
        mapping_config = json.load(f)
    
    # Track which test cases need precondition linking
    test_precondition_pairs = {}  # {test_title: precondition_id}
    
    mapped_tests = []
    for test_case in test_cases:
        try:
            # Map the test case
            mapped_test = map_test_case(test_case, sections_data, mapping_config)
            
            # Add repository path
            repo_path = build_repository_path(test_case, sections_data)
            if repo_path:
                mapped_test['xray_test_repository_folder'] = repo_path
            
            # Store the relationship if this test has a precondition
            if test_case['id'] in precondition_mapping:
                test_precondition_pairs[mapped_test['fields']['summary']] = precondition_mapping[test_case['id']]
            
            # Validate required fields
            validate_test_case(mapped_test)
            
            mapped_tests.append(mapped_test)
            
        except Exception as e:
            logger.error(f"Error mapping test case {test_case.get('id')}: {str(e)}")
            continue
    
    if not mapped_tests:
        raise ValueError("No valid test cases to import")
    
    # Import in batches of 1000 (Xray's limit)
    imported_tests = {}  # {test_title: test_key}
    batch_size = 1000
    for i in range(0, len(mapped_tests), batch_size):
        batch = mapped_tests[i:i + batch_size]
        job_id = client.import_tests(batch)
        
        # Wait for import to complete and get results
        status = client.check_import_status(job_id)
        logger.info(f"Batch {i//batch_size + 1} import status: {status}")
        
        # Get the created test keys from the import result
        if status == 'success':
            result = client.get_import_result(job_id)
            for issue in result.get('issues', []):
                imported_tests[issue['fields']['summary']] = issue['key']
    
    # Link preconditions to their respective tests
    logger.info("Linking preconditions to tests...")
    for test_title, precondition_id in test_precondition_pairs.items():
        if test_title in imported_tests:
            test_key = imported_tests[test_title]
            success = client.link_precondition_to_test(test_key, precondition_id)
            if success:
                logger.info(f"Linked precondition to test: {test_title}")
            else:
                logger.error(f"Failed to link precondition to test: {test_title}")

def main():
    try:
        logger.info("Starting Xray test import process")
        
        # Initialize Xray client
        client = XrayClient()
        
        # Load field mapping configuration
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'field_mapping.json')
        with open(config_path, 'r') as f:
            field_mapping = json.load(f)
            logger.info("Loaded field mapping configuration")
            logger.debug("Field mapping: %s", json.dumps(field_mapping, indent=2))

        # Load sections data
        sections_file = os.path.join(os.path.dirname(__file__), '../../data/output/sections.json')
        with open(sections_file, 'r') as f:
            sections_raw = json.load(f)
            sections_data = {str(section['id']): section for section in sections_raw['sections']}
            logger.info("Loaded sections data")
            
        # Load test cases
        input_file = os.path.join(os.path.dirname(__file__), '../../data/output/test_cases.json')
        with open(input_file, 'r') as f:
            test_cases = json.load(f)
            logger.info(f"Loaded {len(test_cases)} test cases")

        # Map test cases to Xray format
        mapped_tests = []
        for idx, test_case in enumerate(test_cases, 1):
            try:
                mapped_test = map_test_case(test_case, field_mapping, sections_data)
                if mapped_test:
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
            client.create_folder_structure({'sections': sections_raw['sections']}, client.project_id)
        except Exception as e:
            logger.warning(f"Failed to create folder structure: {str(e)}")
            # Continue with import even if folder creation fails
        
        # Import tests
        job_id = client.import_tests(mapped_tests, project_key)
        
        # Monitor import status
        final_status = client.check_import_status(job_id)
        logger.info(f"Import completed with status: {final_status.get('status')}")
        
    except Exception as e:
        logger.error(f"Import process failed: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    main()

