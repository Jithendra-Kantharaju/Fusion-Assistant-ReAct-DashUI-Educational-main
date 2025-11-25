# Asset Authentication

## All authentication types ##
- groupby(logon_type)

## All authentication results ##
- groupby(result)

## All failed authentication activity ##
- where(result AND result != SUCCESS) groupby(destination_user) calculate(count)

## All failed authentication activity ##
- where(result starts-with "failed") groupby(destination_user) calculate(count)

## All failed Logins by IP ##
- where(/(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/) groupby(ip) calculate(count)

## All failed Non-Kerberos logins ##
- where(service NOT IIN ["krbtgt", "kerberos"] AND result ISTARTS-WITH "failed") groupby(destination_account)

## All Non-Kerberos logins by destination asset ##
- where(service NOT IN [krbtgt, kerberos]AND result="FAILED_BAD_PASSWORD")groupby("destination_asset")

## All accounts attempting to authenticate that failed ##
- where(result ISTARTS-WITH "FAILED")groupby(destination_user)
- destination_account

## All invalid logins ##
- where(/4625 EVENT/ OR /\s529 EVENT/)

## All invalid logins by host ##
- where(/:\d{2} (?P<host>\w+)./ AND /4625 EVENT/ OR /\s529 EVENT/) groupby(host)

## All Microsoft event IDs for collected events ##

- where(/eventCode\\":(?P<EVID>\d{4})/) groupby(EVID)
- where(/eventCode\\":\\"(?P<EVID>\d{4})/)groupby(EVID)

## All hosts that logs have been collected from ##
- where(/computerName\\":\\"(?P<HostName>[\w\d\-]*)/)groupby(HostName)
