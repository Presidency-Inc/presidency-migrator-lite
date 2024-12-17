# TestRail to Xray Migration Tool

A tool designed to facilitate the migration of test cases and associated data from TestRail to Xray for Jira.

## Overview

This proof-of-concept tool automates the process of migrating test cases from TestRail to Xray, ensuring data integrity and providing a smooth transition process.

### Key Features

- TestRail API integration for data extraction
- Data transformation between TestRail and Xray formats
- Xray API integration for data import
- Secure credential handling
- Detailed logging and error handling
- User interface for configuration and migration control

## Prerequisites

- Python 3.8 or higher
- Access to TestRail instance with API key
- Access to Xray Cloud/Jira with API credentials
- Git (for cloning the repository)

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd presidency-migrator-lite
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip3 install -r requirements.txt
```

4. Set up environment variables:
```bash
Edit the `.env` file with your TestRail and Xray credentials:
```
```
TESTRAIL_URL=your-testrail-url
TESTRAIL_USERNAME=your-username
TESTRAIL_API_KEY=your-api-key
XRAY_CLIENT_ID=your-client-id
XRAY_CLIENT_SECRET=your-client-secret
JIRA_URL=your-jira-url
```

5. Define migration scope file:
[
    {
        "sourceProjectId": "TEMP_PROJECT_ID", # TestRail project ID
        "targetProjectKey": "TEMP_PROJECT_KEY", # Xray project key
        "targetProjectId": "TEMP_PROJECT_ID",  # Xray project ID
        "rootFolderPath": "TEMP_FOLDER_PATH", # Xray folder path
        "assignee": "TEMP_ASSIGNEE" # Xray assignee
    }
]


## Usage

1. Configure your migration settings in the UI or through configuration files.
2. Review the mapping between TestRail and Xray fields in `backend/config/field_mapping.json`.
3. Run the migration process:

   a. Extract data from TestRail:
   ```bash
   python3 backend/testrail_client.py
   ```

   b. Import data into Xray:
   ```bash
   python3 backend/xray_client.py
   ```

4. Monitor the migration progress through the UI or logs.
5. Verify the migrated data in Xray.

## Project Structure

```
├── src/                    # Source code
│   ├── backend/           # Backend implementation
│   │   ├── config/       # Configuration files
│   │   │   └── field_mapping.json  # TestRail to Xray field mapping
│   │   ├── testrail_client.py  # TestRail data extraction script
│   │   └── xray_client.py      # Xray data ingestion script
│   └── __init__.py
├── data/                  # Migration data
├── logs/                  # Log files
├── reference/            # Reference materials
├── backup/               # Backup directory
├── requirements.txt      # Python dependencies
└── .env                 # Environment configuration
```

## Configuration

### Field Mapping Configuration
The `backend/config/field_mapping.json` file contains the mapping preferences that define how TestRail fields are mapped to Xray fields. This configuration is crucial for ensuring correct data transformation during the migration process.

### TestRail Configuration
- API access must be enabled in TestRail
- API key should be generated from TestRail's account settings
- Required permissions: Read access to test cases and test suites

### Xray Configuration
- Xray Cloud API credentials (Client ID and Secret)
- Jira project must be configured with Xray
- Required permissions: Create/modify test issues

## Error Handling

- The tool implements comprehensive error handling
- All operations are logged in the `logs` directory
- Failed migrations can be retried
- Backup of original data is maintained

## Security Considerations

- API credentials are stored securely in environment variables
- No sensitive data is logged or stored in plain text
- All API communications use HTTPS
- Regular credential rotation is recommended

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

See the LICENSE file for details.

## Support

For support and questions, please refer to:
- [design_doc.md](design_doc.md) for detailed design information
- [setup_guide.md](setup_guide.md) for detailed setup instructions
- [testrail_api_updates_guide.md](testrail_api_updates_guide.md) for TestRail API documentation
- [testrail_integration_export_guide.md](testrail_integration_export_guide.md) for export process documentation