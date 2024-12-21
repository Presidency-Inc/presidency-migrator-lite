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
        self.current_mode = None
        self.current_project = None
        self.current_suite = None

    def get_project_by_id(self, project_id):
        return next((project for project in self.migration_projects if project['source_project_id'] == project_id), None)

    def projects_counter(self):
        return len(self.migration_projects)

    def get_project_assignee(self, project_id):
        project = self.get_project_by_id(project_id)
        return project['assignee']

    # New methods for scope management
    def get_project_scope(self, source_project_id):
        """Get project scope for project mode extraction"""
        project = next((p for p in self.migration_projects 
                       if p['source_project_id'] == source_project_id 
                       and p['extraction_mode'] == 'project'), None)
        
        if not project:
            raise ValueError(f"Project {source_project_id} not found or not in project mode")
            
        return {
            'source_project_id': project['source_project_id'],
            'project_target_key': project['project_target_key'],
            'project_target_id': project['project_target_id'],
            'assignee': project['assignee'],
            'folder_path': project['folder_path']
        }

    def get_suite_scope(self, source_project_id, suite_id):
        """Get suite-specific scope for suite mode extraction"""
        project = next((p for p in self.migration_projects 
                       if p['source_project_id'] == source_project_id 
                       and p['extraction_mode'] == 'suite'), None)
        
        if not project:
            raise ValueError(f"Project {source_project_id} not found in migration scope")
            
        suite = next((s for s in project['suites'] if s['suite_id'] == suite_id), None)
        if not suite:
            raise ValueError(f"Suite {suite_id} not found in project {source_project_id}")
            
        return {
            'source_project_id': source_project_id,
            'suite_id': suite_id,
            'project_target_key': suite['project_target_key'],
            'project_target_id': suite['project_target_id'],
            'assignee': suite['assignee'],
            'folder_path': suite['folder_path']
        }

    def update_current_scope(self, source_project_id, suite_id=None):
        """Update current migration state"""
        project = next((p for p in self.migration_projects 
                       if p['source_project_id'] == source_project_id), None)
        
        if not project:
            raise ValueError(f"Project {source_project_id} not found")
            
        self.current_mode = project['extraction_mode']
        self.current_project = project
        
        if suite_id and self.current_mode == 'suite':
            self.current_suite = next((s for s in project['suites'] 
                                     if s['suite_id'] == suite_id), None)
            if not self.current_suite:
                raise ValueError(f"Suite {suite_id} not found in project {source_project_id}")

    def get_current_target_info(self):
        """Get current target information based on mode"""
        if not self.current_project:
            raise ValueError("No active migration context")
            
        if self.current_mode == 'project':
            return {
                'project_target_key': self.current_project['project_target_key'],
                'project_target_id': self.current_project['project_target_id'],
                'assignee': self.current_project['assignee'],
                'folder_path': self.current_project['folder_path']
            }
        elif self.current_mode == 'suite' and self.current_suite:
            return {
                'project_target_key': self.current_suite['project_target_key'],
                'project_target_id': self.current_suite['project_target_id'],
                'assignee': self.current_suite['assignee'],
                'folder_path': self.current_suite['folder_path']
            }
        else:
            raise ValueError("Invalid state: suite mode requires active suite")
            
def main():
    try:
        # Example usage
        client = ScopeClient()
        
        print("Projects to migrate:")
        for project in client.migration_projects:
            print(f"ID: {project['source_project_id']}, Name: {project['project_target_id']}, Assignee: {project['assignee']}")
        
            
    except Exception as e:
        print(f"Main process failed: {str(e)}")
        raise

if __name__ == '__main__':
    main()
