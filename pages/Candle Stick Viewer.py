import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import datetime
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")

st.title("Commodity Candlestick Viewer")

# ---------------------
# Commodity tickers
# ---------------------
commodities = {
    "Brent Crude": "BZ=F",
    "WTI Crude": "CL=F",
    "Gold": "GC=F",
    "Silver": "SI=F",
    "Platinum": "PL=F",
    "Copper": "HG=F",
    "Wheat": "ZW=F",
    "Corn": "ZC=F",
    "Natural Gas": "NG=F"
}

# ---------------------
# Top button row
# ---------------------
st.subheader("Select a commodity")

cols = st.columns(len(commodities) + 1)  
selected = None

# Custom ticker button first
if cols[0].button("Custom Ticker"):
    st.session_state["custom_mode"] = True

# If custom mode is active show text input
if st.session_state.get("custom_mode", False):
    custom_ticker = st.text_input("Enter your ticker symbol (e.g. AAPL, BTC-USD):", "")
    if custom_ticker:
        selected = custom_ticker.upper()
        st.session_state["selected_commodity"] = selected

# Then load the notrmal commodity buttons
for i, (name, ticker) in enumerate(commodities.items(), start=1):
    if cols[i].button(name):
        selected = ticker
        st.session_state["selected_commodity"] = ticker
        st.session_state["custom_mode"] = False  

# Fall back to session state if no button pressed this run
if "selected_commodity" in st.session_state and selected is None:
    selected = st.session_state["selected_commodity"]

# If still nothing selected, default to Brent
if selected is None:
    selected = "BZ=F"

# ---------------------
# Sidebar date range with presets
# ---------------------
st.sidebar.subheader("Date Range")

today = datetime.date.today()

# Manual date inputs
start = st.sidebar.date_input("Start date", value=today - datetime.timedelta(days=183), key="manual_start")
end = st.sidebar.date_input("End date", value=today, key="manual_end")

# Preset buttons
presets = {
    "1M": today - datetime.timedelta(days=30),
    "6M": today - datetime.timedelta(days=182),
    "YTD": datetime.date(today.year, 1, 1),
    "1Y": today - datetime.timedelta(days=365),
    "5Y": today - datetime.timedelta(days=365*5)
}

st.sidebar.write("Quick Select:")

cols = st.sidebar.columns(len(presets))
preset_selected = None
for i, (label, preset_start) in enumerate(presets.items()):
    if cols[i].button(label):
        preset_selected = label
        start = preset_start
        end = today
        # store preset choice separately
        st.session_state["active_preset"] = label

# If manual dates are changed, clear the preset button
if (
    start != st.session_state.get("manual_start") or
    end != st.session_state.get("manual_end")
):
    st.session_state["active_preset"] = None

# ---------------------
# Controls for risk tab
# ---------------------
st.sidebar.subheader("Risk Settings")
vol_window = st.sidebar.number_input("Rolling Volatility Window (days)", min_value=5, max_value=252, value=30)
var_level = st.sidebar.slider("VaR Confidence Level (%)", min_value=90, max_value=99, value=95)

# ---------------------
# Fetch extended data (extra year before start for calculating certain mathsy indicators)
# ---------------------
extended_start = start - datetime.timedelta(days=365)
raw = yf.download(selected, start=extended_start, end=end)

# Flatten MultiIndex (I dont remember why I added this)
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0)

# Subset to OHLC + Volume and reset index
data = raw[["Open", "High", "Low", "Close", "Volume"]].dropna().reset_index()

# Filter to display the correct range
display_data = data[(data["Date"] >= pd.to_datetime(start)) & (data["Date"] <= pd.to_datetime(end))]

if display_data.empty:
    st.error("No data found for this date range.")
