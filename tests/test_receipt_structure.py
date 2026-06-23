"""Structural validation tests for the transaction receipt HTML email template."""

import re
from pathlib import Path

import pytest

TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "transaction-receipt.html"

PROHIBITED_CSS_VALUES = ["flex", "inline-flex", "grid", "inline-grid"]
PROHIBITED_CSS_PROPERTIES = [
    "flex-direction", "flex-wrap", "flex-flow", "flex-grow", "flex-shrink", "flex-basis",
    "justify-content", "align-items", "align-self", "align-content", "order",
    "grid-template-columns", "grid-template-rows", "grid-template-areas",
    "grid-column", "grid-row", "grid-area", "grid-gap", "gap",
]


@pytest.fixture
def template_html() -> str:
    """Read and return the raw HTML template content."""
    return TEMPLATE_PATH.read_text(encoding="utf-8")


class TestTableStructure:
    """Validate that the template uses nested HTML tables for layout."""

    def test_contains_nested_tables(self, template_html: str):
        tables = re.findall(r"<table\b", template_html, re.IGNORECASE)
        assert len(tables) >= 2, f"Expected at least 2 tables, found {len(tables)}"

    def test_has_header_section(self, template_html: str):
        assert "HEADER SECTION" in template_html or "Order Confirmation" in template_html

    def test_has_body_section(self, template_html: str):
        assert "BODY SECTION" in template_html or "Order Id" in template_html or "order details" in template_html.lower()

    def test_has_footer_section(self, template_html: str):
        assert "FOOTER SECTION" in template_html or "Unsubscribe" in template_html


class TestCSSCompliance:
    """Validate that no flexbox or grid CSS is used."""

    def test_no_prohibited_css_values_in_inline_styles(self, template_html: str):
        style_attrs = re.findall(r'style="([^"]*)"', template_html, re.IGNORECASE)
        for attr in style_attrs:
            for value in PROHIBITED_CSS_VALUES:
                pattern = rf":\s*{re.escape(value)}\b"
                assert not re.search(pattern, attr, re.IGNORECASE), (
                    f"Prohibited CSS value '{value}' found in inline style: {attr[:80]}"
                )

    def test_no_prohibited_css_values_in_style_block(self, template_html: str):
        style_blocks = re.findall(r"<style[^>]*>(.*?)</style>", template_html, re.DOTALL | re.IGNORECASE)
        for block in style_blocks:
            for value in PROHIBITED_CSS_VALUES:
                pattern = rf":\s*{re.escape(value)}\b"
                assert not re.search(pattern, block, re.IGNORECASE), (
                    f"Prohibited CSS value '{value}' found in <style> block"
                )

    def test_no_prohibited_css_properties_in_inline_styles(self, template_html: str):
        style_attrs = re.findall(r'style="([^"]*)"', template_html, re.IGNORECASE)
        for attr in style_attrs:
            for prop in PROHIBITED_CSS_PROPERTIES:
                pattern = rf"\b{re.escape(prop)}\s*:"
                assert not re.search(pattern, attr, re.IGNORECASE), (
                    f"Prohibited CSS property '{prop}' found in inline style: {attr[:80]}"
                )

    def test_no_prohibited_css_properties_in_style_block(self, template_html: str):
        style_blocks = re.findall(r"<style[^>]*>(.*?)</style>", template_html, re.DOTALL | re.IGNORECASE)
        for block in style_blocks:
            for prop in PROHIBITED_CSS_PROPERTIES:
                pattern = rf"\b{re.escape(prop)}\s*:"
                assert not re.search(pattern, block, re.IGNORECASE), (
                    f"Prohibited CSS property '{prop}' found in <style> block"
                )


class TestOrderIDPlaceholder:
    """Validate that {{ORDER_ID}} appears visibly."""

    def test_order_id_present(self, template_html: str):
        assert "{{ORDER_ID}}" in template_html

    def test_order_id_not_in_comment(self, template_html: str):
        without_comments = re.sub(r"<!--.*?-->", "", template_html, flags=re.DOTALL)
        assert "{{ORDER_ID}}" in without_comments

    def test_order_id_in_visible_element(self, template_html: str):
        pattern = r"<td[^>]*>([^<]*\{\{ORDER_ID\}\}[^<]*)</td>"
        match = re.search(pattern, template_html, re.IGNORECASE)
        assert match is not None, "{{ORDER_ID}} is not within a visible <td> element"


class TestResponsiveWidths:
    """Validate responsive width handling and MSO conditional comments."""

    def test_table_widths_are_percentage_or_pixel(self, template_html: str):
        width_attrs = re.findall(r"<table[^>]*\bwidth=\"([^\"]+)\"", template_html, re.IGNORECASE)
        for width in width_attrs:
            assert re.match(r"^\d+%?$", width.strip()), (
                f"Table width '{width}' is not a percentage or pixel value"
            )

    def test_inner_container_max_width(self, template_html: str):
        pattern = r"<table[^>]*style=\"[^\"]*max-width:\s*700px[^\"]*\""
        match = re.search(pattern, template_html, re.IGNORECASE)
        assert match is not None, "Inner container table missing max-width: 700px"

    def test_mso_conditional_comments_present(self, template_html: str):
        assert "<!--[if mso]>" in template_html
        assert "<![endif]-->" in template_html

    def test_all_styling_is_inline(self, template_html: str):
        assert not re.search(r"<link[^>]*rel=[\"']stylesheet[\"']", template_html, re.IGNORECASE)
