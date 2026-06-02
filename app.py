import time
import requests
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Danny AI Quant", layout="wide")

st.markdown("""
<style>
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

@media screen and (max-width: 430px) {
    .block-container {padding-top: 1rem !important; padding-left: 0.5rem !important; padding-right: 0.5rem !important;}
    h1 {font-size: 22px !important;}
    h2, h3 {font-size: 16px !important;}
    .metric-card {padding: 6px 4px; min-height: 48px; border-radius: 8px;}
    .metric-title {font-size: 9px;}
    .metric-value {font-size: 14px;}
    .ai-box {font-size: 12px; padding: 10px 10px; margin-bottom: 8px;}
    .ai-box ul {padding-left: 16px; margin: 4px 0;}
    .ai-box li {margin-bottom: 3px; line-height: 1.45;}
    .stButton button {font-size: 11px !important; padding: 0.1rem 0.3rem !important; border-radius: 5px !important;}
    [data-testid="column"] {width: 100% !important; flex: 1 1 100% !important; min-width: 0 !important;}
    .stTextInput input {font-size: 14px !important;}
    .js-plotly-plot {max-height: 260px !important;}
    header[data-testid="stHeader"] {height: 2rem !important; min-height: 2rem !important;}
    .gtitle, .legendtext {font-size: 10px !important;}
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {flex: 1 1 100% !important; max-width: 100% !important;}
}
</style>
""", unsafe_allow_html=True)

# ── FMP API Key ──────────────────────────────────────────────────────────────
FMP_KEY = st.secrets.get("FMP_API_KEY", "GHehsVW9uu3dTBIdTymMu09U5lnwhXHW")
FMP_BASE = "https://financialmodelingprep.com/api/v3"

# ── FMP 数据获取函数 ─────────────────────────────────────────────────────────

