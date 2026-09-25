import os
os.environ["OMP_NUM_THREADS"] = "1"
import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA
import plotly.express as px
import plotly.graph_objects as go

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Driver Performance Analytics",
    page_icon="🚚",
    layout="wide"
)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🚚 Amazon Delivery Driver Performance Analytics")
st.markdown(
    "Upload a weekly scorecard CSV to run K-Means clustering and "
    "DBSCAN anomaly detection across your driver fleet."
)
st.divider()

# ── Feature list (handles both Week 4 and Week 9 column name variants) ────────
FEATURE_CANDIDATES = [
    ["Total Score", "Delivered Parcels", "Delivery success",
     "DPMO concession", "Photo on delivery",
     "Contact Compliance", "Customer Escalation", "Customer Feedback"],
    ["Total Score", "Delivered Parcels", "Delivery Success",
     "DPMO concessions", "Photo on delivery",
     "Contact Compliance", "Customer Escalation", "Customer Feedback"],
]

# ── Data loading ──────────────────────────────────────────────────────────────
st.sidebar.header("📂 Upload Data")
uploaded = st.sidebar.file_uploader(
    "Upload your scorecard CSV", type=["csv"],
    help="Upload any weekly scorecard CSV file"
)

# Load sample data if nothing uploaded
if uploaded is not None:
    df_raw = pd.read_csv(uploaded)
    week_label = uploaded.name
else:
    df_raw = pd.read_csv("sample_scorecard.csv")
    week_label = "Week 9 (Sample Data)"
    st.sidebar.info("Using sample Week 9 data. Upload your own CSV to analyse a different week.")

st.sidebar.markdown(f"**Loaded:** {week_label}")

# ── Preprocessing ─────────────────────────────────────────────────────────────
df_raw.columns = df_raw.columns.str.strip()

# Detect which feature set matches
features = None
for candidate in FEATURE_CANDIDATES:
    if all(c in df_raw.columns for c in candidate):
        features = candidate
        break

if features is None:
    st.error(
        "Could not find expected columns. "
        f"Found: {df_raw.columns.tolist()}"
    )
    st.stop()

df = df_raw[features + ["Transporter ID", "Status"]].copy()

# Convert all feature columns to numeric (handles % symbols)
for col in features:
    if df[col].dtype == object or df[col].astype(str).str.contains("%").any():
        df[col] = (
            df[col].astype(str)
            .str.replace("%", "", regex=True)
            .str.replace(",", "", regex=True)
            .str.strip()
            .replace("", np.nan)
            .replace("nan", np.nan)
            .astype(float)
        )

df = df.dropna(subset=features)

# Normalise
scaler = StandardScaler()
df_scaled_arr = scaler.fit_transform(df[features])
df_scaled = pd.DataFrame(df_scaled_arr, columns=features, index=df.index)

# K-Means
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
df["Cluster"] = kmeans.fit_predict(df_scaled_arr)
df["Cluster Label"] = df["Cluster"].map({
    0: "Cluster 0", 1: "Cluster 1", 2: "Cluster 2"
})

# PCA
pca = PCA(n_components=2)
pca_result = pca.fit_transform(df_scaled_arr)
df["PCA1"] = pca_result[:, 0]
df["PCA2"] = pca_result[:, 1]

# DBSCAN
dbscan = DBSCAN(eps=1.5, min_samples=5)
df["Anomaly Raw"] = dbscan.fit_predict(df_scaled_arr)
df["Anomaly"] = df["Anomaly Raw"].apply(
    lambda x: "🚨 Anomaly" if x == -1 else "✅ Normal"
)

# Performance category from Total Score
df["Performance"] = pd.cut(
    df["Total Score"],
    bins=[0, 60, 80, 200],
    labels=["🔴 Low", "🟡 Medium", "🟢 High"]
)

# ── KPI Summary ───────────────────────────────────────────────────────────────
st.subheader("📊 Fleet Overview")

total = len(df)
anomalies = (df["Anomaly Raw"] == -1).sum()
low_perf = (df["Performance"] == "🔴 Low").sum()
avg_score = df["Total Score"].mean()
top_driver = df.loc[df["Total Score"].idxmax(), "Transporter ID"]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Drivers", total)
c2.metric("Avg Total Score", f"{avg_score:.1f}")
c3.metric("🚨 Anomalies", anomalies)
c4.metric("🔴 Low Performers", low_perf)
c5.metric("🏆 Top Driver", top_driver[:10] + "…")

st.divider()

# ── Performance Distribution ──────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Performance Category Distribution")
    perf_counts = df["Performance"].value_counts().reset_index()
    perf_counts.columns = ["Category", "Count"]
    fig_perf = px.bar(
        perf_counts, x="Category", y="Count",
        color="Category",
        color_discrete_map={
            "🔴 Low": "#ef4444",
            "🟡 Medium": "#f59e0b",
            "🟢 High": "#10b981"
        },
        title="Drivers by Performance Category"
    )
    fig_perf.update_layout(showlegend=False)
    st.plotly_chart(fig_perf, use_container_width=True)

