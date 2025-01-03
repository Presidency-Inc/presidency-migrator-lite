from hmac import new
from math import e, log
import os
import requests
from flask import Flask, jsonify
from datetime import datetime
from bs4 import BeautifulSoup
from collections import defaultdict
import re
import json

app = Flask(__name__)

with open(os.path.join(os.path.dirname(__file__), 'results.json'), encoding='utf-8') as f:
    content = json.load(f)

def group_results(input_data):
    try:
        grouped_content = []
        processed_projects = {}

        for item in input_data.get("content"):
            if item is None:
                print("Item is None, ignoring...")
                continue

            if "project_id" not in item:
                grouped_content.append(item)
                continue

            project_id = item["project_id"]
            suite_id = item["suite_id"]
            target_project_key = item["target_project_key"]

            # Create a unique key for each project+target combination
            project_key = f"{project_id}_{target_project_key}"

            # Check if the project+target combination already exists
            if project_key in processed_projects:
                current_project = processed_projects[project_key]
                
                # If current project has "all_suites" and new item has different target_project_key
                if current_project["suite_id"] == "all_suites" and suite_id != "all_suites":
                    # Create a new entry for different target_project_key
                    if suite_id != "all_suites":
                        suite_name = item["suite_name"]
                        suite_url = item["url"]
                        new_item = item.copy()
                        del new_item["suite_name"]
                        del new_item["url"]
                        new_item["suite_id"] = [{
                            "id": suite_id,
                            "name": suite_name,
                            "target_project_key": target_project_key,
                            "url": suite_url
                        }]
                        processed_projects[project_key] = new_item
                
                # If current item is not "all_suites", append to suite list
                elif suite_id != "all_suites":
                    suite_name = item["suite_name"]
                    suite_url = item["url"]
                    
                    if isinstance(current_project["suite_id"], list):
                        # Check if suite_id already exists
                        if not any(s["id"] == suite_id for s in current_project["suite_id"]):
                            current_project["suite_id"].append({
                                "id": suite_id,
                                "name": suite_name,
                                "target_project_key": target_project_key,
                                "url": suite_url
                            })
                    else:
                        current_project["suite_id"] = [{
                            "id": suite_id,
                            "name": suite_name,
                            "target_project_key": target_project_key,
                            "url": suite_url
                        }]

            else:
                # Add new project
                if suite_id == "all_suites":
                    processed_projects[project_key] = item
                else:
                    suite_name = item["suite_name"]
                    suite_url = item["url"]
                    new_item = item.copy()
                    del new_item["suite_name"]
                    del new_item["url"]
                    
                    new_item["suite_id"] = [{
                        "id": suite_id,
                        "name": suite_name,
                        "target_project_key": target_project_key,
                        "url": suite_url
                    }]
                    processed_projects[project_key] = new_item

        # Add processed projects to grouped content
        grouped_content.extend(processed_projects.values())
        return grouped_content

    except requests.RequestException as e:
        print(f"Error grouping content: {e}")
        return None

def main():
    resultGroupedContent = group_results(content)

    if resultGroupedContent:
        with open('grouped.json', 'w') as f:
            json.dump({"message": "Extraction done successfully", "content": resultGroupedContent}, f, indent=4)
    else:
        print(f"Error: Extraction failed.")

if __name__ == '__main__':
    main()