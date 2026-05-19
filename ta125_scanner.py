"""
TA-125 Scanner Module
Scans all 125 stocks in the Tel Aviv TA-125 index and finds stocks with
negative daily returns for the last 3 consecutive trading days.

Data sources (in priority order):
  1. TASE API  ג€“ https://api.tase.co.il/api/security/historyeod  (official, accurate)
  2. yfinance  ג€“ Yahoo Finance  (fallback for any stock the TASE API fails on)
"""

import asyncio
import logging
import sys
import io
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import aiohttp
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TASE API constants
# ---------------------------------------------------------------------------
_TASE_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "he-IL",
    "content-type": "application/json;charset=UTF-8",
    "origin": "https://market.tase.co.il",
    "referer": "https://market.tase.co.il/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
}
_TASE_COMPONENTS_URL = "https://api.tase.co.il/api/index/components"
_TASE_HISTORY_URL    = "https://api.tase.co.il/api/security/historyeod"
_TA125_INDEX_ID      = "137"   # official TASE index ID for TA-125
_DAYS_TO_FETCH       = 5       # fetch 5 days so we always have at least 3


# ---------------------------------------------------------------------------
# Step 1 ג€“ fetch the official TA-125 member list from TASE
# ---------------------------------------------------------------------------
def _fetch_ta125_members_sync() -> List[Dict]:
    """
    Return list of all TA-125 member dicts from the TASE API.
    Each dict has at least: SecurityNumber (str), ShortName (str).
    """
    all_items: List[Dict] = []
    page = 1

    # First call: get TotalRec
    body = {"dType": 1, "TotalRec": 1, "pageNum": 1, "oId": _TA125_INDEX_ID, "lang": "0"}
    try:
        r = requests.post(_TASE_COMPONENTS_URL, json=body, headers=_TASE_HEADERS, timeout=15)
        r.raise_for_status()
        total = r.json().get("TotalRec", 0)
    except Exception as e:
        logger.warning(f"TASE components API failed: {e}")
        return []

    while len(all_items) < total:
        body = {"dType": 1, "TotalRec": 150, "pageNum": page, "oId": _TA125_INDEX_ID, "lang": "0"}
        try:
            r = requests.post(_TASE_COMPONENTS_URL, json=body, headers=_TASE_HEADERS, timeout=15)
            r.raise_for_status()
            items = r.json().get("Items", [])
            if not items:
                break
            all_items.extend(items)
            page += 1
        except Exception as e:
            logger.warning(f"TASE components page {page} failed: {e}")
            break

    logger.info(f"Fetched {len(all_items)} TA-125 members from TASE API")
    return all_items


