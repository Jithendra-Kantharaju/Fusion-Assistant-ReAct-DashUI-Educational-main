# File Modification Activity

## All log entries where any of the three File Integrity Monitoring events are logged ##
- where(file_event="delete" OR "write" OR "modify") calculate(count)
