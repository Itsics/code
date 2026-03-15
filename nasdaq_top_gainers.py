"""
Fetch the top 20 NASDAQ performers from last week using Yahoo Finance.
Outputs results to a CSV file and an HTML table.
"""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# NASDAQ-100 tickers (major liquid names; source: Wikipedia Nasdaq-100)
# Using a representative set - script fetches from Wikipedia if available
def get_nasdaq_tickers():
    try:
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        tables = pd.read_html(url)
        for table in tables:
            if "Ticker" in table.columns or "Symbol" in table.columns:
                col = "Ticker" if "Ticker" in table.columns else "Symbol"
                tickers = table[col].str.strip().dropna().tolist()
                # Filter to valid-looking tickers (letters only, 1-5 chars)
                tickers = [t for t in tickers if isinstance(t, str) and t.isalpha() and 1 <= len(t) <= 5]
                if len(tickers) >= 50:
                    return tickers
    except Exception:
        pass
    # Fallback: major NASDAQ tickers
    return [
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA", "AVGO", "COST",
        "PEP", "ADBE", "NFLX", "AMD", "INTC", "CMCSA", "TMUS", "INTU", "QCOM", "TXN",
        "AMAT", "ISRG", "VRTX", "REGN", "BKNG", "ADP", "GILD", "LRCX", "PANW", "SBUX",
        "MDLZ", "KLAC", "SNPS", "CDNS", "ASML", "MAR", "MRVL", "CRWD", "ABNB", "WDAY",
        "ORLY", "MNST", "DXCM", "FTNT", "PAYX", "CPRT", "KDP", "AEP", "CHTR", "MELI",
        "KHC", "ADSK", "PCAR", "CDW", "EXC", "XEL", "FAST", "EA", "CTAS", "ODFL",
        "GEHC", "VRSK", "IDXX", "ZS", "DDOG", "MDB", "TEAM", "SIRI", "CSGP", "FANG",
        "WBD", "ANSS", "TTD", "BKR", "DASH", "ROST", "WBA", "CCEP", "LCID", "RIVN",
    ]


def get_last_week_dates():
    """Return (start_date, end_date) for the most recent full trading week (Mon–Fri)."""
    today = datetime.now().date()
    # Last Friday
    days_since_friday = (today.weekday() - 4) % 7
    if days_since_friday == 0 and today.weekday() == 4:
        last_friday = today
    else:
        last_friday = today - timedelta(days=days_since_friday if days_since_friday else 7)
    last_monday = last_friday - timedelta(days=4)
    return last_monday.strftime("%Y-%m-%d"), last_friday.strftime("%Y-%m-%d")


def write_html(df, start_date, end_date, out_file="nasdaq_top20_last_week.html"):
    """Generate an HTML table from the top-20 dataframe."""
    # Format dates for subtitle (e.g. "Mar 9 – Mar 13, 2026")
    try:
        from datetime import datetime
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        sub_start = start_dt.strftime("%b %d").lstrip("0")
        sub_end = end_dt.strftime("%b %d").lstrip("0")
        year = end_dt.strftime("%Y")
        subtitle = f"Week of {sub_start} – {sub_end}, {year} · Yahoo Finance"
    except Exception:
        subtitle = f"Week of {start_date} – {end_date} · Yahoo Finance"

    rows = []
    for _, row in df.iterrows():
        ticker = row["Ticker"]
        rows.append(
            f'      <tr><td>{int(row["Rank"])}</td><td>{ticker}</td>'
            f'<td>{row["Open"]:.2f}</td><td>{row["Close"]:.2f}</td>'
            f'<td>+{row["Change_Pct"]:.2f}%</td>'
            f'<td><a href="https://finance.yahoo.com/quote/{ticker}" target="_blank" rel="noopener">Yahoo</a></td></tr>'
        )
    tbody = "\n".join(rows)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Top 20 NASDAQ Gainers — Last Week</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      font-family: "Segoe UI", system-ui, sans-serif;
      background: #0f1419;
      color: #e7e9ea;
      margin: 0;
      padding: 2rem;
      min-height: 100vh;
    }}
    h1 {{
      font-size: 1.5rem;
      font-weight: 600;
      margin-bottom: 0.25rem;
    }}
    .subtitle {{
      color: #71767b;
      font-size: 0.9rem;
      margin-bottom: 1.5rem;
    }}
    table {{
      width: 100%;
      max-width: 42rem;
      border-collapse: collapse;
      background: #16181c;
      border-radius: 12px;
      overflow: hidden;
    }}
    th, td {{
      padding: 0.75rem 1rem;
      text-align: left;
    }}
    th {{
      background: #1d2127;
      font-weight: 600;
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #8b98a5;
    }}
    tr:not(:last-child) td {{ border-bottom: 1px solid #2f3336; }}
    tr:hover td {{ background: #1d2127; }}
    td:nth-child(1) {{ width: 3rem; color: #8b98a5; }}
    td:nth-child(2) {{ font-weight: 600; }}
    td:nth-child(5) {{ font-weight: 600; color: #00ba7c; }}
    a {{
      color: #1d9bf0;
      text-decoration: none;
    }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>Top 20 NASDAQ Gainers</h1>
  <p class="subtitle">{subtitle}</p>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Ticker</th>
        <th>Open</th>
        <th>Close</th>
        <th>Change %</th>
        <th>Link</th>
      </tr>
    </thead>
    <tbody>
{tbody}
    </tbody>
  </table>
</body>
</html>
"""
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    start_date, end_date = get_last_week_dates()
    print(f"Checking performance for week {start_date} to {end_date}")

    tickers = get_nasdaq_tickers()
    print(f"Loaded {len(tickers)} NASDAQ tickers")

    results = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date, auto_adjust=True)
            if hist.empty or len(hist) < 2:
                continue
            open_price = hist["Open"].iloc[0]
            close_price = hist["Close"].iloc[-1]
            if open_price <= 0:
                continue
            pct_change = ((close_price - open_price) / open_price) * 100
            results.append({
                "Ticker": ticker,
                "Open": round(open_price, 2),
                "Close": round(close_price, 2),
                "Change_Pct": round(pct_change, 2),
                "Week_Start": start_date,
                "Week_End": end_date,
            })
        except Exception:
            continue

    if not results:
        print("No data retrieved. Check dates and connectivity.")
        return

    df = pd.DataFrame(results)
    df = df.sort_values("Change_Pct", ascending=False).head(20).reset_index(drop=True)
    df.insert(0, "Rank", range(1, len(df) + 1))

    csv_file = "nasdaq_top20_last_week.csv"
    html_file = "nasdaq_top20_last_week.html"
    df.to_csv(csv_file, index=False)
    write_html(df, start_date, end_date, html_file)
    print(f"\nTop 20 NASDAQ gainers saved to {csv_file} and {html_file}")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
