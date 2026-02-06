import os
import time
from playwright.sync_api import sync_playwright
import re

STREAMLIT_URL = "http://localhost:8501"
SCREENSHOT_DIR = os.path.join(os.getcwd(), "screenshots")

def run_test():
    if not os.path.exists(SCREENSHOT_DIR):
        os.makedirs(SCREENSHOT_DIR)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        print(f"Navigating to {STREAMLIT_URL}...")
        try:
            page.goto(STREAMLIT_URL, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"Navigation failed or timed out: {e}")
            
        print("Waiting for app to load...")
        try:
            page.wait_for_selector("text=FEM Analysis", timeout=20000)
            print("FEM Analysis section found.")
            
            if page.get_by_text("FEM preview unavailable").count() > 0:
                print("CRITICAL: FEM preview unavailable error detected!")
                page.screenshot(path=os.path.join(SCREENSHOT_DIR, "fem_preview_error.png"))
                return

        except Exception as e:
            print(f"FEM Analysis section not found: {e}")
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "error_loading.png"))
            return

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_initial_load.png"), full_page=True)
        
        buttons = page.get_by_role("button").all()
        print(f"Found {len(buttons)} buttons on page:")
        for i, b in enumerate(buttons):
            try:
                txt = b.inner_text()
                print(f"  Button {i}: '{txt}'")
            except:
                pass
        
        with open(os.path.join(SCREENSHOT_DIR, "page_content.html"), "w", encoding="utf-8") as f:
            f.write(page.content())

        def check_viz(name):
            print(f"Attempting to switch to {name}...")
            
            # Try finding the button element that contains the text
            
            btn = page.get_by_role("button", name=name)
            
            if btn.count() == 0:
                 print(f"  Role match failed. Trying exact text match for button...")
                 btn = page.locator(f"button:has-text('{name}')")

            if btn.count() > 0:
                print(f"Found button: {name}")
                
                # Check if it's already selected (primary type) - optional
                
                btn.first.scroll_into_view_if_needed()
                btn.first.click()
                print("Clicked, waiting for update...")
                page.wait_for_timeout(3000)
                
                charts = page.locator(".stPlotlyChart")
                count = charts.count()
                print(f"Found {count} Plotly charts in {name}")
                
                clean_name = name.replace(" ", "_").lower()
                page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"view_{clean_name}.png"))
                
                if count > 0:
                    return True
                else:
                    print(f"WARNING: No charts found in {name}")
                    return False
            else:
                print(f"ERROR: Button '{name}' not found")
                return False

        views_to_test = ["Plan View", "Elevation View", "3D View"]
        results = {}
        
        for view in views_to_test:
            results[view] = check_viz(view)

        print("\nTesting Load Combination Dropdown...")
        try:
             label = page.get_by_text("Active Combination")
             if label.count() > 0:
                 print("Found Active Combination label")
                 label.scroll_into_view_if_needed()
                 page.screenshot(path=os.path.join(SCREENSHOT_DIR, "controls_area.png"))
        except:
             print("Could not find Active Combination controls")
        
        print("\nTesting Display Options...")
        try:
            display_options = page.get_by_text("Display Options", exact=False)
            if display_options.count() > 0:
                print("Found Display Options expander")
                display_options.first.click()
                page.wait_for_timeout(1000)
                page.screenshot(path=os.path.join(SCREENSHOT_DIR, "display_options_expanded.png"))
                
                checkbox = page.get_by_text("Show nodes", exact=False)
                if checkbox.count() > 0:
                    print("Found Show nodes checkbox")
                    checkbox.first.click()
                    page.wait_for_timeout(2000)
                    page.screenshot(path=os.path.join(SCREENSHOT_DIR, "nodes_toggled.png"))
        except Exception as e:
            print(f"Error testing display options: {e}")

        print("\nTest Summary:")
        all_pass = True
        for view, passed in results.items():
            status = "PASS" if passed else "FAIL"
            print(f"{view}: {status}")
            if not passed:
                all_pass = False

        browser.close()
        
        if all_pass:
            print("\nOVERALL STATUS: PASS")
        else:
            print("\nOVERALL STATUS: FAIL")

if __name__ == "__main__":
    run_test()
