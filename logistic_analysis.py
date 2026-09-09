import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
import statsmodels.api as sm

# Read the saved raw review data
df = pd.read_csv("mahjong_soul_steam_reviews_2000.csv")


# Convert True/False columns to 1/0
def convert_binary(column):
    return (
        column.astype(str)
        .str.strip()
        .str.lower()
        .map({
            "true": 1,
            "false": 0,
            "1": 1,
            "0": 0
        })
    )


df["recommended_num"] = convert_binary(df["recommended"])
df["steam_purchase_num"] = convert_binary(df["steam_purchase"])
df["received_for_free_num"] = convert_binary(df["received_for_free"])

# Prepare date
df["review_date"] = pd.to_datetime(df["review_date"], utc=True)
df["review_month"] = df["review_date"].dt.strftime("%Y-%m")

# Combine languages with fewer than 50 reviews into "other"
language_counts = df["language"].value_counts()

df["language_group"] = df["language"].where(
    df["language"].map(language_counts) >= 50,
    "other"
)

# Playtime is highly right-skewed, so apply log transformation
df["log_playtime"] = np.log1p(df["playtime_at_review_hours"])

# Standardize for easier interpretation
df["log_playtime_z"] = (
    df["log_playtime"] - df["log_playtime"].mean()
) / df["log_playtime"].std()

model_data = df.dropna(
    subset=[
        "recommended_num",
        "log_playtime_z",
        "language_group",
        "review_month",
        "steam_purchase_num",
        "received_for_free_num"
    ]
).copy()
# Automatically remove binary controls with only one value
control_terms = [
    "C(language_group)",
    "C(review_month)"
]

for column in ["steam_purchase_num", "received_for_free_num"]:
    if model_data[column].nunique() > 1:
        control_terms.append(column)
    else:
        print(f"Dropped {column}: it has only one value.")

adjusted_formula = (
    "recommended_num ~ log_playtime_z + "
    + " + ".join(control_terms)
)

print("\nAdjusted formula:")
print(adjusted_formula)

# GLM with Binomial family is also logistic regression
simple_model = smf.glm(
    "recommended_num ~ log_playtime_z",
    data=model_data,
    family=sm.families.Binomial()
).fit()

adjusted_model = smf.glm(
    adjusted_formula,
    data=model_data,
    family=sm.families.Binomial()
).fit()


def extract_result(model, model_name):
    coefficient = model.params["log_playtime_z"]
    lower, upper = model.conf_int().loc["log_playtime_z"]

    return {
        "model": model_name,
        "coefficient": coefficient,
        "odds_ratio": np.exp(coefficient),
        "ci_lower": np.exp(lower),
        "ci_upper": np.exp(upper),
        "p_value": model.pvalues["log_playtime_z"],
        "pseudo_r_squared": 1 - model.llf / model.llnull
    }


results = pd.DataFrame([
    extract_result(simple_model, "Playtime only"),
    extract_result(adjusted_model, "Adjusted model")
])

print("\n--- LOGISTIC REGRESSION RESULTS ---")
print(results.round(4).to_string(index=False))

results.to_csv(
    "logistic_regression_results.csv",
    index=False
)

print("\nResults saved to logistic_regression_results.csv")