import pandas as pd

base = "data/product_research/output/ornament"
df = pd.read_parquet(f"{base}/historical_search_terms_with_niche.parquet")

print("rows:", len(df))
print("matched:", df["niche_id"].notna().sum())
print("unmatched:", df["niche_id"].isna().sum())
print("matched niches:", df["niche"].dropna().nunique())

print("\nTop unmatched search terms:")
cols = ["search_term", "search_frequency_rank", "month"]
print(
    df[df["niche_id"].isna()][cols]
    .sort_values("search_frequency_rank")
    .head(80)
    .to_string(index=False)
)
