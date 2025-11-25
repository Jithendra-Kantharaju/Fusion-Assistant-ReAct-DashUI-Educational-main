# Cloud Service Admin Activity

## Office365 guest account creations and who created them ##
- where(action=CREATE_USER AND target_user=/.*\#EXT\#.*/i) groupby(source_user, target_user)

## Office365 guest account areas of activity ##
- where(source_user=/.*\#EXT\#.*/i)groupby(source_json.Workload)

## Office365 guest account SharePoint actions ##
- where(source_user=/.*\#EXT\#.*/i AND source_json.Workload=SharePoint)groupby(action)

## Office365 guest account OneDrive files downloaded or accessed ##
- where(source_user=/.*\#EXT\#.*/i AND source_json.Workload=OneDrive AND action=/FileDownloaded|FileAccessed/)groupby(action, source_json.SourceFileName)

## Office365 guest account Team Sessions started ##
- where(source_user=/.*\#EXT\#.*/i AND source_json.Workload=MicrosoftTeams AND action=/TeamsSessionStarted/i)groupby(source_user)
