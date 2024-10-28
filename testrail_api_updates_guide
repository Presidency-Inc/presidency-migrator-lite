# **TestRail API Updates Guide**

This guide provides instructions on how to modify your `testrail_client.py` file to dynamically retrieve the `project_id` and `suite_id` from your TestRail account. This will help you identify the correct IDs without manually specifying them, solving the problem you've encountered.

---

## **Table of Contents**

1. [Introduction](#1-introduction)
2. [Step 1: Fetching Project IDs](#2-step-1-fetching-project-ids)
   - [2.1 Modify the `get_projects` Function](#21-modify-the-get_projects-function)
   - [2.2 Implement a Function to Select a Project](#22-implement-a-function-to-select-a-project)
3. [Step 2: Fetching Suite IDs](#3-step-2-fetching-suite-ids)
   - [3.1 Modify the `get_suites` Function](#31-modify-the-get_suites-function)
   - [3.2 Implement a Function to Select a Suite](#32-implement-a-function-to-select-a-suite)
4. [Step 3: Updating the `main` Function](#4-step-3-updating-the-main-function)
5. [Step 4: Updated `testrail_client.py` Script](#5-step-4-updated-testrail_clientpy-script)
6. [Conclusion](#6-conclusion)

---

## **1. Introduction**

In your current `testrail_client.py` script, you need to specify `project_id` and `suite_id` manually. Since you're unsure of these IDs, we'll modify the script to:

- Fetch all available projects and display them with their IDs.
- Allow you to select a project by name or ID.
- Fetch all test suites within the selected project (if applicable).
- Allow you to select a test suite by name or ID.

This guide will help you make these changes to your script.

---

## **2. Step 1: Fetching Project IDs**

### **2.1 Modify the `get_projects` Function**

Ensure that the `get_projects` function returns the list of projects without any modifications.

```python
def get_projects():
    return send_get('get_projects')
```

### **2.2 Implement a Function to Select a Project**

Add a new function `select_project` that lists all projects and prompts the user to select one.

```python
def select_project():
    projects = get_projects()
    print("Available Projects:")
    for project in projects:
        status = 'Completed' if project['is_completed'] else 'Active'
        print(f"ID: {project['id']}, Name: {project['name']}, Status: {status}")
    while True:
        project_id_input = input("Enter the Project ID you want to select: ").strip()
        if project_id_input.isdigit():
            project_id = int(project_id_input)
            if any(project['id'] == project_id for project in projects):
                return project_id
            else:
                print("Invalid Project ID. Please try again.")
        else:
            print("Please enter a numeric Project ID.")
```

**Explanation:**

- The function `select_project` fetches all projects and displays them.
- It prompts the user to enter a `project_id`.
- It validates the input and ensures the entered ID exists in the list of projects.

---

## **3. Step 2: Fetching Suite IDs**

### **3.1 Modify the `get_suites` Function**

Ensure that the `get_suites` function returns the list of suites for a given project.

```python
def get_suites(project_id):
    return send_get(f'get_suites/{project_id}')
```

### **3.2 Implement a Function to Select a Suite**

Add a new function `select_suite` that lists all suites within the selected project and prompts the user to select one.

```python
def select_suite(project_id):
    suites = get_suites(project_id)
    if not suites:
        print("No test suites found for this project.")
        return None  # For single-suite projects
    print("Available Test Suites:")
    for suite in suites:
        print(f"ID: {suite['id']}, Name: {suite['name']}")
    while True:
        suite_id_input = input("Enter the Suite ID you want to select: ").strip()
        if suite_id_input.isdigit():
            suite_id = int(suite_id_input)
            if any(suite['id'] == suite_id for suite in suites):
                return suite_id
            else:
                print("Invalid Suite ID. Please try again.")
        else:
            print("Please enter a numeric Suite ID.")
```

**Explanation:**

- The function `select_suite` fetches all suites for the selected project.
- It prompts the user to enter a `suite_id`.
- It handles projects that may not use suites (single-suite mode).

**Note:** TestRail projects can be in one of three suite modes:

1. **Single Suite Mode (suite_mode=1):** The project has a single test suite, and you don't need to specify a suite ID.
2. **Single Suite + Baselines (suite_mode=2):** Similar to single suite but with baselines.
3. **Multiple Suites (suite_mode=3):** The project can have multiple test suites.

We need to handle these modes appropriately.

---

## **4. Step 3: Updating the `main` Function**

Modify the `main` function to use the new `select_project` and `select_suite` functions.

```python
def main():
    # Select project
    project_id = select_project()
    project = get_project(project_id)
    suite_mode = project['suite_mode']

    # Determine suite_id based on suite_mode
    if suite_mode == 1:
        # Single Suite Mode
        suite_id = None
    elif suite_mode == 2:
        # Single Suite + Baselines Mode
        suite_id = get_suites(project_id)[0]['id']
    elif suite_mode == 3:
        # Multiple Suites Mode
        suite_id = select_suite(project_id)
    else:
        print("Unknown suite mode.")
        return

    # Fetch and save test cases
    print("Fetching test cases...")
    all_test_cases = get_all_test_cases(project_id, suite_id)
    save_data(all_test_cases, 'test_cases.json')
    print(f"Saved {len(all_test_cases)} test cases to data/output/test_cases.json")

    # Fetch and save sections
    print("Fetching sections...")
    sections = get_sections(project_id, suite_id)
    save_data(sections, 'sections.json')
    print(f"Saved {len(sections)} sections to data/output/sections.json")
```

**Explanation:**

- The `main` function now dynamically selects the `project_id` and `suite_id`.
- It checks the `suite_mode` of the project and handles it accordingly.
- For projects in single suite mode, the `suite_id` may not be necessary.

### **Add `get_project` Function**

We need to add the `get_project` function to fetch the project's details.

```python
def get_project(project_id):
    return send_get(f'get_project/{project_id}')
```

---

## **5. Step 4: Updated `testrail_client.py` Script**

Here's the updated `testrail_client.py` with all the changes:

```python
import os
import time
import json
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TESTRAIL_URL = os.getenv('TESTRAIL_URL')
TESTRAIL_USER = os.getenv('TESTRAIL_USER')
TESTRAIL_API_KEY = os.getenv('TESTRAIL_API_KEY')

auth = HTTPBasicAuth(TESTRAIL_USER, TESTRAIL_API_KEY)
headers = {'Content-Type': 'application/json'}

def send_get(uri, params=None):
    url = f"{TESTRAIL_URL}index.php?/api/v2/{uri}"
    response = requests.get(url, auth=auth, headers=headers, params=params)
    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', '60'))
        print(f"Rate limit exceeded. Retrying after {retry_after} seconds.")
        time.sleep(retry_after)
        return send_get(uri, params)
    elif response.status_code != 200:
        raise Exception(f"GET {uri} failed with status {response.status_code}: {response.text}")
    return response.json()

def send_post(uri, data):
    url = f"{TESTRAIL_URL}index.php?/api/v2/{uri}"
    response = requests.post(url, auth=auth, headers=headers, json=data)
    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', '60'))
        print(f"Rate limit exceeded. Retrying after {retry_after} seconds.")
        time.sleep(retry_after)
        return send_post(uri, data)
    elif response.status_code != 200:
        raise Exception(f"POST {uri} failed with status {response.status_code}: {response.text}")
    return response.json()

def get_projects():
    return send_get('get_projects')

def get_project(project_id):
    return send_get(f'get_project/{project_id}')

def select_project():
    projects = get_projects()
    print("Available Projects:")
    for project in projects:
        status = 'Completed' if project['is_completed'] else 'Active'
        print(f"ID: {project['id']}, Name: {project['name']}, Status: {status}")
    while True:
        project_id_input = input("Enter the Project ID you want to select: ").strip()
        if project_id_input.isdigit():
            project_id = int(project_id_input)
            if any(project['id'] == project_id for project in projects):
                return project_id
            else:
                print("Invalid Project ID. Please try again.")
        else:
            print("Please enter a numeric Project ID.")

def get_suites(project_id):
    return send_get(f'get_suites/{project_id}')

def select_suite(project_id):
    suites = get_suites(project_id)
    if not suites:
        print("No test suites found for this project.")
        return None  # For single-suite projects
    print("Available Test Suites:")
    for suite in suites:
        print(f"ID: {suite['id']}, Name: {suite['name']}")
    while True:
        suite_id_input = input("Enter the Suite ID you want to select: ").strip()
        if suite_id_input.isdigit():
            suite_id = int(suite_id_input)
            if any(suite['id'] == suite_id for suite in suites):
                return suite_id
            else:
                print("Invalid Suite ID. Please try again.")
        else:
            print("Please enter a numeric Suite ID.")

def get_sections(project_id, suite_id):
    if suite_id:
        uri = f'get_sections/{project_id}&suite_id={suite_id}'
    else:
        uri = f'get_sections/{project_id}'
    return send_get(uri)

def get_test_cases(project_id, suite_id, offset=0, limit=250):
    params = {'offset': offset, 'limit': limit}
    if suite_id:
        params['suite_id'] = suite_id
    response = send_get(f'get_cases/{project_id}', params=params)
    return response

def get_all_test_cases(project_id, suite_id):
    all_cases = []
    offset = 0
    limit = 250
    while True:
        test_cases = get_test_cases(project_id, suite_id, offset, limit)
        if not test_cases:
            break
        all_cases.extend(test_cases)
        offset += limit
    return all_cases

def save_data(data, filename):
    output_dir = os.path.join(os.path.dirname(__file__), '../../data/output')
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def main():
    # Select project
    project_id = select_project()
    project = get_project(project_id)
    suite_mode = project['suite_mode']

    # Determine suite_id based on suite_mode
    if suite_mode == 1:
        # Single Suite Mode
        suite_id = None
        print("Project is in Single Suite Mode.")
    elif suite_mode == 2:
        # Single Suite + Baselines Mode
        suite_id = get_suites(project_id)[0]['id']
        print("Project is in Single Suite + Baselines Mode.")
    elif suite_mode == 3:
        # Multiple Suites Mode
        print("Project is in Multiple Suites Mode.")
        suite_id = select_suite(project_id)
    else:
        print("Unknown suite mode.")
        return

    # Fetch and save test cases
    print("Fetching test cases...")
    all_test_cases = get_all_test_cases(project_id, suite_id)
    save_data(all_test_cases, 'test_cases.json')
    print(f"Saved {len(all_test_cases)} test cases to data/output/test_cases.json")

    # Fetch and save sections
    print("Fetching sections...")
    sections = get_sections(project_id, suite_id)
    save_data(sections, 'sections.json')
    print(f"Saved {len(sections)} sections to data/output/sections.json")

if __name__ == "__main__":
    main()
```

**Notes:**

- **Suite Mode Handling:**
  - **suite_mode == 1**: Single Suite Mode. No need to specify `suite_id`.
  - **suite_mode == 2**: Single Suite + Baselines Mode. We use the first suite returned by `get_suites`.
  - **suite_mode == 3**: Multiple Suites Mode. User selects a suite.

- **Modified `get_sections` and `get_test_cases` Functions:**
  - Adjusted to handle cases where `suite_id` might be `None`.

- **User Interaction:**
  - The script now interacts with the user to select the project and suite.

- **Imports:**
  - Ensure all necessary imports are included.

---

## **6. Conclusion**

By following this guide, you've updated your `testrail_client.py` script to dynamically retrieve `project_id` and `suite_id` from your TestRail account. This allows you to proceed without manually specifying these IDs and ensures your script can handle different project configurations.

**Next Steps:**

- **Run the Updated Script:**
  - Navigate to the `src/backend/` directory.
  - Execute the script:

    ```bash
    python testrail_client.py
    ```

- **Test the Functionality:**
  - Verify that the script lists available projects and allows you to select one.
  - If your project uses multiple suites, ensure you can select the desired suite.
  - Confirm that test cases and sections are exported correctly.

- **Error Handling:**
  - If you encounter any issues, check the error messages for guidance.
  - Ensure your API credentials are correct and that you have the necessary permissions in TestRail.

**Important Tips:**

- **Suite Modes:**
  - Be aware of your project's suite mode, as it affects how you interact with suites and test cases.
  - You can check the suite mode by viewing the project's settings in TestRail or via the API (`suite_mode` field).

- **Logging and Debugging:**
  - Consider adding logging to your script for better traceability.
  - You can use the `logging` module to log information to a file or console.

- **Extensibility:**
  - This updated script provides a foundation for further enhancements, such as automating the entire migration process.

---

By incorporating these updates, you can move forward with your project and successfully extract data from TestRail for your migration tool.