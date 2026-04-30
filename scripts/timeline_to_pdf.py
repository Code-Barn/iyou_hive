# /// script
# dependencies = ["markdown", "weasyprint"]
# ///

import sys
import markdown
from weasyprint import HTML, CSS


# --- SET YOUR FILING DETAILS HERE ---
CASE_NAME = "BYERS v. DONATELLO"
CASE_NUMBER = "Case No: 25FA152"
PREPARED_BY = "Prepared by: David Byers"
# ------------------------------------

def convert_md_to_pdf(input_file, output_file):
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            md_text = f.read()

        html_content = markdown.markdown(md_text, extensions=['tables'])

        custom_css = CSS(string=f"""
            @page {{ 
                size: letter landscape; 
                margin: 0.8in 0.5in 0.75in 0.5in; /* Increased top margin for header */
                
                @top-left {{
                    content: "{CASE_NAME}\\A {CASE_NUMBER}";
                    font-family: serif;
                    font-size: 10pt;
                    white-space: pre; /* Allows the \\A to create a new line */
                    font-weight: bold;
                }}

                @top-right {{
                    content: "{PREPARED_BY}";
                    font-family: serif;
                    font-size: 10pt;
                }}

                @bottom-right {{
                    content: "Page " counter(page) " of " counter(pages);
                    font-family: serif;
                    font-size: 9pt;
                }}
            }}
            
            body {{ font-family: serif; font-size: 9pt; margin-top: 10px; }}

            h1, h2, h3 {{ break-after: avoid; page-break-after: avoid; border-bottom: 1px solid #ccc; }}
            
            table {{ 
                width: 100%; 
                border-collapse: collapse; 
                table-layout: fixed; 
            }}
            
            tr {{ break-inside: avoid; page-break-inside: avoid; }}
            
            th, td {{ border: 1pt solid black; padding: 6px; vertical-align: top; word-break: break-all; }}
            th {{ background-color: #f0f0f0; font-weight: bold; }}
            
            /* Column Widths */
            th:nth-child(1), td:nth-child(1) {{ width: 10%; }}
            th:nth-child(2), td:nth-child(2) {{ width: 25%; }}
            th:nth-child(3), td:nth-child(3) {{ width: 10%; }}
            th:nth-child(4), td:nth-child(4) {{ width: 25%; font-family: monospace; font-size: 8pt; }}
            th:nth-child(5), td:nth-child(5) {{ width: 25%; }}
        """)

        HTML(string=html_content).write_pdf(output_file, stylesheets=[custom_css])
        print(f"✅ Success! Created {output_file}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: uv run convert2.py <input.md> <output.pdf>")
    else:
        convert_md_to_pdf(sys.argv[1], sys.argv[2])