# ---------------------------------------------------------------------------
# Step 2 ג€“ fetch 3-day history for each stock using TASE API (async)
# ---------------------------------------------------------------------------
async def _fetch_history_tase_async(
    session: aiohttp.ClientSession,
    sec_number: str,         # e.g. "00662577"
    name: str,
    semaphore: asyncio.Semaphore,
) -> Optional[Tuple[str, str, float, float, float]]:
    """
    Fetch last 3 trading days for one stock via the TASE historyeod API.
    Returns (sec_number, name, day3_pct, day2_pct, day1_pct) where day1 = most recent,
    or None if the stock does not have 3 consecutive negative days or data is unavailable.
    """
    body = {"pType": 1, "TotalRec": _DAYS_TO_FETCH, "pageNum": 1, "oId": sec_number, "lang": "0"}
    async with semaphore:
        try:
            async with session.post(
                _TASE_HISTORY_URL,
                json=body,
                headers=_TASE_HEADERS,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json(content_type=None)
        except Exception as e:
            logger.debug(f"TASE historyeod failed for {sec_number} ({name}): {e}")
            return None

    items = data.get("Items", [])
    if len(items) < 3:
        return None

    # Items sorted newest ג†’ oldest
    c_day1 = items[0].get("Change")   # most recent
    c_day2 = items[1].get("Change")
    c_day3 = items[2].get("Change")   # oldest of the 3

    if c_day1 is None or c_day2 is None or c_day3 is None:
        return None

    if float(c_day1) < 0 and float(c_day2) < 0 and float(c_day3) < 0:
        return (sec_number, name, float(c_day3), float(c_day2), float(c_day1))
    return None


async def _scan_tase_api_async(
    members: List[Dict],
) -> Tuple[List[Tuple[str, str, float, float, float]], int, int]:
    """
    Scan all TA-125 members concurrently via the TASE API.
    Returns (negative_list, scanned_count, failed_count).
    """
    semaphore = asyncio.Semaphore(15)  # max 15 parallel requests
    connector = aiohttp.TCPConnector(limit=20)

    results: List[Tuple[str, str, float, float, float]] = []
    scanned = 0
    failed = 0

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for member in members:
            sec_num = str(member.get("SecurityNumber", "")).zfill(8)
            name = member.get("ShortName", sec_num)
            tasks.append(_fetch_history_tase_async(session, sec_num, name, semaphore))

        raw = await asyncio.gather(*tasks, return_exceptions=True)

    for item in raw:
        if isinstance(item, Exception):
            failed += 1   # actual API / network error
        elif item is None:
            scanned += 1  # fetched OK, but not 3 consecutive negatives
        else:
            scanned += 1  # fetched OK AND 3 consecutive negatives
            results.append(item)

    return results, scanned, failed


# ---------------------------------------------------------------------------
# Step 3 ג€“ yfinance fallback for stocks the TASE API could not serve
# ---------------------------------------------------------------------------
# Mapping from TASE SecurityNumber to Yahoo Finance ticker (for common stocks)
# This list covers the most liquid TA-125 components
_TASE_TO_YFINANCE: Dict[str, str] = {
    "00629014": "TEVA.TA",
    "00604611": "LUMI.TA",
    "00662577": "POLI.TA",
    "01082379": "TSEM.TA",
    "01084557": "NVMI.TA",
    "00767012": "PHOE.TA",
    "00691212": "DSCT.TA",
    "00695437": "MZTF.TA",
    "00720011": "ENIA.TA",
    "00585018": "HARL.TA",
    "00230011": "BEZQ.TA",
    "00224014": "CLIS.TA",
    "01119478": "AZRG.TA",
    "00273011": "NICE.TA",
    "00281014": "ICL.TA",
    "00593038": "FIBI.TA",
    "01097260": "BIGA.TA",
    "00566018": "MNRA.TA",
    "01081165": "MGDL.TA",
    "00323014": "MELISRON.TA",
    "00777037": "SKBN.TA",
    "00746016": "STRS.TA",
    "01084128": "DLEKG.TA",
    "01081124": "ESLT.TA",
}


def _yfinance_fallback(
    sec_numbers_needed: List[Tuple[str, str]]
) -> List[Tuple[str, str, float, float, float]]:
    """
    For sec_numbers that TASE API failed on, try Yahoo Finance.
    sec_numbers_needed: list of (sec_number, name)
    """
    import yfinance as yf
    import pandas as pd

    results = []
    tickers_to_try = []
    for sec_num, name in sec_numbers_needed:
        yf_ticker = _TASE_TO_YFINANCE.get(sec_num)
        if yf_ticker:
            tickers_to_try.append((sec_num, name, yf_ticker))

    if not tickers_to_try:
        return []

    yf_tickers = [t[2] for t in tickers_to_try]
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    try:
        data = yf.download(
            tickers=yf_tickers,
            period="15d",
            interval="1d",
            progress=False,
            auto_adjust=True,
        )
    except Exception as e:
        logger.warning(f"yfinance fallback download error: {e}")
        return []
    finally:
        sys.stderr = old_stderr

    if data.empty:
        return []

    for sec_num, name, yf_ticker in tickers_to_try:
        try:
            close: Optional[pd.Series] = None
            if isinstance(data.columns, pd.MultiIndex):
                if ("Close", yf_ticker) in data.columns:
                    close = data[("Close", yf_ticker)].dropna()
            else:
                if "Close" in data.columns:
                    close = data["Close"].dropna()

            if close is None or len(close) < 4:
                continue

            d1 = (close.iloc[-3] - close.iloc[-4]) / close.iloc[-4] * 100
            d2 = (close.iloc[-2] - close.iloc[-3]) / close.iloc[-3] * 100
            d3 = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100

            if d1 < 0 and d2 < 0 and d3 < 0:
                results.append((yf_ticker, name, d1, d2, d3))
        except Exception as e:
            logger.debug(f"yfinance fallback error for {yf_ticker}: {e}")

    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_negative_3days_stocks() -> Tuple[List[Tuple[str, str, float, float, float]], int, int]:
    """
    Synchronous entry point.
    Returns (negative_stocks, total_scanned, failed_count).

    Each entry in negative_stocks is:
        (ticker_or_secnum, hebrew_name, day3_pct, day2_pct, day1_pct)
    where day1 = most recent trading day, day3 = 3 days ago.
    All three values are negative floats (%).
    Sorted worst-first by cumulative decline.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_main_scan())
    finally:
        loop.close()
    return result


async def _main_scan() -> Tuple[List[Tuple[str, str, float, float, float]], int, int]:
    # 1. Get TA-125 member list from TASE
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as ex:
        members = await loop.run_in_executor(ex, _fetch_ta125_members_sync)

    if not members:
        logger.warning("TASE components API returned no members ג€“ falling back to yfinance only")
        # Minimal fallback using the known yfinance tickers
        neg = _yfinance_fallback(list(_TASE_TO_YFINANCE.items()))
        return neg, len(neg), len(_TASE_TO_YFINANCE) - len(neg)

    # 2. Scan all members via TASE API (async, parallel)
    neg_tase, scanned, failed = await _scan_tase_api_async(members)

    # 3. yfinance fallback for failed stocks
    if failed > 0:
        failed_members = [(str(m.get("SecurityNumber","")).zfill(8), m.get("ShortName","")) for m in members]
        # Get the set of already-scanned sec numbers
        scanned_ids = {t[0] for t in neg_tase}
        all_scanned_ids = {str(m.get("SecurityNumber","")).zfill(8) for m in members}
        # For yfinance we try all (it handles duplicates gracefully)
        yf_results = await asyncio.get_event_loop().run_in_executor(
            None, _yfinance_fallback, failed_members
        )
        # Add yfinance results that aren't already in neg_tase
        for entry in yf_results:
            # entry[0] is yf ticker, not sec_number ג€“ check by name to avoid duplicates
            if not any(e[1] == entry[1] for e in neg_tase):
                neg_tase.append(entry)

    # Sort by total cumulative decline (worst first)
    neg_tase.sort(key=lambda x: x[2] + x[3] + x[4])

    return neg_tase, scanned, failed


async def scan_ta125_async() -> Tuple[List[Tuple[str, str, float, float, float]], int, int]:
    """Async entry point for the Telegram bot."""
    return await _main_scan()


# ---------------------------------------------------------------------------
# Report formatter
# ---------------------------------------------------------------------------
def format_ta125_report(
    negative_stocks: List[Tuple[str, str, float, float, float]],
    total_scanned: int,
    failed_count: int,
) -> str:
    """
    Format the scan results as a Telegram MarkdownV2 message.
    """
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    count = len(negative_stocks)

    if count == 0:
        return (
            f"נ“ *׳¡׳¨׳™׳§׳× ׳׳“׳“ ׳×׳\\-125*\n"
            f"נ• {now}\n\n"
            f"ג… *׳׳™׳ ׳׳ ׳™׳•׳× ׳¢׳ 3 ׳™׳׳™׳ ׳©׳׳™׳׳™׳™׳ ׳¨׳¦׳•׳₪׳™׳\\!*\n\n"
            f"נ“ˆ ׳ ׳¡׳¨׳§׳•: {total_scanned} ׳׳ ׳™׳•׳×\n"
            f"ג ן¸ ׳׳ ׳–׳׳™׳ ׳•׳×: {failed_count}"
        )

    header = (
        f"נ“ *׳¡׳¨׳™׳§׳× ׳׳“׳“ ׳×׳\\-125 \\- 3 ׳™׳׳™׳ ׳©׳׳™׳׳™׳™׳*\n"
        f"נ• {now}\n\n"
        f"נ”´ *{count} ׳׳ ׳™׳•׳× ׳‘׳™׳¨׳™׳“׳” 3 ׳™׳׳™׳ ׳‘׳¨׳¦׳£:*\n\n"
    )

    def _escape(s: str) -> str:
        for ch in r"_*[]()~`>#+-=|{}.!\\":
            s = s.replace(ch, f"\\{ch}")
        return s

    lines = []
    for sec_or_ticker, name, d3, d2, d1 in negative_stocks:
        display = sec_or_ticker.replace(".TA", "")
        safe_name = _escape(name)
        safe_ticker = _escape(display)
        total = d3 + d2 + d1
        lines.append(
            f"נ”´ *{safe_name}* \\(`{safe_ticker}`\\)\n"
            f"   ׳׳₪׳ ׳™ 3 ׳™׳׳™׳: {d3:+.2f}%  \\|  ׳׳₪׳ ׳™ 2: {d2:+.2f}%  \\|  ׳׳×׳׳•׳: {d1:+.2f}%\n"
            f"   נ“ ׳¡׳”\"׳›: {total:+.2f}%\n"
        )

    footer = (
        f"\nנ“ˆ ׳ ׳¡׳¨׳§׳•: *{total_scanned}* ׳׳ ׳™׳•׳× \\| "
        f"ג ן¸ ׳׳ ׳–׳׳™׳ ׳•׳×: {failed_count}\n"
        f"נ”— ׳׳§׳•׳¨: ׳‘׳•׳¨׳¡׳× ׳×׳ ׳׳‘׳™׳‘ \\(TASE\\)"
    )

    body = "\n".join(lines)
    full_msg = header + body + footer

    if len(full_msg) <= 4000:
        return full_msg

    # Truncate to top 25
    truncated = "\n".join(lines[:25])
    return (
        header
        + truncated
        + f"\n_\\(׳׳•׳¦׳’׳•׳× 25 ׳׳×׳•׳ {count}\\)_\n"
        + footer
    )
