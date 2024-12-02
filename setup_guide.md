Sure, here's the updated `setup_guide.md` with the suggested changes incorporated:

---

# **Development Environment Setup Guide**

---

## **Table of Contents**

1. [Introduction](#1-introduction)
2. [Prerequisites](#2-prerequisites)
3. [Development Environment Setup](#3-development-environment-setup)
   - [3.1 Clone the Project Repository](#31-clone-the-project-repository)
   - [3.2 Set Up a Virtual Environment](#32-set-up-a-virtual-environment)
   - [3.3 Install Required Packages](#33-install-required-packages)
   - [3.4 Project Structure Overview](#34-project-structure-overview)
4. [Configuration](#4-configuration)
   - [4.1 Environment Variables](#41-environment-variables)
   - [4.2 Configuration Files](#42-configuration-files)
5. [Setting Up TestRail and Xray Access](#5-setting-up-testrail-and-xray-access)
   - [5.1 TestRail API Access](#51-testrail-api-access)
   - [5.2 Xray API Access](#52-xray-api-access)
6. [Backend Setup](#6-backend-setup)
   - [6.1 Installing API Clients](#61-installing-api-clients)
   - [6.2 Setting Up Logging](#62-setting-up-logging)
7. [Frontend Setup (UI)](#7-frontend-setup-ui)
   - [7.1 Project Structure](#71-project-structure)
   - [7.2 Running the Application](#72-running-the-application)
8. [Database Setup (Optional)](#8-database-setup-optional)
9. [Testing Environment](#9-testing-environment)
   - [9.1 Unit Testing Framework](#91-unit-testing-framework)
   - [9.2 Mocking External APIs](#92-mocking-external-apis)
10. [Version Control](#10-version-control)
    - [10.1 Initializing Git Repository](#101-initializing-git-repository)
    - [10.2 .gitignore File](#102-gitignore-file)
11. [Final Steps](#11-final-steps)
12. [Conclusion](#12-conclusion)

---

## **1. Introduction**

This setup guide provides detailed instructions for setting up the development environment for the TestRail to Xray migration tool as described in Phase 1 of the project. The guide covers the installation of necessary software, configuration of environment variables, and preparation of tools needed for both backend and frontend development.

---

## **2. Prerequisites**

Before starting, ensure you have the following:

- **Operating System**: A modern OS like Windows 10+, macOS, or a Linux distribution (e.g., Ubuntu).
- **Administrative Access**: Ability to install software and modify system settings.
- **Internet Connection**: For downloading packages and accessing APIs.

---

## **3. Development Environment Setup**

### **3.1 Clone the Project Repository**

Navigate to your desired parent directory and clone the repository:

```bash
# Navigate to your desired parent directory
cd /path/to/your/projects

# Clone the repository
git clone https://github.com/yourusername/presidency-migrator-lite.git

# Navigate into the project directory
cd presidency-migrator-lite
```

### **3.2 Set Up a Virtual Environment**

Using a virtual environment ensures package dependencies are isolated.

```bash
# Create a virtual environment named 'venv' inside the project
python3 -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### **3.3 Install Required Packages**

Ensure that the `requirements.txt` file includes all necessary packages. Install them using:

```bash
pip install -r requirements.txt
```

### **3.4 Project Structure Overview**

Familiarize yourself with the project structure as outlined in the repository:

```
presidency-migrator-lite/
├── README.md
├── LICENSE
├── .gitignore
├── requirements.txt
├── .env.example
├── config.yaml.example
├── docs/
│   ├── design_doc_phase1.md
│   ├── setup_guide.md
│   ├── testrail_integration_guide.md
│   └── other_docs.md
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── testrail_client.py
│   │   ├── xray_client.py
│   │   ├── migration.py
│   │   └── utils.py
│   ├── frontend/
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── templates/
│   │   │   ├── index.html
│   │   │   └── result.html
│   │   └── static/
│   │       └── css/
│   │           └── styles.css
│   └── config/
│       ├── __init__.py
│       ├── settings.py
│       └── logger.py
├── tests/
│   ├── __init__.py
│   ├── test_testrail_client.py
│   ├── test_xray_client.py
│   ├── test_migration.py
│   └── test_utils.py
├── data/
│   ├── output/
│   │   ├── test_cases.json
│   │   ├── sections.json
│   │   └── attachments/
│   └── input/
│       └── sample_data.json
├── logs/
│   └── migration.log
└── scripts/
    ├── start.sh
    └── setup_environment.sh
```

---

## **4. Configuration**

### **4.1 Environment Variables**

Copy the example `.env` file to create your own:

```bash
cp .env.example .env
```

Open `.env` and add your API credentials:

```env
# TestRail Configuration
TESTRAIL_URL=https://yourcompany.testrail.io/
TESTRAIL_USER=youremail@company.com
TESTRAIL_API_KEY=your_testrail_api_key

# Xray/Jira Configuration
XRAY_URL=https://yourcompany.atlassian.net/
XRAY_USER=youremail@company.com
XRAY_API_KEY=your_xray_api_key
```

**Important:** Ensure that the `.env` file is included in the `.gitignore` file to prevent it from being committed to version control.

### **4.2 Configuration Files**

Copy the example `config.yaml` file:

```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml` as needed for your environment.

---

## **5. Setting Up TestRail and Xray Access**

### **5.1 TestRail API Access**

1. **Enable API Access**:
   - Log in to TestRail.
   - Navigate to **Administration > Site Settings > API**.
   - Ensure the API is enabled.

2. **Generate API Key**:
   - Go to **My Settings**.
   - Scroll to **API Keys** and generate a new key.

3. **Permissions**:
   - Ensure your TestRail account has sufficient permissions to read test cases and attachments.

### **5.2 Xray API Access**

1. **API Documentation**:
   - Familiarize yourself with the [Xray API documentation](https://docs.getxray.app/display/XRAYCLOUD/REST+API).

2. **Generate API Token**:
   - Log in to Jira.
   - Navigate to **Account Settings > Security > API Tokens**.
   - Generate a new API token.

3. **Permissions**:
   - Ensure your Jira account has the necessary permissions to create issues and attachments in the target project.

---

## **6. Backend Setup**

### **6.1 Installing API Clients**

Ensure that your `requirements.txt` includes all necessary dependencies:

```txt
requests
PyYAML
python-dotenv
flask
flask-wtf
testrail-api
# Add any additional packages required by your backend modules
```

Install the packages:

```bash
pip install -r requirements.txt
```

- **TestRail API Client**:

  - Use the official Python binding or implement your own client in `src/backend/testrail_client.py`.

- **Xray API Client**:

  - Use `requests` to interact with the Xray API, implementing the client in `src/backend/xray_client.py`.

### **6.2 Setting Up Logging**

Logging configuration is handled in `src/config/logger.py`.

- **Logs Directory**:

  - Logs are stored in the `logs/` directory.

- **Configure Logging in Your Scripts**:

  ```python
  # In your scripts
  import logging
  from src.config.logger import setup_logging

  setup_logging()
  logger = logging.getLogger(__name__)
  ```

---

## **7. Frontend Setup (UI)**

### **7.1 Project Structure**

The frontend application is located in `src/frontend/`.

### **7.2 Running the Application**

Use the `start.sh` script to run the application:

```bash
./scripts/start.sh
```

Alternatively, you can run the Flask app directly:

```bash
export FLASK_APP=src/frontend/app.py
export FLASK_ENV=development
flask run
```

Access the application at `http://127.0.0.1:5000/`.

---

## **8. Database Setup (Optional)**

If you need to store data temporarily or maintain state, consider setting up a database.

- **SQLite**: Lightweight and easy to set up.

  ```python
  import sqlite3

  conn = sqlite3.connect('migration.db')
  ```

- **Alternative**: Use JSON files or in-memory data structures if persistent storage is not required.

---

## **9. Testing Environment**

### **9.1 Unit Testing Framework**

Set up a testing framework to write unit tests.

- **Install `pytest`**:

  ```bash
  pip install pytest
  ```

- **Directory Structure**:

  ```bash
  tests/
  ├── test_testrail_client.py
  ├── test_xray_client.py
  ├── test_migration.py
  └── test_utils.py
  ```

### **9.2 Mocking External APIs**

Use mocking to simulate API responses.

- **Install `responses` library**:

  ```bash
  pip install responses
  ```

- **Usage Example**:

  ```python
  import responses

  @responses.activate
  def test_get_test_cases():
      responses.add(
          responses.GET,
          'https://yourcompany.testrail.io/index.php?/api/v2/get_cases/1',
          json={'cases': []},
          status=200
      )
      # Call your function here
  ```

---

## **10. Version Control**

### **10.1 Initializing Git Repository**

If you haven't cloned the repository in step 3.1, initialize a Git repository:

```bash
git init
git add .
git commit -m "Initial commit"
```

### **10.2 .gitignore File**

Ensure your `.gitignore` file includes the following to exclude unnecessary files:

```gitignore
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]

# Virtual environment
venv/

# Environment variables and configuration
.env
config.yaml

# Logs
logs/
*.log

# Data
data/output/
data/input/

# Database
*.sqlite3
migration.db

# Other
.DS_Store
```

---

## **11. Final Steps**

- **Verify Installations**:
  - Run a simple script to ensure all packages are correctly installed.
- **Update Documentation**:
  - Keep your `README.md` updated with setup instructions.
- **Set Up Code Linting (Optional)**:
  - Install `flake8` or `pylint` for code quality checks.
- **Set Up Pre-commit Hooks (Optional)**:
  - Automate code checks before each commit.

---

## **12. Conclusion**

Your development environment is now set up and ready for developing the TestRail to Xray migration tool. You have configured the necessary software, set up API access, and prepared both the backend and frontend components. Remember to follow best practices for security, especially regarding API credentials and sensitive data.

---

**Next Steps:**

- Begin implementing the backend modules for data extraction, transformation, and import in `src/backend/`.
- Develop the frontend UI in `src/frontend/` and integrate it with the backend.
- Write tests in the `tests/` directory to validate functionality.
- Document your code and maintain good version control practices.

---

**Additional Resources:**

- **TestRail API Documentation**: [https://www.gurock.com/testrail/docs/api/](https://www.gurock.com/testrail/docs/api/)
- **Xray API Documentation**: [https://docs.getxray.app/display/XRAYCLOUD/REST+API](https://docs.getxray.app/display/XRAYCLOUD/REST+API)
- **Flask Documentation**: [https://flask.palletsprojects.com/](https://flask.palletsprojects.com/)
- **Python Virtual Environments**: [https://docs.python.org/3/tutorial/venv.html](https://docs.python.org/3/tutorial/venv.html)
- **Git Documentation**: [https://git-scm.com/doc](https://git-scm.com/doc)

---

**Prepared by:** Naman Sudan

**Date:** October 13, 2024

---

**Note:** This updated guide reflects the modular project structure and best practices for repository design. Ensure all file paths and references in your local project match this structure for consistency and ease of development.