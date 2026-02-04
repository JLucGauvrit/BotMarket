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

if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=["timestamp", "equity"])

# --- Fonctions de récupération ---
GATEWAY_URL = "http://gateway:8000"

def get_data():
    try:
        acct = requests.get(f"{GATEWAY_URL}/account", timeout=2).json()
        pos = requests.get(f"{GATEWAY_URL}/positions", timeout=2).json()
        orders = requests.get(f"{GATEWAY_URL}/orders", timeout=2).json() #
        return acct, pos, orders
    except:
        return None, None, None

# --- UI Principal ---
st.title("⚡ AlgoTrading Control Center")

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
            
            # Mise à jour graphique
            new_entry = pd.DataFrame([{"timestamp": datetime.now(), "equity": equity}])
            st.session_state.history = pd.concat([st.session_state.history, new_entry]).tail(100)

            # 2. Top Bar Metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("💰 Valeur Totale", f"${equity:,.2f}", f"{pl_day:+.2f}")
            col2.metric("💵 Cash Dispo", f"${cash:,.2f}")
            col3.metric("🛒 Buying Power", f"${buying_power:,.2f}")
            col4.metric("📦 Positions Ouvertes", len(positions) if positions else 0)

            # 3. Graphique Performance
            st.subheader("📈 Évolution du Capital")
            fig = px.line(st.session_state.history, x="timestamp", y="equity", template="plotly_dark")
            fig.update_traces(line_color='#F63366')
            st.plotly_chart(fig, use_container_width=True)

            # 4. Tableau des Positions (Métriques détaillées)
            st.markdown("---")
            st.subheader("📦 Positions Actuelles")
            if positions and isinstance(positions, list):
                df_pos = pd.DataFrame(positions)
                
                # Calculs et renommage
                df_pos['Asset'] = df_pos['symbol']
                df_pos['Price'] = df_pos['current_price'].astype(float)
                df_pos['Qty'] = df_pos['qty'].astype(float)
                df_pos['Side'] = df_pos['side'].str.upper()
                df_pos['Market Value'] = df_pos['market_value'].astype(float)
                df_pos['Avg Entry'] = df_pos['avg_entry_price'].astype(float)
                df_pos['Cost Basis'] = df_pos['cost_basis'].astype(float)
                df_pos["Today's P/L (%)"] = df_pos['unrealized_intraday_plpc'].astype(float) * 100
                df_pos["Today's P/L ($)"] = df_pos['unrealized_intraday_pl'].astype(float)
                df_pos["Total P/L (%)"] = df_pos['unrealized_plpc'].astype(float) * 100
                df_pos["Total P/L ($)"] = df_pos['unrealized_pl'].astype(float)

                cols_pos = [
                    'Asset', 'Price', 'Qty', 'Side', 'Market Value', 'Avg Entry', 
                    'Cost Basis', "Today's P/L (%)", "Today's P/L ($)", 
                    "Total P/L (%)", "Total P/L ($)"
                ]
                st.dataframe(df_pos[cols_pos].style.format(precision=2), use_container_width=True)
            else:
                st.info("Aucune position active.")

            # 5. Historique des Ordres
            st.markdown("---")
            st.subheader("📜 Historique des Ordres")
            if orders and isinstance(orders, list):
                df_ord = pd.DataFrame(orders)
                
                df_ord['Asset'] = df_ord['symbol']
                df_ord['Order Type'] = df_ord['order_type'].str.upper()
                df_ord['Side'] = df_ord['side'].str.upper()
                df_ord['Qty'] = df_ord['qty']
                df_ord['Filled Qty'] = df_ord['filled_qty']
                df_ord['Avg. Fill Price'] = df_ord['filled_avg_price']
                df_ord['Status'] = df_ord['status'].str.upper()
                df_ord['Source'] = df_ord['source']
                df_ord['Submitted At'] = pd.to_datetime(df_ord['submitted_at']).dt.strftime('%Y-%m-%d %H:%M')
                df_ord['Filled At'] = pd.to_datetime(df_ord['filled_at']).dt.strftime('%Y-%m-%d %H:%M')
                df_ord['Expires At'] = pd.to_datetime(df_ord['expired_at']).dt.strftime('%Y-%m-%d %H:%M')

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
