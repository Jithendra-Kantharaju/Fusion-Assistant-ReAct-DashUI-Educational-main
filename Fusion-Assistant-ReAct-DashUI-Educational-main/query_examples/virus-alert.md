# Virus Alert

## All event codes from Windows Defender ##
- groupby(source_json.eventCode)

## All events where malware or PUP was detected, grouped by user, asset, and file path ##
- where(source_json.eventCode=1116)groupby(user, asset, file_path)

## All risks (alerts) ##
- groupby(risk)

## All risk counts trend by day ##
- calculate(count)timeslice(1d)

## All categories and severity ##
- groupby(source_json.Category, source_json.Severity)

## All Mimecast associated risks ##
- groupby(risk)
