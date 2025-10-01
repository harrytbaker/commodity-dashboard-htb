import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide") # Sets the app to take up the full width
st.title("HB's Metals Dashboard")

# -------------------------
# Common metals tickers
# -------------------------
METALS = {
    "Gold": "GC=F",
    "Silver": "SI=F",
    "Copper": "HG=F",
    "Platinum": "PL=F",
    "Palladium": "PA=F",
    "Aluminum": "ALI=F",
    "Nickel": "NID=F",
    "Lead": "LED=F",
    "Tin": "TIN=F",
}


# -------------------------
# Top row with buttons for tickers
# -------------------------
st.subheader("Select metals")
col_sel, col_custom = st.columns([2, 1])

with col_sel:
    selected_names = st.multiselect(
        "Metals (toggle on/off):",
        options=list(METALS.keys()),
        default=["Gold"],
        help="Select one or more metals to plot."
    )

    # Show warning only if any LME base metals are selected
    lme_metals = {"Aluminum", "Nickel", "Lead", "Tin"}
    if any(m in lme_metals for m in selected_names):
        st.warning(
            "Note: Some selected metals (eg Aluminum, Nickel, Lead, Tin) are traded primarily on the "
            "London Metal Exchange (LME). Yahoo Finance may not provide reliable data for these contracts."
        )


with col_custom:
    custom_str = st.text_input(
        "Custom tickers (comma-separated):",
        value="",
        help="Optional. Add extra Yahoo tickers."
    )
custom_tickers = [t.strip().upper() for t in custom_str.split(",") if t.strip()]

# Map selection to tickers
selected_tickers = [METALS[n] for n in selected_names] + custom_tickers
selected_labels = selected_names + custom_tickers  # names for columns (customs use ticker as label)

if len(selected_tickers) == 0:
    st.warning("Select at least one metal.")
    st.stop()

# -------------------------
# Sidebar date range with presets
# -------------------------
st.sidebar.subheader("Date Range")

today = datetime.date.today()

presets = {
    "1M": today - datetime.timedelta(days=30),
    "6M": today - datetime.timedelta(days=182),
    "YTD": datetime.date(today.year, 1, 1),
    "1Y": today - datetime.timedelta(days=365),
    "5Y": today - datetime.timedelta(days=365 * 5),
}

# Initialise session state once
if "manual_start" not in st.session_state:
    st.session_state.manual_start = today - datetime.timedelta(days=365)
if "manual_end" not in st.session_state:
    st.session_state.manual_end = today

# Quick select buttons - update state BEFORE widgets are drawn
st.sidebar.write("Quick Select:")
cols = st.sidebar.columns(len(presets))
for i, (label, preset_start) in enumerate(presets.items()):
    if cols[i].button(label):
        st.session_state.manual_start = preset_start
        st.session_state.manual_end = today
        st.session_state.active_preset = label

# Now render widgets (they reflect updated state automatically)
start = st.sidebar.date_input("Start date", key="manual_start")
end = st.sidebar.date_input("End date", key="manual_end")

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
# Fetch historical data
# -------------------------
raw = yf.download(
    selected_tickers,
    start=start,
    end=end,
    interval=interval,
)

# Handle cases where yfinance returns empty or partial data
if raw is None or raw.empty:
    st.error("No data returned for the selected tickers/date range.")
    st.stop()

# If MultiIndex (ticker level), select Close and flatten
if isinstance(raw.columns, pd.MultiIndex):
    if ("Close" not in raw.columns.get_level_values(0)):
        st.error("Downloaded data did not include 'Close' prices.")
        st.stop()
    data = raw["Close"].copy()
else:
    # Single series fallback
    if "Close" not in raw.columns:
        st.error("Downloaded data did not include 'Close' prices.")
        st.stop()
    data = raw["Close"].to_frame()

# Rename columns to friendly labels
rename_map = {}
# Build a map by aligning ticker order to labels
all_downloaded_tickers = list(data.columns)
for t in all_downloaded_tickers:
    # If the ticker is in our selected list, find label index
    if t in selected_tickers:
        idx = selected_tickers.index(t)
        rename_map[t] = selected_labels[idx]
    else:
        # Leave as-is for unexpected columns
        rename_map[t] = t

# Rename columns to friendly labels
data = data.rename(columns=rename_map)
# Ensure all selected labels are present, even if empty (this is so if one column is all NaNs it doesnt impact a column that just has a few NaNs)
for lbl in selected_labels:
    if lbl not in data.columns:
        data[lbl] = np.nan
# Restrict order to match selection
data = data[selected_labels]


if data.empty or len(data.columns) == 0:
    st.error("No valid closing price data for the current selection.")
    st.stop()

