import nmap

def fast_scan(ip: str) -> dict:
    scanner = nmap.PortScanner()
    try:
        scanner.scan(ip, arguments='-T4 -F')
        return scanner[ip]
    except Exception as e:
        return {"error": str(e)}
