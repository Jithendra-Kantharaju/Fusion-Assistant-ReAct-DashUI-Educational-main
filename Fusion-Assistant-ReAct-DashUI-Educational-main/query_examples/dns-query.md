# DNS Query

## All websites visited by users outside of .com, .net, and .org domains ##
- where(public_suffix AND public_suffix NOT IN [com, net, org])groupby(public_suffix)

## All websites in Russia visited by users ##
- where(public_suffix="ru")groupby(query)

## All users who have accessed a website, and how many times ##
- where(/facebook/ AND user!="unknown")calculate(count)

## All users who have accessed Dropbox ##
- where(/dropbox/ AND user!="unknown")groupby(user)

## All users who have accessed Facebook ##
- where(/facebook/ AND user!="unknown")groupby(user)
