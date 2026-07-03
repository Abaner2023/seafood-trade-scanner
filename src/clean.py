from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]

RAW_DATA_PATH = BASE_DIR / "data" / "raw" / "comtrade_imports_combined.csv"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
OUTPUT_PATH = PROCESSED_DATA_DIR / "seafood_trade_clean.csv"

PRODUCT_GROUPS = {
    "030313": "Frozen Atlantic salmon",
    "030342": "Frozen yellowfin tuna",
    "030354": "Frozen mackerel",
    "030366": "Frozen hake",
    "030617": "Frozen shrimp/prawns",
}


def choose_column(df: pd.DataFrame, candidates: list[str]) -> str:
    """
    Finds the first matching column name from a list of candidates.
    This makes the cleaner robust if Comtrade column names differ slightly.
    """
    for col in candidates:
        if col in df.columns:
            return col

    raise KeyError(f"None of these columns were found: {candidates}")


def clean_comtrade_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    year_col = choose_column(df, ["refYear", "period", "year"])
    importer_col = choose_column(df, ["reporterDesc", "reporter", "reporterName"])
    supplier_col = choose_column(df, ["partnerDesc", "partner", "partnerName"])
    product_code_col = choose_column(df, ["cmdCode", "commodityCode"])
    product_desc_col = choose_column(df, ["cmdDesc", "commodityDesc"])
    trade_value_col = choose_column(df, ["primaryValue", "cifvalue", "tradeValue"])
    flow_col = choose_column(df, ["flowDesc", "flowCode"])

    # Net weight is preferred. If missing, fall back to quantity.
    quantity_col = choose_column(df, ["netWgt", "qty", "quantity"])

    clean_df = pd.DataFrame(
        {
            "year": df[year_col],
            "importer_country": df[importer_col],
            "supplier_country": df[supplier_col],
            "product_code": df[product_code_col].astype(str).str.zfill(6),
            "product_description": df[product_desc_col],
            "trade_flow": df[flow_col],
            "trade_value_usd": df[trade_value_col],
            "quantity_kg": df[quantity_col],
        }
    )

    clean_df["trade_value_usd"] = pd.to_numeric(
        clean_df["trade_value_usd"], errors="coerce"
    )

    clean_df["quantity_kg"] = pd.to_numeric(
        clean_df["quantity_kg"], errors="coerce"
    )

    clean_df = clean_df.dropna(subset=["trade_value_usd", "quantity_kg"])

    clean_df = clean_df[clean_df["quantity_kg"] > 0]
    clean_df = clean_df[clean_df["trade_value_usd"] > 0]

    clean_df["avg_price_per_kg"] = (
        clean_df["trade_value_usd"] / clean_df["quantity_kg"]
    )

    clean_df["product_group"] = clean_df["product_code"].map(PRODUCT_GROUPS)

    clean_df = clean_df.dropna(subset=["product_group"])

    # Remove world/aggregate suppliers if they appear
    clean_df = clean_df[
        ~clean_df["supplier_country"].isin(
            ["World", "Areas, nes", "Other Asia, nes"]
        )
    ]

    clean_df = clean_df.sort_values(
        ["year", "importer_country", "product_group", "supplier_country"]
    )

    return clean_df


def main():
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    raw_df = pd.read_csv(RAW_DATA_PATH)
    clean_df = clean_comtrade_data(raw_df)

    clean_df.to_csv(OUTPUT_PATH, index=False)

    print("Cleaned data saved.")
    print(f"Path: {OUTPUT_PATH}")
    print(f"Rows: {len(clean_df):,}")
    print(clean_df.head())


if __name__ == "__main__":
    main()