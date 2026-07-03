from pathlib import Path
import pandas as pd
import numpy as np


BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_DATA_PATH = BASE_DIR / "data" / "processed" / "seafood_trade_clean.csv"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
OUTPUT_PATH = PROCESSED_DATA_DIR / "seafood_trade_scored.csv"


PRICE_BOUNDS = {
    "Frozen shrimp/prawns": (1.0, 50.0),
    "Frozen Atlantic salmon": (1.0, 50.0),
    "Frozen yellowfin tuna": (0.8, 40.0),
    "Frozen hake": (0.8, 30.0),
    "Frozen mackerel": (0.4, 12.0),
}


def rank_score(series: pd.Series) -> pd.Series:
    """
    Converts values to percentile rank scores from 0–100.
    This is more robust than min-max scaling when data contains extreme outliers.
    """
    return series.rank(pct=True) * 100


def filter_price_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Removes commercially unrealistic product-level price observations.
    The clean dataset stays untouched; this only affects the scored market table.
    """
    df = df.copy()

    keep_mask = pd.Series(True, index=df.index)

    for product, (lower, upper) in PRICE_BOUNDS.items():
        product_mask = df["product_group"] == product
        valid_price_mask = df["avg_price_per_kg"].between(lower, upper)

        keep_mask = keep_mask & (~product_mask | valid_price_mask)

    # Remove very tiny trade records that can distort growth and price signals
    keep_mask = keep_mask & (df["trade_value_usd"] >= 1000)
    keep_mask = keep_mask & (df["quantity_kg"] >= 100)

    removed = len(df) - keep_mask.sum()
    print(f"Removed {removed:,} outlier/tiny records before scoring.")

    return df[keep_mask].copy()


def create_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["trade_value_usd"] = pd.to_numeric(df["trade_value_usd"], errors="coerce")
    df["quantity_kg"] = pd.to_numeric(df["quantity_kg"], errors="coerce")
    df["avg_price_per_kg"] = df["trade_value_usd"] / df["quantity_kg"]

    df = df.dropna(subset=["trade_value_usd", "quantity_kg", "avg_price_per_kg"])
    df = df[(df["trade_value_usd"] > 0) & (df["quantity_kg"] > 0)]

    df = filter_price_outliers(df)

    # Aggregate by market: year + importer + product
    market_df = (
        df.groupby(["year", "importer_country", "product_group"], as_index=False)
        .agg(
            trade_value_usd=("trade_value_usd", "sum"),
            quantity_kg=("quantity_kg", "sum"),
            supplier_count=("supplier_country", "nunique"),
        )
    )

    # Weighted average price, not simple average of supplier prices
    market_df["avg_price_per_kg"] = (
        market_df["trade_value_usd"] / market_df["quantity_kg"]
    )

    market_df = market_df.sort_values(
        ["importer_country", "product_group", "year"]
    )

    # Previous year values
    market_df["prev_trade_value_usd"] = market_df.groupby(
        ["importer_country", "product_group"]
    )["trade_value_usd"].shift(1)

    market_df["prev_quantity_kg"] = market_df.groupby(
        ["importer_country", "product_group"]
    )["quantity_kg"].shift(1)

    market_df["prev_price_per_kg"] = market_df.groupby(
        ["importer_country", "product_group"]
    )["avg_price_per_kg"].shift(1)

    # Growth calculations
    market_df["value_growth_pct"] = (
        (market_df["trade_value_usd"] - market_df["prev_trade_value_usd"])
        / market_df["prev_trade_value_usd"]
    ) * 100

    market_df["quantity_growth_pct"] = (
        (market_df["quantity_kg"] - market_df["prev_quantity_kg"])
        / market_df["prev_quantity_kg"]
    ) * 100

    market_df["price_growth_pct"] = (
        (market_df["avg_price_per_kg"] - market_df["prev_price_per_kg"])
        / market_df["prev_price_per_kg"]
    ) * 100

    growth_cols = ["value_growth_pct", "quantity_growth_pct", "price_growth_pct"]
    market_df[growth_cols] = market_df[growth_cols].replace([np.inf, -np.inf], np.nan)
    market_df[growth_cols] = market_df[growth_cols].fillna(0)

    # Cap extreme growth values so tiny base effects do not dominate
    for col in growth_cols:
        lower = market_df[col].quantile(0.05)
        upper = market_df[col].quantile(0.95)
        market_df[col] = market_df[col].clip(lower, upper)

    # Supplier concentration
    supplier_totals = (
        df.groupby(
            ["year", "importer_country", "product_group", "supplier_country"],
            as_index=False,
        )
        .agg(supplier_value_usd=("trade_value_usd", "sum"))
    )

    total_market_value = (
        supplier_totals.groupby(
            ["year", "importer_country", "product_group"],
            as_index=False,
        )
        .agg(total_value_usd=("supplier_value_usd", "sum"))
    )

    supplier_share = supplier_totals.merge(
        total_market_value,
        on=["year", "importer_country", "product_group"],
        how="left",
    )

    supplier_share["supplier_share"] = (
        supplier_share["supplier_value_usd"] / supplier_share["total_value_usd"]
    )

    max_supplier_share = (
        supplier_share.groupby(
            ["year", "importer_country", "product_group"],
            as_index=False,
        )
        .agg(max_supplier_share=("supplier_share", "max"))
    )

    market_df = market_df.merge(
        max_supplier_share,
        on=["year", "importer_country", "product_group"],
        how="left",
    )

    # Lower max supplier share means better diversification
    market_df["supplier_diversification_score"] = (
        100 * (1 - market_df["max_supplier_share"])
    )

    # Robust component scores
    market_df["volume_score"] = rank_score(np.log1p(market_df["quantity_kg"]))
    market_df["value_score"] = rank_score(np.log1p(market_df["trade_value_usd"]))
    market_df["value_growth_score"] = rank_score(market_df["value_growth_pct"])
    market_df["quantity_growth_score"] = rank_score(market_df["quantity_growth_pct"])
    market_df["price_growth_score"] = rank_score(market_df["price_growth_pct"])
    market_df["supplier_score"] = rank_score(
        market_df["supplier_diversification_score"]
    )

    # Opportunity Score
    market_df["opportunity_score"] = (
        0.25 * market_df["value_growth_score"]
        + 0.20 * market_df["quantity_growth_score"]
        + 0.20 * market_df["volume_score"]
        + 0.20 * market_df["value_score"]
        + 0.10 * market_df["price_growth_score"]
        + 0.05 * market_df["supplier_score"]
    )

    market_df["opportunity_score"] = market_df["opportunity_score"].round(1)

    market_df["opportunity_level"] = np.select(
        [
            market_df["opportunity_score"] >= 75,
            market_df["opportunity_score"] >= 55,
            market_df["opportunity_score"] >= 35,
        ],
        [
            "High",
            "Medium-high",
            "Medium",
        ],
        default="Low",
    )

    return market_df


def main():
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INPUT_DATA_PATH)
    scored_df = create_features(df)

    scored_df.to_csv(OUTPUT_PATH, index=False)

    print(f"Scored data saved to: {OUTPUT_PATH}")

    print("\nData check:")
    print(f"Rows: {len(scored_df):,}")
    print(f"Years: {scored_df['year'].min()} - {scored_df['year'].max()}")
    print(f"Importers: {scored_df['importer_country'].nunique()}")
    print(f"Products: {scored_df['product_group'].nunique()}")
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
                "quantity_growth_pct",
                "opportunity_score",
                "opportunity_level",
            ]
        ]
        .head(15)
    )


if __name__ == "__main__":
    main()