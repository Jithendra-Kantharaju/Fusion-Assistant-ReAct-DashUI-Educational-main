# Active Directory Admin Activity

## All failed authentication activity, grouped by destination_user ##
- destination_user

- where(result AND result != SUCCESS) groupby(destination_user) calculate(count)
- where(result ISTARTS-WITH "FAILED") groupby(destination_user) calculate(count)

## All users who completed an admin action ##
- groupby(source_user)

## All admin actions ##
- groupby(action)

## All activity taken by a specific user ##

- where(source_user="Arnold Holt")
- where(source_user=NOCASE("arnold holt"))
- where(source_user="Tina Gonzales (Admin)")
- where(source_user=NOCASE("tina gonzales (admin)"))
- where(source_user="rrn:uba:us:14f8eba8-46c8-474b-a982-29476e7a8bd8:user:JA5G9PI3PC9M")

## All users with âadminâ in their user name ##

- where(source_user ICONTAINS admin)groupby(source_user)
- where(source_user ICONTAINS admin)groupby(action)

## All groups that a user was added to by someone with âadminâ in their name ##
- where(source_user ICONTAINS admin AND action=MEMBER_ADDED_TO_SECURITY_GROUP) groupby(group)

## All users added to a particular group ##
- where(action="MEMBER_ADDED_TO_SECURITY_GROUP" AND group="vpn-users")groupby(target_user)

## Accounts that added users to groups ##
- where(action="MEMBER_ADDED_TO_SECURITY_GROUP")groupby(source_user)

## Accounts (DN display) that had their privileges escalated, to what group, by whom, on what day/time ##
- where(target_account NOT ICONTAINS "$" AND action=PRIVILEGE_ESCALATION)groupby(target_account, group, source_user, timestamp)

## Group changes made to a certain group ##
- where(action IN [MEMBER_ADDED_TO_SECURITY_GROUP, MEMBER_REMOVED_FROM_SECURITY_GROUP]AND group CONTAINS -job-admins)
- /*.-job-admins/

## Admin account created by host ##
- where(/:\d{2} (?P<host>\w+)./ AND /4732 EVENT/ OR /\s636 EVENT/) groupby(host)

## Accounts locked out by host ##
- where(/:\d{2} (?P<host>\w+)./ AND /4740 EVENT/ OR /\s644 EVENT/) groupby(host)

## Audit Log cleared by Host ##
- where(/:\d{2} (?P<host>\w+)./ AND /1102 EVENT/ OR /\s517 EVENT/) groupby(host)

## Audit Policy Changed ##
- where(/4719 EVENT/ OR /\s612 EVENT/)
