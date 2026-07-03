from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[1]

SCORED_DATA_PATH = BASE_DIR / "data" / "processed" / "seafood_trade_scored.csv"
CLEAN_DATA_PATH = BASE_DIR / "data" / "processed" / "seafood_trade_clean.csv"


st.set_page_config(
    page_title="Seafood Trade Opportunity Scanner",
    page_icon="🐟",
    layout="wide",
)


@st.cache_data
def load_data():
    scored_df = pd.read_csv(SCORED_DATA_PATH)
    clean_df = pd.read_csv(CLEAN_DATA_PATH)

    scored_df["year"] = scored_df["year"].astype(int)
    clean_df["year"] = clean_df["year"].astype(int)

    return scored_df, clean_df


def format_opportunity_table(df):
    display_df = df.rename(
        columns={
            "year": "Year",
            "importer_country": "Importer",
            "product_group": "Product",
            "trade_value_usd": "Trade Value USD",
            "quantity_kg": "Quantity KG",
            "avg_price_per_kg": "Avg Price / KG",
            "value_growth_pct": "Value Growth %",
            "quantity_growth_pct": "Quantity Growth %",
            "price_growth_pct": "Price Growth %",
            "opportunity_score": "Opportunity Score",
            "opportunity_level": "Opportunity Level",
        }
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Trade Value USD": st.column_config.NumberColumn(
                "Trade Value USD",
                format="$%d",
            ),
            "Quantity KG": st.column_config.NumberColumn(
                "Quantity KG",
                format="%d kg",
            ),
            "Avg Price / KG": st.column_config.NumberColumn(
                "Avg Price / KG",
                format="$%.2f",
            ),
            "Value Growth %": st.column_config.NumberColumn(
                "Value Growth %",
                format="%.1f%%",
            ),
            "Quantity Growth %": st.column_config.NumberColumn(
                "Quantity Growth %",
                format="%.1f%%",
            ),
            "Price Growth %": st.column_config.NumberColumn(
                "Price Growth %",
                format="%.1f%%",
            ),
            "Opportunity Score": st.column_config.ProgressColumn(
                "Opportunity Score",
                min_value=0,
                max_value=100,
                format="%.1f",
            ),
        },
    )


scored_df, clean_df = load_data()

st.title("Seafood Trade Opportunity Scanner")

st.write(
    "A market intelligence dashboard for analysing seafood import opportunities "
    "by country, product, trade value, volume, price, growth, and supplier structure."
)

st.info(
    "Opportunity Score combines market growth, import volume, trade value, "
    "price movement, and supplier diversification into a 0–100 score."
)


# -----------------------------
# Sidebar filters
# -----------------------------

st.sidebar.header("Filters")

page = st.sidebar.radio(
    "Dashboard section",
    [
        "Market Overview",
        "Opportunity Ranking",
        "Product Deep Dive",
        "Country Deep Dive",
        "Methodology",
    ],
)

available_years = sorted(scored_df["year"].unique())
latest_year = max(available_years)

selected_years = st.sidebar.multiselect(
    "Year",
    options=available_years,
    default=[latest_year],
)

selected_products = st.sidebar.multiselect(
    "Product group",
    options=sorted(scored_df["product_group"].unique()),
    default=sorted(scored_df["product_group"].unique()),
)

selected_importers = st.sidebar.multiselect(
    "Importer country",
    options=sorted(scored_df["importer_country"].unique()),
    default=sorted(scored_df["importer_country"].unique()),
)


filtered_scored_df = scored_df[
    (scored_df["year"].isin(selected_years))
    & (scored_df["product_group"].isin(selected_products))
    & (scored_df["importer_country"].isin(selected_importers))
]

filtered_clean_df = clean_df[
    (clean_df["year"].isin(selected_years))
    & (clean_df["product_group"].isin(selected_products))
    & (clean_df["importer_country"].isin(selected_importers))
]


# -----------------------------
# Market Overview
# -----------------------------

