import html as html_modifier
import re

class GoogleDocsTransformer:
    def __init__(self):
        self.header_titles_captured = 0

    def escape_html(self, text: str) -> str:
        return html_modifier.escape(text)

    def get_heading_level(self, style_type: str) -> int | None:
        heading_map = {
            "HEADING_1": 1,
            "HEADING_2": 2,
            "HEADING_3": 3,
            "HEADING_4": 4,
            "HEADING_5": 5,
            "HEADING_6": 6,
        }
        return heading_map.get(style_type)

    def get_list_tag(self, lists: dict, bullet: dict) -> str:
        if not bullet or not bullet.get("listId"):
            return "ul"
        
        list_id = bullet["listId"]
        list_data = lists.get(list_id, {})
        nesting_level = bullet.get("nestingLevel", 0)
        
        try:
            levels = list_data.get("listProperties", {}).get("nestingLevels", [])
            if nesting_level < len(levels):
                glyph_type = levels[nesting_level].get("glyphType")
                if glyph_type and glyph_type != "BULLET" and glyph_type != "GLYPH_TYPE_UNSPECIFIED":
                    return "ol"
        except Exception:
            pass
        return "ul"

    def build_paragraph_css(self, style: dict, ignore_indent: bool = False) -> str:
        return ""

    def format_text_run(self, text_run: dict, strip_bold: bool = False) -> str:
        text = self.escape_html(text_run.get("content", ""))
        text = text.rstrip("\n")
        
        if not text:
            return ""

        style = text_run.get("textStyle", {})
        if not style:
            return text

        if style.get("link", {}).get("url"):
            return f'<a href="{style["link"]["url"]}">{text}</a>'

        return text

    def is_heading_paragraph(self, paragraph: dict) -> tuple[bool, int]:
        if paragraph.get("bullet"):
            return False, 0

        elements = paragraph.get("elements", [])
        if not elements:
            return False, 0

        full_text = "".join(elem.get("textRun", {}).get("content", "") for elem in elements).strip()
        if not full_text or full_text.startswith("(") or len(full_text) > 80:
            return False, 0

        paragraph_style = paragraph.get("paragraphStyle", {})
        named_style = paragraph_style.get("namedStyleType", "")
        heading_level = self.get_heading_level(named_style)
        if heading_level:
            return True, heading_level

        if full_text.isupper() and len(full_text.split()) <= 5:
            return True, 1

        lower_text = full_text.lower()
        if lower_text.startswith("step "):
            return True, 2
            
        return False, 0

    def process_paragraph(self, paragraph: dict, is_list_item: bool = False, ignore_indent: bool = False) -> str:
        elements = paragraph.get("elements", [])
        full_raw_text = "".join(elem.get("textRun", {}).get("content", "") for elem in elements).strip()
        
        if not full_raw_text:
            return ""

        is_bncc_desc = full_raw_text.startswith("(") and bool(re.search(r"^\([A-Z0-9]+\)", full_raw_text))

        text = ""
        for elem in elements:
            if elem.get("textRun", {}).get("content", "").strip():
                text += self.format_text_run(elem["textRun"], strip_bold=is_bncc_desc)
                
        text = text.strip()
        if not text:
            return ""

        if is_bncc_desc and text.isupper():
            text = text.capitalize()

        paragraph_style = paragraph.get("paragraphStyle", {})
        p_style = self.build_paragraph_css(paragraph_style, ignore_indent)

        if not is_list_item and self.header_titles_captured < 2:
            self.header_titles_captured += 1
            text_upper = text.upper()
            return f'HEADER_SPLIT_FLAG<h1>{text_upper}</h1>HEADER_SPLIT_FLAG'

        is_heading, heading_level = self.is_heading_paragraph(paragraph)
        
        if is_heading and not is_list_item:
            return f'HEADER_SPLIT_FLAG<h{heading_level}>{text}</h{heading_level}>HEADER_SPLIT_FLAG'
            
        if is_list_item:
            return text
            
        return f'<p>{text}</p>'

    def flatten_elements(self, content: list) -> list:
        """Extrai todos os elementos de forma 100% linear, desmontando tabelas para evitar colunas paralelas."""
        flat = []
        for element in content:
            if element.get("paragraph"):
                flat.append(element)
            elif element.get("table"):
                for row in element["table"].get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        flat.extend(self.flatten_elements(cell.get("content", [])))
            elif element.get("sectionBreak"):
                flat.append(element)
        return flat

    def process_header_footer(self, registry: dict, lists: dict, type_str: str) -> str:
        html = ""
        ids = list(registry.keys()) if registry else []
        if not ids:
            return html
            
        html += f'<div class="{type_str}">'
        for doc_id in ids:
            entry = registry.get(doc_id, {})
            html += self.process_content(entry.get("content", []), lists, ignore_indent=True)
        html += "</div>"
        return html

    def process_content(self, content: list, lists: dict = None, ignore_indent: bool = False) -> str:
        if lists is None:
            lists = {}
        
        elements = self.flatten_elements(content)
        
        html = ""
        list_stack = []
        
        def close_lists(until_level=0) -> str:
            res = ""
            while len(list_stack) > until_level:
                res += f"</{list_stack[-1]['type']}>"
                list_stack.pop()
            return res

        def ensure_list(bullet: dict) -> str:
            list_id = bullet.get("listId")
            level = bullet.get("nestingLevel", 0)
            list_type = self.get_list_tag(lists, bullet)
            res = ""
            
            while len(list_stack) > level + 1:
                res += f"</{list_stack[-1]['type']}>"
                list_stack.pop()
                
            if len(list_stack) <= level:
                for i in range(len(list_stack), level + 1):
                    res += f"<{list_type}>"
                    list_stack.append({"listId": list_id, "type": list_type, "level": i})
            return res

        for element in elements:
            if element.get("paragraph"):
                paragraph = element["paragraph"]
                if paragraph.get("bullet"):
                    html += ensure_list(paragraph["bullet"])
                    p_content = self.process_paragraph(paragraph, is_list_item=True, ignore_indent=ignore_indent)
                    if p_content.strip():
                        html += f"<li>{p_content}</li>"
                    continue
                    
                if len(list_stack) > 0:
                    html += close_lists(0)
                
                html += self.process_paragraph(paragraph, is_list_item=False, ignore_indent=ignore_indent)
                
            elif element.get("sectionBreak"):
                if len(list_stack) > 0:
                    html += close_lists(0)
                html += "<hr />"
                
        if len(list_stack) > 0:
            html += close_lists(0)

        if "HEADER_SPLIT_FLAG" in html:
            parts = html.split("HEADER_SPLIT_FLAG")
            sections = []
            current_header = None
            current_content = ""

            def build_block(header, body_text):
                if not header:
                    return body_text
                
                has_list = "<ul" in body_text or "<ol" in body_text
                clean_body = body_text.strip()
                
                if has_list:
                    return f'<details open><summary>{header}</summary><div>{body_text}</div></details>'
                elif clean_body:
                    return f'<div><div>{header}</div><div>{body_text}</div></div>'
                else:
                    return f'<div><div>{header}</div></div>'

            for part in parts:
                if not part:
                    continue
                if part.strip().startswith("<h"):
                    if current_header or current_content:
                        sections.append((current_header, current_content))
                    current_header = part.strip()
                    current_content = ""
                else:
                    current_content += part

            if current_header or current_content:
                sections.append((current_header, current_content))

            regular_blocks = []
            bncc_blocks = []

            for h, b in sections:
                is_bncc = False
                combined_check = (h or "") + " " + (b or "")
                if "BNCC" in combined_check.upper():
                    is_bncc = True

                rendered = build_block(h, b)
                if is_bncc:
                    bncc_blocks.append(rendered)
                else:
                    regular_blocks.append(rendered)

            return "".join(regular_blocks) + "".join(bncc_blocks)

        return html

    def convert_to_html(self, document: dict) -> str:
        self.header_titles_captured = 0
        body = document.get("body", {}).get("content", [])
        lists = document.get("lists", {})
        headers = document.get("headers", {})

        title = self.escape_html(document.get("title", "Documento"))

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>{title}</title>
</head>
<body>

<header>
    {self.process_header_footer(headers, lists, 'header')}
</header>

<div>
{self.process_content(body, lists)}
</div>

</body>
</html>
"""