def fmp_get(endpoint, params=None, retries=3):
    """带重试的 FMP API 请求"""
    p = params or {}
    p["apikey"] = FMP_KEY
    for attempt in range(retries):
        try:
            r = requests.get(f"{FMP_BASE}/{endpoint}", params=p, timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        if attempt < retries - 1:
            time.sleep(1.5 * (attempt + 1))
    return None

@st.cache_data(ttl=1800, show_spinner=False)
def get_quote(symbol):
    """实时报价 + 基本指标，FMP /quote"""
    data = fmp_get(f"quote/{symbol}")
    if data and isinstance(data, list) and len(data) > 0:
        return data[0]
    return {}

@st.cache_data(ttl=3600, show_spinner=False)
def get_profile(symbol):
    """公司简介、行业、描述，FMP /profile"""
    data = fmp_get(f"profile/{symbol}")
    if data and isinstance(data, list) and len(data) > 0:
        return data[0]
    return {}

@st.cache_data(ttl=3600, show_spinner=False)
def get_ratios(symbol):
    """财务比率（P/S、毛利率、净利率等），FMP /ratios/ttm"""
    data = fmp_get(f"ratios-ttm/{symbol}")
    if data and isinstance(data, list) and len(data) > 0:
        return data[0]
    return {}

@st.cache_data(ttl=3600, show_spinner=False)
def get_income_growth(symbol):
    """收入增速，FMP /financial-growth"""
    data = fmp_get(f"financial-growth/{symbol}", {"limit": 1})
    if data and isinstance(data, list) and len(data) > 0:
        return data[0]
    return {}

@st.cache_data(ttl=1800, show_spinner=False)
def get_history(symbol, days=400):
    """历史日K线，FMP /historical-price-full"""
    from_date = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    data = fmp_get(f"historical-price-full/{symbol}", {"from": from_date})
    if not data or "historical" not in data:
        return pd.DataFrame()
    df = pd.DataFrame(data["historical"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").set_index("date")
    df.rename(columns={
        "open": "Open", "high": "High", "low": "Low",
        "close": "Close", "volume": "Volume"
    }, inplace=True)
    return df[["Open", "High", "Low", "Close", "Volume"]]

@st.cache_data(ttl=1800, show_spinner=False)
def get_simple_quote(symbol):
    """单只股票简单报价（用于 SPY/QQQ/VIX）"""
    data = fmp_get(f"quote-short/{symbol}")
    if data and isinstance(data, list) and len(data) > 0:
        return data[0].get("price")
    return None

@st.cache_data(ttl=3600, show_spinner=False)
def get_news(symbol, limit=10):
    """获取股票新闻，FMP /stock_news"""
    data = fmp_get("stock_news", {"tickers": symbol, "limit": limit})
    return data or []

# ── 格式化工具 ───────────────────────────────────────────────────────────────

def fmt_b(v):
    return "N/A" if not v else f"${v/1_000_000_000:.1f}B"

def fmt_pct(v):
    return "N/A" if v is None else f"{v*100:.1f}%"

def fmt_num(v):
    return "N/A" if v is None else f"{v:.1f}"

def card(title, value):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

# ── Session State ────────────────────────────────────────────────────────────

st.title("📈 Danny AI Quant Terminal")

if "recent_tickers" not in st.session_state:
    st.session_state.recent_tickers = ["PLTR","NVDA","TSLA","AMD","RKLB","AAPL","MSFT","META","CRSP","QQQ"]
if "ticker" not in st.session_state:
    st.session_state.ticker = "PLTR"

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
                st.rerun()

ticker = ticker_input or st.session_state.ticker

if ticker not in st.session_state.recent_tickers:
    st.session_state.recent_tickers = [ticker] + st.session_state.recent_tickers
else:
    st.session_state.recent_tickers.remove(ticker)
    st.session_state.recent_tickers = [ticker] + st.session_state.recent_tickers
st.session_state.recent_tickers = st.session_state.recent_tickers[:10]
st.session_state.ticker = ticker

# ── 市场环境 ─────────────────────────────────────────────────────────────────

spy_price  = get_simple_quote("SPY")
qqq_price  = get_simple_quote("QQQ")
vix_price  = get_simple_quote("^VIX")

st.subheader("🌍 市场环境")
m1, m2, m3 = st.columns(3)
with m1: card("SPY", f"{spy_price:.2f}" if spy_price else "N/A")
with m2: card("QQQ", f"{qqq_price:.2f}" if qqq_price else "N/A")
with m3: card("VIX", f"{vix_price:.2f}" if vix_price else "N/A")

# ── 获取主数据 ───────────────────────────────────────────────────────────────

quote   = get_quote(ticker)
profile = get_profile(ticker)
ratios  = get_ratios(ticker)
growth  = get_income_growth(ticker)
df      = get_history(ticker, days=400)

if df.empty:
    st.error("没有下载到股票数据。请检查股票代码是否正确，或稍后重试。")
    st.stop()

# ── 技术指标计算 ─────────────────────────────────────────────────────────────

df["MA20"]  = df["Close"].rolling(20).mean()
df["MA50"]  = df["Close"].rolling(50).mean()
df["MA200"] = df["Close"].rolling(200).mean()

delta = df["Close"].diff()
gain  = delta.clip(lower=0)
loss  = -delta.clip(upper=0)
rs    = gain.rolling(14).mean() / loss.rolling(14).mean()
df["RSI"] = 100 - (100 / (1 + rs))

high_low   = df["High"] - df["Low"]
high_close = (df["High"] - df["Close"].shift()).abs()
low_close  = (df["Low"]  - df["Close"].shift()).abs()
df["ATR"]  = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(14).mean()

# ── 基础数值提取 ─────────────────────────────────────────────────────────────

current_price = float(quote.get("price") or df["Close"].iloc[-1])
all_time_high = float(df["High"].max())
drawdown      = (current_price - all_time_high) / all_time_high * 100
rsi           = float(df["RSI"].iloc[-1])
atr           = float(df["ATR"].iloc[-1])
ma20          = float(df["MA20"].iloc[-1])
ma50          = float(df["MA50"].iloc[-1])
ma200         = float(df["MA200"].iloc[-1])

last_252   = df.tail(252)
high_52    = float(last_252["High"].max())
low_52     = float(last_252["Low"].min())
current_volume = float(df["Volume"].iloc[-1])
avg_volume     = float(df["Volume"].tail(30).mean())
volume_ratio   = current_volume / avg_volume if avg_volume else 0

# ── FMP 基本面字段 ────────────────────────────────────────────────────────────

market_cap      = profile.get("mktCap")
beta            = profile.get("beta")
sector          = profile.get("sector", "N/A")
industry        = profile.get("industry", "N/A")
summary         = profile.get("description", "")

trailing_pe     = quote.get("pe")
forward_pe      = ratios.get("peRatioTTM")
ps              = ratios.get("priceToSalesRatioTTM")
gross_margin    = ratios.get("grossProfitMarginTTM")
profit_margin   = ratios.get("netProfitMarginTTM")
revenue_growth  = growth.get("revenueGrowth")

# ── 主题识别 ─────────────────────────────────────────────────────────────────

theme_words = {
    "AI":       ["artificial intelligence", "ai", "machine learning", "data analytics", "cloud"],
    "机器人":   ["robot", "robotics", "automation"],
    "军工/国防":["defense", "military", "government"],
    "半导体":   ["semiconductor", "chip", "gpu", "processor"],
    "太空":     ["space", "rocket", "satellite", "launch"],
    "生物科技": ["biotech", "clinical", "drug", "therapy", "pharmaceutical"],
    "新能源":   ["energy", "solar", "battery", "electric vehicle"]
}
text_blob  = f"{sector} {industry} {summary}".lower()
themes     = [name for name, words in theme_words.items() if any(w in text_blob for w in words)]
theme_text = "、".join(themes) if themes else "未识别明显热点"

# ── 支撑/压力 ────────────────────────────────────────────────────────────────

recent_lows  = last_252["Low"].nsmallest(8).mean()
recent_highs = last_252["High"].nlargest(8).mean()
support      = recent_lows
resistance   = recent_highs

# ── 估值/资金状态 ────────────────────────────────────────────────────────────

valuation_risk  = "正常"
valuation_class = "good"
if ps is not None and ps > 30:
    valuation_risk  = "极高估值"
    valuation_class = "bad"
elif ps is not None and ps > 15:
    valuation_risk  = "偏高估值"
    valuation_class = "mid"
elif trailing_pe is not None and trailing_pe > 80:
    valuation_risk  = "高估值"
    valuation_class = "mid"

money_attention = "正常"
if volume_ratio > 2:
    money_attention = "明显放量"
elif volume_ratio < 0.7:
    money_attention = "成交偏冷"

# ── 股票指标卡片 ─────────────────────────────────────────────────────────────

st.subheader(f"📊 {ticker}")
cols  = st.columns(8)
items = [
    ("价格",   f"${current_price:.2f}"),
    ("跌幅",   f"{drawdown:.1f}%"),
    ("RSI",    f"{rsi:.1f}"),
    ("量比",   f"{volume_ratio:.2f}x"),
    ("52高",   f"${high_52:.0f}"),
    ("52低",   f"${low_52:.0f}"),
    ("支撑",   f"${support:.0f}"),
    ("压力",   f"${resistance:.0f}")
]
for col, item in zip(cols, items):
    with col:
        card(item[0], item[1])

st.subheader("🏢 基本面")
fcols = st.columns(8)
fitems = [
    ("市值",       fmt_b(market_cap)),
    ("TTM PE",     fmt_num(trailing_pe)),
    ("Forward PE", fmt_num(forward_pe)),
    ("P/S",        fmt_num(ps)),
    ("收入增速",   fmt_pct(revenue_growth)),
    ("毛利率",     fmt_pct(gross_margin)),
    ("净利率",     fmt_pct(profit_margin)),
    ("主题",       theme_text[:14])
]
for col, item in zip(fcols, fitems):
    with col:
        card(item[0], item[1])

# ── Danny 策略模型 ────────────────────────────────────────────────────────────

deep_drop_ok  = drawdown <= -60
growth_ok     = revenue_growth is not None and revenue_growth >= 0.3
profitable_ok = profit_margin is not None and profit_margin > 0
not_overheated= rsi < 70
has_theme     = len(themes) > 0
volume_ok     = volume_ratio >= 0.7

danny_checks = [
    ("跌幅达到60%安全区",  deep_drop_ok),
    ("收入增速超过30%",    growth_ok),
    ("公司已经盈利",       profitable_ok),
    ("RSI没有过热",        not_overheated),
    ("具备热点/核心赛道",  has_theme),
    ("成交量没有明显萎缩", volume_ok),
]
danny_score = sum(1 for _, ok in danny_checks if ok)

if danny_score >= 5 and deep_drop_ok:
    danny_view  = "符合Danny深跌模型"
    danny_class = "good"
elif danny_score >= 4:
    danny_view  = "接近条件，继续观察"
    danny_class = "mid"
else:
    danny_view  = "暂不符合抄底模型"
    danny_class = "bad"

# ── AI 评分逻辑 ───────────────────────────────────────────────────────────────

score    = 50
positive = []
risk     = []
signal   = []

if drawdown <= -60:
    score += 25; positive.append("已进入60%极端深跌区域，符合高赔率反弹观察条件"); signal.append("深跌模型触发")
elif drawdown <= -40:
    score += 15; positive.append("已进入较深回撤区域")
else:
    risk.append("距离历史高点跌幅不够深，尚未进入深跌安全区")

if rsi < 30:
    score += 15; positive.append("RSI低于30，短线超卖"); signal.append("RSI超卖")
elif rsi > 70:
    score -= 15; risk.append("RSI高于70，短期追高风险较高")
else:
    positive.append("RSI处于中性区域，未明显过热")

if current_price > ma200:
    score += 10; positive.append("股价位于MA200上方，长期趋势仍偏强")
else:
    score -= 10; risk.append("股价跌破MA200，长期趋势偏弱")

if volume_ratio > 2:
    score += 5; positive.append("成交量显著放大，可能有资金关注"); signal.append("异常放量")
elif volume_ratio < 0.7:
    risk.append("成交量低于近30日平均，资金关注度不足")

if revenue_growth is not None:
    if revenue_growth >= 0.3:
        score += 15; positive.append("收入增速超过30%，符合成长股筛选条件")
    elif revenue_growth <= 0:
        score -= 10; risk.append("收入增速为负，成长性不足")
else:
    risk.append("未获取到收入增速数据，需要人工核对财报")

if profit_margin is not None:
    if profit_margin > 0:
        score += 5; positive.append("公司当前为盈利状态")
    else:
        risk.append("公司净利率为负，盈利能力仍有压力")

if ps is not None and ps > 30:
    score -= 15; risk.append("P/S估值极高，估值回撤风险明显")
elif ps is not None and ps > 15:
    score -= 8;  risk.append("P/S估值偏高，需要等待更好买点")

if current_price < support * 1.05:
    positive.append("股价接近近一年支撑区域")
elif current_price > resistance * 0.95:
    risk.append("股价接近近一年压力区域")

if vix_price and vix_price > 25:
    score -= 10; risk.append("VIX高于25，市场整体风险较高")

if beta and beta > 2:
    risk.append("Beta高于2，波动性明显高于大盘")

if themes:
    positive.append(f"识别到热点主题：{theme_text}")

score = max(0, min(100, score))

if score >= 80:   final_view = "高关注机会"; color = "good"
elif score >= 65: final_view = "可进入观察名单"; color = "mid"
elif score >= 50: final_view = "中性观察"; color = "mid"
else:             final_view = "风险偏高"; color = "bad"

if not signal:
    signal.append("暂无强信号")

short_term = "观望"
mid_term   = "继续跟踪"
long_term  = "根据估值谨慎判断"

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

# ── Danny 策略展示 ────────────────────────────────────────────────────────────

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

# ── AI 量化判断 ───────────────────────────────────────────────────────────────

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

# ── GPT 分析中心 ──────────────────────────────────────────────────────────────

from openai import OpenAI

st.subheader("🧠 GPT AI 分析中心")

# 暴跌原因分析
st.subheader("🚨 AI暴跌原因分析")
crash_cache_key = f"{ticker}_crash_reason"
if crash_cache_key not in st.session_state:
    st.session_state[crash_cache_key] = None

if st.button("🚨 为什么暴跌？"):
    if st.session_state[crash_cache_key] is None:
        with st.spinner("GPT 正在分析暴跌原因..."):
            try:
                news_list = get_news(ticker, limit=10)
                news_text = ""
                for n in news_list:
                    news_text += f"标题: {n.get('title','')}\n来源: {n.get('site','')}\n摘要: {n.get('text','')[:200]}\n\n"

                client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                prompt = f"""
你是一位专业美股暴跌原因分析师。

股票：{ticker}
当前数据：
价格：{current_price} | 跌幅：{drawdown:.1f}% | RSI：{rsi:.1f} | 量比：{volume_ratio:.2f}
收入增速：{fmt_pct(revenue_growth)} | P/S：{fmt_num(ps)} | PE：{fmt_num(trailing_pe)}
行业：{sector} | 主题：{theme_text}

相关新闻：
{news_text}

请分析：
1. 这只股票最近暴跌真正原因
2. 是财报、指引、估值、AI替代、监管、竞争、机构出货还是情绪踩踏
3. 是短期情绪问题还是长期逻辑恶化
4. 是否属于"错杀"
5. 是否可能继续大跌
6. 是否适合抄底
7. 最危险的点是什么
8. 最终结论：错杀机会 / 普通回调 / 高风险下跌 / 长期逻辑崩坏

输出中文，直接、专业、像真正交易员。
"""
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role":"system","content":"你是专业美股暴跌分析师。"},{"role":"user","content":prompt}],
                    temperature=0.5, max_tokens=1400
                )
                st.session_state[crash_cache_key] = response.choices[0].message.content
            except Exception as e:
                st.error(f"暴跌分析失败: {e}")

    if st.session_state[crash_cache_key]:
        st.markdown(f'<div class="ai-box">{st.session_state[crash_cache_key].replace(chr(10),"<br>")}</div>', unsafe_allow_html=True)

if st.button("🧹 清除暴跌分析缓存"):
    st.session_state[crash_cache_key] = None
    st.rerun()

# 三大 GPT 分析按钮
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
cache_key_deep = f"{ticker}_gpt_deep"
cache_key_plan = f"{ticker}_gpt_plan"
cache_key_risk = f"{ticker}_gpt_risk"

for key in [cache_key_deep, cache_key_plan, cache_key_risk]:
    if key not in st.session_state:
        st.session_state[key] = None

def show_gpt_result(result):
    if result:
        st.markdown(f'<div class="ai-box">{result.replace(chr(10),"<br>")}</div>', unsafe_allow_html=True)

b1, b2, b3 = st.columns(3)

with b1:
    if st.button("🚀 GPT深度分析"):
        if st.session_state[cache_key_deep] is None:
            with st.spinner("GPT 正在深度分析..."):
                try:
                    prompt = f"""
你是一位顶级美股基金经理。请深度分析股票 {ticker}。

当前数据：
价格：{current_price} | 距高点跌幅：{drawdown:.1f}% | RSI：{rsi:.1f} | 量比：{volume_ratio:.2f}
市值：{fmt_b(market_cap)} | PE：{fmt_num(trailing_pe)} | Forward PE：{fmt_num(forward_pe)} | P/S：{fmt_num(ps)}
收入增速：{fmt_pct(revenue_growth)} | 毛利率：{fmt_pct(gross_margin)} | 净利率：{fmt_pct(profit_margin)}
行业：{sector} | 细分：{industry} | 主题：{theme_text} | 估值：{valuation_risk} | Danny模型：{danny_view}

请分析：公司核心逻辑、当前估值、技术面、机构态度、成长性、最大风险、1-3年空间、是否值得长期关注、给出评级。
输出中文，直接专业不废话。
"""
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role":"system","content":"你是专业华尔街基金经理。"},{"role":"user","content":prompt}],
                        temperature=0.7, max_tokens=1200
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
                    prompt = f"""
你是一位职业交易员。请为股票 {ticker} 制定交易计划。

当前数据：
价格：{current_price} | RSI：{rsi:.1f} | 距高点跌幅：{drawdown:.1f}%
支撑位：{support:.2f} | 压力位：{resistance:.2f} | 量比：{volume_ratio:.2f}
估值：{valuation_risk} | Danny模型：{danny_view}

请输出：激进买点、保守买点、是否适合抄底、分批建仓策略、止损位、第一/第二目标价、仓位建议、短/中/长线策略。
输出中文，适合实盘参考，提醒风险。
"""
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role":"system","content":"你是顶级职业交易员。"},{"role":"user","content":prompt}],
                        temperature=0.5, max_tokens=1000
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
                    prompt = f"""
你是一位极度谨慎的做空机构分析师。请从最悲观角度分析股票 {ticker}。

当前数据：
价格：{current_price} | PE：{fmt_num(trailing_pe)} | P/S：{fmt_num(ps)}
收入增速：{fmt_pct(revenue_growth)} | 净利率：{fmt_pct(profit_margin)} | Beta：{beta}
行业：{sector} | 主题：{theme_text} | 估值：{valuation_risk}

请重点分析：最大雷点、估值泡沫、行业竞争、AI泡沫、财报暴雷可能、机构出货、最大跌幅、最坏情况、做空理由。
输出中文，尖锐谨慎不客套。
"""
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role":"system","content":"你是华尔街做空机构分析师。"},{"role":"user","content":prompt}],
                        temperature=0.8, max_tokens=1200
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

# ── 手动新闻情绪分析 ──────────────────────────────────────────────────────────

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
                client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                prompt = f"""
你是一位专业美股新闻与市场情绪分析师。

股票代码：{ticker}
价格：{current_price} | 跌幅：{drawdown:.1f}% | RSI：{rsi:.1f} | 量比：{volume_ratio:.2f}
估值：{valuation_risk} | Danny模型：{danny_view} | 行业：{sector} | 主题：{theme_text}

用户提供的新闻/信息：
{news_input}

请分析：
1. 整体偏利多、利空还是中性
2. 是否影响短期/中长期股价
3. 是真实基本面变化还是市场噪音
4. 是否涉及订单、财报、监管、诉讼、并购、降级、宏观、关税、AI热度
5. 机构 vs 散户可能如何解读
6. 情绪评分 0-100
7. 对短线/中长期影响
8. 最终结论：利多 / 利空 / 中性 / 噪音

输出中文，直接专业不废话。
"""
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role":"system","content":"你是专业美股新闻与市场情绪分析师。"},{"role":"user","content":prompt}],
                    temperature=0.6, max_tokens=1200
                )
                st.session_state[news_cache_key] = response.choices[0].message.content
            except Exception as e:
                st.error(f"新闻情绪分析失败: {e}")

if st.session_state[news_cache_key]:
    st.markdown(f'<div class="ai-box">{st.session_state[news_cache_key].replace(chr(10),"<br>")}</div>', unsafe_allow_html=True)

if st.button("🧹 清除新闻情绪缓存"):
    st.session_state[news_cache_key] = None
    st.rerun()

# ── 风口预测 ──────────────────────────────────────────────────────────────────

st.subheader("🔥 风口预测 / 主题热度雷达")

SHEET_ID    = "1W3DZXgpDoyVSXYQN_XgAp4I5Uzv2I_SnBND2Kw2bPqc"
SIGNALS_GID = "1861710963"

@st.cache_data(ttl=900, show_spinner=False)
def load_theme_signals():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SIGNALS_GID}"
    return pd.read_csv(url, skiprows=10)

