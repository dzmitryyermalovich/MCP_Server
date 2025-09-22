from mcp.server.fastmcp import FastMCP, Context
from dotenv import load_dotenv
import yfinance as yf
from datetime import datetime
from tavily import TavilyClient

import httpx
import json
import os

load_dotenv()

PORT = os.environ.get("PORT", 10000)
mcp = FastMCP("PersonalHelper", host="0.0.0.0", port=PORT)

def _log(*a):
    print(*a, flush=True)

@mcp.tool()
async def convert_pln_to_usd(amount: str) -> str:
    """
    Convert an amount in Polish złoty (PLN) to US dollars (USD) using Yahoo Finance.

    Args:
        amount: Amount in PLN (string, e.g., "100")
    Returns:
        Conversion result with rate and timestamp.
    """
    try:
        pln_value = float(amount)
    except ValueError:
        return f"Invalid amount '{amount}'. Please enter a number."

    ticker = "PLNUSD=X"  # Yahoo Finance FX ticker for PLN→USD
    data = yf.Ticker(ticker).history(period="1d")

    if data.empty:
        return "Could not fetch PLN→USD rate from Yahoo Finance."

    rate = float(data["Close"].iloc[-1])
    usd_value = pln_value * rate
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    return (
        f"{pln_value:g} PLN ≈ {usd_value:,.2f} USD\n"
        f"Exchange rate: 1 PLN = {rate:.6f} USD (as of {ts})"
    )


outfit = {
    "monday": "Casual shirt + jeans + sneakers",
    "tuesday": "Business suit + tie + leather shoes",
    "wednesday": "Polo shirt + chinos + loafers",
    "thursday": "T-shirt + joggers + trainers",
    "friday": "Casual jacket + jeans + boots",
    "saturday": "Relaxed hoodie + shorts + sneakers",
    "sunday": "Smart-casual sweater + trousers + loafers",
}


@mcp.tool()
async def get_outfit(day: str) -> str:
    """
    Recommend an outfit based on the given day.

    Args:
        day: Name of the day (monday, tuesday, ...).
    Returns:
        A string describing the outfit suggestion for that day.
    """
    return outfit[day]


# Initialize Tavily client


@mcp.tool()
async def tavily_search(query: str, ctx: Context) -> str:
    """
    Search the web using Tavily.
    Provide key via:
      - HTTP header 'X-Tavily-Api-Key: <key>'  (preferred)
      - HTTP header 'Authorization: Bearer <key>'
      - or environment variable TAVILY_API_KEY
    """
    hdrs_raw = ctx.client_headers or {}
    hdrs = {(k or "").lower(): v for k, v in hdrs_raw.items()}

    # Accept several variants, prioritize headers
    tavily_key = (
        hdrs.get("x-tavily-api-key")
        or (hdrs.get("authorization")[7:] if isinstance(hdrs.get("authorization"), str) and hdrs.get("authorization").lower().startswith("bearer ") else None)
        or os.getenv("TAVILY_API_KEY")
    )

    _log("=== Tavily Debug ===")
    _log("client_headers (lowercased):", {k: (v[:6] + "..." if isinstance(v, str) and any(t in k for t in ["key","auth","token"]) else v) for k, v in hdrs.items()})
    _log("tavily_key_present:", bool(tavily_key))
    _log("====================")

    if not tavily_key:
        return (
            "Error: Tavily API key missing. "
            "Send header 'X-Tavily-Api-Key: <key>' or 'Authorization: Bearer <key>', "
            "or set TAVILY_API_KEY in server env. "
            f"Seen header keys: {list(hdrs.keys())}"
        )

    try:
        client = TavilyClient(api_key=tavily_key)
        resp = client.search(query)   # simple call; adjust if you use advanced params
    except Exception as e:
        # Surface the actual error to your UI instead of a generic message
        return f"Tavily error during search: {type(e).__name__}: {e}"

    results = (resp or {}).get("results") or []
    if not results:
        # Include the raw response to help diagnose auth/plan errors
        return f"No results. Raw Tavily response: {resp}"

    parts = []
    for r in results:
        title = r.get("title", "(no title)")
        snippet = (r.get("content") or "").replace("\n", " ").strip()
        parts.append(f"{title}\n{snippet}")
    return "\n\n".join(parts)



if __name__ == "__main__":
    mcp.run(transport="streamable-http")
