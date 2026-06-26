from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import Engine, text

from data_access import retrieve_data
from db import get_engine


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"

SQL_MOST_EXPENSIVE = """
SELECT
    PRODUCT_COD,
    PRODUCT_NAME,
    PRODUCT_VAL,
    DEP_NAME,
    DEP_COD,
    SECTION_NAME,
    SECTION_COD
FROM data_product
ORDER BY PRODUCT_VAL DESC
LIMIT 10;
""".strip()

SQL_DEPARTMENT_SECTIONS = """
SELECT DISTINCT
    DEP_NAME,
    SECTION_COD,
    SECTION_NAME
FROM data_product
WHERE DEP_NAME IN ('BEBIDAS', 'PADARIA')
ORDER BY DEP_NAME, SECTION_NAME;
""".strip()

SQL_Q1_BUSINESS_AREA_SALES = """
SELECT
    sc.BUSINESS_NAME,
    ROUND(SUM(ps.SALES_VALUE), 2) AS TOTAL_SALES_VALUE
FROM data_product_sales AS ps
INNER JOIN data_store_cad AS sc
    ON CAST(ps.STORE_CODE AS UNSIGNED) = sc.STORE_CODE
WHERE ps.DATE BETWEEN '2019-01-01' AND '2019-03-31'
GROUP BY sc.BUSINESS_NAME
ORDER BY TOTAL_SALES_VALUE DESC;
""".strip()

CLIENT_QUERY_STORE_CAD = """
SELECT
      STORE_CODE,
      STORE_NAME,
      START_DATE,
      END_DATE,
      BUSINESS_NAME,
      BUSINESS_CODE
FROM data_store_cad
""".strip()

CLIENT_QUERY_STORE_SALES = """
SELECT
        STORE_CODE,
        DATE,
        SALES_VALUE,
        SALES_QTY
FROM data_store_sales
WHERE DATE BETWEEN '2019-01-01' AND '2019-12-31'
""".strip()


def run_sql_tests(engine: Engine) -> dict[str, pd.DataFrame]:
    return {
        "sql_1_most_expensive_products": pd.read_sql_query(text(SQL_MOST_EXPENSIVE), engine),
        "sql_2_department_sections": pd.read_sql_query(text(SQL_DEPARTMENT_SECTIONS), engine),
        "sql_3_q1_sales_by_business_area": pd.read_sql_query(text(SQL_Q1_BUSINESS_AREA_SALES), engine),
    }


def build_case_2_visualization_table(engine: Engine) -> pd.DataFrame:
    stores = pd.read_sql_query(text(CLIENT_QUERY_STORE_CAD), engine)
    sales = pd.read_sql_query(text(CLIENT_QUERY_STORE_SALES), engine)

    sales["DATE"] = pd.to_datetime(sales["DATE"])
    period_sales = sales[sales["DATE"].between("2019-10-01", "2019-12-31")].copy()

    merged = period_sales.merge(stores, on="STORE_CODE", how="left", validate="many_to_one")
    result = (
        merged.groupby(["STORE_NAME", "BUSINESS_NAME"], as_index=False)
        .agg(SALES_VALUE=("SALES_VALUE", "sum"), SALES_QTY=("SALES_QTY", "sum"))
        .assign(TM=lambda df: (df["SALES_VALUE"] / df["SALES_QTY"]).round(2))
        .rename(columns={"STORE_NAME": "Loja", "BUSINESS_NAME": "Categoria"})
        [["Loja", "Categoria", "TM"]]
        .sort_values("Loja")
        .reset_index(drop=True)
    )
    return result


