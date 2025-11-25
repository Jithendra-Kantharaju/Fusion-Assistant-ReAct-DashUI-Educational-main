# Cloud Service Activity

## All Cloud Service Workloads and actions performed ##
- groupby(source_json.Workload, action)

## Top 10 users with the most Office365 activity ##
- groupby(source_user)calculate(count)limit(10)
