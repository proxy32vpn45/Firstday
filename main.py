import asyncio
import aiohttp
import base64
from urllib.parse import urlparse
import socket

# =========================
# CONFIG
# =========================

SOURCE_SUBS = [
    # вставь свои ссылки сюда
]

SUPPORTED = (
    "vless://",
    "vmess://",
    "trojan://",
    "ss://",
    "ssr://",
    "hysteria://",
    "hysteria2://",
    "tuic://",
)

TIMEOUT = 5
MAX_TASKS = 300

OUTPUT_FILE = "output.txt"

# =========================
# FETCH SOURCES
# =========================

async def fetch(session, url):
    try:
        async with session.get(url, timeout=20) as r:
            return await r.text()
    except:
        return ""

async def fetch_all_sources():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url) for url in SOURCE_SUBS]
        return await asyncio.gather(*tasks)

# =========================
# BASE64 SAFE DECODE
# =========================

def decode_if_needed(text: str) -> str:
    text = text.strip()

    if "://" in text:
        return text

    try:
        return base64.b64decode(text + "===").decode("utf-8", errors="ignore")
    except:
        return text

# =========================
# EXTRACT CONFIGS
# =========================

def extract_configs(text: str):
    res = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        if line.startswith(SUPPORTED):
            res.append(line)

    return res

# =========================
# LOAD ALL
# =========================

async def load_configs():
    raw_sources = await fetch_all_sources()

    all_configs = []

    for raw in raw_sources:
        if not raw:
            continue

        decoded = decode_if_needed(raw)
        all_configs.extend(extract_configs(decoded))

    return all_configs

# =========================
# PARSE HOST/PORT
# =========================

def parse_config(cfg: str):
    try:
        u = urlparse(cfg)

        host = u.hostname
        port = u.port

        if not host or not port:
            return None, None

        return host, port

    except:
        return None, None

# =========================
# DNS CHECK
# =========================

async def dns_check(host):
    loop = asyncio.get_running_loop()
    try:
        await loop.getaddrinfo(host, None)
        return True
    except:
        return False

# =========================
# TCP CHECK
# =========================

async def tcp_check(host, port):
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=TIMEOUT
        )

        writer.close()
        await writer.wait_closed()

        return True

    except:
        return False

# =========================
# CHECK NODE
# =========================

async def check_node(cfg):
    host, port = parse_config(cfg)

    if not host or not port:
        return None

    if not await dns_check(host):
        return None

    if not await tcp_check(host, port):
        return None

    return cfg

# =========================
# CHECK ALL
# =========================

async def check_all(nodes):
    sem = asyncio.Semaphore(MAX_TASKS)

    async def worker(n):
        async with sem:
            return await check_node(n)

    tasks = [worker(n) for n in nodes]
    res = await asyncio.gather(*tasks)

    return [r for r in res if r]

# =========================
# DEDUP
# =========================

def deduplicate(nodes):
    seen = set()
    out = []

    for cfg in nodes:
        host, port = parse_config(cfg)

        if not host or not port:
            continue

        key = f"{host}:{port}"

        if key in seen:
            continue

        seen.add(key)
        out.append(cfg)

    return out

# =========================
# PIPELINE
# =========================

async def process(nodes):
    print("📥 loaded:", len(nodes))

    nodes = deduplicate(nodes)
    print("🧹 dedup:", len(nodes))

    nodes = await check_all(nodes)
    print("✅ alive:", len(nodes))

    return nodes

# =========================
# SAVE
# =========================

def save(nodes):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(nodes))

# =========================
# MAIN
# =========================

async def main():
    print("📡 loading sources...")
    configs = await load_configs()

    print("🔎 extracted:", len(configs))

    final = await process(configs)

    save(final)

    print("📦 saved:", len(final), "→", OUTPUT_FILE)

if __name__ == "__main__":
    asyncio.run(main())
