import sqlite3
import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import average_precision_score, precision_score, recall_score, confusion_matrix


conn = sqlite3.connect("ecosec.db")

accounts = pd.read_sql_query(
    "SELECT account_id, created_at, is_bot FROM accounts", conn
)

transactions = pd.read_sql_query(
    "SELECT tx_id, sender_id, receiver_id, amount, timestamp FROM transactions", conn
)

sessions = pd.read_sql_query(
    "SELECT session_id, account_id, start_time, duration_minutes, actions_per_minute FROM game_sessions",
    conn
)

conn.close()


# ============================================================
# Transaction features
# ============================================================

transactions["timestamp"] = pd.to_datetime(transactions["timestamp"])

out = transactions.groupby("sender_id").agg(
    transaction_count=("tx_id", "count"),
    total_sent=("amount", "sum"),
    avg_sent=("amount", "mean"),
    max_sent=("amount", "max"),
    unique_receivers=("receiver_id", "nunique"),
    first_tx=("timestamp", "min"),
    last_tx=("timestamp", "max")
).reset_index()

out = out.rename(columns={"sender_id": "account_id"})


inc = transactions.groupby("receiver_id").agg(
    total_received=("amount", "sum"),
    unique_senders=("sender_id", "nunique"),
    avg_received=("amount", "mean"),
    max_received=("amount", "max")
).reset_index()

inc = inc.rename(columns={"receiver_id": "account_id"})


# ============================================================
# Concentration features
# ============================================================

# What percentage of an account's outgoing money goes to its
# single largest receiver?
receiver_totals = (
    transactions
    .groupby(["sender_id", "receiver_id"])["amount"]
    .sum()
    .reset_index()
)

receiver_concentration = (
    receiver_totals
    .groupby("sender_id")["amount"]
    .max()
    /
    receiver_totals
    .groupby("sender_id")["amount"].sum()
)

receiver_concentration = receiver_concentration.rename(
    "top_receiver_share"
).reset_index()

receiver_concentration = receiver_concentration.rename(
    columns={"sender_id": "account_id"}
)


# What percentage of incoming money comes from the largest sender?
sender_totals = (
    transactions
    .groupby(["receiver_id", "sender_id"])["amount"]
    .sum()
    .reset_index()
)

sender_concentration = (
    sender_totals
    .groupby("receiver_id")["amount"]
    .max()
    /
    sender_totals
    .groupby("receiver_id")["amount"].sum()
)

sender_concentration = sender_concentration.rename(
    "top_sender_share"
).reset_index()

sender_concentration = sender_concentration.rename(
    columns={"receiver_id": "account_id"}
)


# ============================================================
# Transaction behavior
# ============================================================

large_threshold = transactions["amount"].quantile(0.90)

large_tx = (
    transactions
    .assign(is_large=(transactions["amount"] >= large_threshold).astype(int))
    .groupby("sender_id")["is_large"]
    .mean()
    .rename("large_tx_ratio")
    .reset_index()
    .rename(columns={"sender_id": "account_id"})
)


# ============================================================
# Session features
# ============================================================

session_features = sessions.groupby("account_id").agg(
    session_count=("session_id", "count"),
    avg_session_length=("duration_minutes", "mean"),
    avg_actions_per_minute=("actions_per_minute", "mean")
).reset_index()


# ============================================================
# Combine
# ============================================================

df = accounts.merge(out, on="account_id", how="left")
df = df.merge(inc, on="account_id", how="left")
df = df.merge(receiver_concentration, on="account_id", how="left")
df = df.merge(sender_concentration, on="account_id", how="left")
df = df.merge(large_tx, on="account_id", how="left")
df = df.merge(session_features, on="account_id", how="left")


# ============================================================
# Derived behavioral features
# ============================================================

df["mins_to_first_tx"] = (
    pd.to_datetime(df["first_tx"])
    - pd.to_datetime(df["created_at"])
).dt.total_seconds() / 60

df["activity_span_hours"] = (
    pd.to_datetime(df["last_tx"])
    - pd.to_datetime(df["first_tx"])
).dt.total_seconds() / 3600

df["activity_span_hours"] = df["activity_span_hours"].clip(lower=0)

df["received_sent_ratio"] = (
    df["total_received"] /
    (df["total_sent"] + 1)
)

df["transactions_per_session"] = (
    df["transaction_count"] /
    (df["session_count"] + 1)
)

df["money_per_session"] = (
    (df["total_sent"] + df["total_received"]) /
    (df["session_count"] + 1)
)

df["receiver_sender_ratio"] = (
    df["unique_receivers"] /
    (df["unique_senders"] + 1)
)


