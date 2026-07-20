# -*- coding: utf-8 -*-
"""Lee la URL publica de ngrok desde su API local y arma el link de playoffs live."""
import json, urllib.request, os
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ngrok_url.txt")
url = ""
err = ""
try:
    d = json.load(urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=5))
    tuns = d.get("tunnels", [])
    https = [t.get("public_url", "") for t in tuns if t.get("public_url", "").startswith("https")]
    url = https[0] if https else (tuns[0].get("public_url", "") if tuns else "")
except Exception as e:
    err = str(e)

link = (url + "/static/becbuc-live-playoffs.html") if url else ""
with open(out, "w", encoding="utf-8") as f:
    f.write("base=" + (url or "(sin ngrok)") + "\n")
    f.write("playoffs=" + (link or "(sin ngrok)") + "\n")
    if err:
        f.write("error=" + err + "\n")
print("base:", url or ("ERROR " + err))
print("playoffs link:", link)
