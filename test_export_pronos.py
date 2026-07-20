# -*- coding: utf-8 -*-
import sys, os
try:
    import requests
except ImportError:
    os.system(f'"{sys.executable}" -m pip install requests --quiet'); import requests
API="http://localhost:8000/api/v1"
lr=requests.post(f"{API}/auth/login", json={"username":"jose","password":"catalina"}, timeout=30)
hdr={"Authorization":f"Bearer {lr.json().get('access_token','')}"}

rc=requests.get(f"{API}/bets/pronosticos-completados/2", headers=hdr, timeout=60)
comp=rc.json()
re_=requests.get(f"{API}/bets/exportar-pronosticos/2", headers=hdr, timeout=120)
ct=re_.headers.get("content-type","")
size=len(re_.content)
ok_comp = rc.status_code==200 and "fases" in comp
ok_xlsx = re_.status_code==200 and "spreadsheet" in ct and size>2000
out=(f"[completados] {rc.status_code} total_apostadores={comp.get('total_apostadores')} fases={comp.get('fases')}\n"
     f"[exportar] {re_.status_code} ct={ct} bytes={size}\n"
     f"RESULTADO: {'PASS' if (ok_comp and ok_xlsx) else 'REVISAR'} (comp={ok_comp}, xlsx={ok_xlsx})\n")
print(out)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"test_export_pronos_out.txt"),"w",encoding="utf-8").write(out)