else:

    # ---------------------
    # Top row: quick metrics
    # ---------------------
    info = yf.Ticker(selected).fast_info

    last_price = float(info.last_price)
    prev_close = float(info.previous_close)
    change_pct = (last_price - prev_close) / prev_close * 100
    change_abs = last_price - prev_close

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(f"{selected} Last Price (Daily % Change)", f"${last_price:.2f}", f"{change_pct:.2f}%")
    with col2:
        st.metric(f"{selected} Previous Close", f"${prev_close:.2f}")
    with col3:
        st.metric(f"{selected} Change ($)", f"${change_abs:.2f}")

    # ---------------------
    # Tabs
    # ---------------------
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Candlestick", 
        "EMA Overlay", 
        "Rolling Volatility & VaR",
        "Bollinger Bands",
        "RSI"
    ])

    # ---------------------
    # Tab 1: Candlestick + Volume
    # ---------------------
    with tab1:
        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=display_data["Date"],
            open=display_data["Open"],
            high=display_data["High"],
            low=display_data["Low"],
            close=display_data["Close"],
            name="Price"
        ))

        fig.add_trace(go.Bar(
            x=display_data["Date"],
            y=display_data["Volume"],
            name="Volume",
            marker_color="grey",
            opacity=0.3,
            yaxis="y2"
        ))

        fig.update_layout(
            title=f"{selected} Daily Candlestick Chart with Volume",
            xaxis=dict(title="Date"),
            yaxis=dict(title="Price (USD)"),
            yaxis2=dict(
                title="Volume",
                overlaying="y",
                side="right",
                showgrid=False,
                visible=False
            ),
            barmode="overlay",
            xaxis_rangeslider_visible=False,
            height=700
        )

        st.plotly_chart(fig, use_container_width=True)

    # ---------------------
    # Tab 2: EMA Overlay
    # ---------------------
    with tab2:
        data["EMA20"] = data["Close"].ewm(span=20, adjust=False).mean()
        data["EMA50"] = data["Close"].ewm(span=50, adjust=False).mean()
        data["EMA200"] = data["Close"].ewm(span=200, adjust=False).mean()

        ema_display = data[(data["Date"] >= pd.to_datetime(start)) & (data["Date"] <= pd.to_datetime(end))]

        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=ema_display["Date"],
            open=ema_display["Open"],
            high=ema_display["High"],
            low=ema_display["Low"],
            close=ema_display["Close"],
            name="Price"
        ))

        fig.add_trace(go.Scatter(x=ema_display["Date"], y=ema_display["EMA20"], line=dict(color="blue"), name="EMA 20"))
        fig.add_trace(go.Scatter(x=ema_display["Date"], y=ema_display["EMA50"], line=dict(color="orange"), name="EMA 50"))
        fig.add_trace(go.Scatter(x=ema_display["Date"], y=ema_display["EMA200"], line=dict(color="green"), name="EMA 200"))

        fig.update_layout(
            title=f"{selected} Daily Candlestick with EMA Overlays",
            xaxis=dict(title="Date"),
            yaxis=dict(title="Price (USD)"),
            xaxis_rangeslider_visible=False,
            height=700
        )

        st.plotly_chart(fig, use_container_width=True)

    # ---------------------
    # Tab 3: Rolling Volatility & VaR
    # ---------------------
    with tab3:
        returns = data[["Date", "Close"]].copy()
        returns["Return"] = returns["Close"].pct_change()

        roll_vol = returns.set_index("Date")["Return"].rolling(f"{vol_window}D").std() * np.sqrt(252)
        roll_var = returns.set_index("Date")["Return"].rolling(f"{vol_window}D").quantile((100 - var_level) / 100.0)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=returns["Date"], y=roll_vol, line=dict(color="purple"), name=f"Annualised Volatility ({vol_window}d)"))
        fig.add_trace(go.Scatter(x=returns["Date"], y=roll_var, line=dict(color="red", dash="dash"), name=f"Rolling VaR {var_level}%"))

        fig.update_layout(
            title=f"{selected} Rolling Volatility & Rolling VaR",
            xaxis=dict(title="Date"),
            yaxis=dict(title="Volatility / VaR"),
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)

    # ---------------------
    # Tab 4: Bollinger Bands
    # ---------------------
    with tab4:
        window = 20
        data["MA20"] = data["Close"].rolling(window).mean()
        data["BB_upper"] = data["MA20"] + 2 * data["Close"].rolling(window).std()
        data["BB_lower"] = data["MA20"] - 2 * data["Close"].rolling(window).std()

        bb_display = data[(data["Date"] >= pd.to_datetime(start)) & (data["Date"] <= pd.to_datetime(end))]

        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=bb_display["Date"], open=bb_display["Open"], high=bb_display["High"], low=bb_display["Low"], close=bb_display["Close"], name="Price"))
        fig.add_trace(go.Scatter(x=bb_display["Date"], y=bb_display["MA20"], line=dict(color="blue"), name="MA 20"))
        fig.add_trace(go.Scatter(x=bb_display["Date"], y=bb_display["BB_upper"], line=dict(color="green", dash="dot"), name="Upper Band"))
        fig.add_trace(go.Scatter(x=bb_display["Date"], y=bb_display["BB_lower"], line=dict(color="red", dash="dot"), name="Lower Band"))

        fig.update_layout(
            title=f"{selected} Bollinger Bands (20d, ±2σ)",
            xaxis=dict(title="Date"),
            yaxis=dict(title="Price (USD)"),
            xaxis_rangeslider_visible=False,
            height=700
        )
        st.plotly_chart(fig, use_container_width=True)

    # ---------------------
    # Tab 5: RSI
    # ---------------------
    with tab5:
        delta = data["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        data["RSI"] = 100 - (100 / (1 + rs))

        rsi_display = data[(data["Date"] >= pd.to_datetime(start)) & (data["Date"] <= pd.to_datetime(end))]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=rsi_display["Date"], y=rsi_display["RSI"], line=dict(color="purple"), name="RSI (14)"))
        fig.add_hline(y=70, line=dict(color="red", dash="dash"), annotation_text="Overbought (70)")
        fig.add_hline(y=30, line=dict(color="green", dash="dash"), annotation_text="Oversold (30)")

        fig.update_layout(
            title=f"{selected} Relative Strength Index (14d)",
            xaxis=dict(title="Date"),
            yaxis=dict(title="RSI", range=[0, 100]),
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

# ---------------------
# Footer
# ---------------------
st.caption(
    """This dashboard is for educational/analytical use only.  
    Data powered by [Yahoo Finance](https://finance.yahoo.com/) and the [yfinance](https://ranaroussi.github.io/yfinance/) python module.  
    You can find me at https://www.linkedin.com/in/harrytbaker/"""
)
