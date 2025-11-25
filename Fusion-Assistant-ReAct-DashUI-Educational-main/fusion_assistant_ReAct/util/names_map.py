import pandas as pd

def load_names_from_excel(name_excel_path: str) -> list[str]:
    df = pd.read_excel(name_excel_path, usecols=[0], engine='openpyxl')
    return df.iloc[:,0].dropna().astype(str).tolist()

def split_name_variants(names: list[str]) -> dict:
    out = {}
    for full_name in names:
        parts = full_name.strip().split()
        if not parts: continue
        first = parts[0]; last = parts[-1] if len(parts)>1 else ''
        out[full_name] = {"first": first, "last": last}
    return out

def build_name_to_ip_mapping_from_csv(csv_path: str) -> dict:
    df = pd.read_csv(csv_path)
    required = ['Machine Name','IP Address','User']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column in CSV: {col}")
    df = df.dropna(subset=['IP Address','User','Machine Name'])
    out = {}
    for _, row in df.iterrows():
        full = str(row['User']).strip()
        out[full] = {
            'ip': str(row['IP Address']).strip(),
            'workstation': str(row['Machine Name']).strip(),
            'netmask': str(row.get('Netmask','')).strip(),
            'gateway': str(row.get('Gateway','')).strip(),
            'dns1': str(row.get('DNS1','')).strip(),
        }
    return out
