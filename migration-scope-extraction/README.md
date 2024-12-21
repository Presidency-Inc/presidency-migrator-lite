## Extracting migration scope tesrail data
### app.py
1. extract data uisng linkList.json which is an array of links extracted from testrail excel sheet. This will extract the data from testrail and save it in a json file called ***results.json*** -> [***app.py***]

### grouping.py
2. GroupBy project id. calling grouping.py which will programatically group the data based on project id and store list of suites id that need to be migrated. Results are stored in a json file called ***grouped.json*** -> [***grouping.py***]

---
// Extra stuff
### milestone_url_extract.py
3. special extraction for testrail milestones urls (Get the content of links using beautiful soup, extract the "runs/view" url to call a second time beautiful soup and extract the final "suites/view" url and store it in a json file called ***milestone_urls.json*** in the same format as results.json) -> [***milestone_url_extract.py***]
---

### xrayDataMapping.py
4. mapping data from testrail grouped data and getting information for target Xray project uisng ExcelMigratedTable.json and XRayProjectData.json to find the right XRay project key using the URL as unique identifier. This process will generate a json file called ***final_migration_scope.json*** -> [***xrayDataMapping.py***]

