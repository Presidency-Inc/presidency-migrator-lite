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
from scope_client import ScopeClient
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

    def import_tests(self, tests):
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

    def check_import_status(self, job_id, polling_interval=5, max_retries=2):
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

def main():
    client = XrayClient()
    try: 
        # load files from importFiles folder using
        importFiles_folder = os.path.join(os.path.dirname(__file__), 'importFiles', 'test_cases_3.json')
        with open(importFiles_folder, encoding='utf-8') as f:
            mapped_tests = json.load(f)

        job_id = client.import_tests(mapped_tests)

        # Monitor import status
        final_status = client.check_import_status(job_id)
        logger.info(f"Import completed with status: {final_status.get('status')}")
        
    except Exception as e:
        logger.error(f"Import process failed: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    main()
