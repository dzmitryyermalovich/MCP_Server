from mcp.server.fastmcp import FastMCP, Context
from dotenv import load_dotenv
import yfinance as yf
from datetime import datetime
from tavily import TavilyClient
from fastmcp.server.dependencies import get_http_headers
import httpx
import json
import os

load_dotenv()

PORT = os.environ.get("PORT", 10000)
mcp = FastMCP("PersonalHelper", host="0.0.0.0", port=PORT)

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

def _log(*a): print(*a, flush=True)

# ---------------- helpers ----------------
def _read_tavily_key_from_headers() -> str | None:
    """
    Preferred: Authorization: Bearer <token>
    Fallback:  X-Tavily-Api-Key: <token>
    """
    headers = get_http_headers() or {}
    # normalize keys to lowercase
    headers = { (k or "").lower(): v for k, v in headers.items() }

    # Authorization: Bearer <token>
    auth = headers.get("authorization", "")
    if isinstance(auth, str) and auth.lower().startswith("bearer "):
        return auth[7:].strip()

    # X-Tavily-Api-Key: <token>
    xkey = headers.get("x-tavily-api-key")
    if isinstance(xkey, str) and xkey.strip():
        return xkey.strip()

    return None

def _resolve_tavily_key() -> str | None:
    # 1) headers
    key = _read_tavily_key_from_headers()
    if key:
        return key
    # 2) env
    return os.getenv("TAVILY_API_KEY")



@mcp.tool()
async def tavily_search(query: str, ctx: Context) -> str:
    """
    Search the web using Tavily.

    Args:
        query: Your search question (e.g. 'Who is Leo Messi?').
    Returns:
        Titles + snippets of the top results.
    """
    tavily_key = _resolve_tavily_key()

    if not tavily_key:
        return "Error: No Tavily API key provided. Supply it via HTTP header TAVILY_API_KEY or set TAVILY_API_KEY in the environment."

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
