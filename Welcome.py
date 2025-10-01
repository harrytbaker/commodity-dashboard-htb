import streamlit as st

st.set_page_config(page_title="Harry's Commodity Dashboard", layout="wide")

# ---------------------
# Title and intro
# ---------------------
st.title("HTB's Commodity Dashboard")
st.markdown(
    """
    Welcome to my Commodities Dashboard.  
    This tool provides interactive analysis and visualisation for key commodity markets, 
    with quick access to **candlestick charts**, **metals**, **oil**, and **soft commodities**.

    Use the buttons below to jump into the different sections.
    """
)

st.divider()

# ---------------------
# Navigation buttons
# ---------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("Candlestick Viewer"):
        st.switch_page("pages/Candle Stick Viewer.py")

with col2:
    if st.button("Metals"):
        st.switch_page("pages/Metals.py")

with col3:
    if st.button("Oil"):
        st.switch_page("pages/Oil.py")

with col4:
    if st.button("Softs"):
        st.switch_page("pages/Softs.py")

st.divider()

# ---------------------
# Footer
# ---------------------
st.caption(
    """This dashboard is for educational/analytical use only.  
    Data powered by [Yahoo Finance](https://finance.yahoo.com/) and the [yfinance](https://ranaroussi.github.io/yfinance/) python module.  
    You can find me at https://www.linkedin.com/in/harrytbaker/"""
)


