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

# Harde Black-Mode Styling
st.markdown("""
    <style>
    .stApp { background-color: #000000 !important; color: #ffffff !important; }
    [data-testid="stSidebar"] { background-color: #050505 !important; border-right: 1px solid #333 !important; }
    h1, h2, h3, h4, p, label, span { color: #ffffff !important; }
    .stButton>button { background-color: #222 !important; color: white !important; border: 1px solid #444 !important; font-weight: bold; width: 100%; }
    .stButton>button:hover { border-color: #39d353 !important; color: #39d353 !important; }
    .metric-container { background-color: #111; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    /* Styling voor de tabel */
    .stTable { background-color: #050505 !important; color: white !important; }
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
    return ["AAPL", "NVDA", "TSLA", "MSFT"]

def get_earnings_date(ticker):
    try:
        url = f"https://finance.yahoo.com/quote/{ticker}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        text = soup.get_text()
        match = re.search(r'Earnings Date([A-Za-z0-9\s,]+)', text)
        return match.group(1).strip().split('-')[0].strip() if match else "N/A"
    except: return "N/A"

# --- 4. AI & PINE SCRIPT LOGICA ---
def run_full_analysis(ticker):
    try:
        data = yf.Ticker(ticker).history(period="200d")
        if data.empty: return None
        
        curr_p = float(data['Close'].iloc[-1])
        prev_p = float(data['Close'].iloc[-2])
        change = ((curr_p / prev_p) - 1) * 100
        
        # --- Pine Script Code 3 & 4 Vertaling ---
        # EMA's
        ema20 = data['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = data['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
        ema200 = data['Close'].ewm(span=200, adjust=False).mean().iloc[-1]
        
        # Trend Score (Code 3)
        bull_trend = (10 if curr_p > ema20 else 0) + (10 if ema20 > ema50 else 0) + (10 if ema50 > ema200 else 0)
        ai_pine_score = 50 + (bull_trend * 1.5)
        
        # Exit Engine (Code 4)
        atr = (data['High'] - data['Low']).rolling(14).mean().iloc[-1]
        long_tp = curr_p + (atr * 2.5)
        long_sl = curr_p - (atr * 1.5)

        # --- Lineaire Regressie (Code 1 & 2) ---
        y = data['Close'].values.reshape(-1, 1)
        X = np.array(range(len(y))).reshape(-1, 1)
        reg = LinearRegression().fit(X, y)
        pred = float(reg.predict(np.array([[len(y)]]))[0][0])
        
        # Ensemble Score
        ensemble = int(72 + (12 if pred > curr_p else -8))
        
        # Status Bepaling
        status, col, ico = "HOLD", "#d29922", "⏳"
        if (ensemble > 75 or ai_pine_score > 75):
            status, col, ico = "BUY", "#39d353", "🚀"
        elif ensemble < 65:
            status, col, ico = "AVOID", "#f85149", "⚠️"

        return {
            "T": ticker, "P": curr_p, "C": change, "E": ensemble, 
            "AI_PINE": ai_pine_score, "TP": long_tp, "SL": long_sl,
            "ST": status, "COL": col, "ICO": ico, "EARN": get_earnings_date(ticker),
            "DATA": data, "PRED": pred
        }
    except: return None

# --- 5. HOOFD DASHBOARD ---
if not st.session_state.logged_in:
    login_screen()
else:
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = load_watchlist()

    # Sidebar
    with st.sidebar:
        st.title("🛡️ SST Terminal")
        st.write(f"Ingelogd: **{st.session_state.user_email}**")
        
        input_string = st.text_area("Voeg Tickers toe (bijv: AAPL, TSLA)")
        if st.button("➕ Toevoegen aan lijst"):
            new_tickers = [t.strip().upper() for t in input_string.split(',') if t.strip()]
            st.session_state.watchlist = list(dict.fromkeys(st.session_state.watchlist + new_tickers))
            save_watchlist(st.session_state.watchlist)
            st.rerun()
            
        if st.button("🗑️ Wis Watchlist"):
            st.session_state.watchlist = []
            save_watchlist([])
            st.rerun()
            
        if st.button("🚪 Uitloggen"):
            st.session_state.logged_in = False
            st.rerun()

    st.title("🏹 AI Strategy Master Terminal")

    # --- GRID WATCHLIST (Onbeperkt aandelen tonen) ---
    @st.fragment(run_every=30)
    def show_live_dashboard():
        if not st.session_state.watchlist:
            st.info("Je watchlist is leeg. Voeg tickers toe in de sidebar.")
            return

        st.subheader("🔄 Live Watchlist Grid")
        num_cols = 4 # Aantal blokken per rij
        watchlist = st.session_state.watchlist
        
        for i in range(0, len(watchlist), num_cols):
            cols = st.columns(num_cols)
            batch = watchlist[i:i + num_cols]
            for j, ticker in enumerate(batch):
                res = run_full_analysis(ticker)
                if res:
                    with cols[j]:
                        st.markdown(f"""
                        <div style="border: 1px solid {res['COL']}; padding: 12px; border-radius: 10px; background-color: #0a0a0a; text-align: center; margin-bottom: 15px;">
                            <h4 style="margin:0; color: #aaa;">{res['T']}</h4>
                            <h2 style="color:{res['COL']}; margin:5px 0;">{res['ICO']} {res['ST']}</h2>
                            <p style="margin:0; font-size: 1.1em; font-weight: bold;">${res['P']:.2f}</p>
                            <p style="margin:0; color: {res['COL']}; font-size: 0.9em;">{res['C']:+.2f}%</p>
                            <div style="margin-top:8px; font-size: 0.75em; color: #666; border-top: 1px solid #222; padding-top: 5px;">
                                AI: {res['E']}% | Pine: {res['AI_PINE']:.0f}%
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

        st.markdown("---")
        
        # --- DETAIL ANALYSE ---
        st.subheader("🔍 Gedetailleerde Analyse")
        selected_stock = st.selectbox("Selecteer aandeel uit lijst:", st.session_state.watchlist)
        
        if selected_stock:
            res = run_full_analysis(selected_stock)
            if res:
                col_left, col_right = st.columns([2, 1])
                
                with col_left:
                    st.line_chart(res['DATA']['Close'], use_container_width=True)
                    
                    # Strategie Tabel
                    df_strat = pd.DataFrame([
                        {"Methode": "AI Ensemble Learning", "Score": f"{res['E']}%", "Status": "BUY" if res['E'] >= 75 else "HOLD"},
                        {"Methode": "Pine Script AI Engine", "Score": f"{res['AI_PINE']:.0f}%", "Status": "BUY" if res['AI_PINE'] >= 75 else "HOLD"},
                        {"Methode": "Linear Regression", "Score": "Bullish" if res['PRED'] > res['P'] else "Bearish", "Status": "UP" if res['PRED'] > res['P'] else "DOWN"},
                        {"Methode": "Volatility Exit", "Score": "N/A", "Status": "READY", "Target": f"${res['TP']:.2f}"}
                    ])
                    st.table(df_strat)

                with col_right:
                    st.markdown(f"""
                    <div class="metric-container" style="border-left: 5px solid {res['COL']};">
                        <h3 style="color: {res['COL']};">Market Intel</h3>
                        <p style="color: #888;">Ticker: <b>{res['T']}</b></p>
                        <hr style="border-color: #333;">
                        <h4 style="color: #39d353;">🚀 AI Exit Engine</h4>
                        <p style="margin: 5px 0;"><b>Take Profit:</b> <span style="font-size: 1.2em;">${res['TP']:.2f}</span></p>
                        <p style="margin: 5px 0;"><b>Stop Loss:</b> <span style="font-size: 1.2em; color: #f85149;">${res['SL']:.2f}</span></p>
                        <hr style="border-color: #333;">
                        <p>📅 <b>Earnings Date:</b><br>{res['EARN']}</p>
                        <p style="font-size: 0.8em; color: #555; margin-top: 20px;">
                            * Pine Script Exit Engine berekent TP/SL op basis van 2.5x en 1.5x ATR.
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

    show_live_dashboard()