try:
    theme_df = load_theme_signals()
    if not theme_df.empty:
        latest_time = theme_df["RunTime"].iloc[0] if "RunTime" in theme_df.columns else "N/A"
        st.caption(f"数据更新时间：{latest_time}")
        show_cols = [c for c in ["Theme","TodayCount","Avg7","Growth","Score","Status","TopTitle","TopSource"] if c in theme_df.columns]
        hot_df = theme_df.sort_values("Score", ascending=False).head(10)
        st.dataframe(hot_df[show_cols], use_container_width=True, hide_index=True)

        if st.button("🧠 GPT解读今日风口"):
            with st.spinner("GPT 正在解读风口趋势..."):
                try:
                    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                    prompt = f"""
你是一位美股主题投资和产业趋势分析师。

今日风口主题监控数据：
{hot_df[show_cols].to_string(index=False)}

请分析：
1. 今天最值得关注的风口主题
2. 哪些是短线噪音
3. 哪些可能影响美股相关股票
4. 哪些主题和 AI、半导体、军工、机器人、生物科技、加密货币有关
5. 给出可能相关股票方向
6. 给出风险提醒
7. 最终列出今日 Top 3 风口

中文输出，直接专业。
"""
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role":"system","content":"你是专业美股主题投资分析师。"},{"role":"user","content":prompt}],
                        temperature=0.6, max_tokens=1200
                    )
                    st.markdown(f'<div class="ai-box">{response.choices[0].message.content.replace(chr(10),"<br>")}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"风口GPT分析失败: {e}")
    else:
        st.info("风口表格暂时没有数据。")
except Exception as e:
    st.warning("暂时无法读取风口预测 Google Sheet。请确认分享权限是"知道链接的人可查看"。")
    st.caption(str(e))

# ── K线图 + 成交量 ────────────────────────────────────────────────────────────

chart_df = df.tail(252)
st.subheader("📉 近一年K线 + 成交量")
g1, g2 = st.columns([1.25, 1])

fig = go.Figure()
fig.add_trace(go.Candlestick(x=chart_df.index, open=chart_df["Open"], high=chart_df["High"], low=chart_df["Low"], close=chart_df["Close"], name="K线"))
fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["MA20"],  name="MA20"))
fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["MA50"],  name="MA50"))
fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["MA200"], name="MA200"))
fig.add_hline(y=support,    line_dash="dot", annotation_text="支撑")
fig.add_hline(y=resistance, line_dash="dot", annotation_text="压力")
fig.update_layout(template="plotly_white", height=360, margin=dict(l=5,r=5,t=10,b=5),
                  dragmode="zoom", xaxis_rangeslider_visible=True,
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))

volume_fig = go.Figure()
volume_fig.add_trace(go.Bar(x=chart_df.index, y=chart_df["Volume"], name="Volume"))
volume_fig.update_layout(template="plotly_white", height=360, margin=dict(l=5,r=5,t=10,b=5),
                         dragmode="zoom", xaxis_rangeslider_visible=True)

with g1:
    st.plotly_chart(fig, use_container_width=True)
with g2:
    st.plotly_chart(volume_fig, use_container_width=True)