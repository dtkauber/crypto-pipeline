import time
import boto3
import pandas as pd
import streamlit as st
import plotly.express as px

REGION = "us-east-1"
DATABASE = "crypto_pipeline_db"
TABLE = "crypto_pipeline_processed_dtkauber"  # confirm this matches your actual table name
WORKGROUP = "crypto-pipeline-workgroup"

st.set_page_config(page_title="Crypto Pipeline Dashboard", layout="wide", page_icon="📊")

# --- Custom styling ---
st.markdown("""
    <style>
    .stMetric {
        background-color: #1e1e2e;
        border: 1px solid #333;
        border-radius: 10px;
        padding: 15px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 24px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🪙 Crypto Market Data Pipeline")
st.caption("Serverless AWS pipeline — ingested via Lambda, stored in S3, queried live with Athena")

@st.cache_data(ttl=300)
def run_athena_query(query: str) -> pd.DataFrame:
    client = boto3.client("athena", region_name=REGION)
    response = client.start_query_execution(QueryString=query, WorkGroup=WORKGROUP)
    query_id = response["QueryExecutionId"]

    while True:
        status = client.get_query_execution(QueryExecutionId=query_id)
        state = status["QueryExecution"]["Status"]["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(1)

    if state != "SUCCEEDED":
        reason = status["QueryExecution"]["Status"].get("StateChangeReason", "Unknown error")
        raise RuntimeError(f"Query {state}: {reason}")

    results = client.get_query_results(QueryExecutionId=query_id)
    columns = [col["Label"] for col in results["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]]
    rows = results["ResultSet"]["Rows"][1:]
    data = [[field.get("VarCharValue", "") for field in row["Data"]] for row in rows]
    return pd.DataFrame(data, columns=columns)

# --- Load data ---
df = run_athena_query(f"""
    SELECT name, symbol, market_cap_usd, current_price_usd,
           total_volume_usd, price_change_24h_pct
    FROM {DATABASE}.{TABLE}
    ORDER BY CAST(market_cap_usd AS DOUBLE) DESC
""")
for col in ["market_cap_usd", "current_price_usd", "total_volume_usd", "price_change_24h_pct"]:
    df[col] = pd.to_numeric(df[col])

# --- Top-line metrics ---
st.subheader("Market snapshot")
top_gainer = df.loc[df["price_change_24h_pct"].idxmax()]
top_loser = df.loc[df["price_change_24h_pct"].idxmin()]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total market cap tracked", f"${df['market_cap_usd'].sum()/1e9:,.1f}B")
m2.metric("Coins tracked", len(df))
m3.metric(f"Top gainer: {top_gainer['symbol']}", f"{top_gainer['price_change_24h_pct']:+.2f}%")
m4.metric(f"Top loser: {top_loser['symbol']}", f"{top_loser['price_change_24h_pct']:+.2f}%")

st.divider()

# --- Market cap treemap ---
st.subheader("Market cap distribution — top 20")
df_top20 = df.head(20)
fig_treemap = px.treemap(
    df_top20,
    path=[px.Constant("All coins"), "symbol"],
    values="market_cap_usd",
    color="price_change_24h_pct",
    color_continuous_scale="RdYlGn",
    color_continuous_midpoint=0,
    hover_data={"name": True, "current_price_usd": ":.2f"},
)
fig_treemap.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=400)
st.plotly_chart(fig_treemap, use_container_width=True)

# --- Two-column: bar chart + movers table ---
col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("Top 10 by market cap")
    fig_bar = px.bar(
        df.head(10),
        x="symbol",
        y="market_cap_usd",
        color="price_change_24h_pct",
        color_continuous_scale="RdYlGn",
        color_continuous_midpoint=0,
        labels={"market_cap_usd": "Market cap (USD)", "symbol": ""},
    )
    fig_bar.update_layout(height=380, coloraxis_showscale=False)
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    st.subheader("Biggest 24h movers")
    df_movers = df.reindex(df["price_change_24h_pct"].abs().sort_values(ascending=False).index).head(10)
    st.dataframe(
        df_movers[["name", "symbol", "price_change_24h_pct"]].style.format(
            {"price_change_24h_pct": "{:+.2f}%"}
        ).background_gradient(cmap="RdYlGn", subset=["price_change_24h_pct"], vmin=-10, vmax=10),
        use_container_width=True,
        hide_index=True,
        height=380,
    )

st.divider()

# --- Volume vs market cap scatter ---
st.subheader("Volume vs market cap")
fig_scatter = px.scatter(
    df.head(30),
    x="market_cap_usd",
    y="total_volume_usd",
    size="market_cap_usd",
    color="price_change_24h_pct",
    color_continuous_scale="RdYlGn",
    color_continuous_midpoint=0,
    hover_name="name",
    log_x=True,
    log_y=True,
    labels={"market_cap_usd": "Market cap (log)", "total_volume_usd": "24h volume (log)"},
)
fig_scatter.update_layout(height=420)
st.plotly_chart(fig_scatter, use_container_width=True)

# --- Full table, sortable ---
with st.expander("View full dataset"):
    st.dataframe(df, use_container_width=True, hide_index=True)

st.caption(f"Data cached for 5 minutes · {len(df)} assets · Source: CoinGecko via serverless AWS ETL pipeline")