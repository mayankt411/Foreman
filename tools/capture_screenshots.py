import os
import time
from playwright.sync_api import sync_playwright

def capture_screenshots():
    out_dir = os.path.join(os.path.dirname(__file__), "docs", "images")
    os.makedirs(out_dir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 950})
        page = context.new_page()

        # 1. Inspection Console (Nominal Case)
        page.goto("http://localhost:8000")
        page.wait_for_selector("h1")
        time.sleep(2)
        page.screenshot(path=os.path.join(out_dir, "dashboard_inspection_console.png"), full_page=True)
        print("Captured dashboard_inspection_console.png")

        # 2. Defect Case (Seek to defect frame e.g. frame with short_circuit or dry_joint)
        # Click Next 2 times to show a defect frame
        next_btn = page.locator("button:has-text('Next')")
        if next_btn.is_visible():
            next_btn.click()
            time.sleep(0.5)
            next_btn.click()
            time.sleep(1)
        page.screenshot(path=os.path.join(out_dir, "defect_inspection_detail.png"), full_page=True)
        print("Captured defect_inspection_detail.png")

        # 3. Benchmark Results & ECE Tab
        bench_btn = page.locator("button:has-text('Benchmark results & ECE')")
        bench_btn.click()
        time.sleep(1.5)
        page.screenshot(path=os.path.join(out_dir, "benchmark_results_and_ece.png"), full_page=True)
        print("Captured benchmark_results_and_ece.png")

        browser.close()
    print("All screenshots successfully captured!")

if __name__ == "__main__":
    capture_screenshots()
