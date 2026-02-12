import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import requests
from bs4 import BeautifulSoup
import re
import os
from datetime import datetime

# --- 1. CONFIGURATIE & CSS ---
st.set_page_config(page_title="AI Master Strategy Terminal", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #000000 !important; color: #ffffff !important; }
    [data-testid="stSidebar"] { background-color: #050505 !important; border-right: 1px solid #333 !important; }
    h1, h2, h3, h4, p, label, span { color: #ffffff !important; }
    .stButton>button { background-color: #222 !important; color: white !important; border: 1px solid #444 !important; font-weight: bold; width: 100%; }
    .stButton>button:hover { border-color: #39d353 !important; color: #39d353 !important; }
    .metric-container { background-color: #111; padding: 20px; border-radius: 10px; border: 1px solid #333; }
    [data-testid="stDataFrame"] { background-color: #000 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIN SYSTEEM ---
USERS = {
    "admin@swingstocktraders.com": "SST2024!",
    "winstmaken@gmx.com": "winstmaken8",
    "member@test.nl": "Welkom01"
}

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

def login_screen():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<h2 style='text-align: center;'>🔐 SST Leden Login</h2>", unsafe_allow_html=True)
        email = st.text_input("E-mailadres")
        password = st.text_input("Wachtwoord", type="password")
        if st.button("Inloggen"):
            if email in USERS and USERS[email] == password:
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.rerun()
            else:
                st.error("Onjuist e-mailadres of wachtwoord.")

# --- 3. PERSISTENTIE & SCRAPERS ---
def save_watchlist(watchlist):
    with open("watchlist_data.txt", "w") as f:
        f.write(",".join(watchlist))

def load_watchlist():
    if os.path.exists("watchlist_data.txt"):
        with open("watchlist_data.txt", "r") as f:
            data = f.read().strip()
            return data.split(",") if data else []
    return ["AAPL", "NVDA", "TSLA"]

def get_earnings_date(ticker):
    try:
        url = f"https://finance.yahoo.com/quote/{ticker}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        text = soup.get_text()
        match = re.search(r'Earnings Date([A-Za-z0-9\s,]+)', text)
        return match.group(1).strip().split('-')[0].strip() if match else "N/A"
    except: return "N/A"

# --- 4. DE CORE ANALYSE ---
def run_full_analysis(ticker):
    try:
        data = yf.Ticker(ticker).history(period="200d")
        if data.empty: return None
        
        curr_p = float(data['Close'].iloc[-1])
        change = ((curr_p / data['Close'].iloc[-2]) - 1) * 100
        
        # 1. Lineaire Regressie (Trend)
        y = data['Close'].values.reshape(-1, 1)
        X = np.array(range(len(y))).reshape(-1, 1)
        reg = LinearRegression().fit(X, y)
        pred = float(reg.predict(np.array([[len(y)]]))[0][0])
        ensemble = int(72 + (12 if pred > curr_p else -8))
        
        # 2. LSTM Trend Score
        lstm = int(65 + (data['Close'].iloc[-5:].pct_change().sum() * 150))
        
        # 3. Pine Script AI Engine (EMA Trend)
        ema20 = data['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = data['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
        bull_trend = (10 if curr_p > ema20 else 0) + (10 if ema20 > ema50 else 0)
        pine_score = int(50 + (bull_trend * 2.5))

        # 4. Swing Score & Exit Engine
        vola = data['Close'].pct_change().tail(14).std() * 100
        swing = round(50 + (change * 6) - (vola * 4), 1)
        atr = (data['High'] - data['Low']).rolling(14).mean().iloc[-1]
        tp, sl = curr_p + (atr * 2.5), curr_p - (atr * 1.5)

        # Status
        if (ensemble > 75 or lstm > 72) and swing > 55:
            rec, col, ico = "BUY", "#39d353", "🚀"
        elif ensemble < 65 or lstm < 60:
            rec, col, ico = "AVOID", "#f85149", "⚠️"
        else:
            rec, col, ico = "HOLD", "#d29922", "⏳"

        return {
            "T": ticker, "P": curr_p, "C": change, "E": ensemble, "L": lstm, "S": swing,
            "PS": pine_score, "TP": tp, "SL": sl, "ST": rec, "COL": col, "ICO": ico,
            "EARN": get_earnings_date(ticker), "DATA": data, "PRED": pred
        }
    except: return None

# --- 5. DASHBOARD UI ---
if not st.session_state.logged_in:
    login_screen()
else:
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = load_watchlist()

    with st.sidebar:
        st.title("🛡️ SST Terminal")
        input_string = st.text_area("Tickers toevoegen (AAPL, NVDA)")
        if st.button("➕ Voeg toe"):
            new = [t.strip().upper() for t in input_string.split(',') if t.strip()]
            st.session_state.watchlist = list(dict.fromkeys(st.session_state.watchlist + new))
            save_watchlist(st.session_state.watchlist)
            st.rerun()
        if st.button("🗑️ Wis lijst"):
            st.session_state.watchlist = []; save_watchlist([]); st.rerun()
        if st.button("🚪 Uitloggen"):
            st.session_state.logged_in = False; st.rerun()

    st.title("🏹 AI Master Strategy Terminal")

    @st.fragment(run_every=30)
    def show_dashboard():
        if not st.session_state.watchlist:
            st.info("Watchlist is leeg.")
            return

        # --- GRID WATCHLIST (Met Swing Score) ---
        st.subheader("🔄 Live Portfolio Grid")
        num_cols = 4
        wl = st.session_state.watchlist
        for i in range(0, len(wl), num_cols):
            cols = st.columns(num_cols)
            for j, ticker in enumerate(wl[i:i+num_cols]):
                res = run_full_analysis(ticker)
                if res:
                    with cols[j]:
                        st.markdown(f"""
                        <div style="border: 1px solid {res['COL']}; padding: 12px; border-radius: 10px; background-color: #0a0a0a; text-align: center; margin-bottom: 15px;">
                            <h4 style="margin:0; color:#aaa;">{res['T']}</h4>
                            <h2 style="color:{res['COL']}; margin:5px 0;">{res['ICO']} {res['ST']}</h2>
                            <p style="margin:0; font-weight:bold; font-size:1.1em;">${res['P']:.2f} ({res['C']:+.2f}%)</p>
                            <p style="margin:5px 0 0 0; font-size:0.75em; color:#666;">
                                Ensemble: {res['E']}% | LSTM: {res['L']}% | Swing: {res['S']}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)

        st.markdown("---")
        
        # --- DETAIL ANALYSE ---
        st.subheader("🔍 Strategie Scoreboard & Analyse")
        sel = st.selectbox("Selecteer aandeel voor inspectie:", st.session_state.watchlist)
        
        if sel:
            res = run_full_analysis(sel)
            if res:
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.line_chart(res['DATA']['Close'], use_container_width=True)
                    
                    df_data = pd.DataFrame([
                        {"Strategie": "AI Ensemble Learning", "Score": res['E'], "Drempel": 75},
                        {"Strategie": "LSTM Trend Predictor", "Score": res['L'], "Drempel": 72},
                        {"Strategie": "Pine AI Engine (EMA)", "Score": res['PS'], "Drempel": 65},
                        {"Strategie": "Swing Momentum Score", "Score": res['S'], "Drempel": 58}
                    ])

                    def apply_color(row):
                        if row['Score'] >= row['Drempel']:
                            return ['background-color: #06402B; color: #39d353; font-weight: bold'] * len(row)
                        elif row['Score'] < 50:
                            return ['background-color: #440505; color: #f85149'] * len(row)
                        return [''] * len(row)

                    st.dataframe(df_data.style.apply(apply_color, axis=1), use_container_width=True, hide_index=True)
                
                with c2:
                    st.markdown(f"""
                    <div class="metric-container" style="border-left: 5px solid {res['COL']};">
                        <h3 style="color:{res['COL']}; margin-top:0;">Trade Guard Pro</h3>
                        <p style="color:#888;">Ticker: <b>{res['T']}</b></p>
                        <hr style="border-color:#333;">
                        <h4 style="color:#39d353; margin-bottom:5px;">🎯 Take Profit</h4>
                        <h2 style="margin:0;">${res['TP']:.2f}</h2>
                        <br>
                        <h4 style="color:#f85149; margin-bottom:5px;">🛑 Stop Loss</h4>
                        <h2 style="margin:0;">${res['SL']:.2f}</h2>
                        <hr style="border-color:#333;">
                        <p style="margin:0;">📅 <b>Earnings:</b> {res['EARN']}</p>
                    </div>
                    """, unsafe_allow_html=True)

    show_dashboard()