if page == "Market Overview":
    st.header("Market Overview")

    if filtered_scored_df.empty:
        st.warning("No data available for the selected filters.")
        st.stop()

    total_value = filtered_scored_df["trade_value_usd"].sum()
    total_quantity = filtered_scored_df["quantity_kg"].sum()
    avg_price = total_value / total_quantity if total_quantity > 0 else 0
    avg_opportunity_score = filtered_scored_df["opportunity_score"].mean()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Trade Value", f"${total_value:,.0f}")
    col2.metric("Total Quantity", f"{total_quantity:,.0f} kg")
    col3.metric("Average Price/kg", f"${avg_price:.2f}")
    col4.metric("Avg Opportunity Score", f"{avg_opportunity_score:.1f}")

    st.subheader("Executive Insights")

    latest_filtered_df = filtered_scored_df[
        filtered_scored_df["year"] == filtered_scored_df["year"].max()
    ]

    if latest_filtered_df.empty:
        st.warning("No latest-year data available for the selected filters.")
    else:
        top_market = (
            latest_filtered_df.groupby("importer_country")["trade_value_usd"]
            .sum()
            .sort_values(ascending=False)
            .index[0]
        )

        top_product = (
            latest_filtered_df.groupby("product_group")["trade_value_usd"]
            .sum()
            .sort_values(ascending=False)
            .index[0]
        )

        best_opportunity = latest_filtered_df.sort_values(
            "opportunity_score", ascending=False
        ).iloc[0]

        col1, col2, col3 = st.columns(3)

        col1.info(f"**Largest import market:** {top_market}")
        col2.info(f"**Largest product category:** {top_product}")
        col3.info(
            "**Highest opportunity:** "
            f"{best_opportunity['product_group']} in "
            f"{best_opportunity['importer_country']} "
            f"({best_opportunity['opportunity_score']:.1f})"
        )

    st.subheader("Trade Value Over Time")

    value_by_year = (
        filtered_scored_df.groupby("year", as_index=False)["trade_value_usd"]
        .sum()
        .sort_values("year")
    )

    fig_year = px.line(
        value_by_year,
        x="year",
        y="trade_value_usd",
        markers=True,
        title="Total Import Value Over Time",
        labels={
            "year": "Year",
            "trade_value_usd": "Trade Value USD",
        },
    )

    st.plotly_chart(fig_year, use_container_width=True)

    st.subheader("Trade Value by Importer")

    value_by_country = (
        filtered_scored_df.groupby("importer_country", as_index=False)[
            "trade_value_usd"
        ]
        .sum()
        .sort_values("trade_value_usd", ascending=False)
    )

    fig_country = px.bar(
        value_by_country,
        x="importer_country",
        y="trade_value_usd",
        title="Total Trade Value by Importer Country",
        labels={
            "importer_country": "Importer",
            "trade_value_usd": "Trade Value USD",
        },
    )

    st.plotly_chart(fig_country, use_container_width=True)

    st.subheader("Trade Value by Product")

    value_by_product = (
        filtered_scored_df.groupby("product_group", as_index=False)[
            "trade_value_usd"
        ]
        .sum()
        .sort_values("trade_value_usd", ascending=False)
    )

    fig_product = px.bar(
        value_by_product,
        x="product_group",
        y="trade_value_usd",
        title="Total Trade Value by Product Group",
        labels={
            "product_group": "Product",
            "trade_value_usd": "Trade Value USD",
        },
    )

    st.plotly_chart(fig_product, use_container_width=True)


# -----------------------------
# Opportunity Ranking
# -----------------------------

elif page == "Opportunity Ranking":
    st.header("Opportunity Ranking")

    if filtered_scored_df.empty:
        st.warning("No data available for the selected filters.")
        st.stop()

    st.write(
        "This page ranks country-product combinations by their calculated "
        "opportunity score."
    )

    top_opportunities = (
        filtered_scored_df.sort_values("opportunity_score", ascending=False)
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
                "price_growth_pct",
                "opportunity_score",
                "opportunity_level",
            ]
        ]
        .head(50)
    )

    format_opportunity_table(top_opportunities)

    st.subheader("Market Opportunity: Volume vs Value")

    fig_score = px.scatter(
        filtered_scored_df,
        x="quantity_kg",
        y="trade_value_usd",
        size="opportunity_score",
        color="product_group",
        hover_data=[
            "year",
            "importer_country",
            "product_group",
            "value_growth_pct",
            "quantity_growth_pct",
            "opportunity_score",
            "opportunity_level",
        ],
        labels={
            "quantity_kg": "Quantity Imported KG",
            "trade_value_usd": "Trade Value USD",
            "product_group": "Product Group",
            "opportunity_score": "Opportunity Score",
            "value_growth_pct": "Value Growth %",
            "quantity_growth_pct": "Quantity Growth %",
            "importer_country": "Importer",
            "year": "Year",
        },
        title="Market Opportunity: Import Volume vs Trade Value",
    )

    st.plotly_chart(fig_score, use_container_width=True)