st.caption(f"Data interval automatically set to **{interval}** based on requested date range ({delta_days} days).")

# -------------------------
# Live Metrics
# -------------------------

# Load fast_info for each present series if possible
metrics = []
for lbl in data.columns:
    # Try to recover the original ticker for this label
    if lbl in METALS:
        tkr = METALS[lbl]
    else:
        tkr = lbl  # custom tickers: label == ticker
    try:
        info = yf.Ticker(tkr).fast_info
        last_price = float(info.last_price)
        prev_close = float(info.previous_close)
        change_pct = (last_price - prev_close) / prev_close * 100 if prev_close != 0 else np.nan
        change_abs = last_price - prev_close
        metrics.append((lbl, last_price, prev_close, change_abs, change_pct))
    except Exception:
        metrics.append((lbl, np.nan, np.nan, np.nan, np.nan))

# Display in rows of up to 3 metrics (Last, Prev, Δ$)
per_row = 5 # trying 5
rows = (len(metrics) + per_row - 1) // per_row
for r in range(rows):
    cols_row = st.columns(per_row)
    for i in range(per_row):
        idx = r * per_row + i
        if idx >= len(metrics):
            break
        lbl, last_price, prev_close, change_abs, change_pct = metrics[idx]
        with cols_row[i]:
            st.metric(f"{lbl} Last", f"${last_price:.2f}" if pd.notna(last_price) else "N/A",
                      f"{change_pct:.2f}%" if pd.notna(change_pct) else None)
            st.caption(f"Prev Close: {('$' + f'{prev_close:.2f}') if pd.notna(prev_close) else 'N/A'}  |  Δ: {('$' + f'{change_abs:.2f}') if pd.notna(change_abs) else 'N/A'}")

# -------------------------
# Overview (Main plot with Normalise toggle)
# -------------------------
st.subheader("Overview")

# --- Normalise toggle ---
normalise = st.checkbox(
    "Normalise prices (index = 100 at start)",
    value=False,
    help="Scales each series so that its first available value in the selected window equals 100."
)

# Prepare plotting dataframe based on toggle
plot_df = data.copy()
y_axis_label = "Price (USD)"

if normalise:
    # Get first valid (non-NaN) value per column within the current window
    first_vals = plot_df.apply(lambda s: s.dropna().iloc[0] if not s.dropna().empty else np.nan)
    # Avoid division by NaN; drop columns that cannot be normalised
    valid_cols = [c for c in plot_df.columns if pd.notna(first_vals.get(c, np.nan)) and first_vals[c] != 0]
    if len(valid_cols) == 0:
        st.info("Cannot normalise: no valid starting values.")
        plot_df = data.copy()
    else:
        plot_df = plot_df[valid_cols].divide(first_vals[valid_cols], axis=1) * 100.0
        y_axis_label = "Indexed Price (100 = start)"
        st.caption("Normalised to 100 at the first available value within the selected date range for each series.")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("**Price Chart**")
    fig = px.line(plot_df, x=plot_df.index, y=plot_df.columns,
                  labels={"value": y_axis_label, "variable": "Metal", "index": "Date"})
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("**Returns Comparison**")
    returns = data.pct_change().dropna()
    if returns.empty:
        st.info("Not enough data to compute returns for the current selection.")
    else:
        fig = px.line(returns, x=returns.index, y=returns.columns,
                      labels={"value": "Returns", "variable": "Metal", "index": "Date"})
        st.plotly_chart(fig, use_container_width=True)

# -------------------------
# Bottom row: tabs for extra analysis
# -------------------------
st.subheader("More Analysis")

tab1, tab2, tab3, tab4 = st.tabs([
    "Rolling Volatility",
    "Rolling Mean & Std",
    "Spread (2 series only)",
    "Rolling Correlation (2 series only)",
])

# -------------------------
# Rolling Volatility (time-based 30D)
# -------------------------
with tab1:
    if data.shape[1] == 0:
        st.info("Select at least one series.")
    else:
        ret = data.pct_change()
        vol = ret.rolling("30D").std() * np.sqrt(252)
        if vol.dropna(how="all").empty:
            st.info("Not enough data to compute 30D rolling volatility.")
        else:
            vol.columns = [f"Volatility_{c}" for c in vol.columns]
            fig = px.line(vol, x=vol.index, y=vol.columns,
                          labels={"value": "Volatility (Annualised)", "variable": "Metal", "index": "Date"})
            st.plotly_chart(fig, use_container_width=True)

