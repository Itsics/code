"""
Daily Movers — real-time page: NASDAQ & TASE gainers and losers.
Run: python app.py
Open: http://127.0.0.1:5000
Data is cached for 10 minutes; refresh the page to get latest after cache expires.
"""

from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime, timedelta
import os
import yfinance as yf
from daily_movers import fetch_all_movers

app = Flask(__name__)

@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

@app.route("/stock-report")
def serve_stock_report():
    return send_from_directory(os.path.dirname(__file__), "stock_report.html")

_cache = {"data": None, "expiry": None}
CACHE_MINUTES = 10


def get_movers(force_refresh=False):
    global _cache
    now = datetime.now()
    if not force_refresh and _cache["data"] is not None and _cache["expiry"] and now < _cache["expiry"]:
        return _cache["data"]
    data = fetch_all_movers()
    _cache["data"] = data
    _cache["expiry"] = now + timedelta(minutes=CACHE_MINUTES)
    return data


def table_rows(rows, is_gainer=True):
    out = []
    for i, r in enumerate(rows, 1):
        pct = r["Change_Pct"]
        sign = "+" if pct >= 0 else ""
        color = "#00ba7c" if pct >= 0 else "#f4212e"
        out.append(
            f'<tr><td>{i}</td><td>{r["Ticker"]}</td>'
            f'<td>{r["Open"]:.2f}</td><td>{r["Close"]:.2f}</td>'
            f'<td style="color:{color};font-weight:600">{sign}{pct:.2f}%</td>'
            f'<td><a href="https://finance.yahoo.com/quote/{r["Ticker"]}" target="_blank" rel="noopener">Yahoo</a></td></tr>'
        )
    return "\n".join(out) if out else "<tr><td colspan='6'>No data</td></tr>"


