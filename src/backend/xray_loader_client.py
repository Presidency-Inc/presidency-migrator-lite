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
import glob

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
        """Import tests with better error handling"""
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
            
            if "already in progress" in response.text:
                raise XrayAPIError(
                    "Import job already in progress",
                    status_code=response.status_code,
                    response=response.text
                )
            
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
                    
                    if status in ['unsuccessful']:
                        logger.error("Import job %s failed with status: %s", job_id, status)
                        if attempt < max_retries - 1:
                            logger.warning("Import job failed, retrying job...")
                            self.retry_import_job(job_id)
                            time.sleep(polling_interval)
                            continue
                        else:
                            raise XrayAPIError("Import job failed after retries", 
                                status_code=400, response=status_data)

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

    def check_for_in_progress_jobs(self):
        """Check if there are any jobs currently in progress"""
        url = f"{self.api_url}/import/test/bulk/status"
        headers = {'Authorization': f'Bearer {self._token}'}
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                jobs = response.json()
                in_progress = [job for job in jobs if job.get('status') == 'in_progress']
                return in_progress
            return []
        except Exception as e:
            logger.error(f"Error checking in-progress jobs: {str(e)}")
            return []


    def get_files_to_process(self, import_folder):
        """
        Determine which files need to be processed based on import_status.json
        Returns a list of files that need to be imported
        """
        status_file = os.path.join(os.path.dirname(__file__), 'import_status.json')
        import_files = glob.glob(os.path.join(import_folder, '*.json'))
        
        try:
            with open(status_file, encoding='utf-8') as f:
                import_jobs = json.load(f)
                
            # Get files that need processing (failed, unsuccessful, or not in status file)
            files_to_process = []
            for file_path in import_files:
                filename = os.path.basename(file_path)
                job_status = import_jobs.get(filename, {})
                
                if (
                    filename not in import_jobs or  # New file
                    'error' in job_status or  # Failed with error
                    job_status.get('status') in ['failed', 'unsuccessful']  # Failed status
                ):
                    files_to_process.append(file_path)
                    logger.info(f"File {filename} needs processing: " + (
                        "New file" if filename not in import_jobs
                        else f"Previous status: {job_status.get('status', 'error')}"
                    ))
                else:
                    logger.info(f"Skipping {filename} - already processed successfully")
                    
            return files_to_process
            
        except FileNotFoundError:
            logger.info("No previous import status found - processing all files")
            return import_files

    def process_import_files(self, import_folder):
        """
        Process JSON files in the import folder that need importing
        Returns a dictionary mapping filenames to their job IDs and status
        """
        # Get files that need processing
        files_to_process = self.get_files_to_process(import_folder)
        
        if not files_to_process:
            logger.info("No files need processing")
            return {}
        
        # Load existing import status if available
        status_file = os.path.join(os.path.dirname(__file__), 'import_status.json')
        try:
            with open(status_file, encoding='utf-8') as f:
                import_jobs = json.load(f)
        except FileNotFoundError:
            import_jobs = {}
        
        for file_path in files_to_process:
            filename = os.path.basename(file_path)
            logger.info(f"Processing file: {filename}")
            
            try:
                # Wait for any in-progress jobs to complete
                if not self.wait_for_in_progress_jobs():
                    raise XrayAPIError("Timeout waiting for in-progress jobs to complete")

                # Read and import the test cases
                with open(file_path, encoding='utf-8') as f:
                    mapped_tests = json.load(f)
                
                # Create import job with retries
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        job_id = self.import_tests(mapped_tests)
                        break
                    except XrayAPIError as e:
                        if "already in progress" in str(e) and attempt < max_retries - 1:
                            logger.warning(f"Import job in progress, retrying in 30 seconds...")
                            time.sleep(30)
                            continue
                        raise
                
                if job_id:
                    # Monitor the import status
                    status = self.check_import_status(job_id)
                    
                    # Store results
                    import_jobs[filename] = {
                        'job_id': job_id,
                        'status': status.get('status'),
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Save progress after each file
                    self._save_import_status(import_jobs)
                    
                    logger.info(f"Import job for {filename}: ID={job_id}, Status={status.get('status')}")
                
            except Exception as e:
                logger.error(f"Error processing {filename}: {str(e)}")
                import_jobs[filename] = {
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                self._save_import_status(import_jobs)
        
        return import_jobs

    def _save_import_status(self, import_jobs):
        """Save import job status to a JSON file"""
        status_file = os.path.join(os.path.dirname(__file__), 'import_status.json')
        try:
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(import_jobs, f, indent=2)
            logger.debug(f"Import status saved to {status_file}")
        except Exception as e:
            logger.error(f"Error saving import status: {str(e)}")

    def retry_failed_imports(self):
        """Retry any failed import jobs"""
        status_file = os.path.join(os.path.dirname(__file__), 'import_status.json')
        
        try:
            with open(status_file, encoding='utf-8') as f:
                import_jobs = json.load(f)
        except FileNotFoundError:
            logger.warning("No previous import status found")
            return {}
        
        failed_jobs = {
            filename: data for filename, data in import_jobs.items()
            if data.get('status') in ['failed', 'partially_successful'] or 'error' in data
        }
        
        if not failed_jobs:
            logger.info("No failed jobs to retry")
            return import_jobs
        
        logger.info(f"Retrying {len(failed_jobs)} failed imports")
        
        import_folder = os.path.join(os.path.dirname(__file__), 'importFiles')
        for filename in failed_jobs:
            file_path = os.path.join(import_folder, filename)
            
            if not os.path.exists(file_path):
                logger.error(f"File not found for retry: {filename}")
                continue
                
            try:
                with open(file_path, encoding='utf-8') as f:
                    mapped_tests = json.load(f)
                
                job_id = self.import_tests(mapped_tests)
                status = self.check_import_status(job_id)
                
                import_jobs[filename] = {
                    'job_id': job_id,
                    'status': status.get('status'),
                    'timestamp': datetime.now().isoformat(),
                    'retry': True
                }
                
                self._save_import_status(import_jobs)
                
            except Exception as e:
                logger.error(f"Error retrying {filename}: {str(e)}")
                import_jobs[filename]['error'] = str(e)
                import_jobs[filename]['timestamp'] = datetime.now().isoformat()
                self._save_import_status(import_jobs)
        
        return import_jobs

def main():
    client = XrayClient()
    try:
        import_folder = os.path.join(os.path.dirname(__file__), 'importFiles')
                
        import_jobs = client.process_import_files(import_folder)
        
        if not import_jobs:
            logger.info("No files were processed - all files are up to date")
            return
        
        # Log summary of results
        logger.info("Import Summary:")
        for filename, job_data in import_jobs.items():
            status = job_data.get('status', 'ERROR')
            job_id = job_data.get('job_id', 'N/A')
            logger.info(f"{filename}: JobID={job_id}, Status={status}")
        
        # Handle retries
        failed_jobs = {k: v for k, v in import_jobs.items() 
                      if v.get('status') in ['failed'] 
                      or 'error' in v}
        
        if failed_jobs:
            logger.info(f"Failed imports: {len(failed_jobs)}")
            retry = input("Would you like to retry failed imports? (y/n): ").lower()
            if retry == 'y':
                retry_results = client.retry_failed_imports()
                logger.info("Retry Summary:")
                for filename, job_data in retry_results.items():
                    if job_data.get('retry'):
                        status = job_data.get('status', 'ERROR')
                        job_id = job_data.get('job_id', 'N/A')
                        logger.info(f"Retry {filename}: JobID={job_id}, Status={status}")
    
    except Exception as e:
        logger.error(f"Import process failed: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    main()
