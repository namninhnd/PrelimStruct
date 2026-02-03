import pytest
import os

# Skip if playwright not installed OR if e2e tests not explicitly requested
pytest.importorskip("pytest_playwright")

# Skip unless E2E_TESTS=1 is set (requires running Streamlit server)
pytestmark = pytest.mark.skipif(
    os.environ.get("E2E_TESTS") != "1",
    reason="E2E tests require running Streamlit server. Set E2E_TESTS=1 to enable."
)

from playwright.sync_api import Page, expect


MOBILE_VIEWPORT_IPHONE_X = {"width": 375, "height": 812}
APP_URL = "http://localhost:8501"
SIDEBAR_COLLAPSED_MAX_WIDTH_PX = 50


def test_mobile_viewport_sidebar_no_overlay(page: Page):
    page.set_viewport_size(MOBILE_VIEWPORT_IPHONE_X)
    page.goto(APP_URL)
    page.wait_for_selector("h1", timeout=10000)
    
    main_content = page.locator("[data-testid='stAppViewContainer']")
    expect(main_content).to_be_visible()
    
    sidebar = page.locator("[data-testid='stSidebar']")
    
    if sidebar.is_visible():
        bounding_box = sidebar.bounding_box()
        if bounding_box:
            assert bounding_box["width"] < SIDEBAR_COLLAPSED_MAX_WIDTH_PX, \
                f"Sidebar width {bounding_box['width']}px overlays content"
    
    header = page.locator("h1:has-text('PrelimStruct')")
    expect(header).to_be_visible()
    
    story_height_input = page.locator("input[aria-label='Story Height (m)']").first
    if story_height_input.is_visible():
        expect(story_height_input).to_be_visible()


def test_mobile_warning_banner_visible(page: Page):
    page.set_viewport_size(MOBILE_VIEWPORT_IPHONE_X)
    page.goto(APP_URL)
    page.wait_for_selector("h1", timeout=10000)
    
    warning_text = page.locator("text=⚠️ Desktop Recommended")
    
    count = warning_text.count()
    assert count > 0, "Mobile warning banner not found in DOM"


def test_mobile_content_accessible(page: Page):
    page.set_viewport_size(MOBILE_VIEWPORT_IPHONE_X)
    page.goto(APP_URL)
    page.wait_for_selector("h1", timeout=10000)
    
    header = page.locator("h1:has-text('PrelimStruct')")
    expect(header).to_be_visible()
    
    main_content = page.locator("[data-testid='stAppViewContainer']")
    expect(main_content).to_be_visible()
    
    main_bbox = main_content.bounding_box()
    viewport_width = MOBILE_VIEWPORT_IPHONE_X["width"]
    
    if main_bbox:
        min_content_width = viewport_width * 0.9
        assert main_bbox["width"] >= min_content_width, \
            f"Main content width {main_bbox['width']}px < 90% of viewport {viewport_width}px"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