# -------------------------
# Rolling Mean & Std (time-based window)
# -------------------------
with tab2:
    window_days = st.sidebar.number_input(
        "Rolling window (days)",
        min_value=1, max_value=365, value=30, step=1
    )

    # --- Normalise toggle inside this tab ---
    norm_roll = st.checkbox(
        "Normalise rolling values (index = 100 at start of windowed mean)",
        value=False,
        help="Scales each rolling mean/std so the first valid rolling mean in the window equals 100."
    )

    if (end - start).days < window_days:
        st.error(f"Not enough data for a {window_days}-day rolling window. "
                 f"Increase the viewing window.")
    else:
        roll_mean = data.rolling(f"{window_days}D").mean()
        roll_std = data.rolling(f"{window_days}D").std()

        # Apply normalisation if toggled
        if norm_roll:
            first_vals = roll_mean.apply(lambda s: s.dropna().iloc[0] if not s.dropna().empty else np.nan)
            valid_cols = [c for c in roll_mean.columns if pd.notna(first_vals.get(c, np.nan)) and first_vals[c] != 0]
            if len(valid_cols) > 0:
                roll_mean = roll_mean[valid_cols].divide(first_vals[valid_cols], axis=1) * 100.0
                roll_std = roll_std[valid_cols]  # std not reindexed to 100, kept absolute
                st.caption("Rolling mean values normalised to 100 at their first available value.")
            else:
                st.info("Cannot normalise: no valid starting values.")

        if roll_mean.dropna(how="all").empty:
            st.info("Not enough data to compute rolling statistics.")
        else:
            from plotly.subplots import make_subplots

            fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True,
                subplot_titles=(f"{window_days}-Day Rolling Mean",
                                f"{window_days}-Day Rolling Std")
            )

            # Row 1: Rolling Mean (all series)
            for c in roll_mean.columns:
                fig.add_trace(go.Scatter(x=roll_mean.index, y=roll_mean[c],
                                         mode="lines", name=f"Mean {c}"),
                              row=1, col=1)

            # Row 2: Rolling Std (all series)
            for c in roll_std.columns:
                fig.add_trace(go.Scatter(x=roll_std.index, y=roll_std[c],
                                         mode="lines", name=f"Std {c}"),
                              row=2, col=1)

            fig.update_xaxes(title="Date", row=2, col=1)
            fig.update_yaxes(title="Price (USD)" if not norm_roll else "Indexed (100=start)", row=1, col=1)
            fig.update_yaxes(title="Std (USD)", row=2, col=1)
            fig.update_layout(height=600, title_text=f"Rolling Mean & Std ({window_days}-Day)")

            st.plotly_chart(fig, use_container_width=True)


# -------------------------
# Spread (requires exactly 2 series)
# -------------------------
with tab3:
    if data.shape[1] != 2:
        st.info("Select exactly two series to compute a spread (A − B).")
    else:
        a, b = data.columns.tolist()
        spread = data[a] - data[b]

        spread_current = spread.iloc[-1]
        spread_avg = spread.mean()
        spread_p5 = np.percentile(spread.dropna(), 5)
        spread_p95 = np.percentile(spread.dropna(), 95)

        colA, colB, colC, colD = st.columns(4)
        colA.metric("Current Spread", f"${spread_current:.2f}")
        colB.metric("Average Spread", f"${spread_avg:.2f}")
        colC.metric("5th Percentile", f"${spread_p5:.2f}")
        colD.metric("95th Percentile", f"${spread_p95:.2f}")

        fig1 = px.line(x=spread.index, y=spread.values,
                       labels={"x": "Date", "y": f"Spread (USD): {a} − {b}"})
        st.plotly_chart(fig1, use_container_width=True)

        hist = px.histogram(spread.dropna(), nbins=30,
                            labels={"value": f"Spread (USD): {a} − {b}"})
        st.plotly_chart(hist, use_container_width=True)

# -------------------------
# Rolling Correlation (requires exactly 2 series)
# -------------------------
with tab4:
    if data.shape[1] != 2:
        st.info("Select exactly two series to compute rolling correlation.")
    else:
        a, b = data.columns.tolist()
        rolling_corr = data[a].rolling("90D").corr(data[b])
        if rolling_corr.dropna().empty:
            st.info("Not enough data to compute 90D rolling correlation.")
        else:
            fig = px.line(x=rolling_corr.index, y=rolling_corr.values,
                          labels={"x": "Date", "y": f"Correlation ({a} vs {b})"})
            st.plotly_chart(fig, use_container_width=True)

# ---------------------
# Footer
# ---------------------
st.caption(
    """This dashboard is for educational/analytical use only.  
    Data powered by [Yahoo Finance](https://finance.yahoo.com/) and the [yfinance](https://ranaroussi.github.io/yfinance/) python module.  
    You can find me at https://www.linkedin.com/in/harrytbaker/"""
)

