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

# Initialisation de l'historique
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
    except Exception:
        return None, None, None

# --- UI Principal ---
st.title("⚡ AlgoTrading Control Center")

placeholder = st.empty()

while True:
    account, positions, orders = get_data()
    
    with placeholder.container():
        if account and 'equity' in account:
            # 1. Données Financières
            equity = float(account.get('equity', 0))
            cash = float(account.get('cash', 0))
            buying_power = float(account.get('buying_power', 0))
            last_equity = float(account.get('last_equity', equity))
            pl_day = equity - last_equity
            
            # Mise à jour historique
            new_entry = pd.DataFrame([{"timestamp": datetime.now(), "equity": equity}])
            to_concat = [df for df in [st.session_state.history, new_entry] if not df.empty]
            if to_concat:
                st.session_state.history = pd.concat(to_concat, ignore_index=True)
                # On garde les 100 derniers points
                if len(st.session_state.history) > 100:
                    st.session_state.history = st.session_state.history.iloc[-100:]

            # 2. Métriques
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("💰 Valeur Totale", f"${equity:,.2f}", f"{pl_day:+.2f}")
            col2.metric("💵 Cash Dispo", f"${cash:,.2f}")
            col3.metric("🛒 Buying Power", f"${buying_power:,.2f}")
            col4.metric("📦 Positions", len(positions) if positions else 0)

            # 3. Graphique
            st.subheader("📈 Performance")
            if not st.session_state.history.empty:
                fig = px.line(st.session_state.history, x="timestamp", y="equity", template="plotly_dark")
                fig.update_traces(line_color='#F63366')
                st.plotly_chart(fig, width="stretch")

            # 4. Positions
            st.markdown("---")
            st.subheader("📦 Positions Actuelles")
            if positions and isinstance(positions, list):
                df_pos = pd.DataFrame(positions)
                
                # Création sécurisée des colonnes d'affichage
                df_pos['Asset'] = df_pos['symbol']
                df_pos['Qty'] = pd.to_numeric(df_pos['qty'], errors='coerce')
                df_pos['Price'] = pd.to_numeric(df_pos['current_price'], errors='coerce')
                df_pos['Side'] = df_pos['side'].str.upper()
                df_pos['Market Value'] = pd.to_numeric(df_pos['market_value'], errors='coerce')
                df_pos['Cost Basis'] = pd.to_numeric(df_pos['cost_basis'], errors='coerce')
                df_pos['P/L ($)'] = pd.to_numeric(df_pos['unrealized_pl'], errors='coerce')
                
                # Sélection des colonnes
                cols_pos = ['Asset', 'Side', 'Qty', 'Price', 'Market Value', 'Cost Basis', 'P/L ($)']
                # On s'assure qu'elles existent toutes
                actual_cols = [c for c in cols_pos if c in df_pos.columns]
                
                st.dataframe(df_pos[actual_cols].style.format(precision=2), width="stretch")
            else:
                st.info("Aucune position active.")

            # 5. Historique des Ordres (La partie qui plantait)
            st.markdown("---")
            st.subheader("📜 Historique des Ordres")
            if orders and isinstance(orders, list):
                df_ord = pd.DataFrame(orders)
                
                # --- CORRECTION DU KEYERROR ---
                # On crée explicitement les colonnes avec des noms conviviaux
                # .get(..., 0) ou .get(..., '') évite le plantage si la clé manque
                df_ord['Asset'] = df_ord['symbol']
                df_ord['Type'] = df_ord.get('order_type', 'market').astype(str).str.upper()
                df_ord['Side'] = df_ord.get('side', '').astype(str).str.upper()
                df_ord['Qty'] = df_ord.get('qty', 0)
                df_ord['Filled Qty'] = df_ord.get('filled_qty', 0)
                df_ord['Avg Price'] = df_ord.get('filled_avg_price', 0.0)
                df_ord['Status'] = df_ord.get('status', '').astype(str).str.upper()
                
                # Gestion de la date (Submitted At)
                if 'submitted_at' in df_ord.columns:
                    df_ord['Submitted'] = pd.to_datetime(df_ord['submitted_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    df_ord['Submitted'] = '-'

                # Colonnes finales à afficher
                cols_ord = ['Asset', 'Type', 'Side', 'Qty', 'Filled Qty', 'Avg Price', 'Status', 'Submitted']
                
                # Filtrage de sécurité (au cas où)
                final_cols = [c for c in cols_ord if c in df_ord.columns]
                
                # Correction deprecated argument: width='stretch' remplace use_container_width=True
                # Note: 'width=None' laisse Streamlit gérer, souvent équivalent à stretch en responsive
                st.dataframe(df_ord[final_cols], width="stretch")
            else:
                st.info("Aucun ordre récent.")

        elif account and "error" in account:
            st.error(f"❌ Erreur Alpaca : {account['error']}")
        else:
            st.error("⚠️ En attente de la Gateway...")

    time.sleep(2)
    