"""Converte os SVG de docs/diagramas em PNG (docs/img) usando o Chrome instalado."""
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / "docs" / "diagramas"
DST = RAIZ / "docs" / "img"
DST.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    for f in sorted(SRC.glob("*.svg")):
        page = browser.new_page(device_scale_factor=1.6)
        page.goto(f.as_uri())
        page.locator("svg").screenshot(path=str(DST / f"{f.stem}.png"))
        page.close()
        print("ok", f.stem)
    browser.close()
