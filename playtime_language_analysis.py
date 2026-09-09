import pandas as pd


df = pd.read_csv(
    "mahjong_soul_steam_reviews_2000.csv"
)

recommendation_map = {
    True: 1,
    False: 0,
    "True": 1,
    "False": 0,
    "true": 1,
    "false": 0
}

df["recommended_num"] = (
    df["recommended"]
    .replace(recommendation_map)
)

df["recommended_num"] = pd.to_numeric(
    df["recommended_num"],
    errors="coerce"
)

playtime_labels = [
    "Under 10 hours",
    "10-25 hours",
    "25-75 hours",
    "75-200 hours",
    "Over 200 hours"
]

df["playtime_group"] = pd.cut(
    df["playtime_at_review_hours"],
    bins=[0, 10, 25, 75, 200, float("inf")],
    labels=playtime_labels,
    right=False,
    include_lowest=True
)

# Keep languages with at least 50 total reviews
language_counts = df["language"].value_counts()

main_languages = language_counts[
    language_counts >= 50
].index

analysis_data = df[
    df["language"].isin(main_languages)
].copy()

segment_results = (
    analysis_data.groupby(
        ["language", "playtime_group"],
        observed=True
    )
    .agg(
        review_count=("recommended_num", "count"),
        positive_reviews=("recommended_num", "sum"),
        positive_rate=("recommended_num", "mean")
    )
    .reset_index()
)

segment_results["positive_rate"] = (
    segment_results["positive_rate"] * 100
).round(2)

segment_results = segment_results.sort_values(
    ["language", "playtime_group"]
)

print("\n--- LANGUAGE × PLAYTIME RESULTS ---")
print(segment_results.to_string(index=False))

segment_results.to_csv(
    "playtime_language_analysis.csv",
    index=False,
    encoding="utf-8-sig"
)

print(
    "\nResults saved to "
    "playtime_language_analysis.csv"
)