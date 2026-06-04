import time
import os
import html
import math
import requests
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from openai import OpenAI

st.set_page_config(page_title="Danny AI Quant", layout="wide")

st.markdown("""
<style>
/* ===== 原有样式 ===== */
.block-container {padding-top: 2.2rem; padding-left: 1rem; padding-right: 1rem;}
h1 {font-size: 34px !important; margin-bottom: 0.4rem !important;}
h2, h3 {font-size: 20px !important; margin-top: 0.45rem !important; margin-bottom: 0.2rem !important;}
.metric-card {background:white; padding:8px 10px; border-radius:10px; text-align:center; box-shadow:0 1px 4px rgba(0,0,0,0.06); min-height:58px;}
.metric-title {font-size:11px; color:#666; margin-bottom:2px;}
.metric-value {font-size:22px; font-weight:700; color:#111;}
.ai-box {background:white; padding:12px 14px; border-radius:10px; box-shadow:0 1px 4px rgba(0,0,0,0.06); font-size:14px; line-height:1.55;}
.good {color:#008f3a; font-weight:700;}
.bad {color:#d32f2f; font-weight:700;}
.mid {color:#f57c00; font-weight:700;}
.stButton button {padding:0.15rem 0.45rem; font-size:12px; border-radius:6px;}

/* ===== iPhone 适配（≤430px，覆盖 iPhone 17 Pro 393px） ===== */
@media screen and (max-width: 430px) {

    .block-container {
        padding-top: 1rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }

    h1 {font-size: 22px !important;}
    h2, h3 {font-size: 16px !important;}

    .metric-card {
        padding: 6px 4px;
        min-height: 48px;
        border-radius: 8px;
    }
    .metric-title {font-size: 9px;}
    .metric-value {font-size: 14px;}

    .ai-box {
        font-size: 12px;
        padding: 10px 10px;
        margin-bottom: 8px;
    }
    .ai-box ul {
        padding-left: 16px;
        margin: 4px 0;
    }
    .ai-box li {
        margin-bottom: 3px;
        line-height: 1.45;
    }

    .stButton button {
        font-size: 11px !important;
        padding: 0.1rem 0.3rem !important;
        border-radius: 5px !important;
    }

    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 0 !important;
    }

    .stTextInput input {
        font-size: 14px !important;
    }

    .js-plotly-plot {
        max-height: 260px !important;
    }

    header[data-testid="stHeader"] {
        height: 2rem !important;
        min-height: 2rem !important;
    }

    .gtitle, .legendtext {
        font-size: 10px !important;
    }

    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        flex: 1 1 100% !important;
        max-width: 100% !important;
    }
}
</style>
""", unsafe_allow_html=True)

st.title("📈 Danny AI Quant Terminal")

DEFAULT_TICKERS = ["PLTR", "NVDA", "TSLA", "AMD", "RKLB", "AAPL", "MSFT", "META", "CRSP", "QQQ"]


def clean_ticker(value):
    return "".join(ch for ch in str(value).upper().strip() if ch.isalnum() or ch in ".-^")


def parse_recent_tickers(value):
    tickers = []
    for item in str(value or "").split(","):
        ticker_value = clean_ticker(item)
        if ticker_value and ticker_value not in tickers:
            tickers.append(ticker_value)
    return tickers[:10]


query_ticker = clean_ticker(st.query_params.get("ticker", ""))
query_recent = parse_recent_tickers(st.query_params.get("recent", ""))

if "recent_tickers" not in st.session_state:
    st.session_state.recent_tickers = query_recent or DEFAULT_TICKERS

if "ticker" not in st.session_state:
    st.session_state.ticker = query_ticker or st.session_state.recent_tickers[0]

left, right = st.columns([4, 2])

with left:
    ticker_input = st.text_input("输入股票代码", st.session_state.ticker).upper().strip()

with right:
    st.caption("最近看过")
    cols = st.columns(5)
    for i, t in enumerate(st.session_state.recent_tickers[:10]):
        with cols[i % 5]:
            if st.button(t, key=f"btn_{t}"):
                st.session_state.ticker = t
                st.query_params["ticker"] = t
                st.query_params["recent"] = ",".join(st.session_state.recent_tickers)
                st.rerun()

ticker = clean_ticker(ticker_input or st.session_state.ticker)

if ticker not in st.session_state.recent_tickers:
    st.session_state.recent_tickers = [ticker] + st.session_state.recent_tickers
else:
    st.session_state.recent_tickers.remove(ticker)
    st.session_state.recent_tickers = [ticker] + st.session_state.recent_tickers

st.session_state.recent_tickers = st.session_state.recent_tickers[:10]
st.session_state.ticker = ticker
st.query_params["ticker"] = ticker
st.query_params["recent"] = ",".join(st.session_state.recent_tickers)

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


