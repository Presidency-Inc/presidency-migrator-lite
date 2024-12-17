import os
import json
import requests
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from dotenv import load_dotenv
import mimetypes
import base64

class ScopeClient:
    def __init__(self):
        load_dotenv()
        # Load list of projects to migrate
        input_file = os.path.join(os.path.dirname(__file__), './config/migration_scope.json')
        with open(input_file, 'r', encoding='utf-8') as f:
            projects_to_migrate = json.load(f)
            print(f"Loaded {len(projects_to_migrate)} test cases")

        self.migration_projects = projects_to_migrate or []

    def get_project_by_id(self, project_id):
        return next((project for project in self.migration_projects if project['sourceProjectId'] == project_id), None)

    def projects_counter(self):
        return len(self.migration_projects)

    def get_project_assignee(self, project_id):
        project = self.get_project_by_id(project_id)
        return project['assignee']

def main():
    try:
        # Example usage
        client = ScopeClient()
        
        print("Projects to migrate:")
        for project in client.migration_projects:
            print(f"ID: {project['sourceProjectId']}, Name: {project['targetProjectKey']}, Assignee: {project['assignee']}")
        
            
    except Exception as e:
        print(f"Main process failed: {str(e)}")
        raise

if __name__ == '__main__':
    main()
