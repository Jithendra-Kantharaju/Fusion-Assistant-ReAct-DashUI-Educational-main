# Firewall Activity

## All countries that users have downloaded data from ##
- where(incoming_bytes>0 AND geoip_country_code NOT IN [US, IE, GB, DE, JP, CA, AU])groupby(geoip_country_code)

## All firewall traffic from countries other than the United States ##
- where(geoip_country_name!="United States")groupby(geoip_country_name)

## A count of all firewall logs ##
- calculate(count)

## Top 10 external systems (outside of the United States) receiving the most data ##
- where(direction=OUTBOUND AND geoip_country_code!=US)groupby(destination_address)calculate(sum:outgoing_bytes)limit(10)

## Top 10 internal systems receiving the most data ##
- where(direction=INBOUND)groupby(destination_address)calculate(sum:incoming_bytes)limit(10)

## All users accessing a particular destination ##
- where(direction="OUTBOUND" AND destination_address="52.205.169.150")groupby(user)

## All countries with a connection status of deny ##
- deny
- where(connection_status="DENY") calculate(count)

## All denied outbound traffic ##
- where(direction="OUTBOUND" AND connection_status="DENY")calculate(count)

## All used outbound ports except for 443, 80, and 53, grouped by destination_port ##
- destination_port
- where(connection_status="ACCEPT" AND direction="OUTBOUND" AND destination_port NOT IN ["443", "80", "53"]) groupby(destination_port)

## Top outbound destinations ##
- where(direction=OUTBOUND)groupby(destination_address)calculate(sum:outgoing_bytes)

## Top inbound destinations ##
- where(direction=INBOUND)groupby(source_address)calculate(sum:incoming_bytes)

## Allowlisted countries ##
- where(geoip_country_name IN [Czechia, Russia, "Hong Kong"] AND connection_status = ACCEPT AND direction=INBOUND)groupby(geoip_country_name)

## External firewall denials by subnet ##
- where(connection_status = DENY AND source_address NOT IN [IP(10.0.0.0/8),IP(172.27.0.0/16),IP(169.254.0.0/16),IP(192.168.0.0/16),IP(172.16.0.0/16)])

## All known users with a status of deny from an IP address not listed ##
- deny
- where(user!="unknown" AND connection_status = DENY AND source_address NOT IN [IP(10.0.0.0/8), IP(172.27.0.0/16), IP(169.254.0.0/16), IP(192.168.0.0/16), IP(172.16.0.0/16)])

## All invalid connection attempts from a country that isnât the United States ##
- where(connection_status="DENY" AND geoip_country_name!="United States") groupby(geoip_country_name) calculate(count)

## All inbound denies by country ##
- where(connection_status=DENY AND direction=INBOUND AND geoip_country_name!="United States") groupby(geoip_country_name) calculate(count)

## All data transmissions greater than 50,000,000 bytes to âBox.comâ ##
- where(direction="OUTBOUND" AND outgoing_bytes>50000000 AND geoip_organization="Box.com")

## All Docker traffic (RAW) received in bytes ##
- where(stats.networks.eth0.rx_bytes!=null) calculate(average:stats.networks.eth0.rx_bytes)
