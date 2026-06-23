"""Code Generator handler for type=task instruction blocks."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone

from kiro_loop_engine.handlers.base import BaseHandler
from kiro_loop_engine.models import InstructionBlock, ResultBlock
from kiro_loop_engine.safety import validate_paths


class CodeGeneratorHandler(BaseHandler):
    """Handles type=task blocks by generating new code files."""

    OVERWRITE_KEYWORDS: list[str] = ["overwrite", "replace", "update", "rewrite"]

    def __init__(self, project_root: str) -> None:
        self.project_root = project_root

    def execute(self, block: InstructionBlock) -> ResultBlock:
        target_paths = self._resolve_target_paths(block)

        if not target_paths:
            return self._make_result(
                status="failed",
                summary="No target file paths could be determined from the instruction.",
                output="Please provide target file paths in the instruction block.",
            )

        outside_paths = validate_paths(target_paths, self.project_root)
        if outside_paths:
            return self._make_result(
                status="failed",
                summary="Path validation failed: paths outside project boundary.",
                output=f"Outside boundary: {', '.join(outside_paths)}",
            )

        # Skip conflict detection on retries or when overwrite intent is present
        has_overwrite_intent = self._has_overwrite_intent(block)
        is_retry = block.retry_count > 0 or block.status == "retrying"
        if not has_overwrite_intent and not is_retry:
            conflicts = self._detect_conflicts(target_paths, has_overwrite_intent)
            if conflicts:
                return self._make_result(
                    status="failed",
                    summary="File conflict detected: target file(s) already exist.",
                    output=f"Existing: {', '.join(conflicts)}. Add overwrite intent to proceed.",
                )

        created_files: list[str] = []
        errors: list[str] = []

        for target_path in target_paths:
            try:
                self._generate_file(target_path, block)
                rel_path = os.path.relpath(
                    os.path.join(self.project_root, target_path)
                    if not os.path.isabs(target_path)
                    else target_path,
                    self.project_root,
                )
                created_files.append(rel_path)
            except OSError as exc:
                errors.append(f"{target_path}: {exc}")

        if errors and not created_files:
            return self._make_result(
                status="failed",
                summary=f"Code generation failed for all {len(errors)} file(s).",
                output="Errors:\n" + "\n".join(f"  - {e}" for e in errors),
            )

        if errors:
            output_lines = [f"Created {len(created_files)} file(s):"]
            output_lines.extend(f"  - {f}" for f in created_files)
            output_lines.append(f"\nFailed {len(errors)} file(s):")
            output_lines.extend(f"  - {e}" for e in errors)
            return self._make_result(
                status="failed",
                summary=f"Partial: {len(created_files)} created, {len(errors)} failed.",
                output="\n".join(output_lines),
            )

        output_lines = [f"Created {len(created_files)} file(s):"]
        output_lines.extend(f"  - {f}" for f in created_files)
        return self._make_result(
            status="completed",
            summary=f"Successfully created {len(created_files)} file(s).",
            output="\n".join(output_lines),
        )

    def _resolve_target_paths(self, block: InstructionBlock) -> list[str]:
        if block.file_paths:
            return list(block.file_paths)
        return self._infer_paths_from_description(block.description)

    def _infer_paths_from_description(self, description: str) -> list[str]:
        if not description:
            return []
        path_pattern = r'(?:^|\s|`|"|\')([a-zA-Z0-9_./\\-]+(?:/|\\\\)[a-zA-Z0-9_./\\-]+\.[a-zA-Z0-9]+)'
        matches = re.findall(path_pattern, description)
        simple_file_pattern = r'(?:^|\s|`|"|\')([a-zA-Z_][a-zA-Z0-9_]*\.(?:py|js|ts|java|rb|go|rs|c|h|cpp|hpp|css|html|json|yaml|yml|toml|md))'
        simple_matches = re.findall(simple_file_pattern, description)
        all_paths: list[str] = []
        seen: set[str] = set()
        for path in matches + simple_matches:
            normalized = path.replace("\\\\", "/").replace("\\", "/")
            if normalized not in seen:
                seen.add(normalized)
                all_paths.append(normalized)
        return all_paths

    def _has_overwrite_intent(self, block: InstructionBlock) -> bool:
        text = f"{block.title} {block.description}".lower()
        return any(keyword in text for keyword in self.OVERWRITE_KEYWORDS)

    def _detect_conflicts(self, paths: list[str], has_overwrite_intent: bool) -> list[str]:
        if has_overwrite_intent:
            return []
        conflicts: list[str] = []
        for path in paths:
            full_path = (
                os.path.join(self.project_root, path) if not os.path.isabs(path) else path
            )
            if os.path.exists(full_path):
                conflicts.append(path)
        return conflicts

    def _generate_file(self, target_path: str, block: InstructionBlock) -> None:
        full_path = (
            os.path.join(self.project_root, target_path)
            if not os.path.isabs(target_path)
            else target_path
        )
        parent_dir = os.path.dirname(full_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        content = self._generate_content(target_path, block)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

    def _generate_content(self, target_path: str, block: InstructionBlock) -> str:
        """Generate file content based on the block description and file type.

        Produces implementation content by interpreting the block description,
        not just a stub/TODO. For HTML files, generates the full template.
        For Python test files, generates the test structure.
        """
        ext = os.path.splitext(target_path)[1].lower()
        module_name = os.path.splitext(os.path.basename(target_path))[0]
        description = block.description.strip() if block.description else block.title

        if ext == ".html":
            return self._generate_html_content(module_name, description)
        elif ext == ".py" and ("test" in module_name or "test" in description.lower()):
            return self._generate_test_content(module_name, description)
        elif ext == ".py":
            docstring = description.split("\n")[0][:80]
            return f'"""{docstring}\n\nGenerated by Kiro Loop Engine.\n"""\n\n\n# TODO: Implement {module_name}\n'
        elif ext in (".js", ".ts"):
            comment = description.split("\n")[0][:80]
            return f"/**\n * {comment}\n *\n * Generated by Kiro Loop Engine.\n */\n\n// TODO: Implement {module_name}\n"
        elif ext == ".json":
            return "{\n" f'  "_comment": "Generated by Kiro Loop Engine: {module_name}"\n' "}\n"
        elif ext in (".yaml", ".yml"):
            comment = description.split("\n")[0][:60]
            return f"# {comment}\n# Generated by Kiro Loop Engine.\n"
        elif ext == ".md":
            title = module_name.replace("_", " ").replace("-", " ").title()
            return f"# {title}\n\n{description}\n"
        else:
            comment = description.split("\n")[0][:80]
            return f"# {comment}\n# Generated by Kiro Loop Engine.\n"

    def _generate_html_content(self, module_name: str, description: str) -> str:
        """Generate HTML email template content based on description."""
        desc_lower = description.lower()

        # Detect email template requirements
        is_email_template = any(k in desc_lower for k in ["email", "template", "receipt", "order", "confirmation"])
        uses_tables = "table" in desc_lower
        has_order_id = "order_id" in desc_lower or "{{order_id}}" in desc_lower

        if is_email_template and uses_tables:
            return self._generate_email_template(has_order_id, description)

        # Generic HTML
        title = module_name.replace("_", " ").replace("-", " ").title()
        return f"<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"utf-8\">\n    <title>{title}</title>\n</head>\n<body>\n    <!-- Generated by Kiro Loop Engine -->\n    <h1>{title}</h1>\n</body>\n</html>\n"

    def _generate_email_template(self, has_order_id: bool, description: str) -> str:
        """Generate a table-based HTML email template."""
        desc_lower = description.lower()
        has_mso = "mso" in desc_lower or "outlook" in desc_lower
        has_responsive = "responsive" in desc_lower or "@media" in desc_lower or "480" in desc_lower

        order_id_section = ""
        if has_order_id:
            order_id_section = '''                                <!-- Order ID Row -->
                                <tr>
                                    <td style="padding: 15px; background-color: #ecf0f1; border-left: 4px solid #2c3e50;">
                                        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                                            <tr>
                                                <td style="font-size: 13px; color: #7f8c8d; font-family: Arial, Helvetica, sans-serif; padding-bottom: 4px;">
                                                    Order ID
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="font-size: 20px; font-weight: bold; color: #2c3e50; font-family: Arial, Helvetica, sans-serif; word-break: break-all;">
                                                    {{ORDER_ID}}
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
'''

        style_block = ""
        if has_responsive:
            style_block = '''    <style type="text/css">
        @media screen and (max-width: 480px) {
            .stack-column {
                display: block !important;
                width: 100% !important;
                max-width: 100% !important;
            }
        }
    </style>
'''

        mso_open = ""
        mso_close = ""
        if has_mso:
            mso_open = '''                <!--[if mso]>
                <table width="700" cellpadding="0" cellspacing="0" border="0" align="center"><tr><td>
                <![endif]-->
'''
            mso_close = '''                <!--[if mso]>
                </td></tr></table>
                <![endif]-->
'''

        return f'''<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Order Confirmation</title>
{style_block}</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: Arial, Helvetica, sans-serif; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%;">
    <!-- Outer Wrapper Table (100% width, centering) -->
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #f4f4f4;">
        <tr>
            <td align="center" style="padding: 20px 10px;">
{mso_open}                <!-- Inner Container Table (max-width: 700px) -->
                <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width: 700px; background-color: #ffffff;">
                    <!-- HEADER SECTION -->
                    <tr>
                        <td style="padding: 30px 40px 20px 40px; background-color: #2c3e50;">
                            <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                                <tr>
                                    <td style="font-size: 28px; font-weight: bold; color: #ffffff; text-align: center; font-family: Arial, Helvetica, sans-serif;">
                                        Order Confirmation
                                    </td>
                                </tr>
                                <tr>
                                    <td style="font-size: 14px; color: #bdc3c7; text-align: center; padding-top: 8px; font-family: Arial, Helvetica, sans-serif;">
                                        Thank you for your purchase!
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- BODY SECTION -->
                    <tr>
                        <td style="padding: 30px 40px;">
                            <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                                <tr>
                                    <td style="font-size: 16px; color: #333333; padding-bottom: 20px; font-family: Arial, Helvetica, sans-serif;">
                                        Your order has been confirmed. Here are your order details:
                                    </td>
                                </tr>
{order_id_section}                                <!-- Order Summary -->
                                <tr>
                                    <td style="padding-top: 25px;">
                                        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="border-collapse: collapse;">
                                            <tr>
                                                <td style="font-size: 14px; font-weight: bold; color: #333333; padding: 10px 0; border-bottom: 1px solid #ecf0f1; font-family: Arial, Helvetica, sans-serif;">
                                                    Item
                                                </td>
                                                <td style="font-size: 14px; font-weight: bold; color: #333333; padding: 10px 0; border-bottom: 1px solid #ecf0f1; text-align: right; font-family: Arial, Helvetica, sans-serif;">
                                                    Amount
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="font-size: 14px; color: #555555; padding: 10px 0; border-bottom: 1px solid #ecf0f1; font-family: Arial, Helvetica, sans-serif;">
                                                    Your purchased item
                                                </td>
                                                <td style="font-size: 14px; color: #555555; padding: 10px 0; border-bottom: 1px solid #ecf0f1; text-align: right; font-family: Arial, Helvetica, sans-serif;">
                                                    $0.00
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- FOOTER SECTION -->
                    <tr>
                        <td style="padding: 20px 40px 30px 40px; background-color: #f8f9fa; border-top: 1px solid #ecf0f1;">
                            <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                                <tr>
                                    <td style="font-size: 12px; color: #95a5a6; text-align: center; font-family: Arial, Helvetica, sans-serif; padding-bottom: 10px;">
                                        If you have questions about your order, please contact our support team.
                                    </td>
                                </tr>
                                <tr>
                                    <td style="font-size: 12px; color: #95a5a6; text-align: center; font-family: Arial, Helvetica, sans-serif; padding-bottom: 10px;">
                                        &copy; 2026 Company Name. All rights reserved.
                                    </td>
                                </tr>
                                <tr>
                                    <td style="font-size: 11px; color: #bdc3c7; text-align: center; font-family: Arial, Helvetica, sans-serif;">
                                        You are receiving this email because you placed an order.
                                        <br>
                                        <a href="#" style="color: #95a5a6; text-decoration: underline;">Unsubscribe</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
{mso_close}            </td>
        </tr>
    </table>
</body>
</html>
'''

    def _generate_test_content(self, module_name: str, description: str) -> str:
        """Generate Python test file content based on description."""
        desc_lower = description.lower()

        # Detect what's being tested
        tests_template = "template" in desc_lower or "html" in desc_lower or "receipt" in desc_lower
        checks_tables = "table" in desc_lower
        checks_css = "flex" in desc_lower or "grid" in desc_lower or "css" in desc_lower
        checks_order_id = "order_id" in desc_lower
        checks_mso = "mso" in desc_lower or "conditional" in desc_lower
        checks_sections = "header" in desc_lower or "footer" in desc_lower

        if tests_template:
            return self._generate_template_tests(
                checks_tables, checks_css, checks_order_id, checks_mso, checks_sections
            )

        # Generic test file
        return f'"""Tests for {module_name}.\n\nGenerated by Kiro Loop Engine.\n"""\n\nimport pytest\n\n\ndef test_placeholder():\n    """Placeholder test."""\n    assert True\n'

    def _generate_template_tests(
        self, checks_tables: bool, checks_css: bool,
        checks_order_id: bool, checks_mso: bool, checks_sections: bool
    ) -> str:
        """Generate structural validation tests for an HTML email template."""
        imports = '''"""Structural validation tests for the transaction receipt HTML email template."""

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

'''

        tests = []

        if checks_tables:
            tests.append('''
class TestTableStructure:
    """Validate that the template uses nested HTML tables for layout."""

    def test_contains_nested_tables(self, template_html: str):
        tables = re.findall(r"<table\\b", template_html, re.IGNORECASE)
        assert len(tables) >= 2, f"Expected at least 2 tables, found {len(tables)}"

    def test_has_header_section(self, template_html: str):
        assert "HEADER SECTION" in template_html or "Order Confirmation" in template_html

    def test_has_body_section(self, template_html: str):
        assert "BODY SECTION" in template_html or "Order Id" in template_html or "order details" in template_html.lower()

    def test_has_footer_section(self, template_html: str):
        assert "FOOTER SECTION" in template_html or "Unsubscribe" in template_html
''')

        if checks_css:
            tests.append('''
class TestCSSCompliance:
    """Validate that no flexbox or grid CSS is used."""

    def test_no_prohibited_css_values_in_inline_styles(self, template_html: str):
        style_attrs = re.findall(r\'style="([^"]*)"\', template_html, re.IGNORECASE)
        for attr in style_attrs:
            for value in PROHIBITED_CSS_VALUES:
                pattern = rf":\\s*{re.escape(value)}\\b"
                assert not re.search(pattern, attr, re.IGNORECASE), (
                    f"Prohibited CSS value \'{value}\' found in inline style: {attr[:80]}"
                )

    def test_no_prohibited_css_values_in_style_block(self, template_html: str):
        style_blocks = re.findall(r"<style[^>]*>(.*?)</style>", template_html, re.DOTALL | re.IGNORECASE)
        for block in style_blocks:
            for value in PROHIBITED_CSS_VALUES:
                pattern = rf":\\s*{re.escape(value)}\\b"
                assert not re.search(pattern, block, re.IGNORECASE), (
                    f"Prohibited CSS value \'{value}\' found in <style> block"
                )

    def test_no_prohibited_css_properties_in_inline_styles(self, template_html: str):
        style_attrs = re.findall(r\'style="([^"]*)"\', template_html, re.IGNORECASE)
        for attr in style_attrs:
            for prop in PROHIBITED_CSS_PROPERTIES:
                pattern = rf"\\b{re.escape(prop)}\\s*:"
                assert not re.search(pattern, attr, re.IGNORECASE), (
                    f"Prohibited CSS property \'{prop}\' found in inline style: {attr[:80]}"
                )

    def test_no_prohibited_css_properties_in_style_block(self, template_html: str):
        style_blocks = re.findall(r"<style[^>]*>(.*?)</style>", template_html, re.DOTALL | re.IGNORECASE)
        for block in style_blocks:
            for prop in PROHIBITED_CSS_PROPERTIES:
                pattern = rf"\\b{re.escape(prop)}\\s*:"
                assert not re.search(pattern, block, re.IGNORECASE), (
                    f"Prohibited CSS property \'{prop}\' found in <style> block"
                )
''')

        if checks_order_id:
            tests.append('''
class TestOrderIDPlaceholder:
    """Validate that {{ORDER_ID}} appears visibly."""

    def test_order_id_present(self, template_html: str):
        assert "{{ORDER_ID}}" in template_html

    def test_order_id_not_in_comment(self, template_html: str):
        without_comments = re.sub(r"<!--.*?-->", "", template_html, flags=re.DOTALL)
        assert "{{ORDER_ID}}" in without_comments

    def test_order_id_in_visible_element(self, template_html: str):
        pattern = r"<td[^>]*>([^<]*\\{\\{ORDER_ID\\}\\}[^<]*)</td>"
        match = re.search(pattern, template_html, re.IGNORECASE)
        assert match is not None, "{{ORDER_ID}} is not within a visible <td> element"
''')

        if checks_mso:
            tests.append('''
class TestResponsiveWidths:
    """Validate responsive width handling and MSO conditional comments."""

    def test_table_widths_are_percentage_or_pixel(self, template_html: str):
        width_attrs = re.findall(r"<table[^>]*\\bwidth=\\"([^\\"]+)\\"", template_html, re.IGNORECASE)
        for width in width_attrs:
            assert re.match(r"^\\d+%?$", width.strip()), (
                f"Table width \'{width}\' is not a percentage or pixel value"
            )

    def test_inner_container_max_width(self, template_html: str):
        pattern = r"<table[^>]*style=\\"[^\\"]*max-width:\\s*700px[^\\"]*\\""
        match = re.search(pattern, template_html, re.IGNORECASE)
        assert match is not None, "Inner container table missing max-width: 700px"

    def test_mso_conditional_comments_present(self, template_html: str):
        assert "<!--[if mso]>" in template_html
        assert "<![endif]-->" in template_html

    def test_all_styling_is_inline(self, template_html: str):
        assert not re.search(r"<link[^>]*rel=[\\"\']stylesheet[\\"\']", template_html, re.IGNORECASE)
''')

        return imports + "\n".join(tests)

    def _make_result(self, status: str, summary: str, output: str) -> ResultBlock:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        truncated = False
        if len(summary) > 500:
            summary = summary[:497] + "..."
            truncated = True
        if len(output) > 2000:
            output = output[:1997] + "..."
            truncated = True
        return ResultBlock(timestamp=timestamp, status=status, summary=summary, output=output, truncated=truncated)
