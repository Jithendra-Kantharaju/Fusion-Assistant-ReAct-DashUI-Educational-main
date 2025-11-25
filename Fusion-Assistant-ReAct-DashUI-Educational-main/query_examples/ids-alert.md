# IDS Alert

## Informational alerts by signature ##
- where(severity="INFORMATIONAL")groupby(signature)limit(1000)

## All informational alerts with SSH signatures ##
- where(severity="INFORMATIONAL" AND signature=/.*ssh.*/i)groupby(signature)

## All low severity alerts grouped by description ##
- where(severity="LOW")groupby(description)

## All alerts grouped by severity with unique signatures ##
- groupby(severity)calculate(unique:signature)

## All high severity alerts grouped by asset with unique signatures ##
- where(severity="HIGH")groupby(asset)calculate(unique:signature)

## All critical severity alerts grouped by asset with unique signatures ##
- where(severity="CRITICAL")groupby(asset)calculate(unique:signature)
