import asyncio
import aiohttp
import base64

SOURCE_SUBS = [
    "https://happy-decoder.cc/p/https://sillyvpn.qwaqdev.ru/sub/79ddc110-12a0-445e-abd5-ee25d8351e34",
    "https://happy-decoder.cc/p/hwid=e58a42fbb67e3da9/https://sub.xexvpn.ru/sub/YQI5CVN8OO/lte/"
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

OUTPUT_FILE = "output.txt"


async def fetch(session, url):
    try:
        async with session.get(url, timeout=20) as r:
            if r.status != 200:
                print(f"❌ {url} -> HTTP {r.status}")
                return ""
            text = await r.text()
            print(f"✅ Loaded {url} ({len(text)} chars)")
            return text
    except Exception as e:
        print(f"❌ Error {url}: {e}")
        return ""


async def fetch_all():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url) for url in SOURCE_SUBS]
        return await asyncio.gather(*tasks)


def decode_if_needed(text):
    text = text.strip()

    # если это уже конфиг
    if text.startswith(SUPPORTED):
        return text

    try:
        decoded = base64.b64decode(text + "===")
        return decoded.decode("utf-8", errors="ignore")
    except:
        return text


def extract_configs(text):
    result = []

    for line in text.splitlines():
        line = line.strip()
        if any(line.startswith(x) for x in SUPPORTED):
            result.append(line)

    return result


def deduplicate(configs):
    return list(dict.fromkeys(configs))


async def main():
    print("🚀 Loading subscriptions...")

    sources = await fetch_all()

    print(f"📦 Sources received: {len([s for s in sources if s])}")

    configs = []

    for source in sources:
        if not source:
            continue

        decoded = decode_if_needed(source)
        found = extract_configs(decoded)

        print(f"🔎 Found {len(found)} configs in source")
        configs.extend(found)

    configs = deduplicate(configs)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(configs))

    print(f"💾 Saved {len(configs)} configs -> {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
