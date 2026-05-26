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
            
        if style.get("spaceAbove", {}).get("magnitude"):
            css.append(f"margin-top:{style['spaceAbove']['magnitude']}pt")
            
        if style.get("spaceBelow", {}).get("magnitude"):
            css.append(f"margin-bottom:{style['spaceBelow']['magnitude']}pt")
            
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
            
        if style.get("backgroundColor", {}).get("color", {}).get("rgbColor"):
            css.append("color:white")
        elif style.get("foregroundColor", {}).get("color", {}).get("rgbColor"):
            rgb = style["foregroundColor"]["color"]["rgbColor"]
            if not self.is_white_color(rgb):
                has_real_color = any(k in rgb for k in ["red", "green", "blue"])
                if has_real_color:
                    css.append(f"color:rgb({round(rgb.get('red', 0)*255)},{round(rgb.get('green', 0)*255)},{round(rgb.get('blue', 0)*255)})")
                    
        if style.get("backgroundColor", {}).get("color", {}).get("rgbColor"):
            rgb = style["backgroundColor"]["color"]["rgbColor"]
            css.append(f"background-color:rgb({round(rgb.get('red', 0)*255)},{round(rgb.get('green', 0)*255)},{round(rgb.get('blue', 0)*255)})")
            
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

    def process_paragraph(self, paragraph: dict, is_list_item: bool = False, ignore_indent: bool = False) -> str:
        elements = paragraph.get("elements", [])
        text = ""
        
        for elem in elements:
            if elem.get("textRun", {}).get("content", "").strip():
                text += self.format_text_run(elem["textRun"])
                
        text = text.strip()
        if not text:
            return "" if is_list_item else "<br />"
            
        paragraph_style = paragraph.get("paragraphStyle", {})
        p_style = self.build_paragraph_css(paragraph_style, ignore_indent)
        heading_level = self.get_heading_level(paragraph_style.get("namedStyleType", ""))
        
        if heading_level:
            return f'\n<h{heading_level} style="{p_style}">\n{text}\n</h{heading_level}>\n'
            
        if is_list_item:
            return text
            
        return f'\n<p style="{p_style}">\n{text}\n</p>\n'

    def process_table(self, table: dict, lists: dict) -> str:
        rows = table.get("tableRows", [])
        html = "<table>"
        for row in rows:
            html += "<tr>"
            cells = row.get("tableCells", [])
            for cell in cells:
                html += "<td>"
                html += self.process_content(cell.get("content", []), lists)
                html += "</td>"
            html += "</tr>"
        html += "</table>"
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
    padding: 24px; 
    font-family: 'Montserrat', sans-serif; 
}}

.table-header {{ width: 100%; border-collapse: collapse; margin-bottom: 0px; border: none; }}
.table-header td {{ border: none; padding: 0; vertical-align: middle; }}
.header-text-container {{ padding-left: 15px; text-align: left; }}

p {{ margin: 0; padding-bottom: 6px; }}
h1, h2, h3, h4, h5, h6 {{ margin-top: 0px; margin-bottom: 8px; }}

table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
td {{ border: 1px solid #000; padding: 6px; vertical-align: top; }}
ul, ol {{ margin-top: 6px; margin-bottom: 6px; }}

.header {{ margin-bottom: 0px; }}
.doc-footer {{ display: flex; align-items: center; gap: 12px; margin-top: 5px; padding-top: 0px; border-top: none; }}
.doc-footer-image {{ width: 60px; height: auto; object-fit: contain; flex-shrink: 0; }}
.doc-footer-content {{ flex: 1; font-size: 12px; opacity: 0.8; }}
.footer {{ margin-bottom: 0px; }}

.table-footer {{ width: 100%; border-collapse: collapse; margin-top: 5px; border: none; }}
.table-footer td {{ border: none; padding: 0; vertical-align: middle; }}
</style>
</head>
<body>

<table class="table-header">
    <tr>
        <td style="width: 80px;">
            <img src="../../static/be.png" width="75" height="75" style="display: block;" alt="BE logo" />
        </td>
        <td class="header-text-container">
            {self.process_header_footer(headers, lists, 'header')}
        </td>
        <td style="width: 180px; text-align: right;">
            <img src="../../static/be_details.png" width="170" style="display: block;" alt="BE details" />
        </td>
    </tr>
</table>

<div class="content-body">
"""
        html += self.process_content(body, lists)
        
        html += f"""
</div>

<table class="table-footer">
    <tr>
        <td style="width: 65px;">
            <img src="../../static/be_footer.png" width="60" style="display: block;" alt="BE footer" />
        </td>
        <td style="padding-left: 15px; text-align: left; font-size: 10pt; color: #555555;">
            {self.process_header_footer(footers, lists, 'footer')}
        </td>
        <td style="width: 65px; text-align: right;">
            <img src="../../static/be_qrcode.png" width="60" style="display: block;" alt="BE QR Code" />
        </td>
    </tr>
</table>

</body>
</html>
"""
        return html