"""Lee la URL de ngrok desde la API local y la muestra."""
import urllib.request, json, os

try:
    with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=5) as r:
        data = json.loads(r.read())
    tunnels = data.get("tunnels", [])
    if tunnels:
        for t in tunnels:
            url = t.get("public_url","")
            name = t.get("name","")
            print(f"ngrok URL: {url}  ({name})")
        # Escribir URL al archivo de texto
        url = tunnels[0]["public_url"]
        live_url = url + "/static/becbuc-live.html"
        with open("ngrok_url.txt", "w") as f:
            f.write(f"URL ngrok base: {url}\n")
            f.write(f"BECBUC Live: {live_url}\n")
        print(f"\nBECBUC Live URL: {live_url}")
        print(f"\nGuardado en ngrok_url.txt")
    else:
        print("No hay tunnels activos en ngrok")
except Exception as e:
    print(f"Error: {e}")
    print("ngrok no responde en 127.0.0.1:4040")
input("\nEnter para cerrar...")
