import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide")  # full width

st.title("HB's Oil Dashboard (Brent vs WTI)")

# -------------------------
# Sidebar date range with presets
# -------------------------
st.sidebar.subheader("Date Range")

today = datetime.date.today()

# Preset buttons
presets = {
    "1M": today - datetime.timedelta(days=30),
    "6M": today - datetime.timedelta(days=182),
    "YTD": datetime.date(today.year, 1, 1),
    "1Y": today - datetime.timedelta(days=365),
    "5Y": today - datetime.timedelta(days=365*5)
}

# Initialize session state once
if "manual_start" not in st.session_state:
    st.session_state.manual_start = today - datetime.timedelta(days=365)
if "manual_end" not in st.session_state:
    st.session_state.manual_end = today

# Quick select buttons – update state BEFORE widgets are drawn
st.sidebar.write("Quick Select:")
cols = st.sidebar.columns(len(presets))
for i, (label, preset_start) in enumerate(presets.items()):
    if cols[i].button(label):
        st.session_state.manual_start = preset_start
        st.session_state.manual_end = today
        st.session_state.active_preset = label

# Now render widgets (they reflect updated state automatically)
start = st.sidebar.date_input("Start date", key="manual_start")
end   = st.sidebar.date_input("End date", key="manual_end")



# -------------------------
# Determine interval based on requested range
# -------------------------
delta_days = (end - start).days
if delta_days <= 7:
    interval = "1m"     # up to 7 days
elif delta_days <= 60:
    interval = "15m"    # up to ~60 days
else:
    interval = "1d"     # daily data for longer spans

# -------------------------
# Fetch Brent & WTI historical data (for charts/analysis)
# -------------------------
tickers = {"Brent": "BZ=F", "WTI": "CL=F"}
data = yf.download(
    list(tickers.values()),
    start=start,
    end=end,
    interval=interval
)["Close"].dropna()

data = data.rename(columns={v: k for k, v in tickers.items()})

st.caption(f"Data interval automatically set to **{interval}** based on requested date range ({delta_days} days).")

# -------------------------
# Fetch current quote info (for Yahoo-style metrics)
# -------------------------
brent_info = yf.Ticker("BZ=F").fast_info
wti_info   = yf.Ticker("CL=F").fast_info

brent_live   = float(brent_info.last_price)
brent_prev   = float(brent_info.previous_close)
brent_change = (brent_live - brent_prev) / brent_prev * 100

wti_live     = float(wti_info.last_price)
wti_prev     = float(wti_info.previous_close)
wti_change   = (wti_live - wti_prev) / wti_prev * 100

# -------------------------
# Top row: quick metrics
# -------------------------
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric("Brent Last Price", f"${brent_live:.2f}", f"{brent_change:.2f}%")
with col2:
    st.metric("Brent Previous Close", f"${brent_prev:.2f}")
with col3:
    st.metric("Brent Change ($)", f"${(brent_live - brent_prev):.2f}")

with col4:
    st.metric("WTI Last Price", f"${wti_live:.2f}", f"{wti_change:.2f}%")
with col5:
    st.metric("WTI Previous Close", f"${wti_prev:.2f}")
with col6:
    st.metric("WTI Change ($)", f"${(wti_live - wti_prev):.2f}")

# -------------------------
# Middle row: price chart + returns chart
# -------------------------
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Brent vs WTI Price Chart")
    fig = px.line(data, x=data.index, y=["Brent", "WTI"], 
                  labels={"value": "Price (USD)", "variable": "Crude Type", "index": "Date"})
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Returns Comparison")
    returns = data.pct_change().dropna()
    fig = px.line(returns, x=returns.index, y=["Brent", "WTI"],
                  labels={"value": "Returns", "variable": "Crude Type", "index": "Date"})
    st.plotly_chart(fig, use_container_width=True)

# -------------------------
# Bottom row: tabs for extra analysis
# -------------------------
st.subheader("More Analysis")

tab1, tab2, tab3, tab4 = st.tabs([
    "Rolling Volatility", 
    "Rolling Mean & Std", 
    "Brent–WTI Spread", 
    "Rolling Correlation"
])