def build_imdb_chart(engine: Engine) -> tuple[pd.DataFrame, Path]:
    movies = pd.read_sql_query(
        text(
            """
            SELECT Title, Genre, Rating, Votes, RevenueMillions
            FROM IMDB_movies
            WHERE RevenueMillions IS NOT NULL
            """
        ),
        engine,
    )

    exploded = movies.assign(Genre=movies["Genre"].str.split(",")).explode("Genre")
    exploded["Genre"] = exploded["Genre"].str.strip()

    genre_summary = (
        exploded.groupby("Genre", as_index=False)
        .agg(
            movies=("Title", "count"),
            avg_revenue_millions=("RevenueMillions", "mean"),
            avg_rating=("Rating", "mean"),
            total_votes=("Votes", "sum"),
        )
        .query("movies >= 15")
        .assign(
            avg_revenue_millions=lambda df: df["avg_revenue_millions"].round(2),
            avg_rating=lambda df: df["avg_rating"].round(2),
        )
        .sort_values("avg_revenue_millions", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )

    chart_data = genre_summary.sort_values("avg_revenue_millions", ascending=True)
    chart_path = OUTPUT / "imdb_top_genres_by_avg_revenue.png"

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(chart_data["Genre"], chart_data["avg_revenue_millions"], color="#2F6B7C")
    ax.set_title("Filmes IMDB: gêneros com maior receita média")
    ax.set_xlabel("Receita média (US$ milhões)")
    ax.set_ylabel("")
    ax.grid(axis="x", alpha=0.25)
    for index, value in enumerate(chart_data["avg_revenue_millions"]):
        ax.text(float(value) + 2, index, f"{value:.2f}", va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(chart_path, dpi=180)
    plt.close(fig)

    return genre_summary, chart_path


def save_outputs(frames: dict[str, pd.DataFrame], case_2: pd.DataFrame, imdb_summary: pd.DataFrame) -> None:
    OUTPUT.mkdir(exist_ok=True)
    for name, df in frames.items():
        df.to_csv(OUTPUT / f"{name}.csv", index=False)
    case_2.to_csv(OUTPUT / "case_2_store_ticket.csv", index=False)
    imdb_summary.to_csv(OUTPUT / "imdb_genre_summary.csv", index=False)


def _format_value(value: object) -> str:
    if isinstance(value, Decimal):
        return f"{float(value):,.2f}"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return "" if pd.isna(value) else str(value)


def _table_from_df(df: pd.DataFrame, widths: list[float] | None = None, max_rows: int | None = None) -> Table:
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=7,
        leading=8,
    )
    data_frame = df.head(max_rows) if max_rows else df
    data = [[Paragraph(str(col), cell_style) for col in data_frame.columns]]
    for _, row in data_frame.iterrows():
        data.append([Paragraph(_format_value(value), cell_style) for value in row])

    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAF0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17313A")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#A8B7BD")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _add_code(story: list, code: str, title: str) -> None:
    styles = getSampleStyleSheet()
    story.append(Paragraph(title, styles["Heading3"]))
    story.append(Preformatted(code, ParagraphStyle("Code", fontName="Courier", fontSize=6, leading=7)))
    story.append(Spacer(1, 0.12 * inch))