@app.route("/")
def index():
    force = request.args.get("refresh") == "1"
    data = get_movers(force_refresh=force)
    ng = table_rows(data["nasdaq_gainers"])
    nl = table_rows(data["nasdaq_losers"])
    tg = table_rows(data["tase_gainers"])
    tl = table_rows(data["tase_losers"])
    as_of = data["as_of"]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Daily Movers — NASDAQ & TASE</title>
  <meta http-equiv="refresh" content="300">
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      font-family: "Segoe UI", system-ui, sans-serif;
      background: #0f1419;
      color: #e7e9ea;
      margin: 0;
      padding: 1.5rem;
      min-height: 100vh;
    }}
    header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 1rem;
      margin-bottom: 1.5rem;
    }}
    h1 {{ font-size: 1.5rem; font-weight: 600; margin: 0; }}
    .subtitle {{
      color: #71767b;
      font-size: 0.85rem;
    }}
    .refresh {{ color: #8b98a5; font-size: 0.8rem; }}
    section {{
      margin-bottom: 2rem;
    }}
    section h2 {{
      font-size: 1.1rem;
      font-weight: 600;
      margin-bottom: 0.5rem;
      color: #e7e9ea;
    }}
    section h2 .badge {{
      font-size: 0.7rem;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      margin-left: 0.5rem;
    }}
    .badge-gain {{ background: #00ba7c33; color: #00ba7c; }}
    .badge-loss {{ background: #f4212e33; color: #f4212e; }}
    table {{
      width: 100%;
      max-width: 36rem;
      border-collapse: collapse;
      background: #16181c;
      border-radius: 10px;
      overflow: hidden;
    }}
    th, td {{ padding: 0.6rem 0.9rem; text-align: left; }}
    th {{
      background: #1d2127;
      font-weight: 600;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #8b98a5;
    }}
    tr:not(:last-child) td {{ border-bottom: 1px solid #2f3336; }}
    tr:hover td {{ background: #1d2127; }}
    td:nth-child(1) {{ width: 2.5rem; color: #8b98a5; }}
    td:nth-child(2) {{ font-weight: 600; }}
    a {{ color: #1d9bf0; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
      gap: 1.5rem;
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Daily Movers — NASDAQ & TASE</h1>
      <p class="subtitle">Gainers and losers · Data from Yahoo Finance</p>
    </div>
    <p class="refresh">Last updated: {as_of} · <a href="/?refresh=1">Refresh now</a> · Auto-refresh every 5 min</p>
  </header>

  <div class="grid">
    <section>
      <h2>NASDAQ <span class="badge badge-gain">Gainers</span></h2>
      <table>
        <thead><tr><th>#</th><th>Ticker</th><th>Prev</th><th>Last</th><th>Change %</th><th></th></tr></thead>
        <tbody>{ng}</tbody>
      </table>
    </section>
    <section>
      <h2>NASDAQ <span class="badge badge-loss">Losers</span></h2>
      <table>
        <thead><tr><th>#</th><th>Ticker</th><th>Prev</th><th>Last</th><th>Change %</th><th></th></tr></thead>
        <tbody>{nl}</tbody>
      </table>
    </section>
    <section>
      <h2>TASE (Tel Aviv) <span class="badge badge-gain">Gainers</span></h2>
      <table>
        <thead><tr><th>#</th><th>Ticker</th><th>Prev</th><th>Last</th><th>Change %</th><th></th></tr></thead>
        <tbody>{tg}</tbody>
      </table>
    </section>
    <section>
      <h2>TASE (Tel Aviv) <span class="badge badge-loss">Losers</span></h2>
      <table>
        <thead><tr><th>#</th><th>Ticker</th><th>Prev</th><th>Last</th><th>Change %</th><th></th></tr></thead>
        <tbody>{tl}</tbody>
      </table>
    </section>
  </div>
</body>
</html>"""
    return html


# ── Ticker pools per strategy ──
STRATEGY_TICKERS = {
    "Momentum": [
        "NVDA","SMCI","ARM","PLTR","RXRX","PLUG","UPST","AFRM","DUOL","CAVA",
        "RKLB","ASTS","HIMS","TTD","SHOP","HOOD","MNDY","GTLB",
    ],
    "Value": [
        "INTC","CSCO","HPQ","AMGN","GILD","SCHW","SOFI","ACMR",
        "CRUS","CLNE","PENN","META","GOOGL","QCOM","TXN",
    ],
    "Growth": [
        "SNOW","DDOG","MNDY","GTLB","HIMS","IRTC","TTD","SHOP",
        "HOOD","ASTS","RKLB","ZS","MDB","TEAM","CRWD","PANW",
    ],
    "Breakout": [
        "MRVL","ALAB","CIEN","DOCS","NU","FLUT","WING","ARRY",
        "TDW","AFRM","RXRX","NVDA","AMD","AVGO","LRCX","KLAC",
    ],
}

SECTOR_MAP = {
    "Technology": ["NVDA","SMCI","ARM","PLTR","INTC","CSCO","HPQ","SNOW","DDOG","MNDY",
                   "GTLB","MRVL","ALAB","CIEN","ZS","MDB","TEAM","CRWD","PANW","META","GOOGL"],
    "Healthcare": ["RXRX","NVAX","AMGN","GILD","HIMS","IRTC","DOCS"],
    "Energy":     ["PLUG","FCEL","CLNE","STEM","ARRY"],
    "Finance":    ["UPST","AFRM","SCHW","SOFI","HOOD","NU","FLUT","PENN"],
    "Consumer":   ["DUOL","CAVA","TTD","SHOP","WING"],
    "Industrials":["JOBY","RKLB","ASTS","TDW","ACMR"],
    "Materials":  ["MP","CRUS"],
    "Real Estate":["OPEN"],
}

_report_cache = {}  # key -> (data, expiry)


@app.route("/api/stock-report")
def api_stock_report():
    strategy = request.args.get("strategy", "Momentum")
    sectors   = request.args.get("sectors", "").split(",")
    count     = min(int(request.args.get("count", 10)), 20)
    min_change = float(request.args.get("min_change", 5))
    timeframe  = request.args.get("timeframe", "5d")

    # Build candidate list from strategy ∩ sectors
    strat_pool = set(STRATEGY_TICKERS.get(strategy, STRATEGY_TICKERS["Momentum"]))
    sector_pool = set()
    for sec in sectors:
        sector_pool.update(SECTOR_MAP.get(sec.strip(), []))
    candidates = list(strat_pool & sector_pool) if sector_pool else list(strat_pool)

    if not candidates:
        return jsonify({"stocks": [], "error": "No candidates for selected filters"})

    cache_key = f"{strategy}|{'|'.join(sorted(candidates))}|{timeframe}"
    now = datetime.now()
    if cache_key in _report_cache:
        cached_data, expiry = _report_cache[cache_key]
        if now < expiry:
            # still filter by min_change and count on cached data
            filtered = [s for s in cached_data if abs(s["changePct"]) >= min_change]
            return jsonify({"stocks": filtered[:count], "as_of": now.strftime("%H:%M:%S")})

    tf_map = {"1d": "2d", "5d": "5d", "1m": "1mo", "3m": "3mo"}
    yf_period = tf_map.get(timeframe, "5d")

    results = []
    for ticker in candidates:
        try:
            t = yf.Ticker(ticker)
            info = t.info

            price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            prev  = info.get("previousClose") or price
            hist  = t.history(period=yf_period)
            if hist.empty or price == 0:
                continue

            start_price = float(hist["Close"].iloc[0])
            change_pct  = round((price - start_price) / start_price * 100, 2) if start_price else 0
            volume      = round((info.get("volume") or info.get("regularMarketVolume") or 0) / 1_000_000, 2)
            pe          = info.get("trailingPE") or info.get("forwardPE")
            rev_growth  = info.get("revenueGrowth")
            rev_growth_pct = round(rev_growth * 100, 1) if rev_growth is not None else None
            market_cap  = info.get("marketCap") or 0
            name        = info.get("longName") or info.get("shortName") or ticker
            sector      = info.get("sector") or "Technology"

            results.append({
                "ticker":      ticker,
                "name":        name,
                "currentPrice": round(price, 2),
                "changePct":   change_pct,
                "pe":          round(pe, 1) if pe else None,
                "rev_growth":  rev_growth_pct,
                "volume":      volume,
                "marketCap":   market_cap,
                "sector":      sector,
            })
        except Exception:
            continue

    results.sort(key=lambda x: abs(x["changePct"]), reverse=True)
    _report_cache[cache_key] = (results, now + timedelta(minutes=10))

    filtered = [s for s in results if abs(s["changePct"]) >= min_change]
    return jsonify({"stocks": filtered[:count], "as_of": now.strftime("%H:%M:%S")})


if __name__ == "__main__":
    print("Daily Movers — open http://127.0.0.1:5001")
    app.run(host="127.0.0.1", port=5001, debug=False)
