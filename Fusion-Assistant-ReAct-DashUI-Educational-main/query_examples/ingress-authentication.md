# Ingress Authentication

## All events where the user logged in from a specific country ##

- where(geoip_country_name="United States")calculate(count)
- where(geoip_country_name="United States")groupby(user)calculate(count)

## All users accessing the network from a specific city ##
- where(geoip_city="San Jose")groupby(user)

## All users accessing the network from a list of cities ##
- where(geoip_city=/Providence|Framingham|Dallas|Minneapolis|Appleton|Phoenix|Omaha|Melbourne|Tuzla|Leeds|Zurich|Singapore|Toronto/i)groupby(geoip_city)

## All ingress from a certain country ##
- where(geoip_country_name="Russia")

## All users accessing the network from a specific service ##

- where(service="box")groupby(user)
- where(service="o365")groupby(user)

## All users accessing the network from countries other than the United States ##
- where(geoip_country_code!="US") groupby(geoip_country_name)

## All countries with successful authentication outside those listed ##
- where(geoip_country_name AND geoip_country_name!=/United States|Canada|Mexico/i AND result=SUCCESS)groupby(geoip_country_name)limit(100)

## All accounts that have ingressed into the application as stipulated by the applicationâs ID ##
- where(source_json.ApplicationId="[insert application ID]")groupby(account)

## All successful ingress authentications by a specific service, country, and user agent ##
- where(result=SUCCESS)groupby(service, geoip_country_name, user_agent)

## All weekly Ingress Authentications from the United States, All Services - Success ##
- where(result=SUCCESS AND geoip_country_name=""United States"")calculate(count)timeslice(1h)

## All weekly CONUS Ingress Authentications, All Services - Success ##
- where(result=/failed.*/i AND geoip_country_name=""United States"")calculate(count)timeslice(1h)

## All weekly CONUS Ingress Authentications, All Services - Failure ##
- where(result=SUCCESS AND geoip_country_name!=""United States"")calculate(count)timeslice(1d)

## All weekly CONUS Ingress Authentications, All Services - Failure ##
- where(result=/failed.*/i AND geoip_country_name!=""United States"")calculate(count)timeslice(1d)

## All apps being successfully signed into ##
- where(source_json.operationName="Sign-in activity" AND result=SUCCESS)groupby(source_json.properties.appDisplayName)

## All users who attempted to sign in but failed due to the account being disabled ##
- where(source_json.operationName="Sign-in activity" AND result=FAILED_ACCOUNT_DISABLED)groupby(user)

## All sign-in risk levels ##
- where(source_json.properties.riskLevelDuringSignIn!=none)groupby("source_json.properties.riskLevelDuringSignIn")

## Azure MFA Methods Used ##
- groupby(source_json.properties.mfaDetail.authMethod)

## Azure MFA Text Message Notifications ##
- where(source_json.properties.mfaDetail.authMethod=/Text message/i)groupby(result

## Azure Mobile app Verification Code Results ##
- where(source_json.properties.mfaDetail.authMethod=/Mobile app verification code/i)groupby(result)

## All failed Azure MFA phone calls grouped by result ##
- where(source_json.properties.mfaDetail.authMethod=/Phone call \(Authentication phone\)/i)groupby(result)

## All Azure MFA OATH verification codes grouped by result ##
- where(source_json.properties.mfaDetail.authMethod="OATH verification code")groupby(result)