# -----------------------------
# Product Deep Dive
# -----------------------------

elif page == "Product Deep Dive":
    st.header("Product Deep Dive")

    product_options = sorted(filtered_scored_df["product_group"].unique())

    if not product_options:
        st.warning("No product data available for the selected filters.")
        st.stop()

    selected_product = st.selectbox(
        "Choose a product to analyse",
        options=product_options,
    )

    product_scored_df = filtered_scored_df[
        filtered_scored_df["product_group"] == selected_product
    ]

    product_clean_df = filtered_clean_df[
        filtered_clean_df["product_group"] == selected_product
    ]

    st.subheader(f"{selected_product}: Key Metrics")

    total_value = product_scored_df["trade_value_usd"].sum()
    total_quantity = product_scored_df["quantity_kg"].sum()
    avg_price = total_value / total_quantity if total_quantity > 0 else 0
    avg_score = product_scored_df["opportunity_score"].mean()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Import Value", f"${total_value:,.0f}")
    col2.metric("Total Quantity", f"{total_quantity:,.0f} kg")
    col3.metric("Average Price/kg", f"${avg_price:.2f}")
    col4.metric("Avg Opportunity Score", f"{avg_score:.1f}")

    st.subheader("Import Value Trend")

    product_trend = (
        product_scored_df.groupby("year", as_index=False)["trade_value_usd"]
        .sum()
        .sort_values("year")
    )

    fig_product_trend = px.line(
        product_trend,
        x="year",
        y="trade_value_usd",
        markers=True,
        title=f"{selected_product}: Total Import Value Over Time",
        labels={
            "year": "Year",
            "trade_value_usd": "Trade Value USD",
        },
    )

    st.plotly_chart(fig_product_trend, use_container_width=True)

    st.subheader("Top Import Markets")

    top_markets = (
        product_scored_df.groupby("importer_country", as_index=False)
        .agg(
            trade_value_usd=("trade_value_usd", "sum"),
            quantity_kg=("quantity_kg", "sum"),
            opportunity_score=("opportunity_score", "mean"),
        )
        .sort_values("trade_value_usd", ascending=False)
        .head(15)
    )

    fig_top_markets = px.bar(
        top_markets,
        x="importer_country",
        y="trade_value_usd",
        title=f"Top Import Markets for {selected_product}",
        labels={
            "importer_country": "Importer",
            "trade_value_usd": "Trade Value USD",
        },
    )

    st.plotly_chart(fig_top_markets, use_container_width=True)

    st.subheader("Average Price Trend by Importer")

    price_trend = (
        product_scored_df.groupby(["year", "importer_country"], as_index=False)
        .agg(
            trade_value_usd=("trade_value_usd", "sum"),
            quantity_kg=("quantity_kg", "sum"),
        )
    )

    price_trend["avg_price_per_kg"] = (
        price_trend["trade_value_usd"] / price_trend["quantity_kg"]
    )

    top_price_importers = top_markets["importer_country"].head(6).tolist()

    price_trend = price_trend[
        price_trend["importer_country"].isin(top_price_importers)
    ]

    fig_price = px.line(
        price_trend,
        x="year",
        y="avg_price_per_kg",
        color="importer_country",
        markers=True,
        title=f"{selected_product}: Average Price/kg Trend",
        labels={
            "year": "Year",
            "avg_price_per_kg": "Average Price / KG",
            "importer_country": "Importer",
        },
    )

    st.plotly_chart(fig_price, use_container_width=True)

    st.subheader("Top Supplier Countries")

    if product_clean_df.empty:
        st.warning("No supplier data available for this product.")
    else:
        top_suppliers = (
            product_clean_df.groupby("supplier_country", as_index=False)
            .agg(
                trade_value_usd=("trade_value_usd", "sum"),
                quantity_kg=("quantity_kg", "sum"),
            )
            .sort_values("trade_value_usd", ascending=False)
            .head(15)
        )

        fig_suppliers = px.bar(
            top_suppliers,
            x="supplier_country",
            y="trade_value_usd",
            title=f"Top Suppliers for {selected_product}",
            labels={
                "supplier_country": "Supplier",
                "trade_value_usd": "Trade Value USD",
            },
        )

        st.plotly_chart(fig_suppliers, use_container_width=True)

    st.subheader("Best Product-Country Opportunities")

    best_product_opportunities = (
        product_scored_df.sort_values("opportunity_score", ascending=False)
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
                "price_growth_pct",
                "opportunity_score",
                "opportunity_level",
            ]
        ]
        .head(20)
    )

    format_opportunity_table(best_product_opportunities)


