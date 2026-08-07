import html as html_modifier

class GoogleDocsTransformer:
    def __init__(self):
        pass

    def escape_html(self, text: str) -> str:
        return html_modifier.escape(text)

    def is_white_color(self, rgb: dict) -> bool:
        r = round((rgb.get("red", 0)) * 255)
        g = round((rgb.get("green", 0)) * 255)
        b = round((rgb.get("blue", 0)) * 255)
        return r >= 250 and g >= 250 and b >= 250

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
        if not style:
            return ""
        
        css = []
        align_map = {"START": "left", "CENTER": "center", "END": "right", "JUSTIFIED": "justify"}
        
        if style.get("alignment"):
            css.append(f"text-align:{align_map.get(style['alignment'], 'left')}")
            
        if style.get("lineSpacing"):
            css.append(f"line-height:{style['lineSpacing'] / 100}")
            
        if not ignore_indent and style.get("indentStart", {}).get("magnitude", 0) > 0:
            css.append(f"padding-left:{style['indentStart']['magnitude']}pt")
            
        if not ignore_indent and style.get("indentFirstLine", {}).get("magnitude", 0) > 0:
            css.append(f"text-indent:{style['indentFirstLine']['magnitude']}pt")
            
        if style.get("keepLinesTogether"):
            css.append("page-break-inside:avoid")
            
        return ";".join(css)

    def format_text_run(self, text_run: dict) -> str:
        text = self.escape_html(text_run.get("content", ""))
        text = text.rstrip("\n")
        
        style = text_run.get("textStyle", {})
        if not style:
            return f'<span>{text}</span>'
            
        css = []
        
        if style.get("weightedFontFamily", {}).get("fontFamily"):
            css.append(f"font-family:{style['weightedFontFamily']['fontFamily']}")
            
        if style.get("fontSize", {}).get("magnitude"):
            css.append(f"font-size:{style['fontSize']['magnitude']}pt")
            
        if style.get("bold"):
            css.append("font-weight:bold")
            
        if style.get("italic"):
            css.append("font-style:italic")
            
        if style.get("underline"):
            css.append("text-decoration:underline")
            
        if style.get("strikethrough"):
            css.append("text-decoration:line-through")
            
        if style.get("smallCaps"):
            css.append("font-variant:small-caps")

        if style.get("foregroundColor", {}).get("color", {}).get("rgbColor"):
            rgb = style["foregroundColor"]["color"]["rgbColor"]
            if not self.is_white_color(rgb):
                has_real_color = any(k in rgb for k in ["red", "green", "blue"])
                if has_real_color:
                    css.append(f"color:rgb({round(rgb.get('red', 0)*255)},{round(rgb.get('green', 0)*255)},{round(rgb.get('blue', 0)*255)})")
            
        if style.get("baselineOffset") == "SUPERSCRIPT":
            css.append("vertical-align:super")
            css.append("font-size:smaller")
        elif style.get("baselineOffset") == "SUBSCRIPT":
            css.append("vertical-align:sub")
            css.append("font-size:smaller")
            
        style_attr = ";".join(css)
        
        if style.get("link", {}).get("url"):
            return f'<a href="{style["link"]["url"]}" style="{style_attr}">{text}</a>'
            
        return f'<span style="{style_attr}">{text}</span>'

    def is_heading_paragraph(self, paragraph: dict) -> tuple[bool, int]:
        paragraph_style = paragraph.get("paragraphStyle", {})
        named_style = paragraph_style.get("namedStyleType", "")
        heading_level = self.get_heading_level(named_style)
        if heading_level:
            return True, heading_level
        
        elements = paragraph.get("elements", [])
        if not elements:
            return False, 0
            
        full_text = ""
        is_all_bold = True
        has_text = False
        
        for elem in elements:
            tr = elem.get("textRun", {})
            content = tr.get("content", "").strip()
            if content:
                has_text = True
                full_text += content + " "
                st = tr.get("textStyle", {})
                if not st.get("bold"):
                    is_all_bold = False
                    
        full_text = full_text.strip()
        
        if has_text and len(full_text) < 80:
            if is_all_bold or full_text.isupper() or paragraph_style.get("alignment") == "CENTER":
                return True, 2
                
        return False, 0

    def process_paragraph(self, paragraph: dict, is_list_item: bool = False, ignore_indent: bool = False) -> str:
        elements = paragraph.get("elements", [])
        text = ""
        
        for elem in elements:
            if elem.get("textRun", {}).get("content", "").strip():
                text += self.format_text_run(elem["textRun"])
                
        text = text.strip()
        if not text:
            return ""
            
        paragraph_style = paragraph.get("paragraphStyle", {})
        p_style = self.build_paragraph_css(paragraph_style, ignore_indent)
        is_heading, heading_level = self.is_heading_paragraph(paragraph)
        
        if is_heading and not is_list_item:
            return f'HEADER_SPLIT_FLAG<h{heading_level} style="{p_style}">{text}</h{heading_level}>HEADER_SPLIT_FLAG'
            
        if is_list_item:
            return text
            
        return f'<p style="{p_style}">{text}</p>'

    def process_table(self, table: dict, lists: dict) -> str:
        rows = table.get("tableRows", [])
        html = ""
        for row in rows:
            cells = row.get("tableCells", [])
            for cell in cells:
                html += self.process_content(cell.get("content", []), lists)
        return html

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

        for element in content:
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
                
            elif element.get("table"):
                if len(list_stack) > 0:
                    html += close_lists(0)
                html += self.process_table(element["table"], lists)
                
            elif element.get("sectionBreak"):
                if len(list_stack) > 0:
                    html += close_lists(0)
                html += ""
                
        if len(list_stack) > 0:
            html += close_lists(0)

        if "HEADER_SPLIT_FLAG" in html:
            parts = html.split("HEADER_SPLIT_FLAG")
            formatted_html = ""
            current_header = None
            current_content = ""
            
            def flush_section(header, body_text):
                if not header:
                    return body_text
                
                has_content = bool(body_text.strip())
                has_content_class = " has-content" if has_content else ""
                
                if not has_content:
                    return f'<div class="section-accordion"><div class="section-header">{header}</div></div>'
                
                return f'<details open class="section-accordion{has_content_class}"><summary class="section-header">{header}</summary><div class="section-content">{body_text}</div></details>'

            for part in parts:
                if not part:
                    continue

                if part.strip().startswith("<h"):
                    formatted_html += flush_section(current_header, current_content)
                    current_header = part.strip()
                    current_content = ""
                else:
                    current_content += part

            formatted_html += flush_section(current_header, current_content)
            return formatted_html

        return html

    def convert_to_html(self, document: dict) -> str:
        body = document.get("body", {}).get("content", [])
        lists = document.get("lists", {})
        headers = document.get("headers", {})
        footers = document.get("footers", {})
        
        title = self.escape_html(document.get("title", "Documento"))
        
        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
