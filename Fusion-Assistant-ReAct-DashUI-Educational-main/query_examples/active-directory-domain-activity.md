# Active Directory Domain Activity

These queries only work with Microsoft Logs.

## All Microsoft Event IDs for collected events ##

- where(/eventCode\\":(?P<EVID>\d{4})/) groupby(EVID)
- where(/eventCode\\":\\"(?P<EVID>\d{4})/)groupby(EVID)

## All hosts that logs have been collected from ##
- where(/computerName\\":\\"(?P<HostName>[\w\d\-]*)/)groupby(HostName)
