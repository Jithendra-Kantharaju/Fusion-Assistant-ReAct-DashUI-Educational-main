# SSO Authentication

## All successful single-service sign-ons grouped by service ##
- where(source_json.outcome.result=SUCCESS)groupby(service)