* {{ box-sizing: border-box; }}
body {{ 
    background: white; 
    color: black; 
    max-width: 900px; 
    margin: 0 auto; 
    padding: 16px; 
    font-family: 'Montserrat', sans-serif; 
}}

p {{ margin: 0; padding-bottom: 2px; }}
h1, h2, h3, h4, h5, h6 {{ margin: 0; display: inline-block; vertical-align: middle; }}
ul, ol {{ margin-top: 2px; margin-bottom: 4px; padding-left: 20px; }}
li {{ margin-bottom: 2px; }}

.header {{ margin-bottom: 8px; }}
.footer {{ margin-top: 8px; font-size: 10pt; color: #555555; }}

.section-accordion {{
    margin-bottom: 8px;
    border: none;
}}

.section-header {{
    user-select: none;
    list-style: none;
    outline: none;
    margin-bottom: 2px;
    display: inline-flex;
    align-items: center;
}}

summary.section-header {{
    cursor: pointer;
}}

.section-header::-webkit-details-marker {{
    display: none;
}}

.has-content > .section-header::after {{
    content: "▸";
    font-size: 11pt;
    font-weight: bold;
    margin-left: 10px;
    display: inline-block;
    vertical-align: middle;
    transform: translateY(1px);
    line-height: 1;
    color: #44516B;
}}

details.has-content[open] > .section-header::after {{
    content: "▾";
    transform: translateY(0px);
}}

.section-content {{
    padding: 2px 0;
}}
</style>
</head>
<body>

<header class="header">
    {self.process_header_footer(headers, lists, 'header')}
</header>

<div class="content-body">
{self.process_content(body, lists)}
</div>

</body>
</html>
"""
        return html