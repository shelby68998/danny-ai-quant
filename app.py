import time
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="Danny AI Quant",
    layout="wide"
)

st.markdown("""
<style>

.block-container {
    padding-top: 2.2rem;
    padding-left: 1rem;
    padding-right: 1rem;
}

h1 {
    font-size: 34px !important;
    margin-bottom: 0.4rem !important;
}

h2, h3 {
    font-size: 20px !important;
    margin-top: 0.45rem !important;
    margin-bottom: 0.2rem !important;
}

.metric-card {
    background:white;
    padding:8px 10px;
    border-radius:10px;
    text-align:center;
    box-shadow:0 1px 4px rgba(0,0,0,0.06);
    min-height:58px;
}

.metric-title {
    font-size:11px;
    color:#666;
    margin-bottom:2px;
}

.metric-value {
    font-size:22px;
    font-weight:700;
    color:#111;
}

.ai-box {
    background:white;
    padding:12px 14px;
    border-radius:10px;
    box-shadow:0 1px 4px rgba(0,0,0,0.06);
    font-size:14px;
    line-height:1.55;
}

.good {
    color:#008f3a;
    font-weight:700;
}

.bad {
    color:#d32f2f;
    font-weight:700;
}

.mid {
    color:#f57c00;
    font-weight:700;
}

.stButton button {
    padding:0.15rem 0.45rem;
    font-size:12px;
    border-radius:6px;
}

/* =========================
   手机优化
========================= */

@media (max-width: 768px) {

    .block-container {
        padding-top: 1rem;
        padding-left: 0.45rem;
        padding-right: 0.45rem;
    }

    h1 {
        font-size: 26px !important;
    }

    h2, h3 {
        font-size: 16px !important;
    }

    .metric-card {
        min-height: 48px;
        padding: 6px 4px;
        border-radius: 8px;
    }

    .metric-title {
        font-size: 9px;
    }

    .metric-value {
        font-size: 16px;
    }

    .ai-box {
        padding: 10px;
        font-size: 12px;
        line-height: 1.45;
    }

    .stButton button {
        width: 100%;
        font-size: 10px;
        padding: 0.15rem 0.2rem;
    }

    iframe {
        width: 100% !important;
    }

}

</style>
""", unsafe_allow_html=True)

st.title("📈 Danny AI Quant Terminal")

# =========================
# 最近股票
# =========================

if "recent_tickers" not in st.session_state:
    st.session_state.recent_tickers = [
        "PLTR","NVDA","TSLA","AMD",
        "RKLB","AAPL","MSFT","META",
        "CRSP","QQQ"
    ]

if "ticker" not in st.session_state:
    st.session_state.ticker = "PLTR"

left, right = st.columns([4, 2])

with left:

    ticker_input = st.text_input(
        "输入股票代码",
        st.session_state.ticker
    ).upper().strip()

with right:

    st.caption("最近看过")

    cols = st.columns(5)

    for i, t in enumerate(
        st.session_state.recent_tickers[:10]
    ):

        with cols[i % 5]:

            if st.button(t):

                st.session_state.ticker = t
                st.rerun()

ticker = ticker_input or st.session_state.ticker

if ticker not in st.session_state.recent_tickers:

    st.session_state.recent_tickers = (
        [ticker] +
        st.session_state.recent_tickers
    )

st.session_state.recent_tickers = (
    st.session_state.recent_tickers[:10]
)

# =========================
# 工具函数
# =========================

def card(title, value):

    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def fmt_b(v):

    return "N/A" if not v else f"${v/1_000_000_000:.1f}B"

def fmt_pct(v):

    return "N/A" if v is None else f"{v*100:.1f}%"

def fmt_num(v):

    return "N/A" if v is None else f"{v:.1f}"

# =========================
# 数据获取
# =========================

@st.cache_data(ttl=1800)

def get_price_safe(symbol):

    try:

        data = yf.download(
            symbol,
            period="5d",
            auto_adjust=False,
            progress=False
        )

        if isinstance(data.columns, pd.MultiIndex):

            data.columns = (
                data.columns.get_level_values(0)
            )

        if data.empty:

            return None

        return float(
            data["Close"].dropna().iloc[-1]
        )

    except:

        return None

@st.cache_data(ttl=3600)

def get_stock_data_safe(symbol):

    try:

        stock = yf.Ticker(symbol)

        info = stock.info

        time.sleep(0.3)

        df = yf.download(
            symbol,
            period="max",
            auto_adjust=False,
            progress=False
        )

        if isinstance(df.columns, pd.MultiIndex):

            df.columns = (
                df.columns.get_level_values(0)
            )

        return info, df, None

    except Exception as e:

        return {}, pd.DataFrame(), str(e)

# =========================
# 市场环境
# =========================

spy_price = get_price_safe("SPY")

qqq_price = get_price_safe("QQQ")

vix_price = get_price_safe("^VIX")

st.subheader("🌍 市场环境")

m1, m2, m3 = st.columns(3)

