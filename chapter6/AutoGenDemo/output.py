
"""
比特币实时价格看板
数据源：CoinGecko（主）→ Binance（备）→ CoinPaprika（备）
运行：streamlit run app.py
依赖：streamlit>=1.37, requests>=2.31
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import requests
import streamlit as st

# ============================================================================
# 配置
# ============================================================================
CACHE_TTL_SECONDS = 25          # 行情缓存，必须 < 自动刷新间隔
HISTORY_TTL_SECONDS = 300       # 7 日走势缓存
HISTORY_DAYS = 7
REQUEST_TIMEOUT = 8
AUTO_REFRESH_SECONDS = 30
RETRIES = 1
STALE_AFTER_SECONDS = 120       # 超过该时长未更新则提示过期

st.set_page_config(page_title="比特币实时价格", page_icon="₿", layout="centered")

# ============================================================================
# 异常
# ============================================================================
class DataFetchError(RuntimeError):
    """所有数据源均失败时抛出。"""

# ============================================================================
# 网络层
# ============================================================================
def _http_json(url: str, params: dict[str, Any] | None = None) -> Any:
    """GET + JSON 解析。429/451 等确定性失败不重试，其余重试一次。"""
    last_exc: Exception | None = None
    for attempt in range(RETRIES + 1):
        try:
            resp = requests.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT,
                headers={
                    "User-Agent": "btc-price-board/1.2",
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            last_exc = exc
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (429, 451) or attempt >= RETRIES:
                break
            time.sleep(0.4 * (attempt + 1))
    if last_exc is None:
        raise DataFetchError("网络请求失败")
    raise last_exc          # 原样抛出：保留 Timeout / HTTPError 等真实类型

def _describe(exc: Exception) -> str:
    """把异常压成可读短标签，例如 HTTP 429 / Timeout。"""
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status is not None:
        return f"HTTP {status}"
    return type(exc).__name__

# ============================================================================
# 业务层
# ============================================================================
def _change_amount(price: float, pct: float) -> float:
    """由涨跌幅反推 24h 涨跌额，保证与涨跌幅同号自洽。"""
    if pct <= -100.0:                        # 极端值保护，避免除零
        return -price
    return price - price / (1.0 + pct / 100.0)

def _quote(price, pct, amount, source: str, updated_at: datetime) -> dict:
    return {
        "price": float(price),
        "change_pct": float(pct),
        "change_amount": float(amount),
        "source": source,
        "updated_at": updated_at,
    }

@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def get_btc_quote() -> dict:
    """返回 price / change_pct / change_amount / source / updated_at。"""
    problems: list[str] = []

    # ---- 源 1：CoinGecko ----
    try:
        payload = _http_json(
            "https://api.coingecko.com/api/v3/simple/price",
            {
                "ids": "bitcoin",
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_last_updated_at": "true",
            },
        )
        node = payload["bitcoin"]
        price = float(node["usd"])
        pct = float(node.get("usd_24h_change") or 0.0)
        ts = node.get("last_updated_at")
        updated = (
            datetime.fromtimestamp(float(ts), tz=timezone.utc)
            if ts
            else datetime.now(timezone.utc)
        )
        return _quote(price, pct, _change_amount(price, pct), "CoinGecko", updated)
    except Exception as exc:
        problems.append(f"CoinGecko {_describe(exc)}")

    # ---- 源 2：Binance（美国等地区可能返回 451） ----
    try:
        payload = _http_json(
            "https://api.binance.com/api/v3/ticker/24hr", {"symbol": "BTCUSDT"}
        )
        return _quote(
            payload["lastPrice"],
            payload["priceChangePercent"],
            payload["priceChange"],
            "Binance",
            datetime.now(timezone.utc),
        )
    except Exception as exc:
        problems.append(f"Binance {_describe(exc)}")

    # ---- 源 3：CoinPaprika（免密钥，含 24h 涨跌幅） ----
    try:
        payload = _http_json("https://api.coinpaprika.com/v1/tickers/btc-bitcoin")
        usd = payload["quotes"]["USD"]
        price = float(usd["price"])
        pct = float(usd.get("percent_change_24h") or 0.0)
        return _quote(
            price, pct, _change_amount(price, pct), "CoinPaprika",
            datetime.now(timezone.utc),
        )
    except Exception as exc:
        problems.append(f"CoinPaprika {_describe(exc)}")

    raise DataFetchError("；".join(problems))

@st.cache_data(ttl=HISTORY_TTL_SECONDS, show_spinner=False)
def get_btc_history(days: int = HISTORY_DAYS) -> list[float]:
    """7 日价格序列。失败直接抛异常，避免把空列表缓存住。"""
    payload = _http_json(
        "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
        {"vs_currency": "usd", "days": days},
    )
    return [float(row[1]) for row in payload["prices"]]

# ============================================================================
# 展示层
# ============================================================================
CUSTOM_CSS = """
<style>
  .btc-card {
      background: linear-gradient(135deg, #171c2b 0%, #232a3f 100%);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 20px;
      padding: 28px 32px;
      box-shadow: 0 14px 36px rgba(0, 0, 0, 0.35);
      margin: 6px 0 12px;
  }
  .btc-label {
      color: #8b93a7; font-size: 13px; letter-spacing: 1.2px; text-transform: uppercase;
  }
  .btc-price {
      color: #ffffff; font-size: 52px; font-weight: 800; line-height: 1.15;
      margin: 8px 0 4px; font-variant-numeric: tabular-nums;
  }
  .btc-change { font-size: 20px; font-weight: 700; }
  .btc-amt { font-size: 16px; opacity: 0.85; }
  .btc-caption { color: #6b7280; font-size: 13px; margin-top: 10px; }
  .btc-meta { color: #8b93a7; font-size: 13px; margin-bottom: 4px; }
  .btc-trend {
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 16px;
      padding: 18px 20px 12px;
      margin: 4px 0 12px;
  }
  .btc-trend-foot { color: #8b93a7; font-size: 13px; margin-top: 6px; }
</style>
"""

def _sparkline_svg(
    values: list[float], color: str, width: int = 600, height: int = 130, pad: int = 8
) -> str:
    """纯 SVG 折线 + 渐变面积，零额外依赖。"""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    n = len(values) - 1
    pts = []
    for i, v in enumerate(values):
        x = pad + (width - 2 * pad) * i / n
        y = height - pad - (height - 2 * pad) * (v - lo) / span
        pts.append(f"{x:.1f},{y:.1f}")
    poly = " ".join(pts)
    area = f"{pad},{height - pad} {poly} {width - pad},{height - pad}"
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">'
        f'<polygon points="{area}" fill="{color}" fill-opacity="0.12"/>'
        f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2.5" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
        f"</svg>"
    )

def render_price_card(quote: dict) -> None:
    up = quote["change_pct"] >= 0
    color = "#16c784" if up else "#ea3943"
    arrow = "▲" if up else "▼"
    sign = "+" if up else "−"

    # 单行 HTML + &#36; 实体：避免被 Markdown 解析成代码块或 LaTeX
    card = (
        '<div class="btc-card">'
        '<div class="btc-label">比特币 / 美元 · BTC/USD</div>'
        f'<div class="btc-price">&#36;{quote["price"]:,.2f}</div>'
        f'<div class="btc-change" style="color:{color};">'
        f'{arrow} {sign}{abs(quote["change_pct"]):.2f}%'
        f'<span class="btc-amt">&nbsp;({sign}&#36;{abs(quote["change_amount"]):,.2f})</span>'
        "</div>"
        '<div class="btc-caption">过去 24 小时涨跌</div>'
        "</div>"
    )
    st.markdown(card, unsafe_allow_html=True)

def render_meta(quote: dict) -> None:
    local = quote["updated_at"].astimezone()
    tz_name = local.tzname() or local.strftime("UTC%z") or "本地时间"
    age = (datetime.now(timezone.utc) - quote["updated_at"]).total_seconds()

    parts = [
        f"数据来源：{quote['source']}",
        f"更新时间：{local.strftime('%Y-%m-%d %H:%M:%S')} {tz_name}",
        f"缓存 {CACHE_TTL_SECONDS} 秒",
    ]
    if age > STALE_AFTER_SECONDS:
        parts.append(f"⚠️ 已 {int(age // 60)} 分钟未更新")

    st.markdown(
        f'<div class="btc-meta">{"　·　".join(parts)}</div>', unsafe_allow_html=True
    )

def render_price_section() -> None:
    """取数 + 渲染。失败时回退到上次成功数据，而不是空白页。"""
    first_load = "last_quote" not in st.session_state
    try:
        if first_load:
            with st.spinner("正在获取最新行情…"):   # 仅首屏显示，自动刷新不闪
                quote = get_btc_quote()
        else:
            quote = get_btc_quote()
        st.session_state["last_quote"] = quote
    except Exception as exc:
        detail = str(exc) if isinstance(exc, DataFetchError) else _describe(exc)
        cached = st.session_state.get("last_quote")
        if not cached:
            st.error("⚠️ 暂时无法获取比特币价格，请检查网络后点击「刷新价格」重试。")
            st.caption(f"技术细节：{detail}")
            return
        st.warning("⚠️ 行情更新失败，下方为最近一次成功获取的数据。")
        st.caption(f"技术细节：{detail}")
        quote = cached

    render_price_card(quote)
    render_meta(quote)

def render_trend_section() -> None:
    try:
        history = get_btc_history(HISTORY_DAYS)
    except Exception:
        st.caption(f"ℹ️ {HISTORY_DAYS} 日走势暂时不可用（不影响上方实时行情）")
        return

    if len(history) < 2:
        return

    first, last = history[0], history[-1]
    pct = ((last - first) / first * 100.0) if first else 0.0
    color = "#16c784" if pct >= 0 else "#ea3943"
    sign = "+" if pct >= 0 else "−"

    st.markdown(
        '<div class="btc-trend">'
        f'<div class="btc-label">过去 {HISTORY_DAYS} 天走势</div>'
        f"{_sparkline_svg(history, color)}"
        '<div class="btc-trend-foot">区间涨跌 '
        f'<span style="color:{color};font-weight:700;">{sign}{abs(pct):.2f}%</span>'
        "</div></div>",
        unsafe_allow_html=True,
    )

# 自动刷新片段（Streamlit >= 1.37）
_FRAGMENT = st.fragment(run_every=AUTO_REFRESH_SECONDS)(render_price_section)

# ============================================================================
# 主流程
# ============================================================================
def main() -> None:
    if not hasattr(st, "fragment"):
        st.error("需要 Streamlit ≥ 1.37，请升级：`pip install -U 'streamlit>=1.37'`")
        st.stop()

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.title("₿ 比特币实时价格")
    st.caption("实时追踪 BTC/USD 价格与 24 小时涨跌")

    col_btn, col_toggle = st.columns([1, 2])
    with col_btn:
        if st.button("🔄 刷新价格", type="primary", use_container_width=True):
            get_btc_quote.clear()     # 清缓存 → 本轮 rerun 立刻拉新数据
            get_btc_history.clear()
    with col_toggle:
        auto = st.toggle(f"自动刷新（每 {AUTO_REFRESH_SECONDS} 秒）", value=False)

    if auto:
        _FRAGMENT()
    else:
        render_price_section()

    render_trend_section()

    st.divider()
    st.caption("数据来自公开行情 API，仅供参考，不构成任何投资建议。")

if __name__ == "__main__":
    main()



# ```text
# # requirements.txt
# streamlit>=1.37,<2
# requests>=2.31
# ```

# ```bash
# pip install -r requirements.txt
# streamlit run app.py
# ```
