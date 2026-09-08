import requests
import pandas as pd
import time

app_id = 2739990

url = f"https://store.steampowered.com/appreviews/{app_id}"

all_reviews = []
cursor = "*"
maximum_reviews = 2000

while len(all_reviews) < maximum_reviews:
    params = {
        "json": 1,
        "filter": "recent",
        "language": "all",
        "review_type": "all",
        "purchase_type": "all",
        "num_per_page": 100,
        "cursor": cursor
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    new_reviews = data["reviews"]

    if len(new_reviews) == 0:
        break

    all_reviews.extend(new_reviews)
    cursor = data["cursor"]

    print("Reviews collected:", len(all_reviews))

    time.sleep(1)

all_reviews = all_reviews[:maximum_reviews]

print("Final number of reviews:", len(all_reviews))

rows = []

for review in all_reviews:
    author = review["author"]

    rows.append({
        "review_id": review["recommendationid"],
        "language": review["language"],
        "review_text": review["review"],
        "recommended": review["voted_up"],
        "timestamp_created": review["timestamp_created"],
        "helpful_votes": review["votes_up"],
        "funny_votes": review["votes_funny"],
        "comment_count": review["comment_count"],
        "steam_purchase": review["steam_purchase"],
        "received_for_free": review["received_for_free"],
        "playtime_at_review_minutes": author.get("playtime_at_review"),
        "total_playtime_minutes": author.get("playtime_forever")
    })

df = pd.DataFrame(rows)

# Remove duplicate reviews
df = df.drop_duplicates(
    subset="review_id"
).reset_index(drop=True)

print("Reviews after removing duplicates:", len(df))

# Convert timestamp to date
df["review_date"] = pd.to_datetime(
    df["timestamp_created"],
    unit="s",
    utc=True
)

df["playtime_at_review_hours"] = (
    df["playtime_at_review_minutes"] / 60
)

df["total_playtime_hours"] = (
    df["total_playtime_minutes"] / 60
)

print(df.head())
print("Rows and columns:", df.shape)

language_counts = df["language"].value_counts()

print("\nNumber of reviews by language:")
print(language_counts)
language_summary = (
    df.groupby("language")
    .agg(
        review_count=("review_id", "count"),
        positive_reviews=("recommended", "sum"),
        positive_rate=("recommended", "mean"),
        median_playtime_hours=("playtime_at_review_hours", "median")
    )
    .reset_index()
)

language_summary["positive_rate"] = (
    language_summary["positive_rate"] * 100
).round(2)

language_summary["median_playtime_hours"] = (
    language_summary["median_playtime_hours"].round(2)
)

print("\nLanguage summary:")
print(language_summary)

print("\n--- DATA QUALITY CHECK ---")

# Number of rows and columns
print("Dataset shape:", df.shape)

# Duplicate review IDs
print("Duplicate review IDs:", df["review_id"].duplicated().sum())

# Date range
print("Earliest review:", df["review_date"].min())
print("Latest review:", df["review_date"].max())

# Language distribution
print("\nReviews by language:")
print(df["language"].value_counts())

# Positive and negative reviews
print("\nRecommendation distribution:")
print(df["recommended"].value_counts())

# Missing values
print("\nMissing values:")
print(df.isna().sum())

# Playtime statistics
print("\nPlaytime at review:")
print(df["playtime_at_review_hours"].describe())


# Keep languages with at least 50 reviews
language_analysis = language_summary[
    language_summary["review_count"] >= 50
].copy()

language_analysis = language_analysis.sort_values(
    by="review_count",
    ascending=False
)

print("\nMain language analysis:")
print(language_analysis)

df["review_month"] = df["review_date"].dt.strftime("%Y-%m")

monthly_analysis = (
    df.groupby("review_month")
    .agg(
        review_count=("review_id", "count"),
        positive_rate=("recommended", "mean")
    )
    .reset_index()
)

monthly_analysis["positive_rate"] = (
    monthly_analysis["positive_rate"] * 100
).round(2)

print("\nMonthly analysis:")
print(monthly_analysis)

playtime_bins = [0, 10, 25, 75, 200, float("inf")]

playtime_labels = [
    "Under 10 hours",
    "10-25 hours",
    "25-75 hours",
    "75-200 hours",
    "Over 200 hours"
]

df["playtime_group"] = pd.cut(
    df["playtime_at_review_hours"],
    bins=playtime_bins,
    labels=playtime_labels,
    right=False,
    include_lowest=True
)

playtime_analysis = (
    df.groupby("playtime_group", observed=True)
    .agg(
        review_count=("review_id", "count"),
        positive_rate=("recommended", "mean"),
        median_playtime_hours=("playtime_at_review_hours", "median")
    )
    .reset_index()
)

playtime_analysis["positive_rate"] = (
    playtime_analysis["positive_rate"] * 100
).round(2)

playtime_analysis["median_playtime_hours"] = (
    playtime_analysis["median_playtime_hours"].round(2)
)

print("\nPlaytime analysis:")
print(playtime_analysis)

df.to_csv(
    "mahjong_soul_steam_reviews_2000.csv",
    index=False,
    encoding="utf-8-sig"
)

language_summary.to_csv(
    "mahjong_soul_language_summary.csv",
    index=False,
    encoding="utf-8-sig"
)

print("CSV file saved successfully!")

language_analysis.to_csv(
    "language_analysis.csv",
    index=False,
    encoding="utf-8-sig"
)

monthly_analysis.to_csv(
    "monthly_analysis.csv",
    index=False,
    encoding="utf-8-sig"
)

playtime_analysis.to_csv(
    "playtime_analysis.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\nAll analysis files saved!")