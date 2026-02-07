import requests

# URL de ta Gateway (localhost car tu es hors docker)
url = "http://localhost:8000/order"

payload = {
    "symbol": "DOGE/USD",
    "side": "buy",
    "qty": 10,  # On met 10 pour dépasser le $1 minimum
    "type": "market",
    "time_in_force": "gtc"
}

print(f"Envoi de: {payload}")
resp = requests.post(url, json=payload)

print(f"Code: {resp.status_code}")
print(f"Réponse: {resp.text}") # <--- C'est ça qu'on veut voir !