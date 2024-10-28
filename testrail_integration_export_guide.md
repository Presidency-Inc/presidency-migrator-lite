# **TestRail Integration and Data Export Guide**

This guide provides step-by-step instructions to successfully integrate with the TestRail API and export test case data. Follow these instructions carefully to ensure a smooth setup and data extraction process.

---

## **Table of Contents**

1. [Prerequisites](#1-prerequisites)
2. [Step 1: Setting Up API Access in TestRail](#2-step-1-setting-up-api-access-in-testrail)
3. [Step 2: Setting Up the Development Environment](#3-step-2-setting-up-the-development-environment)
4. [Step 3: Authenticating with the TestRail API](#4-step-3-authenticating-with-the-testrail-api)
5. [Step 4: Extracting Data from TestRail](#5-step-4-extracting-data-from-testrail)
6. [Step 5: Handling Pagination and Rate Limits](#6-step-5-handling-pagination-and-rate-limits)
7. [Step 6: Saving Extracted Data](#7-step-6-saving-extracted-data)
8. [Step 7: Testing the Data Extraction](#8-step-7-testing-the-data-extraction)
9. [Conclusion](#9-conclusion)

---

## **1. Prerequisites**

- **TestRail Account**: Access to your TestRail instance with appropriate permissions.
- **API Access Enabled**: Ensure API access is enabled in TestRail (will be covered in Step 1).
- **Python 3.8 or Higher**: Installed on your development machine.
- **Python Packages**: `requests`, `python-dotenv`, `PyYAML` installed in your environment.
- **Code Editor or IDE**: Such as Cursor AI IDE, Visual Studio Code, PyCharm, etc.
- **Internet Connection**: Required to interact with the TestRail API.
- **Project Repository**: Cloned `asset-mark-migration` repository with the structured project layout.

---

## **2. Step 1: Setting Up API Access in TestRail**

### **2.1 Enable API Access**

1. **Log In to TestRail**: Access your TestRail instance via the web browser.
2. **Navigate to Administration**:
   - Click on the **"Administration"** link usually found at the top of the page.
3. **Enable API**:
   - Go to **"Site Settings"**.
   - Click on the **"API"** tab.
   - Ensure that the **"Enable API"** checkbox is **checked**.
   - Click **"Save Settings"** if you made changes.

### **2.2 Generate an API Key**

1. **Go to My Settings**:
   - Click on your username or the **"My Settings"** link.
2. **Create an API Key**:
   - Scroll down to the **"API Keys"** section.
   - Click on **"Add Key"**.
   - Optionally, add a description.
   - Click **"Generate"**.
3. **Copy the API Key**:
   - Copy the generated API key and store it securely. You'll need it for authentication.

**Note**: Do not share your API key. Treat it like a password.

---

## **3. Step 2: Setting Up the Development Environment**

### **3.1 Clone the Project Repository**

If you haven't already cloned the project repository, do so now:

```bash
# Navigate to your desired parent directory
cd /path/to/your/projects

# Clone the repository
git clone https://github.com/yourusername/asset-mark-migration.git

# Navigate into the project directory
cd asset-mark-migration
```

### **3.2 Navigate to the Backend Directory**

```bash
cd src/backend/
```

### **3.3 Create Necessary Files**

- **Ensure `__init__.py` exists** in the `backend/` directory. If not, create it:

  ```bash
  touch __init__.py
  ```

- **Create the TestRail client module**:

  ```bash
  touch testrail_client.py
  ```

### **3.4 Set Up a Virtual Environment**

Using a virtual environment ensures package dependencies are isolated.

```bash
# Navigate back to the project root
cd ../../

# Create a virtual environment named 'venv' inside the project
python3 -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### **3.5 Install Required Python Packages**

Ensure that the `requirements.txt` file includes all necessary packages.

Install the packages:

```bash
pip install -r requirements.txt
```

---

## **4. Step 3: Authenticating with the TestRail API**

### **4.1 Configure Environment Variables**

Copy the example `.env` file to create your own:

```bash
cp .env.example .env
```

Open the `.env` file and add the following:

```env
# TestRail Configuration
TESTRAIL_URL=https://yourcompany.testrail.io/
TESTRAIL_USER=youremail@company.com
TESTRAIL_API_KEY=your_generated_api_key
```

**Replace** the placeholders with your actual TestRail URL, username, and API key.

**Important**: Ensure that the `.env` file is included in the `.gitignore` file to prevent it from being committed to version control.

### **4.2 Load Environment Variables in Your Script**

In `src/backend/testrail_client.py`, add the following at the top:

```python
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TESTRAIL_URL = os.getenv('TESTRAIL_URL')
TESTRAIL_USER = os.getenv('TESTRAIL_USER')
TESTRAIL_API_KEY = os.getenv('TESTRAIL_API_KEY')
```

### **4.3 Verify Credentials**

Ensure that the variables `TESTRAIL_URL`, `TESTRAIL_USER`, and `TESTRAIL_API_KEY` are loaded correctly.

---

## **5. Step 4: Extracting Data from TestRail**

### **5.1 Import Required Modules**

In your `testrail_client.py` script, import the necessary modules:

```python
import requests
import json
import time
```

### **5.2 Set Up the API Client**

```python
from requests.auth import HTTPBasicAuth

auth = HTTPBasicAuth(TESTRAIL_USER, TESTRAIL_API_KEY)

headers = {
    'Content-Type': 'application/json'
}
```

### **5.3 Define Helper Functions**

#### **5.3.1 Send GET Request**

```python
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
```

#### **5.3.2 Send POST Request (if needed)**

```python
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
```

### **5.4 Fetch Test Cases**

#### **5.4.1 Get Project ID**

If you know your project ID, you can skip this step.

```python
def get_projects():
    return send_get('get_projects')

# Example usage:
if __name__ == "__main__":
    projects = get_projects()
    for project in projects:
        print(f"Project ID: {project['id']}, Name: {project['name']}")
```

Run the script to list projects and find the ID of your sample project.

#### **5.4.2 Get Test Suites (if applicable)**

If your project uses multiple test suites:

```python
def get_suites(project_id):
    return send_get(f'get_suites/{project_id}')

# Example usage:
suites = get_suites(project_id)
for suite in suites:
    print(f"Suite ID: {suite['id']}, Name: {suite['name']}")
```

#### **5.4.3 Get Sections**

```python
def get_sections(project_id, suite_id):
    return send_get(f'get_sections/{project_id}&suite_id={suite_id}')

# Example usage:
sections = get_sections(project_id, suite_id)
```

#### **5.4.4 Get Test Cases**

```python
def get_test_cases(project_id, suite_id, offset=0, limit=250):
    params = {
        'suite_id': suite_id,
        'offset': offset,
        'limit': limit
    }
    response = send_get(f'get_cases/{project_id}', params=params)
    return response['cases']
```

---

## **6. Step 5: Handling Pagination and Rate Limits**

### **6.1 Pagination Logic**

Since the API returns a maximum of 250 cases per request, implement pagination to fetch all cases.

```python
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
```

### **6.2 Rate Limit Handling**

TestRail Cloud has a rate limit of **180 requests per minute**.

- **Best Practice**: Use bulk endpoints and minimize the number of requests.
- **Implement Delay**: The `send_get` and `send_post` functions already handle rate limiting by checking for `429 Too Many Requests` and retrying after the specified delay.

---

## **7. Step 6: Saving Extracted Data**

### **7.1 Define a Function to Save Data**

Modify the `save_data` function to save outputs to the `data/output/` directory.

```python
def save_data(data, filename):
    output_dir = os.path.join(os.path.dirname(__file__), '../../data/output')
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
```

### **7.2 Save Test Cases**

After fetching all test cases:

```python
project_id = your_project_id  # Replace with your project ID
suite_id = your_suite_id      # Replace with your suite ID

all_test_cases = get_all_test_cases(project_id, suite_id)
save_data(all_test_cases, 'test_cases.json')
print(f"Saved {len(all_test_cases)} test cases to data/output/test_cases.json")
```

### **7.3 Save Sections**

```python
sections = get_sections(project_id, suite_id)
save_data(sections, 'sections.json')
print(f"Saved {len(sections)} sections to data/output/sections.json")
```

---

## **8. Step 7: Testing the Data Extraction**

### **8.1 Run the Script**

Ensure your `testrail_client.py` script includes the necessary code to fetch and save test cases and sections.

**Full Example Script (`testrail_client.py`):**

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

def get_projects():
    return send_get('get_projects')

def get_suites(project_id):
    return send_get(f'get_suites/{project_id}')

def get_sections(project_id, suite_id):
    return send_get(f'get_sections/{project_id}&suite_id={suite_id}')

def get_test_cases(project_id, suite_id, offset=0, limit=250):
    params = {'suite_id': suite_id, 'offset': offset, 'limit': limit}
    response = send_get(f'get_cases/{project_id}', params=params)
    return response['cases']

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
    # Replace with your project and suite IDs
    project_id = your_project_id   # e.g., 1
    suite_id = your_suite_id       # e.g., 1

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

**Note**: Replace `your_project_id` and `your_suite_id` with the actual IDs.

### **8.2 Execute the Script**

When running the script, ensure you're in the `src/backend/` directory.

```bash
cd src/backend/
python testrail_client.py
```

### **8.3 Verify the Output**

- Check the `data/output/` directory in the project root.
- Ensure `test_cases.json` and `sections.json` are created.
- Open the JSON files to verify the content.

---

## **9. Conclusion**

You have successfully integrated with the TestRail API and exported test cases and sections to JSON files. This data is now ready for transformation and import into Xray or any other system.

---

**Next Steps**:

- **Data Transformation**: Implement scripts to transform the extracted data into the format required by Xray.
- **Attachment Handling**: If you need to export attachments, extend the script to download attachments for each test case.
- **Error Handling and Logging**: Enhance the script to include robust error handling and logging mechanisms.
- **Integration with Xray API**: Proceed to integrate with the Xray API to import the transformed data.

---

**Important Tips**:

- **API Rate Limits**: Be cautious of the rate limits. Use bulk endpoints and consider implementing delays if necessary.
- **Data Validation**: Always validate the extracted data to ensure completeness and accuracy.
- **Security**: Keep your API credentials secure. Do not commit the `.env` file to version control.
- **Documentation**: Document your code and any decisions made during development for future reference.

---

**Note**: This updated guide reflects the modular project structure and best practices for repository design. Ensure all file paths and references in your local project match this structure for consistency and ease of development.

---

**Prepared by:** Naman Sudan

**Date:** October 13, 2024