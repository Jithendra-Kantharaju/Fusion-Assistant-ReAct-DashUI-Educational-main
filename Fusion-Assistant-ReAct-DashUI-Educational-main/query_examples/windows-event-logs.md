# Windows Event Logs

## All Security event logs, grouped by event code ##
- where(data.logName ICONTAINS "SECURITY")groupby(data.eventCode)
