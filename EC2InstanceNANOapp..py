import boto3
import time
import csv
import io
from flask import Flask, render_template_string

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION  –  Update these three values before running on EC2
# ─────────────────────────────────────────────────────────────────────────────
AWS_REGION         = "us-east-1"                        # e.g. "us-east-1"
ATHENA_DATABASE    = "orders_db"                        # Glue DB name
S3_OUTPUT_LOCATION = "s3://YOUR-BUCKET-NAME/enriched/" # Athena result bucket
# ─────────────────────────────────────────────────────────────────────────────

app           = Flask(__name__)
athena_client = boto3.client('athena', region_name=AWS_REGION)
s3_client     = boto3.client('s3',     region_name=AWS_REGION)

# ── Athena SQL queries ────────────────────────────────────────────────────────
QUERIES = [
    {
        "title": "1. Total Sales by Customer",
        "description": "Cumulative revenue contributed by each customer, ranked highest first.",
        "query": """
            SELECT Customer,
                   ROUND(SUM(Amount), 2) AS TotalAmountSpent
            FROM "filtered_orders"
            GROUP BY Customer
            ORDER BY TotalAmountSpent DESC;
        """
    },
    {
        "title": "2. Monthly Order Volume & Revenue",
        "description": "Number of orders and total revenue aggregated per calendar month.",
        "query": """
            SELECT DATE_TRUNC('month', CAST(OrderDate AS DATE)) AS OrderMonth,
                   COUNT(OrderID)              AS NumberOfOrders,
                   ROUND(SUM(Amount), 2)       AS MonthlyRevenue
            FROM "filtered_orders"
            GROUP BY 1
            ORDER BY OrderMonth;
        """
    },
    {
        "title": "3. Order Status Dashboard",
        "description": "Breakdown of order count and revenue by fulfilment status.",
        "query": """
            SELECT Status,
                   COUNT(OrderID)        AS OrderCount,
                   ROUND(SUM(Amount), 2) AS TotalAmount
            FROM "filtered_orders"
            GROUP BY Status
            ORDER BY OrderCount DESC;
        """
    },
    {
        "title": "4. Average Order Value (AOV) per Customer",
        "description": "Mean spend per transaction for each customer, sorted by highest AOV.",
        "query": """
            SELECT Customer,
                   ROUND(AVG(Amount), 2) AS AverageOrderValue
            FROM "filtered_orders"
            GROUP BY Customer
            ORDER BY AverageOrderValue DESC;
        """
    },
    {
        "title": "5. Top 10 Largest Orders — February 2025",
        "description": "The ten highest-value individual orders placed during February 2025.",
        "query": """
            SELECT OrderDate, OrderID, Customer,
                   ROUND(Amount, 2) AS Amount
            FROM "filtered_orders"
            WHERE CAST(OrderDate AS DATE)
                  BETWEEN DATE '2025-02-01' AND DATE '2025-02-28'
            ORDER BY Amount DESC
            LIMIT 10;
        """
    },
]

# ── Athena helper ─────────────────────────────────────────────────────────────
def run_athena_query(sql: str):
    """
    Submits an Athena query, polls until complete, then fetches and parses
    the CSV result from S3.

    Returns:
        (header: list[str], rows: list[list[str]])   on success
        (None,   error_msg: str)                      on failure
    """
    try:
        resp = athena_client.start_query_execution(
            QueryString=sql,
            QueryExecutionContext={"Database": ATHENA_DATABASE},
            ResultConfiguration={"OutputLocation": S3_OUTPUT_LOCATION},
        )
        exec_id = resp["QueryExecutionId"]

        # Poll
        while True:
            stats  = athena_client.get_query_execution(QueryExecutionId=exec_id)
            state  = stats["QueryExecution"]["Status"]["State"]
            if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
                break
            time.sleep(1)

        if state != "SUCCEEDED":
            reason = stats["QueryExecution"]["Status"].get(
                "StateChangeReason", "Unknown error"
            )
            return None, f"Query {state}: {reason}"

        # Fetch CSV result from S3
        s3_uri     = stats["QueryExecution"]["ResultConfiguration"]["OutputLocation"]
        bucket, key = s3_uri.replace("s3://", "").split("/", 1)
        obj        = s3_client.get_object(Bucket=bucket, Key=key)
        raw        = obj["Body"].read().decode("utf-8")

        reader = csv.reader(io.StringIO(raw))
        rows   = list(reader)
        if not rows:
            return [], []
        header = [h.strip('"') for h in rows[0]]
        data   = [[c.strip('"') for c in r] for r in rows[1:] if r]
        return header, data

    except Exception as exc:
        return None, f"Exception: {exc}"


