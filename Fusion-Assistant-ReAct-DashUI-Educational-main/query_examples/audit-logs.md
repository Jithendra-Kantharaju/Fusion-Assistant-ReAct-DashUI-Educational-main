# Audit Logs

## All investigation activity performed from within the SIEM (InsightIDR) Platform, grouped by action ##
- action
- where(access_method="web")groupby(action)

## All analysts who have closed an investigation, grouped by their user name ##
- where(action="INVESTIGATION_CLOSED")groupby(request.user.name)

## Manually created investigations, grouped by alert name ##
- where(service_info.investigation_type="MANUAL")groupby(service_info.investigation_name)limit(1000)

## All instances where data has been added to an investigation, grouped by investigation type and the data types ##
- where(action="INVESTIGATION_DATA_ADDED")groupby(service_info.investigation_type, service_info.data_type)
