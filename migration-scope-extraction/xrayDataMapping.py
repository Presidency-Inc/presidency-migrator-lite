
from math import log
import requests
from flask import Flask
from fuzzywuzzy import fuzz

import json

app = Flask(__name__)

with open('ExcelMigratedTable.json') as f:
    excel_migrated_data = json.load(f)

with open('XRayProjectData.json') as f:
    xray_project_data = json.load(f)

with open('grouped.json') as f:
    grouped_content_data = json.load(f)

class MigrationScopeClient:
    def __init__(self):

        # Validate if data is present
        if not excel_migrated_data or not xray_project_data or not grouped_content_data:
            print("Error: One of the input files is empty")
            return
        self.excel_migrated_data = excel_migrated_data
        self.xray_project_data = xray_project_data
        self.grouped_content_data = grouped_content_data
        self.MATCH_THRESHOLD = 90

        self.final_migration_scope = []

    def find_excel_extracted_item_by_name(self, name):
        for index, item in enumerate(self.excel_migrated_data):
            if item.get("Test Suite Name") == name:
                return index, item
        return None, None

    def find_excel_extracted_item_by_url(self, url):
        print("finding from (", len(self.excel_migrated_data), ") left items")
        
        for index, item in enumerate(self.excel_migrated_data):
            if item.get("Suite ID").get("url") == url:
                print("@@ Excel extraced item with project KEY: ", item.get("JIRA Project"))
                
                del self.excel_migrated_data[index]
                return item
        return None
    
    def extend_final_migration_scope(self, object):
        self.final_migration_scope.extend([object])

    def match_validation(self, XRayValue, ExtractedDataValue ):
        partial_ratio = fuzz.partial_ratio(XRayValue.lower(), ExtractedDataValue.lower())
        
        # best_ratio = max(partial_ratio)        
        if partial_ratio >= self.MATCH_THRESHOLD:
            print("Best ratio: ", partial_ratio)
            return True

        return False

    def get_xray_data(self, ExtractedDataItem):        
        # Early return if ExtractedDataItem is empty or missing required fields
        if not ExtractedDataItem:
            print("Error: ExtractedDataItem is empty")
            return None
            
        print("ExtractedDataItem available ")
        jira_project = ExtractedDataItem.get("JIRA Project", "").strip()
        
        # If both matching fields are empty, return empty list
        if not jira_project:
            return None
        
        # Iterate through XRayData entries
        for xray_entry in self.xray_project_data:
            if not isinstance(xray_entry, dict):
                continue
                
            project_name = xray_entry.get("projectName", "").strip()
            project_id = xray_entry.get("projectId", "").strip()
            project_key = xray_entry.get("projectKey", "").strip()
            
            # Check for project name match (case-insensitive)
            if self.match_validation(project_name, jira_project) or self.match_validation(project_key, jira_project):

                print("-" * 50)
                print("Match found for project name or key")
                print(f"project_key: {project_key}, jira_project: {jira_project}")
                print(f"project_name: {project_name}, jira_project: {jira_project}")
                print("-" * 50)
                return {
                    "project_name": project_name,
                    "project_id": project_id,
                    "project_key": project_key
                }
            # else:
            #     print("-" * 50)
            #     print("No match found for project name or key")
            #     print(f"project_key: {project_key}, jira_project: {jira_project}")
            #     print(f"project_name: {project_name}, jira_project: {jira_project}")
            #     print("-" * 50)

def map_migration_scoupe():
    client = MigrationScopeClient()

    try:
        # Process the content
        grouped_content_array = client.grouped_content_data.get("content", [])
        
        print("Length of grouped_content_data.get('content'): ", len(grouped_content_array))
        for project_item in grouped_content_array:
            if project_item.get("project_id"):
                project_name = project_item.get("project_name")
                project_id = project_item.get("project_id")
                project_url = project_item.get("url")
                extraction_mode = project_item.get("extraction_mode")
                extraction_suite_content = project_item.get("suite_id")

                if extraction_mode == "project": # Getting all suites inside a project
                    excel_item = client.find_excel_extracted_item_by_url(project_item.get("url"))
            
                    if excel_item:
                        xray_project_data = client.get_xray_data(excel_item)

                        xray_project_target_name = None
                        xray_project_target_key = None
                        xray_project_target_id = None

                        if xray_project_data:
                            xray_project_target_name = xray_project_data.get("project_name")
                            xray_project_target_key = xray_project_data.get("project_key")
                            xray_project_target_id = xray_project_data.get("project_id")
                        else:
                            xray_project_target_name = excel_item.get("Test Suite Name")
                            xray_project_target_key = None
                            xray_project_target_id = None
                                         
                        project_final_object = {
                            "extraction_mode": extraction_mode,
                            "source_project_name": project_name,
                            "source_project_id": project_id,
                            "source_project_url": project_url,
                            "project_target_name": xray_project_target_name,
                            "project_target_key": xray_project_target_key,
                            "project_target_id": xray_project_target_id, # Placeholder
                            "assignee": excel_item.get("QA Lead First").get("Last Name"),
                            "suites": "fetch_all_suites",
                            "folder_path": excel_item.get("JIRA Folder structure"),
                        }

                        client.extend_final_migration_scope(project_final_object)
                    else:
                        print(f"Error: Excel item not found for project: {project_item.get('project_name')}")
                elif extraction_mode == "suite": # Getting specific suite list in a project
                    suites_final_data = []
                    project_final_object = {
                        "extraction_mode": extraction_mode,
                        "source_project_name": project_name,
                        "source_project_id": project_id
                    }

                    if not isinstance(extraction_suite_content, list):
                        print(f"Error: extraction_suite_content is not of type list for project: {project_item.get('project_name')}")
                        continue

                    for suite_item in extraction_suite_content:
                        excel_item = client.find_excel_extracted_item_by_url(suite_item.get("url"))
                        if excel_item:
                            xray_project_data = client.get_xray_data(excel_item)

                            xray_project_target_name = None
                            xray_project_target_key = None
                            xray_project_target_id = None

                            if xray_project_data:
                                xray_project_target_name = xray_project_data.get("project_name")
                                xray_project_target_key = xray_project_data.get("project_key")
                                xray_project_target_id = xray_project_data.get("project_id")
                            else:
                                xray_project_target_name = excel_item.get("Test Suite Name")
                                xray_project_target_key = None
                                xray_project_target_id = None

                            suites_final_data.append({
                                "suite_name": suite_item.get("name"),
                                "suite_id": suite_item.get("id"),
                                "suite_url": suite_item.get("url"),
                                "project_target_name": xray_project_target_name,
                                "project_target_key": xray_project_target_key,
                                "project_target_id": xray_project_target_id,
                                "assignee": excel_item.get("QA Lead First").get("Last Name"),
                                "folder_path": excel_item.get("JIRA Folder structure"),
                            })

                            project_final_object["suites"] = suites_final_data
                        else:
                            print(f"Error: Excel item not found for suite: {suite_item.get('name')}")

                    client.extend_final_migration_scope(project_final_object)
                else:
                    print("Invalid extraction mode: ", extraction_mode)
            
            else:
                print("Invalid project_item format: ", project_item)
                
        return client.final_migration_scope

        # Write result to output file
    except requests.RequestException as e:
        print(f"Error grouping content: {e}")
        return None

def main():
    resultMigrationScoupeData = map_migration_scoupe()

    if resultMigrationScoupeData:
        with open('final_migration_scope.json', 'w') as f:
            json.dump(resultMigrationScoupeData, f, indent=4)
    else:
        print(f"Error: Extraction failed.")

if __name__ == '__main__':
    main()
