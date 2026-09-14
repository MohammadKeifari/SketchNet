"""WhiteNoise header hooks.

Cloudflare (and similar proxies) must not minify or otherwise rewrite
SketchMod's large canvas.js — a truncated copy leaves the left palette empty.
"""


def add_static_headers(headers, path, url):
    if not str(path).endswith((".js", ".css")):
        return
    existing = headers.get("Cache-Control", "")
    if "no-transform" in existing.lower():
        return
    headers["Cache-Control"] = (
        f"{existing}, no-transform" if existing else "no-transform"
    )