with col_right:
    st.subheader("Status Distribution")
    status_counts = df_raw["Status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Count"]
    fig_status = px.pie(
        status_counts, names="Status", values="Count",
        title="Driver Status Breakdown",
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    st.plotly_chart(fig_status, use_container_width=True)

st.divider()

# ── K-Means Clustering ────────────────────────────────────────────────────────
st.subheader("🎯 K-Means Clustering (PCA Visualisation)")

cluster_filter = st.selectbox(
    "Filter by cluster",
    options=["All Clusters", "Cluster 0", "Cluster 1", "Cluster 2"]
)

if cluster_filter == "All Clusters":
    plot_df = df
else:
    cluster_num = int(cluster_filter.split()[-1])
    plot_df = df[df["Cluster"] == cluster_num]

fig_kmeans = px.scatter(
    plot_df, x="PCA1", y="PCA2",
    color="Cluster Label",
    hover_data=["Transporter ID", "Total Score", "Status"],
    title="K-Means Clustering — Each point is a driver",
    color_discrete_sequence=px.colors.qualitative.Bold
)
fig_kmeans.update_traces(marker=dict(size=10, opacity=0.8))
st.plotly_chart(fig_kmeans, use_container_width=True)

with st.expander("What does this chart mean?"):
    st.markdown(
        "Each dot is a driver. K-Means groups drivers into 3 clusters based on "
        "their performance across all 8 KPIs. Drivers in the same cluster have "
        "similar performance patterns. PCA reduces the 8 dimensions down to 2 "
        "so we can plot it — the axes do not have a direct meaning but the "
        "distance between points does."
    )

st.divider()

# ── DBSCAN Anomaly Detection ──────────────────────────────────────────────────
st.subheader("🚨 DBSCAN Anomaly Detection")

show_only_anomalies = st.checkbox("Show only anomalies")

anomaly_df = df[df["Anomaly"] == "🚨 Anomaly"] if show_only_anomalies else df

if anomaly_df.empty:
    st.success("No anomalies detected in this dataset.")
else:
    fig_dbscan = px.scatter(
        anomaly_df, x="PCA1", y="PCA2",
        color="Anomaly",
        hover_data=["Transporter ID", "Total Score", "Status"],
        title="DBSCAN Anomaly Detection",
        color_discrete_map={
            "🚨 Anomaly": "#ef4444",
            "✅ Normal": "#6b7280"
        }
    )
    fig_dbscan.update_traces(marker=dict(size=10, opacity=0.8))
    st.plotly_chart(fig_dbscan, use_container_width=True)

    if anomalies > 0:
        st.warning(f"**{anomalies} driver(s) flagged as anomalies** — these drivers sit outside normal cluster patterns and warrant closer review.")
        anomaly_table = df[df["Anomaly Raw"] == -1][
            ["Transporter ID", "Status", "Total Score", "Customer Feedback", "Contact Compliance"]
        ].reset_index(drop=True)
        st.dataframe(anomaly_table, use_container_width=True)

with st.expander("What does anomaly detection mean?"):
    st.markdown(
        "DBSCAN identifies drivers whose performance pattern does not fit any "
        "cluster. These are not necessarily the worst performers — they are the "
        "most unusual ones. A driver scoring extremely high in one area but very "
        "low in another might be flagged even if their total score looks fine."
    )

st.divider()

# ── KPI Bar Charts ────────────────────────────────────────────────────────────
st.subheader("📈 KPI Breakdown Across All Drivers")

kpi_options = [f for f in features if f != "Total Score" and f != "Delivered Parcels" and f != "DPMO concession" and f != "DPMO concessions"]
selected_kpi = st.selectbox("Select KPI to visualise", options=kpi_options)

fig_kpi = px.bar(
    df.sort_values(selected_kpi, ascending=False),
    x="Transporter ID", y=selected_kpi,
    color="Performance",
    color_discrete_map={
        "🔴 Low": "#ef4444",
        "🟡 Medium": "#f59e0b",
        "🟢 High": "#10b981"
    },
    title=f"{selected_kpi} — All Drivers",
    labels={"Transporter ID": "Driver ID"}
)
fig_kpi.update_layout(xaxis_tickangle=-90)
st.plotly_chart(fig_kpi, use_container_width=True)

st.divider()

# ── Full Data Table ───────────────────────────────────────────────────────────
st.subheader("📋 Full Driver Data")

show_anomalies_only = st.checkbox("Show anomalies only", key="table_filter")
display_df = df[df["Anomaly Raw"] == -1] if show_anomalies_only else df

display_cols = ["Transporter ID", "Status", "Total Score",
                "Performance", "Anomaly", "Cluster Label",
                "Customer Feedback", "Contact Compliance", "Customer Escalation"]

st.dataframe(
    display_df[display_cols].reset_index(drop=True),
    use_container_width=True
)

st.caption(
    "Built by Meschac Goredji — MSc Computer Science, University of Kent. "
    "Analysis uses K-Means clustering and DBSCAN anomaly detection on real "
    "operational delivery scorecard data."
)