with m1:
    card("SPY", f"{spy_price:.2f}" if spy_price else "N/A")

with m2:
    card("QQQ", f"{qqq_price:.2f}" if qqq_price else "N/A")

with m3:
    card("VIX", f"{vix_price:.2f}" if vix_price else "N/A")

# =========================
# 股票数据
# =========================

info, df, error_msg = (
    get_stock_data_safe(ticker)
)

if error_msg:

    st.warning(
        "Yahoo Finance 可能暂时限流，请稍后刷新。"
    )

if df.empty:

    st.error("没有获取到数据。")

    st.stop()

# =========================
# 指标
# =========================

df["MA20"] = (
    df["Close"].rolling(20).mean()
)

df["MA50"] = (
    df["Close"].rolling(50).mean()
)

df["MA200"] = (
    df["Close"].rolling(200).mean()
)

delta = df["Close"].diff()

gain = delta.clip(lower=0)

loss = -delta.clip(upper=0)

rs = (
    gain.rolling(14).mean() /
    loss.rolling(14).mean()
)

df["RSI"] = (
    100 - (100 / (1 + rs))
)

current_price = float(
    df["Close"].iloc[-1]
)

all_time_high = float(
    df["High"].max()
)

drawdown = (
    (current_price - all_time_high)
    / all_time_high
    * 100
)

rsi = float(df["RSI"].iloc[-1])

last_52 = df.tail(252)

high_52 = float(
    last_52["High"].max()
)

low_52 = float(
    last_52["Low"].min()
)

current_volume = float(
    df["Volume"].iloc[-1]
)

avg_volume = float(
    df["Volume"].tail(30).mean()
)

volume_ratio = (
    current_volume / avg_volume
)

# =========================
# 核心数据
# =========================

st.subheader(f"📊 {ticker}")

cols = st.columns(6)

items = [
    ("价格", f"${current_price:.2f}"),
    ("跌幅", f"{drawdown:.1f}%"),
    ("RSI", f"{rsi:.1f}"),
    ("量比", f"{volume_ratio:.2f}x"),
    ("52高", f"${high_52:.0f}"),
    ("52低", f"${low_52:.0f}")
]

for col, item in zip(cols, items):

    with col:

        card(item[0], item[1])

# =========================
# AI分析
# =========================

st.subheader("🤖 AI量化判断")

score = 50

positive = []

risk = []

if drawdown <= -60:

    score += 25

    positive.append(
        "已进入60%极端深跌区域"
    )

elif drawdown <= -40:

    score += 15

    positive.append(
        "已进入较深回撤区域"
    )

else:

    risk.append(
        "跌幅尚未达到安全区"
    )

if rsi < 30:

    score += 15

    positive.append(
        "RSI超卖"
    )

elif rsi > 70:

    score -= 15

    risk.append(
        "RSI过热"
    )

else:

    positive.append(
        "RSI中性"
    )

if volume_ratio > 2:

    positive.append(
        "成交量明显放大"
    )

if score >= 80:

    final_view = "高关注机会"

elif score >= 65:

    final_view = "可观察"

else:

    final_view = "中性"

a1, a2 = st.columns([1, 2])

with a1:

    st.markdown(f"""
    <div class="ai-box">

    <div style="font-size:18px;">
    AI判断
    </div>

    <div style="
    font-size:30px;
    font-weight:800;
    margin-top:5px;
    ">
    {score}/100
    </div>

    <div style="margin-top:10px;">
    {final_view}
    </div>

    </div>
    """, unsafe_allow_html=True)

with a2:

    st.markdown(f"""
    <div class="ai-box">

    <b>积极因素</b>

    <ul>
    {''.join([f"<li>{x}</li>" for x in positive])}
    </ul>

    <b>风险因素</b>

    <ul>
    {''.join([f"<li>{x}</li>" for x in risk])}
    </ul>

    </div>
    """, unsafe_allow_html=True)

# =========================
# 图表
# =========================

chart_df = df.tail(252)

st.subheader("📉 K线图")

fig = go.Figure()

fig.add_trace(
    go.Candlestick(
        x=chart_df.index,
        open=chart_df["Open"],
        high=chart_df["High"],
        low=chart_df["Low"],
        close=chart_df["Close"],
        name="K线"
    )
)

fig.add_trace(
    go.Scatter(
        x=chart_df.index,
        y=chart_df["MA20"],
        name="MA20"
    )
)

fig.add_trace(
    go.Scatter(
        x=chart_df.index,
        y=chart_df["MA50"],
        name="MA50"
    )
)

fig.add_trace(
    go.Scatter(
        x=chart_df.index,
        y=chart_df["MA200"],
        name="MA200"
    )
)

fig.update_layout(
    template="plotly_white",
    height=420,
    dragmode="zoom",
    margin=dict(
        l=5,
        r=5,
        t=10,
        b=5
    ),
    xaxis_rangeslider_visible=True
)

st.plotly_chart(
    fig,
    use_container_width=True
)