def generate_pdf(
    frames: dict[str, pd.DataFrame],
    case_2: pd.DataFrame,
    imdb_summary: pd.DataFrame,
    chart_path: Path,
    retrieve_sample: pd.DataFrame,
) -> Path:
    pdf_path = OUTPUT / "looqbox_data_challenge_carlos.pdf"
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=landscape(A4),
        rightMargin=28,
        leftMargin=28,
        topMargin=26,
        bottomMargin=26,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("CenteredTitle", parent=styles["Title"], alignment=TA_CENTER))

    story: list = []
    story.append(Paragraph("Looqbox Data Challenge", styles["CenteredTitle"]))
    story.append(Paragraph("Candidato: Carlos", styles["Normal"]))
    story.append(Paragraph("Stack: Python, SQL, MySQL, pandas e matplotlib.", styles["Normal"]))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Teste SQL", styles["Heading2"]))
    _add_code(story, SQL_MOST_EXPENSIVE, "1) Dez produtos mais caros")
    story.append(
        _table_from_df(
            frames["sql_1_most_expensive_products"],
            widths=[48, 250, 54, 72, 42, 100, 46],
        )
    )
    story.append(PageBreak())

    _add_code(story, SQL_DEPARTMENT_SECTIONS, "2) Seções dos departamentos BEBIDAS e PADARIA")
    story.append(_table_from_df(frames["sql_2_department_sections"], widths=[90, 70, 160]))
    story.append(Spacer(1, 0.2 * inch))

    _add_code(story, SQL_Q1_BUSINESS_AREA_SALES, "3) Vendas de produtos por área de negócio no 1º trimestre de 2019")
    story.append(_table_from_df(frames["sql_3_q1_sales_by_business_area"], widths=[130, 130]))
    story.append(PageBreak())

    story.append(Paragraph("Caso 1 - Recuperação dinâmica de dados", styles["Heading2"]))
    _add_code(
        story,
        """my_data = retrieve_data(
    product_code=18,
    store_code=1,
    date=["2019-01-01", "2019-01-31"],
    engine=engine,
)""",
        "Exemplo de chamada",
    )
    story.append(Paragraph("Resultado de exemplo para product_code=18, store_code=1 e janeiro de 2019:", styles["Normal"]))
    story.append(_table_from_df(retrieve_sample.head(10), widths=[70, 80, 80, 90, 80]))
    story.append(Spacer(1, 0.2 * inch))
    story.append(
        Paragraph(
            "A função mantém todos os filtros opcionais, valida as entradas e usa parâmetros vinculados para evitar SQL injection.",
            styles["Normal"],
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("Caso 2 - Consultas do cliente e tabela solicitada", styles["Heading2"]))
    _add_code(story, CLIENT_QUERY_STORE_CAD, "Consulta 1 do cliente, usada como fornecida")
    _add_code(story, CLIENT_QUERY_STORE_SALES, "Consulta 2 do cliente, usada como fornecida")
    story.append(
        Paragraph(
            "O intervalo de datas solicitado foi aplicado no pandas depois da carga da consulta 2, mantendo as duas consultas do cliente inalteradas. "
            "O TM foi calculado como o total de SALES_VALUE dividido pelo total de SALES_QTY para cada loja.",
            styles["Normal"],
        )
    )
    story.append(_table_from_df(case_2, widths=[150, 110, 60]))
    story.append(PageBreak())

    story.append(Paragraph("Caso 3 - Visualizacao com IMDB", styles["Heading2"]))
    story.append(
        Paragraph(
            "Escolhi um grafico de barras horizontais porque o objetivo e comparar categorias com clareza. "
            "A coluna Genre possui múltiplos valores por filme, então cada filme foi expandido para suas tags de gênero. "
            "Considerei apenas gêneros com pelo menos 15 filmes e receita não nula para reduzir ruído de grupos muito pequenos.",
            styles["Normal"],
        )
    )
    story.append(Image(str(chart_path), width=7.2 * inch, height=4.0 * inch))
    story.append(Spacer(1, 0.15 * inch))
    story.append(_table_from_df(imdb_summary, widths=[90, 60, 120, 80, 90]))

    doc.build(story)
    return pdf_path


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    engine = get_engine()
    try:
        sql_frames = run_sql_tests(engine)
        retrieve_sample = retrieve_data(product_code=18, store_code=1, date=["2019-01-01", "2019-01-31"], engine=engine)
        case_2 = build_case_2_visualization_table(engine)
        imdb_summary, chart_path = build_imdb_chart(engine)
        save_outputs(sql_frames, case_2, imdb_summary)
        pdf_path = generate_pdf(sql_frames, case_2, imdb_summary, chart_path, retrieve_sample)
    finally:
        engine.dispose()

    print(f"Generated outputs in: {OUTPUT}")
    print(f"PDF: {pdf_path}")


if __name__ == "__main__":
    main()