def get_secret(name):
    try:
        return st.secrets[name]
    except Exception:
        return os.getenv(name)


FMP_KEY = get_secret("FMP_API_KEY")

FMP_STABLE_BASE = "https://financialmodelingprep.com/stable"


def fmp_stable_get(endpoint, params=None):
    if not FMP_KEY:
        return {"_error": "缺少 FMP_API_KEY，已跳过 FMP 并使用 Yahoo 备用数据。"}

    try:
        p = dict(params or {})
        p["apikey"] = FMP_KEY

        url = f"{FMP_STABLE_BASE}/{endpoint}"
        r = requests.get(url, params=p, timeout=15)

        if r.status_code != 200:
            return {"_error": f"FMP HTTP {r.status_code}: {r.text[:300]}"}

        data = r.json()

        if isinstance(data, dict) and "Error Message" in data:
            return {"_error": data.get("Error Message")}
        if isinstance(data, dict) and "error" in data:
            return {"_error": data.get("error")}
        if isinstance(data, dict) and "message" in data and len(data) <= 2:
            return {"_error": data.get("message")}

        return data

    except Exception as e:
        return {"_error": f"FMP request exception: {e}"}


def first_dict(data):
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        return data[0]
    if isinstance(data, dict) and "_error" not in data:
        return data
    return {}


def to_float(value):
    try:
        if value in (None, "", "None", "N/A"):
            return None
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return None
        return number
    except (TypeError, ValueError):
        return None


def safe_number(value, default=0.0):
    number = to_float(value)
    return default if number is None else number


def fmp_symbol_for(symbol):
    return symbol.strip().upper()


def normalize_ohlcv(df):
    if df is None or df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    rename_map = {
        "date": "date",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "adjClose": "Adj Close",
        "volume": "Volume",
    }
    df = df.rename(columns=rename_map)
    required_cols = ["Open", "High", "Low", "Close", "Volume"]

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date").set_index("date")

    if not all(c in df.columns for c in required_cols):
        return pd.DataFrame()

    df = df[required_cols].apply(pd.to_numeric, errors="coerce").dropna(subset=["Close"])
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


def yf_info_safe(symbol):
    try:
        info = yf.Ticker(symbol).info
        return info if isinstance(info, dict) else {}
    except Exception:
        return {}


def first_value(*values, default=None):
    for value in values:
        if value not in (None, "", "N/A"):
            return value
    return default


def merge_fundamentals(fmp_info, yf_info):
    return {
        "marketCap": to_float(first_value(fmp_info.get("marketCap"), yf_info.get("marketCap"))),
        "beta": to_float(first_value(fmp_info.get("beta"), yf_info.get("beta"))),
        "trailingPE": to_float(first_value(fmp_info.get("trailingPE"), yf_info.get("trailingPE"))),
        "forwardPE": to_float(first_value(fmp_info.get("forwardPE"), yf_info.get("forwardPE"))),
        "priceToSalesTrailing12Months": to_float(first_value(
            fmp_info.get("priceToSalesTrailing12Months"),
            yf_info.get("priceToSalesTrailing12Months")
        )),
        "profitMargins": to_float(first_value(fmp_info.get("profitMargins"), yf_info.get("profitMargins"))),
        "revenueGrowth": to_float(first_value(fmp_info.get("revenueGrowth"), yf_info.get("revenueGrowth"))),
        "grossMargins": to_float(first_value(fmp_info.get("grossMargins"), yf_info.get("grossMargins"))),
        "sector": first_value(fmp_info.get("sector"), yf_info.get("sector"), default="N/A"),
        "industry": first_value(fmp_info.get("industry"), yf_info.get("industry"), default="N/A"),
        "longBusinessSummary": first_value(
            fmp_info.get("longBusinessSummary"),
            yf_info.get("longBusinessSummary"),
            default=""
        ),
    }


def fmp_limited(data):
    if not (isinstance(data, dict) and "_error" in data):
        return False
    error = str(data.get("_error", "")).lower()
    return "402" in error or "premium" in error or "subscription" in error


def render_text_box(text):
    if not text:
        return
    safe_text = html.escape(text).replace("\n", "<br>")
    st.markdown(f"""
    <div class="ai-box">
    {safe_text}
    </div>
    """, unsafe_allow_html=True)


