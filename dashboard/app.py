import streamlit as st
import pandas as pd
import requests
import time
import plotly.express as px
from datetime import datetime

# --- Configuration de la page ---
st.set_page_config(
    page_title="Bot Dashboard",
    page_icon="📈",
    layout="wide"
)

# Initialisation d'un historique en mémoire pour le graphique (Optionnel si pas de DB)
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=["timestamp", "equity"])

# --- Fonctions de récupération ---
GATEWAY_URL = "http://gateway:8000"

def get_data():
    try:
        # On vérifie les réponses avant de les transformer en JSON
        r_acct = requests.get(f"{GATEWAY_URL}/account", timeout=5)
        r_pos = requests.get(f"{GATEWAY_URL}/positions", timeout=5)
        
        if r_acct.status_code == 200 and r_pos.status_code == 200:
            return r_acct.json(), r_pos.json()
        else:
            # Affiche l'erreur d'authentification Alpaca si présente
            return {"error": r_acct.text}, None
    except Exception as e:
        return None, None

# --- UI Principal ---
st.title("⚡ AlgoTrading Control Center")

placeholder = st.empty()

while True:
    account, positions = get_data()
    
    with placeholder.container():
        # Sécurité : Vérification que 'equity' existe dans la réponse
        if account and 'equity' in account:
            # 1. Extraction des données
            equity = float(account['equity'])
            cash = float(account['cash'])
            buying_power = float(account['buying_power'])
            last_equity = float(account.get('last_equity', equity))
            pl = equity - last_equity
            
            # Mise à jour de l'historique pour le graphique
            new_entry = pd.DataFrame([{"timestamp": datetime.now(), "equity": equity}])
            st.session_state.history = pd.concat([st.session_state.history, new_entry]).tail(100)

            # 2. Métriques Clés
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("💰 Valeur Totale", f"${equity:,.2f}", f"{pl:+.2f}")
            col2.metric("💵 Cash Dispo", f"${cash:,.2f}")
            col3.metric("🛒 Buying Power", f"${buying_power:,.2f}")
            col4.metric("📦 Positions Ouvertes", len(positions) if positions else 0)

            # 3. Graphique de Performance
            st.subheader("Évolution du Capital (Live)")
            fig = px.line(st.session_state.history, x="timestamp", y="equity", template="plotly_dark")
            fig.update_traces(line_color='#F63366')
            st.plotly_chart(fig, use_container_width=True)

            # 4. Tableau des Positions
            st.markdown("---")
            if positions and isinstance(positions, list):
                st.subheader("Positions Actuelles")
                df = pd.DataFrame(positions)
                cols_to_keep = ['symbol', 'qty', 'current_price', 'market_value', 'unrealized_pl']
                display_df = df[[c for c in cols_to_keep if c in df.columns]]
                st.dataframe(display_df, use_container_width=True)
            else:
                st.info("Aucune position active.")
                
        elif account and "error" in account:
            st.error(f"❌ Erreur Alpaca : {account['error']}")
            st.warning("Vérifiez vos clés API Paper Trading dans le fichier .env.")
        else:
            st.error("⚠️ Gateway injoignable. Vérifiez Docker.")

    time.sleep(2)
    