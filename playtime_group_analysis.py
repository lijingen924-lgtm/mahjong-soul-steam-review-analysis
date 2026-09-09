import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import chi2


# 1. Read raw review data
df = pd.read_csv("mahjong_soul_steam_reviews_2000.csv")


# 2. Convert recommendation to 0/1
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


# 3. Create review month
df["review_month"] = (
    pd.to_datetime(
        df["review_date"],
        errors="coerce",
        utc=True
    )
    .dt.strftime("%Y-%m")
)


# 4. Group languages with fewer than 50 reviews as "other"
language_counts = df["language"].value_counts()

df["language_group"] = df["language"].where(
    df["language"].map(language_counts) >= 50,
    "other"
)


# 5. Create playtime groups
playtime_bins = [
    0,
    10,
    25,
    75,
    200,
    float("inf")
]

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


# 6. Keep complete observations
model_data = df[
    [
        "recommended_num",
        "playtime_group",
        "language_group",
        "review_month"
    ]
].dropna().copy()


# 7. Full model with playtime groups
playtime_term = (
    "C(playtime_group, "
    "Treatment(reference='Under 10 hours'))"
)

control_terms = (
    "C(language_group) + "
    "C(review_month)"
)

full_formula = (
    "recommended_num ~ "
    + playtime_term
    + " + "
    + control_terms
)

full_model = smf.glm(
    formula=full_formula,
    data=model_data,
    family=sm.families.Binomial()
).fit()


# 8. Reduced model without playtime groups
reduced_formula = (
    "recommended_num ~ "
    + control_terms
)

reduced_model = smf.glm(
    formula=reduced_formula,
    data=model_data,
    family=sm.families.Binomial()
).fit()


# 9. Overall likelihood-ratio test for playtime groups
lr_statistic = 2 * (
    full_model.llf - reduced_model.llf
)

df_difference = (
    full_model.df_model
    - reduced_model.df_model
)

overall_p_value = chi2.sf(
    lr_statistic,
    df_difference
)


# 10. Observed results by playtime group
observed_results = (
    model_data.groupby(
        "playtime_group",
        observed=True
    )
    .agg(
        review_count=("recommended_num", "count"),
        observed_positive_rate=("recommended_num", "mean")
    )
    .reindex(playtime_labels)
    .reset_index()
)

observed_results["observed_positive_rate"] *= 100


# 11. Adjusted predicted rate for each group
adjusted_rates = {}

for group in playtime_labels:
    prediction_data = model_data.copy()
    prediction_data["playtime_group"] = group

    adjusted_rates[group] = (
        full_model.predict(prediction_data).mean()
        * 100
    )


# 12. Extract odds ratios
confidence_intervals = full_model.conf_int()
result_rows = []

term_prefix = (
    "C(playtime_group, "
    "Treatment(reference='Under 10 hours'))"
)

for _, row in observed_results.iterrows():
    group = row["playtime_group"]

    result = {
        "playtime_group": group,
        "review_count": int(row["review_count"]),
        "observed_positive_rate":
            row["observed_positive_rate"],
        "adjusted_positive_rate":
            adjusted_rates[group]
    }

    if group == "Under 10 hours":
        result["coefficient"] = 0
        result["odds_ratio"] = 1
        result["ci_lower"] = np.nan
        result["ci_upper"] = np.nan
        result["p_value"] = np.nan

    else:
        term_name = (
            f"{term_prefix}[T.{group}]"
        )

        coefficient = full_model.params[term_name]
        lower = confidence_intervals.loc[
            term_name, 0
        ]
        upper = confidence_intervals.loc[
            term_name, 1
        ]

        result["coefficient"] = coefficient
        result["odds_ratio"] = np.exp(coefficient)
        result["ci_lower"] = np.exp(lower)
        result["ci_upper"] = np.exp(upper)
        result["p_value"] = full_model.pvalues[
            term_name
        ]

    result_rows.append(result)


results = pd.DataFrame(result_rows).round(4)


# 13. Print and save results
print("\n--- PLAYTIME GROUP REGRESSION ---")
print(results.to_string(index=False))

print("\n--- OVERALL PLAYTIME GROUP TEST ---")
print("Likelihood-ratio statistic:",
      round(lr_statistic, 4))
print("Degrees of freedom:",
      int(df_difference))
print("Overall p-value:",
      round(overall_p_value, 4))

results.to_csv(
    "playtime_group_regression_results.csv",
    index=False,
    encoding="utf-8-sig"
)

print(
    "\nResults saved to "
    "playtime_group_regression_results.csv"
)