def get_openai_client():
    key = get_secret("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("缺少 OPENAI_API_KEY，请先在 Streamlit secrets 或环境变量里设置。")
    return OpenAI(api_key=key)


@st.cache_data(ttl=1800, show_spinner=False)
def get_price_safe(symbol):
    fmp_symbol = fmp_symbol_for(symbol)

    data = fmp_stable_get("quote-short", {"symbol": fmp_symbol})

    if data and isinstance(data, list) and len(data) > 0:
        price = to_float(data[0].get("price"))
        if price is not None:
            return price

    try:
        data = yf.download(symbol, period="5d", auto_adjust=False, progress=False)
        data = normalize_ohlcv(data)

        if data.empty:
            return None

        return safe_number(data["Close"].dropna().iloc[-1])

    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_data_safe(symbol):
    fmp_errors = []
    fmp_limited_fields = []
    fmp_symbol = fmp_symbol_for(symbol)

    quote_raw = fmp_stable_get("quote", {"symbol": fmp_symbol})
    profile_raw = fmp_stable_get("profile", {"symbol": fmp_symbol})
    ratios_raw = fmp_stable_get("ratios-ttm", {"symbol": fmp_symbol})
    growth_raw = fmp_stable_get("income-statement-growth", {"symbol": fmp_symbol, "limit": 1})
    hist_raw = fmp_stable_get("historical-price-eod/full", {"symbol": fmp_symbol})

    for name, data in {
        "quote": quote_raw,
        "profile": profile_raw,
        "ratios": ratios_raw,
        "growth": growth_raw,
        "history": hist_raw
    }.items():
        if isinstance(data, dict) and "_error" in data:
            if fmp_limited(data):
                fmp_limited_fields.append(name)
            else:
                fmp_errors.append(f"{name}: {data['_error']}")

    quote = first_dict(quote_raw)
    profile = first_dict(profile_raw)
    ratios = first_dict(ratios_raw)
    growth = first_dict(growth_raw)

    fmp_info = {
        "marketCap": to_float(profile.get("marketCap") or profile.get("mktCap") or quote.get("marketCap")),
        "beta": to_float(profile.get("beta") or quote.get("beta")),
        "trailingPE": to_float(quote.get("pe") or quote.get("priceEarningsRatio") or ratios.get("priceEarningsRatioTTM")),
        "forwardPE": to_float(ratios.get("peRatioTTM")),
        "priceToSalesTrailing12Months": to_float(ratios.get("priceToSalesRatioTTM")),
        "profitMargins": to_float(ratios.get("netProfitMarginTTM")),
        "revenueGrowth": to_float(growth.get("growthRevenue") or growth.get("revenueGrowth")),
        "grossMargins": to_float(ratios.get("grossProfitMarginTTM")),
        "sector": profile.get("sector", "N/A"),
        "industry": profile.get("industry", "N/A"),
        "longBusinessSummary": profile.get("description", "")
    }
    info = merge_fundamentals(fmp_info, yf_info_safe(symbol))
    limited_note = ""
    if fmp_limited_fields:
        limited_note = "FMP当前套餐限制了部分数据，已自动改用Yahoo备用数据。"

    if isinstance(hist_raw, list) and len(hist_raw) > 0:
        df = normalize_ohlcv(pd.DataFrame(hist_raw))
        if not df.empty:
            note = "；".join(fmp_errors) if fmp_errors else limited_note
            return info, df, note or None

    try:
        df = yf.download(symbol, period="max", auto_adjust=False, progress=False)
        df = normalize_ohlcv(df)

        if not df.empty:
            note_parts = []
            if limited_note:
                note_parts.append(limited_note)
            elif not fmp_errors:
                note_parts.append("FMP历史K线未返回可用数据，已使用Yahoo备用。")
            note_parts.extend(fmp_errors)
            note = "；".join(note_parts)
            return info, df, note

    except Exception as e:
        note = "；".join(fmp_errors) if fmp_errors else limited_note or "FMP无具体错误。"
        return info, pd.DataFrame(), f"行情数据失败：{note}；Yahoo也失败：{e}"

    note = "；".join(fmp_errors) if fmp_errors else limited_note or "FMP和Yahoo都没有返回可用数据。"
    return info, pd.DataFrame(), note



spy_price = get_price_safe("SPY")
qqq_price = get_price_safe("QQQ")
vix_price = get_price_safe("^VIX")

st.subheader("🌍 市场环境")
m1, m2, m3 = st.columns(3)
with m1: card("SPY", f"{spy_price:.2f}" if spy_price else "N/A")
with m2: card("QQQ", f"{qqq_price:.2f}" if qqq_price else "N/A")
with m3: card("VIX", f"{vix_price:.2f}" if vix_price else "N/A")

info, df, error_msg = get_stock_data_safe(ticker)

if error_msg:
    st.info(error_msg)

if df.empty:
    st.error("没有下载到股票数据。请稍后重试，或检查股票代码是否正确。")
    st.stop()

df["MA20"] = df["Close"].rolling(20).mean()
df["MA50"] = df["Close"].rolling(50).mean()
df["MA200"] = df["Close"].rolling(200).mean()

delta = df["Close"].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
rs = gain.rolling(14).mean() / loss.rolling(14).mean()
df["RSI"] = 100 - (100 / (1 + rs))

high_low = df["High"] - df["Low"]
high_close = (df["High"] - df["Close"].shift()).abs()
low_close = (df["Low"] - df["Close"].shift()).abs()
df["ATR"] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(14).mean()

current_price = safe_number(df["Close"].iloc[-1])
all_time_high = safe_number(df["High"].max(), current_price)
drawdown = (current_price - all_time_high) / all_time_high * 100 if all_time_high else 0
rsi = safe_number(df["RSI"].iloc[-1], 50)
atr = safe_number(df["ATR"].iloc[-1])
ma20 = safe_number(df["MA20"].iloc[-1], current_price)
ma50 = safe_number(df["MA50"].iloc[-1], current_price)
ma200 = safe_number(df["MA200"].iloc[-1], current_price)

last_52 = df.tail(252)
high_52 = safe_number(last_52["High"].max(), current_price)
low_52 = safe_number(last_52["Low"].min(), current_price)
current_volume = safe_number(df["Volume"].iloc[-1])
avg_volume = safe_number(df["Volume"].tail(30).mean())
volume_ratio = current_volume / avg_volume if avg_volume else 0

market_cap = info.get("marketCap")
beta = info.get("beta")
trailing_pe = info.get("trailingPE")
forward_pe = info.get("forwardPE")
ps = info.get("priceToSalesTrailing12Months")
profit_margin = info.get("profitMargins")
revenue_growth = info.get("revenueGrowth")
gross_margin = info.get("grossMargins")
sector = info.get("sector", "N/A")
industry = info.get("industry", "N/A")
summary = info.get("longBusinessSummary", "")

theme_words = {
    "AI": ["artificial intelligence", "ai", "machine learning", "data analytics", "cloud"],
    "机器人": ["robot", "robotics", "automation"],
    "军工/国防": ["defense", "military", "government"],
    "半导体": ["semiconductor", "chip", "gpu", "processor"],
    "太空": ["space", "rocket", "satellite", "launch"],
    "生物科技": ["biotech", "clinical", "drug", "therapy", "pharmaceutical"],
    "新能源": ["energy", "solar", "battery", "electric vehicle"]
}

text_blob = f"{sector} {industry} {summary}".lower()
themes = [name for name, words in theme_words.items() if any(w in text_blob for w in words)]
theme_text = "、".join(themes) if themes else "未识别明显热点"

recent_lows = last_52["Low"].nsmallest(8).mean()
recent_highs = last_52["High"].nlargest(8).mean()
support = recent_lows
resistance = recent_highs

valuation_risk = "正常"
valuation_class = "good"
if ps is not None and ps > 30:
    valuation_risk = "极高估值"
    valuation_class = "bad"
elif ps is not None and ps > 15:
    valuation_risk = "偏高估值"
    valuation_class = "mid"
elif trailing_pe is not None and trailing_pe > 80:
    valuation_risk = "高估值"
    valuation_class = "mid"

money_attention = "正常"
if volume_ratio > 2:
    money_attention = "明显放量"
elif volume_ratio < 0.7:
    money_attention = "成交偏冷"

st.subheader(f"📊 {ticker}")
cols = st.columns(8)
items = [
    ("价格", f"${current_price:.2f}"),
    ("跌幅", f"{drawdown:.1f}%"),
    ("RSI", f"{rsi:.1f}"),
    ("量比", f"{volume_ratio:.2f}x"),
    ("52高", f"${high_52:.0f}"),
    ("52低", f"${low_52:.0f}"),
    ("支撑", f"${support:.0f}"),
    ("压力", f"${resistance:.0f}")
]
for col, item in zip(cols, items):
    with col:
        card(item[0], item[1])

st.subheader("🏢 基本面")
fcols = st.columns(8)
fitems = [
    ("市值", fmt_b(market_cap)),
    ("TTM PE", fmt_num(trailing_pe)),
    ("Forward PE", fmt_num(forward_pe)),
    ("P/S", fmt_num(ps)),
    ("收入增速", fmt_pct(revenue_growth)),
    ("毛利率", fmt_pct(gross_margin)),
    ("净利率", fmt_pct(profit_margin)),
    ("主题", theme_text[:14])
]
for col, item in zip(fcols, fitems):
    with col:
        card(item[0], item[1])

# Danny策略模型
deep_drop_ok = drawdown <= -60
growth_ok = revenue_growth is not None and revenue_growth >= 0.3
profitable_ok = profit_margin is not None and profit_margin > 0
not_overheated = rsi < 70
has_theme = len(themes) > 0
volume_ok = volume_ratio >= 0.7

danny_checks = [
    ("跌幅达到60%安全区", deep_drop_ok),
    ("收入增速超过30%", growth_ok),
    ("公司已经盈利", profitable_ok),
    ("RSI没有过热", not_overheated),
    ("具备热点/核心赛道", has_theme),
    ("成交量没有明显萎缩", volume_ok),
]

danny_score = sum(1 for _, ok in danny_checks if ok)

if danny_score >= 5 and deep_drop_ok:
    danny_view = "符合Danny深跌模型"
    danny_class = "good"
elif danny_score >= 4:
    danny_view = "接近条件，继续观察"
    danny_class = "mid"
else:
    danny_view = "暂不符合抄底模型"
    danny_class = "bad"

# AI评分
score = 50
positive = []
risk = []
signal = []

if drawdown <= -60:
    score += 25
    positive.append("已进入60%极端深跌区域，符合高赔率反弹观察条件")
    signal.append("深跌模型触发")
elif drawdown <= -40:
    score += 15
    positive.append("已进入较深回撤区域")
else:
    risk.append("距离历史高点跌幅不够深，尚未进入深跌安全区")

if rsi < 30:
    score += 15
    positive.append("RSI低于30，短线超卖")
    signal.append("RSI超卖")
elif rsi > 70:
    score -= 15
    risk.append("RSI高于70，短期追高风险较高")
else:
    positive.append("RSI处于中性区域，未明显过热")

if current_price > ma200:
    score += 10
    positive.append("股价位于MA200上方，长期趋势仍偏强")
else:
    score -= 10
    risk.append("股价跌破MA200，长期趋势偏弱")

if volume_ratio > 2:
    score += 5
    positive.append("成交量显著放大，可能有资金关注")
    signal.append("异常放量")
elif volume_ratio < 0.7:
    risk.append("成交量低于近30日平均，资金关注度不足")

if revenue_growth is not None:
    if revenue_growth >= 0.3:
        score += 15
        positive.append("收入增速超过30%，符合成长股筛选条件")
    elif revenue_growth <= 0:
        score -= 10
        risk.append("收入增速为负，成长性不足")
else:
    risk.append("未获取到收入增速数据，需要人工核对财报")

if profit_margin is not None:
    if profit_margin > 0:
        score += 5
        positive.append("公司当前为盈利状态")
    else:
        risk.append("公司净利率为负，盈利能力仍有压力")

if ps is not None and ps > 30:
    score -= 15
    risk.append("P/S估值极高，估值回撤风险明显")
elif ps is not None and ps > 15:
    score -= 8
    risk.append("P/S估值偏高，需要等待更好买点")

if current_price < support * 1.05:
    positive.append("股价接近近一年支撑区域")
elif current_price > resistance * 0.95:
    risk.append("股价接近近一年压力区域")

if vix_price and vix_price > 25:
    score -= 10
    risk.append("VIX高于25，市场整体风险较高")

if beta and beta > 2:
    risk.append("Beta高于2，波动性明显高于大盘")

if themes:
    positive.append(f"识别到热点主题：{theme_text}")

score = max(0, min(100, score))

if score >= 80:
    final_view = "高关注机会"
    color = "good"
elif score >= 65:
    final_view = "可进入观察名单"
    color = "mid"
elif score >= 50:
    final_view = "中性观察"
    color = "mid"
else:
    final_view = "风险偏高"
    color = "bad"

if not signal:
    signal.append("暂无强信号")

# 操作建议
short_term = "观望"
mid_term = "继续跟踪"
long_term = "根据估值谨慎判断"

if rsi < 30 and current_price < support * 1.08:
    short_term = "可小仓观察反弹"
elif rsi > 70:
    short_term = "不宜追高"

if deep_drop_ok and growth_ok:
    mid_term = "可考虑分批研究"
elif drawdown > -40:
    mid_term = "等待更深回调"

if ps is not None and ps > 30:
    long_term = "估值偏贵，长线需谨慎"
elif growth_ok and profitable_ok:
    long_term = "基本面较强，可长期跟踪"

st.subheader("🧠 Danny策略判断")
d1, d2, d3 = st.columns([1, 1, 1.2])

with d1:
    st.markdown(f"""
    <div class="ai-box">
        <div style="font-size:18px;">Danny模型：<span class="{danny_class}">{danny_view}</span></div>
        <div style="font-size:28px; font-weight:800; margin-top:6px;">{danny_score}/6</div>
        <div><b>估值状态：</b><span class="{valuation_class}">{valuation_risk}</span></div>
        <div><b>资金关注：</b>{money_attention}</div>
    </div>
    """, unsafe_allow_html=True)

with d2:
    st.markdown(f"""
    <div class="ai-box">
        <b>操作建议</b>
        <ul>
            <li>短线：{short_term}</li>
            <li>中线：{mid_term}</li>
            <li>长线：{long_term}</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with d3:
    checks_html = "".join([f"<li>{'✅' if ok else '❌'} {name}</li>" for name, ok in danny_checks])
    st.markdown(f"""
    <div class="ai-box">
        <b>Danny深跌模型条件</b>
        <ul>{checks_html}</ul>
    </div>
    """, unsafe_allow_html=True)

st.subheader("🤖 AI量化判断")
a1, a2 = st.columns([1.1, 2.2])

with a1:
    st.markdown(f"""
    <div class="ai-box">
        <div style="font-size:18px;">AI判断：<span class="{color}">{final_view}</span></div>
        <div style="font-size:28px; font-weight:800; margin-top:6px;">{score}/100</div>
        <div style="margin-top:8px;"><b>触发信号：</b>{'、'.join(signal)}</div>
        <div style="margin-top:8px;"><b>行业：</b>{sector}</div>
        <div><b>细分：</b>{industry}</div>
    </div>
    """, unsafe_allow_html=True)

with a2:
    st.markdown(f"""
    <div class="ai-box">
        <b class="good">积极因素</b>
        <ul>{''.join([f"<li>{x}</li>" for x in positive])}</ul>
        <b class="bad">风险因素</b>
        <ul>{''.join([f"<li>{x}</li>" for x in risk])}</ul>
    </div>
    """, unsafe_allow_html=True)

st.subheader("🧠 GPT AI 分析中心")

st.subheader("🚨 AI暴跌原因分析")

crash_cache_key = f"{ticker}_crash_reason"

if crash_cache_key not in st.session_state:
    st.session_state[crash_cache_key] = None

if st.button("🚨 为什么暴跌？"):

    if st.session_state[crash_cache_key] is None:

        with st.spinner("GPT 正在分析暴跌原因..."):

            try:

                stock = yf.Ticker(ticker)
                news = stock.news

                news_text = ""

                for n in news[:10]:
                    title = n.get("title", "")
                    summary = n.get("summary", "")
                    publisher = n.get("publisher", "")

                    news_text += f"""
标题: {title}
来源: {publisher}
摘要: {summary}

"""

                client = get_openai_client()

                prompt = f"""
你是一位专业美股暴跌原因分析师。

股票：{ticker}

当前数据：

价格：{current_price}
跌幅：{drawdown:.1f}%
RSI：{rsi:.1f}
量比：{volume_ratio:.2f}
收入增速：{fmt_pct(revenue_growth)}
P/S：{fmt_num(ps)}
PE：{fmt_num(trailing_pe)}
行业：{sector}
主题：{theme_text}

相关新闻：

{news_text}

请分析：

1. 这只股票最近暴跌真正原因
2. 是财报问题、指引问题、估值问题、AI替代、监管、竞争、机构出货还是情绪踩踏
3. 是短期情绪问题还是长期逻辑恶化
4. 是否属于“错杀”
5. 是否可能继续大跌
6. 是否适合抄底
7. 最危险的点是什么
8. 最终结论：
   - 错杀机会
   - 普通回调
   - 高风险下跌
   - 长期逻辑崩坏

输出中文，直接、专业、像真正交易员。
"""

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "你是专业美股暴跌分析师。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,
                    max_tokens=1400
                )

                st.session_state[crash_cache_key] = response.choices[0].message.content

            except Exception as e:
                st.error(f"暴跌分析失败: {e}")

    render_text_box(st.session_state[crash_cache_key])

if st.button("🧹 清除暴跌分析缓存"):
    st.session_state[crash_cache_key] = None
    st.rerun()

cache_key_deep = f"{ticker}_gpt_deep"
cache_key_plan = f"{ticker}_gpt_plan"
cache_key_risk = f"{ticker}_gpt_risk"

for key in [cache_key_deep, cache_key_plan, cache_key_risk]:
    if key not in st.session_state:
        st.session_state[key] = None

def show_gpt_result(result):
    render_text_box(result)

b1, b2, b3 = st.columns(3)

with b1:
    if st.button("🚀 GPT深度分析"):
        if st.session_state[cache_key_deep] is None:
            with st.spinner("GPT 正在深度分析..."):
                try:
                    client = get_openai_client()
                    prompt = f"""
你是一位顶级美股基金经理。

请深度分析股票 {ticker}。

当前数据：
价格：{current_price}
距历史高点跌幅：{drawdown:.1f}%
RSI：{rsi:.1f}
量比：{volume_ratio:.2f}
市值：{fmt_b(market_cap)}
PE：{fmt_num(trailing_pe)}
Forward PE：{fmt_num(forward_pe)}
P/S：{fmt_num(ps)}
收入增速：{fmt_pct(revenue_growth)}
毛利率：{fmt_pct(gross_margin)}
净利率：{fmt_pct(profit_margin)}
行业：{sector}
细分行业：{industry}
热点主题：{theme_text}
估值状态：{valuation_risk}
Danny模型：{danny_view}

请分析：
1. 公司核心逻辑
2. 当前估值是否危险
3. 技术面强弱
4. 机构资金可能态度
5. 是否符合成长股
6. 最大风险
7. 未来1-3年空间
8. 是否值得长期关注
9. 给出评级

输出中文，直接、专业、不要废话。
"""
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "你是专业华尔街基金经理。"},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=1200
                    )
                    st.session_state[cache_key_deep] = response.choices[0].message.content
                except Exception as e:
                    st.error(f"GPT深度分析失败: {e}")

    show_gpt_result(st.session_state[cache_key_deep])

with b2:
    if st.button("📋 GPT操作计划"):
        if st.session_state[cache_key_plan] is None:
            with st.spinner("GPT 正在制定交易计划..."):
                try:
                    client = get_openai_client()
                    prompt = f"""
你是一位职业交易员。

请为股票 {ticker} 制定交易计划。

当前数据：
价格：{current_price}
RSI：{rsi:.1f}
距高点跌幅：{drawdown:.1f}%
支撑位：{support:.2f}
压力位：{resistance:.2f}
量比：{volume_ratio:.2f}
估值状态：{valuation_risk}
Danny模型：{danny_view}

请输出：
1. 激进买点
2. 保守买点
3. 是否适合抄底
4. 分批建仓策略
5. 止损位
6. 第一目标价
7. 第二目标价
8. 仓位建议
9. 短线/中线/长线策略

输出中文，适合实盘参考，但提醒风险。
"""
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "你是顶级职业交易员。"},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.5,
                        max_tokens=1000
                    )
                    st.session_state[cache_key_plan] = response.choices[0].message.content
                except Exception as e:
                    st.error(f"GPT操作计划失败: {e}")

    show_gpt_result(st.session_state[cache_key_plan])

with b3:
    if st.button("⚠️ GPT风险审查"):
        if st.session_state[cache_key_risk] is None:
            with st.spinner("GPT 正在审查风险..."):
                try:
                    client = get_openai_client()
                    prompt = f"""
你是一位极度谨慎的做空机构分析师。

请从最悲观角度分析股票 {ticker}。

当前数据：
价格：{current_price}
PE：{fmt_num(trailing_pe)}
P/S：{fmt_num(ps)}
收入增速：{fmt_pct(revenue_growth)}
净利率：{fmt_pct(profit_margin)}
Beta：{beta}
行业：{sector}
主题：{theme_text}
估值状态：{valuation_risk}

请重点分析：
1. 最大雷点
2. 估值泡沫风险
3. 行业竞争风险
4. AI泡沫风险
5. 财报暴雷可能
6. 机构是否可能出货
7. 最大跌幅可能
8. 最坏情况
9. 为什么有人会做空它

输出中文，尖锐、谨慎、不要客套。
"""
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "你是华尔街做空机构分析师。"},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.8,
                        max_tokens=1200
                    )
                    st.session_state[cache_key_risk] = response.choices[0].message.content
                except Exception as e:
                    st.error(f"GPT风险分析失败: {e}")

    show_gpt_result(st.session_state[cache_key_risk])

if st.button("🧹 清除当前股票GPT缓存"):
    st.session_state[cache_key_deep] = None
    st.session_state[cache_key_plan] = None
    st.session_state[cache_key_risk] = None
    st.rerun()
 # =========================
# 手动新闻 / 情绪分析
# =========================

st.subheader("📰 手动新闻 / 情绪雷达")

news_input = st.text_area(
    "把新闻标题、链接、正文、X推文、Reddit内容、财报摘要等粘贴到这里",
    height=180,
    placeholder="例如：Palantir wins new Pentagon AI contract...\n或直接粘贴新闻链接 / 财报内容 / 推文内容"
)

news_cache_key = f"{ticker}_manual_news_sentiment"

if news_cache_key not in st.session_state:
    st.session_state[news_cache_key] = None

if st.button("🧠 GPT新闻情绪分析"):

    if not news_input.strip():

        st.warning("请先粘贴新闻标题、链接或正文内容。")

    else:

        with st.spinner("GPT 正在分析新闻情绪..."):

            try:
                client = get_openai_client()

                prompt = f"""
你是一位专业美股新闻与市场情绪分析师。

股票代码：{ticker}

当前股票数据：
价格：{current_price}
距历史高点跌幅：{drawdown:.1f}%
RSI：{rsi:.1f}
量比：{volume_ratio:.2f}
估值状态：{valuation_risk}
Danny模型：{danny_view}
行业：{sector}
主题：{theme_text}

用户提供的新闻 / 信息如下：

{news_input}

请分析：

1. 这条信息整体偏利多、利空还是中性
2. 是否可能影响短期股价
3. 是否可能影响中长期逻辑
4. 是真实基本面变化，还是市场噪音
5. 是否涉及订单、财报、监管、诉讼、并购、降级、宏观、关税、AI热度
6. 机构可能如何解读
7. 散户情绪可能如何反应
8. 情绪评分 0-100
9. 对短线交易的影响
10. 对中长期投资的影响
11. 最终结论：利多 / 利空 / 中性 / 噪音

输出中文，直接、专业、不要废话。
"""

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "你是专业美股新闻与市场情绪分析师。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.6,
                    max_tokens=1200
                )

                st.session_state[news_cache_key] = response.choices[0].message.content

            except Exception as e:
                st.error(f"新闻情绪分析失败: {e}")

if st.session_state[news_cache_key]:
    render_text_box(st.session_state[news_cache_key])

if st.button("🧹 清除新闻情绪缓存"):
    st.session_state[news_cache_key] = None
    st.rerun()
    # =========================
# 风口预测 / 主题热度雷达
# =========================

st.subheader("🔥 风口预测 / 主题热度雷达")

SHEET_ID = "1W3DZXgpDoyVSXYQN_XgAp4I5Uzv2I_SnBND2Kw2bPqc"
SIGNALS_GID = "1861710963"

@st.cache_data(ttl=900, show_spinner=False)
def load_theme_signals():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SIGNALS_GID}"
    df_theme = pd.read_csv(url, skiprows=10)
    return df_theme

try:
    theme_df = load_theme_signals()

    if not theme_df.empty:
        latest_time = theme_df["RunTime"].iloc[0] if "RunTime" in theme_df.columns else "N/A"

        st.caption(f"数据更新时间：{latest_time}")

        show_cols = ["Theme", "TodayCount", "Avg7", "Growth", "Score", "Status", "TopTitle", "TopSource"]
        show_cols = [c for c in show_cols if c in theme_df.columns]

        hot_df = theme_df.sort_values("Score", ascending=False).head(10)

        st.dataframe(
            hot_df[show_cols],
            use_container_width=True,
            hide_index=True
        )

        if st.button("🧠 GPT解读今日风口"):
            with st.spinner("GPT 正在解读风口趋势..."):
                try:
                    client = get_openai_client()

                    theme_text_for_gpt = hot_df[show_cols].to_string(index=False)

                    prompt = f"""
你是一位美股主题投资和产业趋势分析师。

下面是今日风口主题监控数据：

{theme_text_for_gpt}

请分析：
1. 今天最值得关注的风口主题
2. 哪些是短线噪音
3. 哪些可能影响美股相关股票
4. 哪些主题可能和 AI、半导体、军工、机器人、生物科技、加密货币有关
5. 给出可能相关股票方向
6. 给出风险提醒
7. 最终列出今日 Top 3 风口

中文输出，直接、专业。
"""

                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "你是专业美股主题投资分析师。"},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.6,
                        max_tokens=1200
                    )

                    result = response.choices[0].message.content

                    render_text_box(result)

                except Exception as e:
                    st.error(f"风口GPT分析失败: {e}")

    else:
        st.info("风口表格暂时没有数据。")

except Exception as e:
    st.warning("暂时无法读取风口预测 Google Sheet。请确认分享权限是“知道链接的人可查看”。")
    st.caption(str(e))
chart_df = df.tail(252)

st.subheader("📉 近一年K线 + 成交量")
g1, g2 = st.columns([1.25, 1])

fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=chart_df.index,
    open=chart_df["Open"],
    high=chart_df["High"],
    low=chart_df["Low"],
    close=chart_df["Close"],
    name="K线"
))
fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["MA20"], name="MA20"))
fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["MA50"], name="MA50"))
fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["MA200"], name="MA200"))
fig.add_hline(y=support, line_dash="dot", annotation_text="支撑")
fig.add_hline(y=resistance, line_dash="dot", annotation_text="压力")

fig.update_layout(
    template="plotly_white",
    height=360,
    margin=dict(l=5, r=5, t=10, b=5),
    dragmode="zoom",
    xaxis_rangeslider_visible=True,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

volume_fig = go.Figure()
volume_fig.add_trace(go.Bar(x=chart_df.index, y=chart_df["Volume"], name="Volume"))
volume_fig.update_layout(
    template="plotly_white",
    height=360,
    margin=dict(l=5, r=5, t=10, b=5),
    dragmode="zoom",
    xaxis_rangeslider_visible=True
)

with g1:
    st.plotly_chart(fig, use_container_width=True)

with g2:
    st.plotly_chart(volume_fig, use_container_width=True)
