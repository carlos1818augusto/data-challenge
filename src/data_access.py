from __future__ import annotations

from datetime import date as Date
from typing import Sequence

import pandas as pd
from sqlalchemy import Engine, text

from db import get_engine


def _parse_iso_date(value: str) -> Date:
    try:
        return Date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid date '{value}'. Expected ISO format YYYY-MM-DD.") from exc


def retrieve_data(
    product_code: int | None = None,
    store_code: int | str | None = None,
    date: Sequence[str] | None = None,
    engine: Engine | None = None,
) -> pd.DataFrame:
    """Retrieve rows from data_product_sales using optional, parameterized filters.

    Parameters are optional to keep the function flexible for other teams. When
    `date` is provided, it must be a two-item interval: [start_date, end_date].
    """
    filters: list[str] = []
    params: dict[str, object] = {}

    if product_code is not None:
        if not isinstance(product_code, int):
            raise TypeError("product_code must be an integer.")
        filters.append("PRODUCT_CODE = :product_code")
        params["product_code"] = product_code

    if store_code is not None:
        filters.append("STORE_CODE = :store_code")
        params["store_code"] = str(store_code)

    if date is not None:
        if len(date) != 2:
            raise ValueError("date must contain exactly two values: [start_date, end_date].")
        start_date = _parse_iso_date(date[0])
        end_date = _parse_iso_date(date[1])
        if start_date > end_date:
            raise ValueError("start_date cannot be greater than end_date.")
        filters.append("DATE BETWEEN :start_date AND :end_date")
        params["start_date"] = start_date
        params["end_date"] = end_date

    query = "SELECT * FROM data_product_sales"
    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY DATE, STORE_CODE, PRODUCT_CODE"

    owns_engine = engine is None
    engine = engine or get_engine()
    try:
        return pd.read_sql_query(text(query), engine, params=params)
    finally:
        if owns_engine:
            engine.dispose()