feature_cols = [
    "transaction_count",
    "total_sent",
    "total_received",
    "avg_sent",
    "avg_received",
    "max_sent",
    "max_received",
    "unique_receivers",
    "unique_senders",
    "top_receiver_share",
    "top_sender_share",
    "large_tx_ratio",
    "session_count",
    "avg_session_length",
    "avg_actions_per_minute",
    "mins_to_first_tx",
    "activity_span_hours",
    "received_sent_ratio",
    "transactions_per_session",
    "money_per_session",
    "receiver_sender_ratio"
]

df[feature_cols] = df[feature_cols].replace(
    [np.inf, -np.inf], np.nan
)

df[feature_cols] = df[feature_cols].fillna(0)


# ============================================================
# Inspect data
# ============================================================

print("\nLoaded:")
print(f"Accounts:     {len(accounts)}")
print(f"Transactions: {len(transactions)}")
print(f"Sessions:     {len(sessions)}")

print("\nFeature averages by label:")
print(
    df.groupby("is_bot")[feature_cols]
    .mean()
    .round(2)
    .to_string()
)


# ============================================================
# Train / validation / test
# ============================================================

X = df[feature_cols]
y = df["is_bot"]

X_train, X_temp, y_train, y_temp = train_test_split(
    X,
    y,
    test_size=0.30,
    stratify=y,
    random_state=42
)

X_val, X_test, y_val, y_test = train_test_split(
    X_temp,
    y_temp,
    test_size=0.50,
    stratify=y_temp,
    random_state=42
)

print("\nSplit:")
print(f"Train:      {len(X_train)}")
print(f"Validation: {len(X_val)}")
print(f"Test:       {len(X_test)}")


# ============================================================
# Model
# ============================================================

model = RandomForestClassifier(
    n_estimators=400,
    max_depth=8,
    min_samples_leaf=3,
    class_weight="balanced",
    random_state=42
)

model.fit(X_train, y_train)

val_scores = model.predict_proba(X_val)[:, 1]
test_scores = model.predict_proba(X_test)[:, 1]


# ============================================================
# Threshold selection
# ============================================================

best_threshold = 0.99
best_recall = -1

for threshold in np.linspace(0.01, 0.99, 500):

    predictions = (val_scores >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        y_val,
        predictions,
        labels=[0, 1]
    ).ravel()

    fpr = fp / max(tn + fp, 1)
    recall = tp / max(tp + fn, 1)

    if fpr <= 0.01 and recall > best_recall:
        best_threshold = threshold
        best_recall = recall


# ============================================================
# Test
# ============================================================

test_predictions = (
    test_scores >= best_threshold
).astype(int)

tn, fp, fn, tp = confusion_matrix(
    y_test,
    test_predictions,
    labels=[0, 1]
).ravel()

fpr = fp / max(tn + fp, 1)

print("\n==============================")
print("EcoSec Abuse Detection")
print("==============================")
print(f"PR-AUC:            {average_precision_score(y_test, test_scores):.3f}")
print(f"Threshold:         {best_threshold:.3f}")
print(f"Precision:         {precision_score(y_test, test_predictions, zero_division=0):.3f}")
print(f"Recall:            {recall_score(y_test, test_predictions, zero_division=0):.3f}")
print(f"False Positive Rate: {fpr:.3f}")
print(f"True Positives:    {tp}")
print(f"False Positives:   {fp}")
print(f"False Negatives:   {fn}")
print(f"True Negatives:    {tn}")


# ============================================================
# Feature importance
# ============================================================

importance = pd.DataFrame({
    "feature": feature_cols,
    "importance": model.feature_importances_
}).sort_values(
    "importance",
    ascending=False
)

print("\nFeature Importance")
print("==============================")

for _, row in importance.iterrows():
    print(
        f"{row['feature']:28s} "
        f"{row['importance']:.3f}"
    )


# ============================================================
# Save model scores
# ============================================================

conn = sqlite3.connect("ecosec.db")

cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS model_scores")

cursor.execute("""
CREATE TABLE model_scores (
    account_id INTEGER PRIMARY KEY,
    suspicion_score REAL,
    needs_review INTEGER
)
""")

all_scores = model.predict_proba(X)[:, 1]

rows = [
    (
        int(account_id),
        float(score),
        int(score >= best_threshold)
    )
    for account_id, score
    in zip(df["account_id"], all_scores)
]

cursor.executemany(
    """
    INSERT INTO model_scores
    (account_id, suspicion_score, needs_review)
    VALUES (?, ?, ?)
    """,
    rows
)

conn.commit()
conn.close()

print("\nSaved model scores to ecosec.db")
