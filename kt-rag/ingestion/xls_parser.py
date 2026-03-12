import xlrd
from pathlib import Path

_ROW_BATCH_SIZE = 25


def parse_xls(file_path: str) -> list[dict]:
    """
    Extract text from all sheets of a legacy .xls file using xlrd.
    Rows are emitted in batches so the chunker never splits a row mid-way.
    Returns list of {text, metadata} dicts.
    """
    wb = xlrd.open_workbook(file_path)
    sections = []

    for sheet_name in wb.sheet_names():
        ws = wb.sheet_by_name(sheet_name)

        if ws.nrows < 2:
            continue

        # First row treated as header
        headers = [
            str(ws.cell_value(0, col)).strip() or f"Col{col}"
            for col in range(ws.ncols)
        ]

        formatted_rows = []
        for row_idx in range(1, ws.nrows):
            row = [ws.cell_value(row_idx, col) for col in range(ws.ncols)]
            if all(cell == '' or cell is None for cell in row):
                continue
            pairs = []
            for header, cell in zip(headers, row):
                val = str(cell).strip() if (cell != '' and cell is not None) else ''
                if val:
                    pairs.append(f"{header}: {val}")
            if pairs:
                formatted_rows.append(" | ".join(pairs))

        if not formatted_rows:
            continue

        # Emit in row batches so the chunker never splits a row mid-way
        for batch_start in range(0, len(formatted_rows), _ROW_BATCH_SIZE):
            batch = formatted_rows[batch_start:batch_start + _ROW_BATCH_SIZE]
            row_start = batch_start + 2  # +2: row 1 is header, data is 1-indexed
            row_end = row_start + len(batch) - 1
            text = f"[Sheet: {sheet_name}, Rows {row_start}-{row_end}]\n" + "\n".join(batch)
            sections.append({
                "text": text,
                "metadata": {
                    "source": Path(file_path).name,
                    "file_path": str(file_path),
                    "file_type": "xls",
                    "sheet": sheet_name,
                    "rows_start": row_start,
                    "rows_end": row_end,
                    "page": 1
                }
            })

    return sections
