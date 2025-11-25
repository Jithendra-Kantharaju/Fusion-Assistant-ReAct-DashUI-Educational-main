# Network Flow

## All versions of the TLS protocol in your outbound Network Flow logs, grouped by app_protocol_description ##
- app_protocol_description
- where(direction="OUTBOUND" AND app_protocol_description ISTARTS-WITH "TLS")groupby(app_protocol_description)
