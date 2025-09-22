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

    Args:
        query: Your search question (e.g. 'Who is Leo Messi?').
    Returns:
        Titles + snippets of the top results.
    """
    # normalize header keys to lowercase
    hdrs = {(k or "").lower(): v for k, v in (ctx.client_headers or {}).items()}
    tavily_key = hdrs.get("x-tavily-api-key") or os.getenv("TAVILY_API_KEY")

    _log("=== Tavily Debug ===")
    _log("client_headers:", hdrs)
    _log("tavily_key_present:", bool(tavily_key))
    _log("====================")


    if not tavily_key:
        return "Error: No Tavily API key provided. Supply it via HTTP header TAVILY_API_KEY or set TAVILY_API_KEY in the environment."

    try:
        client = TavilyClient(api_key=tavily_key)
        response = client.search(query)
    except Exception as e:
        return f"Tavily error: {e}"

    results = response.get("results", [])
    if not results:
        return "No results."

    lines = []
    for r in results:
        title = r.get("title", "(no title)")
        snippet = r.get("content", "").replace("\n", " ").strip()
        lines.append(f"{title}\n{snippet}")

    return "\n\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
