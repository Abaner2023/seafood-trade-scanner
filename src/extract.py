import time
from pathlib import Path

import pandas as pd
import comtradeapicall


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = BASE_DIR / "data" / "raw"

YEARS = [2020, 2021, 2022, 2023, 2024]

IMPORTER_COUNTRIES = {
    "United States": "842",
    "China": "156",
    "Japan": "392",
    "Spain": "724",
    "Germany": "276",
    "United Kingdom": "826",
    "Thailand": "764",
    "Vietnam": "704",
    "Philippines": "608",
    "Côte d'Ivoire": "384",
    "Nigeria": "566",
    "Ghana": "288",
    "Egypt": "818",
    "UAE": "784",
}

PRODUCT_GROUPS = {
    "Frozen Atlantic salmon": "030313",
    "Frozen yellowfin tuna": "030342",
    "Frozen mackerel": "030354",
    "Frozen hake": "030366",
    "Frozen shrimp/prawns": "030617",
}


def fetch_one_query(year, importer_name, importer_code, product_name, product_code):
    print(f"Fetching {year} | {importer_name} | {product_name}")

    try:
        df = comtradeapicall.previewFinalData(
            typeCode="C",
            freqCode="A",
            clCode="HS",
            period=str(year),
            reporterCode=importer_code,
            cmdCode=product_code,
            flowCode="M",
            partnerCode=None,
            partner2Code=None,
            customsCode=None,
            motCode=None,
            maxRecords=500,
            format_output="JSON",
            aggregateBy=None,
            breakdownMode="classic",
            countOnly=None,
            includeDesc=True,
        )

        if df is None or df.empty:
            return pd.DataFrame()

        df["selected_importer"] = importer_name
        df["selected_product_group"] = product_name

        return df

    except Exception as e:
        print(f"Failed: {year} | {importer_name} | {product_name}")
        print(e)
        return pd.DataFrame()


def main():
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    all_frames = []

    for year in YEARS:
        for importer_name, importer_code in IMPORTER_COUNTRIES.items():
            for product_name, product_code in PRODUCT_GROUPS.items():

                output_path = (
                    RAW_DATA_DIR
                    / f"comtrade_{year}_{importer_code}_{product_code}.csv"
                )

                if output_path.exists():
                    df = pd.read_csv(output_path)
                    print(f"Cached: {output_path.name}")
                else:
                    df = fetch_one_query(
                        year,
                        importer_name,
                        importer_code,
                        product_name,
                        product_code,
                    )

                    df.to_csv(output_path, index=False)

                    # Small pause so we do not hammer the API
                    time.sleep(0.5)

                if not df.empty:
                    all_frames.append(df)

    if not all_frames:
        print("No data returned.")
        return

    combined_df = pd.concat(all_frames, ignore_index=True)
    combined_path = RAW_DATA_DIR / "comtrade_imports_combined.csv"
    combined_df.to_csv(combined_path, index=False)

    print("\nDone.")
    print(f"Combined raw data saved to: {combined_path}")
    print(f"Rows: {len(combined_df):,}")
    print("Columns:")
    print(combined_df.columns.tolist())


if __name__ == "__main__":
    main()