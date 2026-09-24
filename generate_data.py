import sqlite3
import random
from datetime import datetime, timedelta

random.seed(42)

def pd_datetime(cur, account_id):
    row = cur.execute(
        "SELECT created_at FROM accounts WHERE account_id = ?",
        (account_id,)
    ).fetchone()
    return datetime.fromisoformat(row[0])


DB = "ecosec.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.executescript("""
DROP TABLE IF EXISTS analyst_feedback;
DROP TABLE IF EXISTS model_scores;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS game_sessions;
DROP TABLE IF EXISTS accounts;

CREATE TABLE accounts (
    account_id INTEGER PRIMARY KEY,
    created_at TEXT,
    is_bot INTEGER
);

CREATE TABLE game_sessions (
    session_id INTEGER PRIMARY KEY,
    account_id INTEGER,
    start_time TEXT,
    duration_minutes REAL,
    actions_per_minute REAL
);

CREATE TABLE transactions (
    tx_id INTEGER PRIMARY KEY,
    sender_id INTEGER,
    receiver_id INTEGER,
    amount REAL,
    timestamp TEXT
);

CREATE TABLE model_scores (
    account_id INTEGER PRIMARY KEY,
    suspicion_score REAL,
    needs_review INTEGER
);

CREATE TABLE analyst_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER,
    status TEXT,
    created_at TEXT
);
""")

BASE = datetime(2026, 1, 1)

normal_ids = list(range(1, 951))
bot_ids = list(range(951, 1001))

MULES = [9999, 10000]

# ------------------------------------------------------------
# Accounts
# ------------------------------------------------------------

for account_id in normal_ids + bot_ids + MULES:

    created = BASE + timedelta(
        days=random.randint(0, 180)
    )

    # 1 = abusive/bot account
    # 0 = legitimate account
    is_bot = int(account_id in bot_ids or account_id in MULES)

    cur.execute(
        """
        INSERT INTO accounts
        VALUES (?, ?, ?)
        """,
        (
            account_id,
            created.isoformat(),
            is_bot
        )
    )


# ------------------------------------------------------------
# Sessions
# ------------------------------------------------------------

session_id = 1

for account_id in normal_ids:

    sessions = random.randint(3, 12)

    for _ in range(sessions):

        account_created = pd_datetime(
            cur,
            account_id
        )

        start = account_created + timedelta(
            hours=random.randint(1, 1500)
        )

        duration = random.uniform(20, 180)

        apm = random.uniform(2.5, 9.0)

        cur.execute(
            """
            INSERT INTO game_sessions
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                account_id,
                start.isoformat(),
                duration,
                apm
            )
        )

        session_id += 1


for account_id in bot_ids:

    sessions = random.randint(4, 12)

    for _ in range(sessions):

        account_created = pd_datetime(
            cur,
            account_id
        )

        start = account_created + timedelta(
            hours=random.randint(1, 1500)
        )

        # Bots overlap heavily with legitimate players
        duration = random.uniform(25, 150)
        apm = random.uniform(3.0, 11.0)

        cur.execute(
            """
            INSERT INTO game_sessions
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                account_id,
                start.isoformat(),
                duration,
                apm
            )
        )

        session_id += 1


# Mules also look like ordinary players

for account_id in MULES:

    for _ in range(random.randint(5, 10)):

        account_created = pd_datetime(
            cur,
            account_id
        )

        start = account_created + timedelta(
            hours=random.randint(1, 1500)
        )

        cur.execute(
            """
            INSERT INTO game_sessions
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                account_id,
                start.isoformat(),
                random.uniform(30, 160),
                random.uniform(3.0, 9.0)
            )
        )

        session_id += 1


# ------------------------------------------------------------
# Transactions
# ------------------------------------------------------------

tx_id = 1

# Legitimate player-to-player transactions

for account_id in normal_ids:

    count = random.randint(3, 12)

    for _ in range(count):

        receiver = random.choice(normal_ids)

        if receiver == account_id:
            continue

        amount = random.uniform(50, 1500)

        timestamp = BASE + timedelta(
            days=random.randint(1, 180),
            hours=random.randint(0, 23)
        )

        cur.execute(
            """
            INSERT INTO transactions
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                tx_id,
                account_id,
                receiver,
                amount,
                timestamp.isoformat()
            )
        )

        tx_id += 1


# ------------------------------------------------------------
# Legitimate transactions involving mules
# ------------------------------------------------------------

# Some legitimate players interact with mule-like accounts.
# This creates realistic false-positive pressure.

for _ in range(350):

    sender = random.choice(normal_ids)
    mule = random.choice(MULES)

    amount = random.uniform(50, 1200)

    timestamp = BASE + timedelta(
        days=random.randint(1, 180),
        hours=random.randint(0, 23)
    )

    cur.execute(
        """
        INSERT INTO transactions
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            tx_id,
            sender,
            mule,
            amount,
            timestamp.isoformat()
        )
    )

    tx_id += 1


# ------------------------------------------------------------
# Abuse network
# ------------------------------------------------------------

for bot in bot_ids:

    # Bot farms currency
    outgoing_count = random.randint(4, 10)

    for _ in range(outgoing_count):

        # Most money goes toward mule accounts,
        # but some goes to ordinary players.
        if random.random() < 0.65:
            receiver = random.choice(MULES)
        else:
            receiver = random.choice(normal_ids)

        amount = random.uniform(300, 2500)

        timestamp = BASE + timedelta(
            days=random.randint(1, 180),
            hours=random.randint(0, 23)
        )

        cur.execute(
            """
            INSERT INTO transactions
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                tx_id,
                bot,
                receiver,
                amount,
                timestamp.isoformat()
            )
        )

        tx_id += 1


    # --------------------------------------------------------
    # Important: bots also receive money.
    #
    # This makes received/sent behavior overlap with
    # legitimate accounts instead of making the label obvious.
    # --------------------------------------------------------

    incoming_count = random.randint(2, 7)

    for _ in range(incoming_count):

        if random.random() < 0.55:
            sender = random.choice(normal_ids)
        else:
            sender = random.choice(bot_ids)

        if sender == bot:
            continue

        amount = random.uniform(100, 1800)

        timestamp = BASE + timedelta(
            days=random.randint(1, 180),
            hours=random.randint(0, 23)
        )

        cur.execute(
            """
            INSERT INTO transactions
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                tx_id,
                sender,
                bot,
                amount,
                timestamp.isoformat()
            )
        )

        tx_id += 1


# ------------------------------------------------------------
# Extra network noise
# ------------------------------------------------------------

for _ in range(1800):

    sender = random.choice(normal_ids)

    receiver = random.choice(
        normal_ids + MULES
    )

    if sender == receiver:
        continue

    amount = random.uniform(25, 1000)

    timestamp = BASE + timedelta(
        days=random.randint(1, 180),
        hours=random.randint(0, 23)
    )

    cur.execute(
        """
        INSERT INTO transactions
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            tx_id,
            sender,
            receiver,
            amount,
            timestamp.isoformat()
        )
    )

    tx_id += 1


conn.commit()
conn.close()

print("Generated new adversarial dataset.")
print(f"Accounts: {len(normal_ids) + len(bot_ids) + len(MULES)}")
print(f"Bots:     {len(bot_ids)}")
print(f"Mules:    {len(MULES)}")


