# File Access Activity

## All files accessed by a specific user ##
- where(user="Pete Coors")groupby(file_name)

## All users who accessed a specific file ##
- where(file_name="audit.csv")groupby(user)

## Top 20 known users accessing Safebrowsing ##
- where(query="safebrowsing.google.com" AND user!="unknown")groupby(user)limit(20)

The following queries only work with Microsoft Logs.

## All Microsoft event IDs for collected events ##

- where(/eventCode\\":(?P<EVID>\d{4})/) groupby(EVID)
- where(/eventCode\\":\\"(?P<EVID>\d{4})/)groupby(EVID)

## All hosts that logs have been collected from ##
- where(/computerName\\":\\"(?P<HostName>[\w\d\-]*)/)groupby(HostName)
