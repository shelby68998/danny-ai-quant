import time
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

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

@st.cache_data(ttl=1800, show_spinner=False)
def get_price_safe(symbol):
    try:
        data = yf.download(symbol, period="5d", auto_adjust=False, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        if data.empty:
            return None
        return float(data["Close"].dropna().iloc[-1])
    except Exception:
        return None

@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_data_safe(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        time.sleep(0.3)
        df = yf.download(symbol, period="max", auto_adjust=False, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return info, df, None
    except Exception as e:
        return {}, pd.DataFrame(), str(e)

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
    st.warning("数据源暂时受限或连接失败，可能是 Yahoo Finance 限流。请稍后刷新，或换一只股票测试。")
    st.caption(error_msg)

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

current_price = float(df["Close"].iloc[-1])
all_time_high = float(df["High"].max())
drawdown = (current_price - all_time_high) / all_time_high * 100
rsi = float(df["RSI"].iloc[-1])
atr = float(df["ATR"].iloc[-1])
ma20 = float(df["MA20"].iloc[-1])
ma50 = float(df["MA50"].iloc[-1])
ma200 = float(df["MA200"].iloc[-1])

last_52 = df.tail(252)
high_52 = float(last_52["High"].max())
low_52 = float(last_52["Low"].min())
current_volume = float(df["Volume"].iloc[-1])
avg_volume = float(df["Volume"].tail(30).mean())
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
from openai import OpenAI

st.subheader("🧠 GPT 深度分析")

if st.button("🚀 使用 OpenAI API 深度分析"):

    with st.spinner("GPT 正在分析中..."):

        try:
            client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

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

请重点分析：

1. 公司核心逻辑
2. 当前估值是否危险
3. 技术面强弱
4. 机构资金可能态度
5. 是否符合成长股
6. 最大风险
7. 未来1-3年空间
8. 现在是否值得关注
9. 给出评级

输出用中文。
"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "你是专业华尔街基金经理。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1200
            )

            ai_result = response.choices[0].message.content

            st.markdown(f"""
            <div class="ai-box">
            {ai_result.replace(chr(10), "<br>")}
            </div>
            """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"GPT分析失败: {e}")
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
