from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]

PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
POWERBI_DIR = BASE_DIR / "powerbi"

SCORED_DATA_PATH = PROCESSED_DATA_DIR / "seafood_trade_scored.csv"
CLEAN_DATA_PATH = PROCESSED_DATA_DIR / "seafood_trade_clean.csv"

POWERBI_EXPORT_PATH = POWERBI_DIR / "seafood_trade_powerbi_dataset.xlsx"


def main():
    POWERBI_DIR.mkdir(parents=True, exist_ok=True)

    scored_df = pd.read_csv(SCORED_DATA_PATH)
    clean_df = pd.read_csv(CLEAN_DATA_PATH)

    dim_country = pd.DataFrame(
        sorted(
            set(clean_df["importer_country"].dropna())
            | set(clean_df["supplier_country"].dropna())
        ),
        columns=["country_name"],
    )

    dim_product = (
        clean_df[["product_code", "product_group", "product_description"]]
        .drop_duplicates()
        .sort_values("product_group")
    )

    dim_time = (
        clean_df[["year"]]
        .drop_duplicates()
        .sort_values("year")
    )

    with pd.ExcelWriter(POWERBI_EXPORT_PATH, engine="openpyxl") as writer:
        clean_df.to_excel(writer, sheet_name="fact_trade_raw", index=False)
        scored_df.to_excel(writer, sheet_name="fact_market_scored", index=False)
        dim_country.to_excel(writer, sheet_name="dim_country", index=False)
        dim_product.to_excel(writer, sheet_name="dim_product", index=False)
        dim_time.to_excel(writer, sheet_name="dim_time", index=False)

    print(f"Power BI dataset exported to: {POWERBI_EXPORT_PATH}")


if __name__ == "__main__":
    main()