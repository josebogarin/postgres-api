print("inicio")
import urllib.request
print("urllib ok")
try:
    r = urllib.request.urlopen("http://localhost:8000/api/v1/bets/ranking/2", timeout=5)
    print("server OK:", r.status)
    r.close()
except Exception as e:
    print("server error:", type(e).__name__, str(e)[:100])
print("fin")
