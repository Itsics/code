"""
Fetch daily gainers and losers for NASDAQ and TASE from Yahoo Finance.
Used by the Flask app to power the real-time daily movers page.
"""

import yfinance as yf
from datetime import datetime, timedelta

# Reuse ticker lists (subset for speed; full lists can be used)
NASDAQ_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "COST", "PEP",
    "ADBE", "NFLX", "AMD", "INTC", "CMCSA", "TMUS", "INTU", "QCOM", "TXN", "AMAT",
    "ISRG", "VRTX", "REGN", "BKNG", "ADP", "GILD", "LRCX", "PANW", "SBUX", "MDLZ",
    "KLAC", "SNPS", "CDNS", "ASML", "MAR", "MRVL", "CRWD", "ABNB", "WDAY", "ORLY",
    "MNST", "DXCM", "FTNT", "PAYX", "CPRT", "KDP", "CHTR", "MELI", "ADSK", "PCAR",
    "CDW", "EA", "CTAS", "ODFL", "GEHC", "VRSK", "IDXX", "ZS", "DDOG", "MDB", "TEAM",
    "CRWD", "LCID", "RIVN",
]

TASE_TICKERS = [
    "TEVA.TA", "TASE.TA", "LUMI.TA", "POLI.TA", "ESLT.TA", "MZTF.TA", "AZRG.TA",
    "DSCT.TA", "NICE.TA", "PHOE.TA", "NVMI.TA", "BEZQ.TA", "ENLT.TA", "ICL.TA",
    "ORL.TA", "NWMD.TA", "FIBI.TA", "ELAL.TA", "PRIM.TA", "SMNR.TA", "TDRN.TA",
    "WILC.TA", "AMOT.TA", "BOLT.TA", "BRAM.TA", "CMDR.TA", "GEFR.TA", "GILT.TA",
    "KMDA.TA", "MTRX.TA", "PNRG.TA", "PTNR.TA", "ROTS.TA", "TSEM.TA", "NVPT.TA",
    "NXSN.TA", "ILCO.TA", "ONE.TA", "BRAN.TA", "HARL.TA", "MMHD.TA", "DIMRI.TA",
    "RVL.TA", "EVGN.TA", "OPK.TA", "TGI.TA", "TRAN.TA", "ALBA.TA", "APLP.TA",
    "SRAC.TA", "STRS.TA", "TATT.TA",
]


def get_daily_movers(tickers, top_n=20):
    """
    For each ticker, get % change from previous close to latest close.
    Returns (gainers_list, losers_list), each list of dicts with Ticker, Open, Close, Change_Pct.
    """
    results = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            # 5 days to ensure we have at least 2 trading days
            hist = stock.history(period="5d", interval="1d", auto_adjust=True)
            if hist.empty or len(hist) < 2:
                continue
            prev_close = hist["Close"].iloc[-2]
            last_close = hist["Close"].iloc[-1]
            if prev_close <= 0:
                continue
            pct = ((last_close - prev_close) / prev_close) * 100
            results.append({
                "Ticker": ticker,
                "Open": round(prev_close, 2),
                "Close": round(last_close, 2),
                "Change_Pct": round(pct, 2),
            })
        except Exception:
            continue

    if not results:
        return [], []

    sorted_by_change = sorted(results, key=lambda x: x["Change_Pct"], reverse=True)
    gainers = sorted_by_change[:top_n]
    losers = sorted_by_change[-top_n:][::-1]  # worst first (most negative)
    return gainers, losers


def fetch_all_movers():
    """Fetch NASDAQ and TASE gainers/losers. Returns dict with four lists and as_of time."""
    nasdaq_gainers, nasdaq_losers = get_daily_movers(NASDAQ_TICKERS, top_n=20)
    tase_gainers, tase_losers = get_daily_movers(TASE_TICKERS, top_n=20)
    return {
        "nasdaq_gainers": nasdaq_gainers,
        "nasdaq_losers": nasdaq_losers,
        "tase_gainers": tase_gainers,
        "tase_losers": tase_losers,
        "as_of": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


if __name__ == "__main__":
    # Quick test
    data = fetch_all_movers()
    print("NASDAQ Gainers:", len(data["nasdaq_gainers"]))
    print("NASDAQ Losers:", len(data["nasdaq_losers"]))
    print("TASE Gainers:", len(data["tase_gainers"]))
    print("TASE Losers:", len(data["tase_losers"]))
    print("As of:", data["as_of"])
