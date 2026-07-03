from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]

CLEAN_DATA_PATH = BASE_DIR / "data" / "processed" / "seafood_trade_clean.csv"
SCORED_DATA_PATH = BASE_DIR / "data" / "processed" / "seafood_trade_scored.csv"


def main():
    clean_df = pd.read_csv(CLEAN_DATA_PATH)
    scored_df = pd.read_csv(SCORED_DATA_PATH)

    print("\n==============================")
    print("CLEAN DATA CHECK")
    print("==============================")

    print(f"Rows: {len(clean_df):,}")
    print(f"Years: {clean_df['year'].min()} - {clean_df['year'].max()}")
    print(f"Importers: {clean_df['importer_country'].nunique()}")
    print(f"Suppliers: {clean_df['supplier_country'].nunique()}")
    print(f"Products: {clean_df['product_group'].nunique()}")

    print("\nMissing values:")
    print(clean_df.isna().sum())

    print("\nProducts:")
    print(clean_df["product_group"].value_counts())

    print("\nTop importers by trade value:")
    print(
        clean_df.groupby("importer_country")["trade_value_usd"]
        .sum()
        .sort_values(ascending=False)
        .head(15)
    )

    print("\nAverage price/kg by product:")
    print(
        clean_df.groupby("product_group")["avg_price_per_kg"]
        .mean()
        .sort_values(ascending=False)
    )

    print("\nPotential price outliers:")
    outliers = clean_df[
        (clean_df["avg_price_per_kg"] > clean_df["avg_price_per_kg"].quantile(0.99))
        | (clean_df["avg_price_per_kg"] < clean_df["avg_price_per_kg"].quantile(0.01))
    ]

    print(
        outliers[
            [
                "year",
                "importer_country",
                "supplier_country",
                "product_group",
                "trade_value_usd",
                "quantity_kg",
                "avg_price_per_kg",
            ]
        ].head(20)
    )

    print("\n==============================")
    print("SCORED DATA CHECK")
    print("==============================")

    print(f"Rows: {len(scored_df):,}")
    print(f"Opportunity score min: {scored_df['opportunity_score'].min()}")
    print(f"Opportunity score max: {scored_df['opportunity_score'].max()}")
    print(f"Opportunity score avg: {scored_df['opportunity_score'].mean():.1f}")

    print("\nTop 15 opportunities:")
    print(
        scored_df.sort_values("opportunity_score", ascending=False)
        [
            [
                "year",
                "importer_country",
                "product_group",
                "trade_value_usd",
                "quantity_kg",
                "avg_price_per_kg",
                "value_growth_pct",
                "opportunity_score",
                "opportunity_level",
            ]
        ]
        .head(15)
    )


if __name__ == "__main__":
    main()