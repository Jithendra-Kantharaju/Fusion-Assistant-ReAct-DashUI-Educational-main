# Endpoint Activity

## All child Powershell process command lines that are not empty or only running a ps1 script ##
- where(process.name=/powershell.exe/i AND process.cmd_line NOT IN ["null", /.*ps1.*/i])groupby(process.cmd_line)

## All processes by file descriptions ##
- groupby(process.exe_file.description)

## All process reputations ##
- groupby(process.hash_reputation.reputation)

## All command lines showing the taskkill.exe process ##
- taskkill.exe
- where(process.name=NOCASE(taskkill.exe)) groupby(process.cmd_line)

## All processes, hostnames, and users running programs for SSH and/or Telnet ##
- where(process.exe_file.description icontains-any ["ssh", "telnet"]) groupby(process.name, hostname, process.username)
