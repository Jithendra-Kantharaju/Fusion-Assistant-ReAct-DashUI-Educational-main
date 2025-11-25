# Host to IP Observations

## All assets that have obtained more than 5 unique IP addresses ##
- where(action="OBTAIN")groupby(asset)calculate(unique:ip)having(unique:ip>=5)
