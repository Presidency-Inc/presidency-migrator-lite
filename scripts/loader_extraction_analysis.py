import json

def filter_status(data):
    # Define the statuses to filter
    target_statuses = ["unsuccessful", "partially_successful", "failed"]

    # Filter and transform the data
    result = [
        {"imported_file": item["imported_file"], "status": item["status"]}
        for item in data
        if item["status"] in target_statuses
    ]

    # Write the result to a json file
    with open("extraction_filtered.json", "w") as f:
        json.dump(result, f, indent=4)

# Input data
input_data = [
    {
        "imported_file": "test_cases_101_1.json",
        "job_id": "208a6977444b4b0da6fb27146c3d196a",
        "status": "unsuccessful",
        "result": {
            "errors": [
                {
                    "elementNumber": 0,
                    "errors": {
                        "otherErrors": [
                            "You do not have permission to create issues in this project."
                        ]
                    }
                }
            ],
            "issues": [],
            "warnings": []
        }
    },
    {
        "imported_file": "test_cases_101_2.json",
        "job_id": "208a6977444b4b0da6fb27146c3d196b",
        "status": "successful",
        "result": {
            "errors": [],
            "issues": [],
            "warnings": []
        }
    },
    {
        "imported_file": "test_cases_101_3.json",
        "job_id": "208a6977444b4b0da6fb27146c3d196c",
        "status": "partially_successful",
        "result": {
            "errors": [],
            "issues": [],
            "warnings": []
        }
    }
]

# Call the function and print the result
filtered_data = filter_status(input_data)
print(filtered_data)
