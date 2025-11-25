import time, requests

def vt_url_scan(api_key: str, url: str) -> dict:
    headers = {"x-apikey": api_key}
    r = requests.post("https://www.virustotal.com/api/v3/urls", headers=headers, data={"url": url})
    r.raise_for_status()
    analysis_id = r.json()["data"]["id"]
    while True:
        rr = requests.get(f"https://www.virustotal.com/api/v3/analyses/{analysis_id}", headers=headers)
        rr.raise_for_status()
        js = rr.json()
        if js["data"]["attributes"]["status"] == "completed":
            return js
        time.sleep(3)

def vt_ip(api_key: str, ip: str) -> dict:
    headers = {"x-apikey": api_key}
    r = requests.get(f"https://www.virustotal.com/api/v3/ip_addresses/{ip}", headers=headers); r.raise_for_status()
    return r.json()

def vt_domain(api_key: str, domain: str) -> dict:
    headers = {"x-apikey": api_key}
    r = requests.get(f"https://www.virustotal.com/api/v3/domains/{domain}", headers=headers); r.raise_for_status()
    return r.json()

def vt_file(api_key: str, file_hash: str) -> dict:
    headers = {"x-apikey": api_key}
    r = requests.get(f"https://www.virustotal.com/api/v3/files/{file_hash}", headers=headers); r.raise_for_status()
    return r.json()