# -------------------------
# Rolling Volatility
# -------------------------
with tab1:
    vol = returns.rolling("30D").std() * np.sqrt(252)
    vol.columns = [f"Volatility_{col}" for col in vol.columns]  # flatten names
    fig = px.line(vol, x=vol.index, y=vol.columns,
                  labels={"value": "Volatility (Annualized)", "variable": "Crude Type", "index": "Date"})
    st.plotly_chart(fig, use_container_width=True)


# -------------------------
# Rolling Mean & Std
# -------------------------
with tab2:
    # Sidebar control for rolling window size (days)
    window_days = st.sidebar.number_input(
        "Rolling window (days)", 
        min_value=1, max_value=365, value=30, step=1
    )

    # Check if date range is long enough
    if (end - start).days < window_days:
        st.error(f"Not enough data for a {window_days}-day rolling window. "
                 f"Please select a larger viewing window.")
    else:
        # Calculate rolling stats using time-based window
        roll_mean = data.rolling(f"{window_days}D").mean()
        roll_std = data.rolling(f"{window_days}D").std()

        from plotly.subplots import make_subplots
        import plotly.graph_objects as go

        # Create subplots: 2 rows, 1 column
        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            subplot_titles=(f"{window_days}-Day Rolling Mean", 
                            f"{window_days}-Day Rolling Std")
        )

        # Row 1: Rolling Mean
        fig.add_trace(go.Scatter(
            x=roll_mean.index, y=roll_mean["Brent"], 
            mode="lines", name="Mean Brent"
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=roll_mean.index, y=roll_mean["WTI"], 
            mode="lines", name="Mean WTI"
        ), row=1, col=1)

        # Row 2: Rolling Std
        fig.add_trace(go.Scatter(
            x=roll_std.index, y=roll_std["Brent"], 
            mode="lines", name="Std Brent"
        ), row=2, col=1)

        fig.add_trace(go.Scatter(
            x=roll_std.index, y=roll_std["WTI"], 
            mode="lines", name="Std WTI"
        ), row=2, col=1)

        # Axis labels
        fig.update_xaxes(title="Date", row=2, col=1)
        fig.update_yaxes(title="Price (USD)", row=1, col=1)
        fig.update_yaxes(title="Std (USD)", row=2, col=1)

        fig.update_layout(height=600, 
                          title_text=f"Rolling Mean & Std ({window_days}-Day)")

        st.plotly_chart(fig, use_container_width=True)


# -------------------------
# Brent–WTI Spread
# -------------------------
with tab3:
    st.subheader("Brent–WTI Spread Analysis")
    spread = data["Brent"] - data["WTI"]

    # Metrics
    spread_current = spread.iloc[-1]
    spread_avg = spread.mean()
    spread_p5 = np.percentile(spread, 5)
    spread_p95 = np.percentile(spread, 95)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Current Spread", f"${spread_current:.2f}")
    with col2:
        st.metric("Average Spread", f"${spread_avg:.2f}")
    with col3:
        st.metric("5th Percentile", f"${spread_p5:.2f}")
    with col4:
        st.metric("95th Percentile", f"${spread_p95:.2f}")

    fig1 = px.line(x=spread.index, y=spread.values,
                   labels={"x": "Date", "y": "Spread (USD)"})
    st.plotly_chart(fig1, use_container_width=True)

    hist = px.histogram(spread, nbins=30, 
                        labels={"value": "Spread (USD)"})
    st.plotly_chart(hist, use_container_width=True)

# -------------------------
# Rolling Correlation
# -------------------------
with tab4:
    st.subheader("90-Day Rolling Correlation (Brent vs WTI)")
    rolling_corr = data["Brent"].rolling("90D").corr(data["WTI"])
    fig = px.line(x=rolling_corr.index, y=rolling_corr.values,
                  labels={"x": "Date", "y": "Correlation"})
    st.plotly_chart(fig, use_container_width=True)

# ---------------------
# Footer
# ---------------------
st.caption(
    """This dashboard is for educational/analytical use only.  
    Data powered by [Yahoo Finance](https://finance.yahoo.com/) and the [yfinance](https://ranaroussi.github.io/yfinance/) python module.  
    You can find me at https://www.linkedin.com/in/harrytbaker/"""
)

