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

# Initialisation de l'historique dans la session
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=["timestamp", "equity"])

# --- Fonctions de récupération ---
GATEWAY_URL = "http://gateway:8000"

def get_data():
    try:
        acct = requests.get(f"{GATEWAY_URL}/account", timeout=2).json()
        pos = requests.get(f"{GATEWAY_URL}/positions", timeout=2).json()
        orders = requests.get(f"{GATEWAY_URL}/orders", timeout=2).json()
        return acct, pos, orders
    except Exception as e:
        return None, None, None

# --- UI Principal ---
st.title("⚡ AlgoTrading Control Center")

# Utilisation d'un placeholder pour éviter le rafraîchissement complet de la page
placeholder = st.empty()

while True:
    account, positions, orders = get_data()
    
    with placeholder.container():
        if account and 'equity' in account:
            # 1. Extraction des données financières
            equity = float(account['equity'])
            cash = float(account['cash'])
            buying_power = float(account['buying_power'])
            last_equity = float(account.get('last_equity', equity))
            pl_day = equity - last_equity
            
            # --- MISE À JOUR DE L'HISTORIQUE DE PERFORMANCE ---
            new_entry = pd.DataFrame([{"timestamp": datetime.now(), "equity": equity}])
            
            # Correction de la concaténation (FutureWarning)
            # On ne concatène que si les données existent pour éviter l'erreur de types
            to_concat = [df for df in [st.session_state.history, new_entry] if not df.empty]
            if to_concat:
                st.session_state.history = pd.concat(to_concat, ignore_index=True)
            
            # Limitation à 100 points pour la fluidité
            if len(st.session_state.history) > 100:
                st.session_state.history = st.session_state.history.iloc[-100:]

            # 2. Top Bar Metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("💰 Valeur Totale", f"${equity:,.2f}", f"{pl_day:+.2f}")
            col2.metric("💵 Cash Dispo", f"${cash:,.2f}")
            col3.metric("🛒 Buying Power", f"${buying_power:,.2f}")
            col4.metric("📦 Positions Ouvertes", len(positions) if positions else 0)

            # 3. Graphique Performance
            st.subheader("📈 Évolution du Capital")
            if not st.session_state.history.empty:
                fig = px.line(st.session_state.history, x="timestamp", y="equity", template="plotly_dark")
                fig.update_traces(line_color='#F63366')
                st.plotly_chart(fig, width="stretch")

            # 4. Tableau des Positions
            st.markdown("---")
            st.subheader("📦 Positions Actuelles")
            if positions and isinstance(positions, list):
                df_pos = pd.DataFrame(positions)
                
                # Conversion sécurisée des types
                df_pos['Asset'] = df_pos['symbol']
                df_pos['Price'] = pd.to_numeric(df_pos['current_price'], errors='coerce')
                df_pos['Qty'] = pd.to_numeric(df_pos['qty'], errors='coerce')
                df_pos['Side'] = df_pos['side'].str.upper()
                df_pos['Market Value'] = pd.to_numeric(df_pos['market_value'], errors='coerce')
                
                cols_to_show = ['Asset', 'Price', 'Qty', 'Side', 'Market Value']
                st.dataframe(df_pos[cols_to_show].style.format(precision=2), width="stretch")
            else:
                st.info("Aucune position active.")

            # 5. Historique des Ordres
            st.markdown("---")
            st.subheader("📜 Historique des Ordres")
            if orders and isinstance(orders, list):
                df_ord = pd.DataFrame(orders)
                
                # Nettoyage et formatage
                df_ord['Asset'] = df_ord['symbol']
                df_ord['Order Type'] = df_ord['order_type'].str.upper() if 'order_type' in df_ord.columns else 'MARKET'
                df_ord['Side'] = df_ord['side'].str.upper()
                df_ord['Status'] = df_ord['status'].str.upper()

                # Correction KeyError: 'source'
                if 'source' in df_ord.columns:
                    df_ord['Source'] = df_ord['source']
                else:
                    df_ord['Source'] = 'Alpaca'
                
                # Formatage des dates
                for col in ['submitted_at', 'filled_at']:
                    if col in df_ord.columns:
                        df_ord[col] = pd.to_datetime(df_ord[col]).dt.strftime('%H:%M:%S')

                cols_ord = [
                    'Asset', 'Order Type', 'Side', 'Qty', 'Filled Qty', 
                    'Avg. Fill Price', 'Status', 'Source', 'Submitted At', 
                    'Filled At', 'Expires At'
                ]
                st.dataframe(df_ord[cols_ord], use_container_width=True)
            else:
                st.info("Aucun ordre dans l'historique.")
                
        elif account and "error" in account:
            st.error(f"❌ Erreur Alpaca : {account['error']}")
        else:
            st.error("⚠️ Connexion à la Gateway impossible.")

    time.sleep(2)
    