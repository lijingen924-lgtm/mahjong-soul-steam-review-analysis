import re
import sys
from pathlib import Path

import pandas as pd
from scipy.stats import fisher_exact


DATA_FILE = (
    Path(sys.argv[1])
    if len(sys.argv) > 1
    else Path(__file__).with_name(
        "mahjong_soul_steam_reviews_2000.csv"
    )
)


TOPIC_PATTERNS = {
    "RNG / perceived unfairness": (
        r"\b(?:rng|luck|lucky|unlucky|rigged|algorithm|variance|random|unfair|pay to win)\b"
        r"|운빨|운이|패산|억까|주작|확률|불합리|몰아주|깔아주|리치|쯔모|화료|방총"
        r"|패가|패 버리|점수|승점|등급전|승급|강등|4위|라스"
    ),
    "Cheating / competitive integrity": (
        r"\b(?:cheat|cheating|report function|ai|calculator|prequeued)\b"
        r"|핵|보조 프로그램|신고|중국인"
    ),
    "Monetization / gacha": (
        r"\b(?:money|monetization|gacha|pulls?|pity|pay to win|outfits?|paid|greediest|freeplay)\b"
        r"|가챠|과금|천장|재화|티켓|뽑|캐릭|스킨|작사"
    ),
    "Operations / content / technical": (
        r"\b(?:update|server|connection|crash|bug|event|artwork|animation|content)\b"
        r"|서버|재연결|턴 지연|이벤트|일러|패치|운영|요스타|콜라보|컨텐츠|관리"
    ),
    "Frustration / burnout": (
        r"\b(?:ruin|damage to the human spirit|not fun|worst|miserable|frustrat|mental|hate|suck|aids|fuck)\b"
        r"|불쾌|분노|스트레스|정신|화만|화딱지|욕|하지마|망겜|병신|빡|고통|질병"
        r"|최악|접|지움|안하는게|그만"
    ),
}

MEME_PATTERN = (
    r"mahjong causes great damage to the human spirit"
    r"|this game ruined my life"
    r"|this game will ruin your life"
)


df = pd.read_csv(DATA_FILE)

# Focus on English and Korean negative reviews because these languages
# have adequate counts in the 200+ hour group.
negative_reviews = df[
    (~df["recommended"])
    & df["language"].isin(["english", "koreana"])
].copy()

negative_reviews["comparison_group"] = negative_reviews[
    "playtime_group"
].apply(
    lambda value: (
        "Over 200 hours"
        if value == "Over 200 hours"
        else "Under 200 hours"
    )
)

negative_reviews["normalized_text"] = (
    negative_reviews["review_text"]
    .fillna("")
    .str.lower()
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

negative_reviews["meme_or_copypasta"] = negative_reviews[
    "normalized_text"
].str.contains(
    MEME_PATTERN,
    regex=True,
    na=False,
)

for topic, pattern in TOPIC_PATTERNS.items():
    negative_reviews[topic] = negative_reviews[
        "normalized_text"
    ].str.contains(
        pattern,
        regex=True,
        na=False,
    )


group_sizes = negative_reviews.groupby(
    "comparison_group"
).size()

summary_rows = []

for topic in TOPIC_PATTERNS:
    high_mentions = int(
        negative_reviews.loc[
            negative_reviews["comparison_group"]
            == "Over 200 hours",
            topic,
        ].sum()
    )

    other_mentions = int(
        negative_reviews.loc[
            negative_reviews["comparison_group"]
            == "Under 200 hours",
            topic,
        ].sum()
    )

    high_total = int(group_sizes["Over 200 hours"])
    other_total = int(group_sizes["Under 200 hours"])

    odds_ratio, p_value = fisher_exact(
        [
            [high_mentions, high_total - high_mentions],
            [other_mentions, other_total - other_mentions],
        ]
    )

    summary_rows.append(
        {
            "topic": topic,
            "over_200_mentions": high_mentions,
            "over_200_negative_reviews": high_total,
            "over_200_topic_share": (
                high_mentions / high_total * 100
            ),
            "under_200_mentions": other_mentions,
            "under_200_negative_reviews": other_total,
            "under_200_topic_share": (
                other_mentions / other_total * 100
            ),
            "odds_ratio": odds_ratio,
            "p_value": p_value,
        }
    )


topic_summary = pd.DataFrame(summary_rows).round(4)

print("\n--- NEGATIVE REVIEW TOPIC COMPARISON ---")
print(topic_summary.to_string(index=False))

print("\nNotes:")
print("- Topic categories may overlap.")
print("- Shares use negative reviews as the denominator.")
print("- Results are exploratory keyword-based classifications.")
print(
    "- Meme/copypasta reviews in 200+ hour group:",
    int(
        negative_reviews.loc[
            negative_reviews["comparison_group"]
            == "Over 200 hours",
            "meme_or_copypasta",
        ].sum()
    ),
)

topic_summary.to_csv(
    "negative_review_topic_comparison.csv",
    index=False,
    encoding="utf-8-sig",
)

print(
    "\nResults saved to "
    "negative_review_topic_comparison.csv"
)