# -----------------------------
# Country Deep Dive
# -----------------------------

elif page == "Country Deep Dive":
    st.header("Country Deep Dive")

    country_options = sorted(filtered_scored_df["importer_country"].unique())

    if not country_options:
        st.warning("No country data available for the selected filters.")
        st.stop()

    selected_country = st.selectbox(
        "Choose an import market to analyse",
        options=country_options,
    )

    country_scored_df = filtered_scored_df[
        filtered_scored_df["importer_country"] == selected_country
    ]

    country_clean_df = filtered_clean_df[
        filtered_clean_df["importer_country"] == selected_country
    ]

    st.subheader(f"{selected_country}: Key Metrics")

    total_value = country_scored_df["trade_value_usd"].sum()
    total_quantity = country_scored_df["quantity_kg"].sum()
    avg_price = total_value / total_quantity if total_quantity > 0 else 0
    avg_score = country_scored_df["opportunity_score"].mean()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Import Value", f"${total_value:,.0f}")
    col2.metric("Total Quantity", f"{total_quantity:,.0f} kg")
    col3.metric("Average Price/kg", f"${avg_price:.2f}")
    col4.metric("Avg Opportunity Score", f"{avg_score:.1f}")

    st.subheader("Product Mix")

    product_mix = (
        country_scored_df.groupby("product_group", as_index=False)[
            "trade_value_usd"
        ]
        .sum()
        .sort_values("trade_value_usd", ascending=False)
    )

    fig_mix = px.bar(
        product_mix,
        x="product_group",
        y="trade_value_usd",
        title=f"{selected_country}: Import Value by Product",
        labels={
            "product_group": "Product",
            "trade_value_usd": "Trade Value USD",
        },
    )

    st.plotly_chart(fig_mix, use_container_width=True)

    st.subheader("Top Suppliers")

    if country_clean_df.empty:
        st.warning("No supplier data available for this country.")
    else:
        top_country_suppliers = (
            country_clean_df.groupby("supplier_country", as_index=False)
            .agg(
                trade_value_usd=("trade_value_usd", "sum"),
                quantity_kg=("quantity_kg", "sum"),
            )
            .sort_values("trade_value_usd", ascending=False)
            .head(15)
        )

        fig_country_suppliers = px.bar(
            top_country_suppliers,
            x="supplier_country",
            y="trade_value_usd",
            title=f"{selected_country}: Top Supplier Countries",
            labels={
                "supplier_country": "Supplier",
                "trade_value_usd": "Trade Value USD",
            },
        )

        st.plotly_chart(fig_country_suppliers, use_container_width=True)

    st.subheader("Best Opportunities in This Country")

    best_country_opportunities = (
        country_scored_df.sort_values("opportunity_score", ascending=False)
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
                "price_growth_pct",
                "opportunity_score",
                "opportunity_level",
            ]
        ]
        .head(20)
    )

    format_opportunity_table(best_country_opportunities)


# -----------------------------
# Methodology
# -----------------------------

elif page == "Methodology":
    st.header("Methodology")

    st.subheader("Data Source")

    st.write(
        "The dashboard uses international seafood import data extracted from "
        "UN Comtrade. The data is cleaned and transformed into a product-country "
        "market table before calculating opportunity scores."
    )

    st.subheader("Pipeline")

    st.code(
        """
UN Comtrade API
→ raw import data
→ cleaned seafood trade table
→ market-level feature engineering
→ opportunity scoring
→ Streamlit dashboard
        """,
        language="text",
    )

    st.subheader("Opportunity Score")

    st.write(
        "The score ranks country-product combinations based on commercial "
        "attractiveness. Component values are converted into percentile-based "
        "scores to reduce the effect of extreme outliers."
    )

    st.code(
        """
Opportunity Score =
0.25 × value growth score
+ 0.20 × quantity growth score
+ 0.20 × volume score
+ 0.20 × trade value score
+ 0.10 × price growth score
+ 0.05 × supplier diversification score
        """,
        language="text",
    )

    st.write(
        "Higher scores suggest stronger potential based on recent import growth, "
        "market size, value, price movement, and supplier diversification."
    )