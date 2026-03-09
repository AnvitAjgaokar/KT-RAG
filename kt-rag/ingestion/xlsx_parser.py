import openpyxl
from pathlib import Path


def parse_xlsx(file_path: str) -> list[dict]:
    """
    Extract text from all sheets of an Excel file.
    Each sheet becomes one document section.
    Returns list of {text, metadata} dicts.
    """
    wb = openpyxl.load_workbook(file_path, data_only=True)
    sections = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = []
        for row in ws.iter_rows(values_only=True):
            row_text = " | ".join(str(cell) for cell in row if cell is not None)
            if row_text.strip():
                rows.append(row_text)

        if rows:
            sections.append({
                "text": "\n".join(rows),
                "metadata": {
                    "source": Path(file_path).name,
                    "file_path": str(file_path),
                    "file_type": "xlsx",
                    "sheet": sheet_name,
                    "page": 1
                }
            })

    wb.close()
    return sections
