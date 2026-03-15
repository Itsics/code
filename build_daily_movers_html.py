"""
Build daily_movers.html so you can open it in the browser without running the server.
Run: python build_daily_movers_html.py
Then double-click daily_movers.html (or open it in your browser).
"""

from datetime import datetime
from daily_movers import fetch_all_movers

OUT_FILE = "daily_movers.html"


def table_rows(rows):
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


def main():
    print("Fetching data from Yahoo Finance (may take 1–2 min)...")
    data = fetch_all_movers()
    as_of = data["as_of"]
    ng = table_rows(data["nasdaq_gainers"])
    nl = table_rows(data["nasdaq_losers"])
    tg = table_rows(data["tase_gainers"])
    tl = table_rows(data["tase_losers"])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Daily Movers — NASDAQ & TASE</title>
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
    header {{ display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; }}
    h1 {{ font-size: 1.5rem; font-weight: 600; margin: 0; }}
    .subtitle {{ color: #71767b; font-size: 0.85rem; }}
    .refresh {{ color: #8b98a5; font-size: 0.8rem; }}
    section {{ margin-bottom: 2rem; }}
    section h2 {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; color: #e7e9ea; }}
    section h2 .badge {{ font-size: 0.7rem; padding: 0.2rem 0.5rem; border-radius: 4px; margin-left: 0.5rem; }}
    .badge-gain {{ background: #00ba7c33; color: #00ba7c; }}
    .badge-loss {{ background: #f4212e33; color: #f4212e; }}
    table {{ width: 100%; max-width: 36rem; border-collapse: collapse; background: #16181c; border-radius: 10px; overflow: hidden; }}
    th, td {{ padding: 0.6rem 0.9rem; text-align: left; }}
    th {{ background: #1d2127; font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; color: #8b98a5; }}
    tr:not(:last-child) td {{ border-bottom: 1px solid #2f3336; }}
    tr:hover td {{ background: #1d2127; }}
    td:nth-child(1) {{ width: 2.5rem; color: #8b98a5; }}
    td:nth-child(2) {{ font-weight: 600; }}
    a {{ color: #1d9bf0; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 1.5rem; }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Daily Movers — NASDAQ & TASE</h1>
      <p class="subtitle">Gainers and losers · Data from Yahoo Finance</p>
    </div>
    <p class="refresh">Last updated: {as_of} · Run <code>python build_daily_movers_html.py</code> to refresh</p>
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

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved {OUT_FILE}")
    print("Open it in your browser (double-click the file).")


if __name__ == "__main__":
    main()
