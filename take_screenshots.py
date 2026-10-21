"""Capture dashboard screenshots with a real desktop-width Chromium window.

Usage:
    python app.py            # in one terminal
    python take_screenshots.py
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8050"
OUT = Path(__file__).resolve().parent / "screenshots"
OUT.mkdir(exist_ok=True)

def settle(page, ms=1500):
    """Give Dash callbacks + Plotly redraws time to finish."""
    page.wait_for_timeout(ms)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=2)
        page.goto(URL, wait_until="networkidle")
        page.wait_for_selector(".js-plotly-plot", timeout=30000)
        settle(page, 2500)

        # 1) Full dashboard, no filters applied
        page.screenshot(path=str(OUT / "01_dashboard_full.png"), full_page=True)
        print("saved 01_dashboard_full.png")

        # 2) KPI cards close-up
        page.locator(".kpi-row").screenshot(path=str(OUT / "02_kpi_cards.png"))
        print("saved 02_kpi_cards.png")

        # 3) Filtered: Electronics only (category + region filters in action)
        page.click("#filter-category")
        settle(page, 600)
        for label in ["Furniture", "Accessories", "Stationery"]:
            page.locator(".dash-options-list-option", has_text=label).first.click()
            settle(page, 500)
        page.keyboard.press("Escape")
        settle(page, 2000)
        page.screenshot(path=str(OUT / "03_filtered_electronics.png"), full_page=True)
        print("saved 03_filtered_electronics.png")

        # 4) Back to all data, then apply a Q2 date range (1 Apr - 30 Jun 2025)
        page.click("#reset-btn")
        settle(page, 2000)

        page.click("#filter-date")
        settle(page, 400)
        page.fill("#filter-date", "01 Apr 2025")
        page.keyboard.press("Enter")
        settle(page, 1200)
        page.click("#filter-date-end-date")
        settle(page, 400)
        page.fill("#filter-date-end-date", "30 Jun 2025")
        page.keyboard.press("Enter")
        page.keyboard.press("Escape")
        settle(page, 2200)
        page.screenshot(path=str(OUT / "04_date_filtered_q2.png"), full_page=True)
        print("saved 04_date_filtered_q2.png")

        browser.close()


if __name__ == "__main__":
    main()
