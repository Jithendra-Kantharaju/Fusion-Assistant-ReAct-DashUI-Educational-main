# Web Proxy Activity

## All blocked URLs counter ##
- where(is_blocked=true)calculate(count)

## All blocked URLs grouped by unique sender ##
- where(is_blocked=true)groupby(source_json.sender)calculate(unique:source_json.sender)