# ── HTML template ─────────────────────────────────────────────────────────────
PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Athena Orders Dashboard — ITCS-6190 A3</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet" />
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Inter', sans-serif;
      background: #0f0f1a;
      color: #e2e8f0;
      min-height: 100vh;
    }

    /* ── Header ── */
    header {
      background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e3a5f 100%);
      padding: 2.5rem 3rem;
      border-bottom: 1px solid rgba(99,102,241,0.3);
      display: flex;
      align-items: center;
      gap: 1.5rem;
    }
    .header-icon { font-size: 2.8rem; }
    header h1 {
      font-size: 1.9rem;
      font-weight: 700;
      background: linear-gradient(90deg, #a5b4fc, #67e8f9);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    header p {
      font-size: 0.85rem;
      color: #94a3b8;
      margin-top: 0.25rem;
    }

    /* ── Main container ── */
    main { max-width: 1100px; margin: 0 auto; padding: 2.5rem 1.5rem; }

    /* ── Query cards ── */
    .card {
      background: #1a1a2e;
      border: 1px solid rgba(99,102,241,0.2);
      border-radius: 12px;
      margin-bottom: 2.5rem;
      overflow: hidden;
      box-shadow: 0 4px 24px rgba(0,0,0,0.4);
      transition: box-shadow 0.2s;
    }
    .card:hover { box-shadow: 0 8px 32px rgba(99,102,241,0.2); }

    .card-header {
      background: linear-gradient(90deg, rgba(99,102,241,0.15), rgba(16,185,129,0.08));
      border-bottom: 1px solid rgba(99,102,241,0.2);
      padding: 1.2rem 1.6rem;
    }
    .card-header h2 {
      font-size: 1.1rem;
      font-weight: 600;
      color: #a5b4fc;
    }
    .card-header p {
      font-size: 0.82rem;
      color: #64748b;
      margin-top: 0.3rem;
    }

    .card-body { padding: 1.2rem 1.6rem 1.6rem; overflow-x: auto; }

    /* ── Table ── */
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.88rem;
    }
    thead tr {
      background: linear-gradient(90deg, #6366f1, #0ea5e9);
    }
    th {
      padding: 0.75rem 1rem;
      text-align: left;
      font-weight: 600;
      color: #fff;
      white-space: nowrap;
    }
    td {
      padding: 0.65rem 1rem;
      border-bottom: 1px solid rgba(255,255,255,0.05);
      color: #cbd5e1;
    }
    tbody tr:hover { background: rgba(99,102,241,0.07); }
    tbody tr:last-child td { border-bottom: none; }

    /* ── Error box ── */
    .error-box {
      background: rgba(239,68,68,0.1);
      border: 1px solid rgba(239,68,68,0.35);
      border-radius: 8px;
      padding: 1rem 1.2rem;
      color: #fca5a5;
      font-size: 0.88rem;
    }

    /* ── Footer ── */
    footer {
      text-align: center;
      padding: 2rem;
      color: #475569;
      font-size: 0.78rem;
      border-top: 1px solid rgba(99,102,241,0.1);
    }
  </style>
</head>
<body>
  <header>
    <span class="header-icon">📊</span>
    <div>
      <h1>Athena Orders Dashboard</h1>
      <p>ITCS-6190 Assignment 3 · AWS Serverless Data Pipeline · Database: <strong>{{ database }}</strong></p>
    </div>
  </header>

  <main>
    {% for item in results %}
    <div class="card">
      <div class="card-header">
        <h2>{{ item.title }}</h2>
        <p>{{ item.description }}</p>
      </div>
      <div class="card-body">
        {% if item.error %}
          <div class="error-box">⚠️ {{ item.error }}</div>
        {% else %}
          <table>
            <thead>
              <tr>{% for col in item.header %}<th>{{ col }}</th>{% endfor %}</tr>
            </thead>
            <tbody>
              {% for row in item.rows %}
              <tr>{% for cell in row %}<td>{{ cell }}</td>{% endfor %}</tr>
              {% endfor %}
            </tbody>
          </table>
        {% endif %}
      </div>
    </div>
    {% endfor %}
  </main>

  <footer>
    Powered by Amazon Athena · AWS Glue · Amazon S3 · Flask on EC2
  </footer>
</body>
</html>
"""


# ── Flask route ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    results = []
    for item in QUERIES:
        header, data = run_athena_query(item["query"])
        if header is None:
            results.append({
                "title":       item["title"],
                "description": item["description"],
                "error":       data,         # data holds the error string
                "header":      None,
                "rows":        None,
            })
        else:
            results.append({
                "title":       item["title"],
                "description": item["description"],
                "error":       None,
                "header":      header,
                "rows":        data,
            })

    return render_template_string(
        PAGE_TEMPLATE,
        results=results,
        database=ATHENA_DATABASE,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
