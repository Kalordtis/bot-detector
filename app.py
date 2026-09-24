from flask import (
    Flask,
    render_template_string,
    request,
    redirect,
    url_for
)

import sqlite3


app = Flask(__name__)

DB_NAME = "ecosec.db"


HTML_TEMPLATE = """

<!DOCTYPE html>

<html>

<head>

<title>EcoSec Analyst Dashboard</title>

<style>

body {
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;

    margin: 0;
    background: #f5f6f8;
    color: #222;
}

.container {
    max-width: 1300px;
    margin: 40px auto;
    padding: 0 25px;
}

.header {
    margin-bottom: 25px;
}

.header h1 {
    margin-bottom: 5px;
}

.header p {
    color: #666;
}

.stats {
    display: flex;
    gap: 15px;
    margin-bottom: 20px;
}

.stat {
    background: white;
    padding: 18px 25px;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    min-width: 150px;
}

.stat-number {
    font-size: 25px;
    font-weight: 700;
}

.stat-label {
    color: #777;
    font-size: 13px;
}

.card {
    background: white;
    border-radius: 10px;
    padding: 25px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    overflow-x: auto;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th {
    text-align: left;
    padding: 14px;
    background: #222;
    color: white;
    font-size: 13px;
}

td {
    padding: 14px;
    border-bottom: 1px solid #eee;
    white-space: nowrap;
}

tr:hover {
    background: #fafafa;
}

.score {
    font-weight: 700;
}

.high {
    color: #d93025;
}

.medium {
    color: #e37400;
}

.low {
    color: #188038;
}

button {
    border: none;
    padding: 8px 12px;
    border-radius: 5px;
    cursor: pointer;
    font-weight: 600;
    margin-right: 5px;
}

.confirm {
    background: #d93025;
    color: white;
}

.false-positive {
    background: #188038;
    color: white;
}

button:hover {
    opacity: 0.85;
}

.account {
    font-weight: 600;
}

.subtitle {
    color: #777;
    font-size: 13px;
    margin-bottom: 15px;
}

</style>

</head>


<body>

<div class="container">

<div class="header">

<h1>EcoSec Investigation Queue</h1>

<p>
Behavioral abuse detection system for analyst review.
</p>

</div>


<div class="stats">

<div class="stat">

<div class="stat-number">
{{ total_accounts }}
</div>

<div class="stat-label">
Accounts Monitored
</div>

</div>


<div class="stat">

<div class="stat-number">
{{ total_flagged }}
</div>

<div class="stat-label">
Requiring Review
</div>

</div>


<div class="stat">

<div class="stat-number">
{{ feedback_count }}
</div>

<div class="stat-label">
Analyst Reviews
</div>

</div>

</div>


<div class="card">

<div class="subtitle">
Showing the highest-risk accounts currently in the investigation queue.
</div>

<table>

<tr>

<th>Account</th>
<th>Suspicion</th>
<th>First Trade</th>
<th>Total Sent</th>
<th>Receivers</th>
<th>Senders</th>
<th>Sessions</th>
<th>Action</th>

</tr>


{% for row in accounts %}

<tr>

<td class="account">
#{{ row['account_id'] }}
</td>


<td class="score
{% if row['suspicion_score'] >= 0.8 %}
high
{% elif row['suspicion_score'] >= 0.5 %}
medium
{% else %}
low
{% endif %}
">

{{ "%.1f"|format(row['suspicion_score'] * 100) }}%

</td>


<td>

{% if row['mins_to_first_tx'] >= 99999 %}

No trade

{% else %}

{{ "%.0f"|format(row['mins_to_first_tx']) }} min

{% endif %}

</td>


<td>

${{ "%.0f"|format(row['total_sent']) }}

</td>


<td>

{{ row['unique_receivers'] }}

</td>


<td>

{{ row['unique_senders'] }}

</td>


<td>

{{ row['session_count'] }}

</td>


<td>

<form
action="/action"
method="post"
>

<input
type="hidden"
name="account_id"
value="{{ row['account_id'] }}"
>


<button
type="submit"
name="status"
value="abuse"
class="confirm"
>

Confirm Abuse

</button>


<button
type="submit"
name="status"
value="false_positive"
class="false-positive"
>

False Positive

</button>

</form>

</td>

</tr>

{% endfor %}

</table>

</div>

</div>

</body>

</html>

"""


def get_db_connection():

    conn = sqlite3.connect(DB_NAME)

    conn.row_factory = sqlite3.Row

    return conn


@app.route("/")
def index():

    conn = get_db_connection()

    # Aggregate each data source separately before joining.
    # This prevents transaction/session joins from multiplying rows.

    query = """

    SELECT

        m.account_id,

        m.suspicion_score,

        COALESCE(tx.mins_to_first_tx, 99999)
            AS mins_to_first_tx,

        COALESCE(tx.total_sent, 0)
            AS total_sent,

        COALESCE(tx.unique_receivers, 0)
            AS unique_receivers,

        COALESCE(incoming.unique_senders, 0)
            AS unique_senders,

        COALESCE(sessions.session_count, 0)
            AS session_count

    FROM model_scores m


    LEFT JOIN (

        SELECT

            t.sender_id AS account_id,

            MIN(
                (
                    JULIANDAY(t.timestamp)
                    - JULIANDAY(a.created_at)
                ) * 24 * 60
            ) AS mins_to_first_tx,

            SUM(t.amount) AS total_sent,

            COUNT(
                DISTINCT t.receiver_id
            ) AS unique_receivers

        FROM transactions t

        JOIN accounts a
            ON t.sender_id = a.account_id

        GROUP BY t.sender_id

    ) tx

        ON m.account_id = tx.account_id


    LEFT JOIN (

        SELECT

            receiver_id AS account_id,

            COUNT(
                DISTINCT sender_id
            ) AS unique_senders

        FROM transactions

        GROUP BY receiver_id

    ) incoming

        ON m.account_id = incoming.account_id


    LEFT JOIN (

        SELECT

            account_id,

            COUNT(*) AS session_count

        FROM game_sessions

        GROUP BY account_id

    ) sessions

        ON m.account_id = sessions.account_id


    WHERE m.needs_review = 1

    ORDER BY m.suspicion_score DESC

    LIMIT 30

    """

    accounts = conn.execute(query).fetchall()


    total_accounts = conn.execute(
        """
        SELECT COUNT(*)
        FROM accounts
        """
    ).fetchone()[0]


    total_flagged = conn.execute(
        """
        SELECT COUNT(*)
        FROM model_scores
        WHERE needs_review = 1
        """
    ).fetchone()[0]


    feedback_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM analyst_feedback
        """
    ).fetchone()[0]


    conn.close()


    return render_template_string(

        HTML_TEMPLATE,

        accounts=accounts,

        total_accounts=total_accounts,

        total_flagged=total_flagged,

        feedback_count=feedback_count

    )


@app.route("/action", methods=["POST"])
def action():

    account_id = request.form["account_id"]

    status = request.form["status"]


    conn = get_db_connection()


    conn.execute(
        """
        INSERT INTO analyst_feedback
        (account_id, status, timestamp)

        VALUES (?, ?, datetime('now'))
        """,

        (
            account_id,
            status
        )
    )


    conn.execute(
        """
        UPDATE model_scores

        SET needs_review = 0

        WHERE account_id = ?
        """,

        (account_id,)
    )


    conn.commit()

    conn.close()


    return redirect(
        url_for("index")
    )


if __name__ == "__main__":

    app.run(
        debug=True,
        port=5000
    )