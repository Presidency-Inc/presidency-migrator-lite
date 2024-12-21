from hmac import new
from math import log
import os
import requests
from flask import Flask, jsonify
from datetime import datetime
from bs4 import BeautifulSoup
from collections import defaultdict
import re
import json

app = Flask(__name__)

with open('results.json') as f:
    content = json.load(f)

def group_results(input_data):
    try:
        # Process the content
        grouped_content = []
        processed_projects = {}

        for item in input_data.get("content"):
            # Handle unsupported URL items directly
            if item is None:
                print("Item is None, ignoring...")
                continue

            if "project_id" not in item:
                grouped_content.append(item)
                continue

            project_id = item["project_id"]
            suite_id = item["suite_id"]

            # Check if the project already exists in the processed projects
            if project_id in processed_projects:
                # If "all_suites" is found, ignore other suites
                if processed_projects[project_id]["suite_id"] == "all_suites":
                    continue
                # If current suite is "all_suites", override previous suites
                if suite_id == "all_suites":
                    processed_projects[project_id] = item
                else:
                    suite_name = item["suite_name"]
                    suite_url = item["url"]
                    # Otherwise, append suite to the list
                    if isinstance(processed_projects[project_id]["suite_id"], list):
                        processed_projects[project_id]["suite_id"].append({"id": suite_id, "name": suite_name, "url": suite_url})
                    else:
                        processed_projects[project_id]["suite_id"] = [{"id": processed_projects[project_id]["suite_id"], "name": suite_name, "url": suite_url}, {"id": suite_id, "name": suite_name, "url": suite_url}]

            else:
                # Add new project
                if suite_id == "all_suites":
                    processed_projects[project_id] = item
                else:
                    suite_name = item["suite_name"]
                    suite_url = item["url"]
                    new_item = item.copy()
                    del new_item["suite_name"]
                    del new_item["url"]
                    
                    new_item["suite_id"] = [{"id": suite_id, "name": suite_name, "url": suite_url}]
                    processed_projects[project_id] = new_item


        # Add processed projects to grouped content
        grouped_content.extend(processed_projects.values())

        # Output result
        return grouped_content

        # Write result to output file
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
