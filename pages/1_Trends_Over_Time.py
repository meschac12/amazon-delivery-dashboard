"""
Phase 1: multi-week tracking.

Upload several weekly scorecard CSVs and see whether each DA is improving,
declining or flat. The key view is "sliding but still looks OK": DAs whose
tier this week looks fine but whose score has been dropping for weeks.
"""

import glob
import os
import re

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Trends Over Time", page_icon="📈", layout="wide")

st.title("📈 Trends Over Time")
st.markdown(
    "Upload several weekly scorecards to see which DAs are improving, "
    "declining or holding steady, before it shows up in their tier."
)
st.divider()

# ── Settings ──────────────────────────────────────────────────────────────────
# A DA must appear in at least this many weeks to get a trend
MIN_WEEKS = 3
# Points per week the score has to move to count as improving or declining
TREND_THRESHOLD = 2.0
# Week-to-week wobble (in points) above which a flat DA is "up and down"
VOLATILE_THRESHOLD = 7.0
# Tiers that already get attention, so a slide hidden behind these is the risk
OK_TIERS = ["Fantastic Plus", "Fantastic", "Great"]

# Scorecards have used two spellings for some columns over time
RENAME = {
    "Delivery success": "Delivery Success",
    "DPMO concession": "DPMO concessions",
}
METRICS = [
    "Total Score", "Delivery Success", "DPMO concessions", "Photo on delivery",
    "Contact Compliance", "Customer Escalation", "Customer Feedback",
]


# ── Loading and cleaning ──────────────────────────────────────────────────────
def week_number(filename, fallback):
    """Pull a week number out of a filename like 'week_07.csv' or 'Wk7 scorecard.csv'."""
    match = re.search(r"(?:week|wk)[\s_-]*(\d+)", filename, re.IGNORECASE)
    return int(match.group(1)) if match else fallback


def clean(df):
    df = df.copy()
    df.columns = df.columns.str.strip()
    df = df.rename(columns=RENAME)
    for col in METRICS:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace("%", "").str.replace(",", "").str.strip(),
                errors="coerce",
            )
    return df


st.sidebar.header("📂 Weekly Scorecards")
uploads = st.sidebar.file_uploader(
    "Upload two or more weekly CSVs",
    type=["csv"],
    accept_multiple_files=True,
    help="Put the week number in each file name (for example week_07.csv) so they line up in order.",
)

frames = []
if uploads:
    for i, f in enumerate(sorted(uploads, key=lambda u: u.name)):
        frames.append((week_number(f.name, i + 1), clean(pd.read_csv(f))))
else:
    demo_files = sorted(glob.glob("data/mock_week_*.csv"))
    for i, path in enumerate(demo_files):
        frames.append((week_number(os.path.basename(path), i + 1), clean(pd.read_csv(path))))
    st.sidebar.info("Showing six weeks of demo data (fake DAs). Upload your own weekly CSVs to replace it.")

if len(frames) < 2:
    st.warning("Upload at least two weekly scorecards to see trends.")
    st.stop()

missing = [w for w, d in frames if "Transporter ID" not in d.columns or "Total Score" not in d.columns]
if missing:
    st.error(f"Weeks {missing} are missing a 'Transporter ID' or 'Total Score' column.")
    st.stop()

long = pd.concat([d.assign(Week=w) for w, d in frames], ignore_index=True)
long = long.dropna(subset=["Total Score"])
weeks = sorted(long["Week"].unique())
latest = weeks[-1]
st.sidebar.markdown(f"**Loaded:** {len(weeks)} weeks (week {weeks[0]} to week {latest})")


# ── Trend for each DA ─────────────────────────────────────────────────────────
def describe_trend(group):
    group = group.sort_values("Week")
    scores = group["Total Score"].to_numpy()
    week_nums = group["Week"].to_numpy()
    n = len(scores)

    if n >= 2:
        slope, intercept = np.polyfit(week_nums, scores, 1)
        wobble = np.std(scores - (slope * week_nums + intercept))
    else:
        slope, wobble = 0.0, 0.0

    if n < MIN_WEEKS:
        trend = "Not enough weeks"
    elif slope <= -TREND_THRESHOLD:
        trend = "Declining"
    elif slope >= TREND_THRESHOLD:
        trend = "Improving"
    elif wobble >= VOLATILE_THRESHOLD:
        trend = "Up and down"
    else:
        trend = "Flat"

    last = group.iloc[-1]
    return pd.Series({
        "Trend": trend,
        "Points per week": round(slope, 1),
        "First score": int(scores[0]),
        "Latest score": int(scores[-1]),
        "Change": int(scores[-1] - scores[0]),
        "Weeks seen": n,
        "Latest status": last.get("Status", ""),
        "In latest week": last["Week"] == latest,
    })


summary = long.groupby("Transporter ID").apply(describe_trend).reset_index()

TREND_COLOURS = {
    "Improving": "#10b981",
    "Flat": "#6b7280",
    "Up and down": "#f59e0b",
    "Declining": "#ef4444",
    "Not enough weeks": "#cbd5e1",
}

# ── Headline numbers ──────────────────────────────────────────────────────────
current = summary[summary["In latest week"]]
hidden = current[(current["Trend"] == "Declining") & (current["Latest status"].isin(OK_TIERS))]
fleet_avg = long.groupby("Week")["Total Score"].mean()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("DAs this week", len(current))
c2.metric("Fleet avg score", f"{fleet_avg.iloc[-1]:.1f}",
          delta=f"{fleet_avg.iloc[-1] - fleet_avg.iloc[0]:+.1f} since week {weeks[0]}")
c3.metric("Improving", int((current["Trend"] == "Improving").sum()))
c4.metric("Declining", int((current["Trend"] == "Declining").sum()))
c5.metric("Sliding but look OK", len(hidden))

st.divider()

# ── The early warning list ────────────────────────────────────────────────────
st.subheader("⚠️ Sliding but still look OK")
st.markdown(
    "These DAs are on a good tier this week, so they would not stand out on the "
    "scorecard. Their score has been dropping week after week, so this is the "
    "time to have a conversation, before they reach Fair or Poor."
)
if hidden.empty:
    st.success("No DAs are sliding while still on a good tier.")
else:
    st.dataframe(
        hidden.sort_values("Points per week")[
            ["Transporter ID", "Latest status", "First score", "Latest score", "Change", "Points per week"]
        ].reset_index(drop=True),
        hide_index=True,
        use_container_width=True,
    )

st.divider()

# ── Phase 2: coaching flags ───────────────────────────────────────────────────
# Percentage metrics where higher is better. We compare these to find the one
# that fell most, as they're all on the same 0 to 100 scale.
PCT_METRICS = ["Delivery Success", "Photo on delivery", "Contact Compliance", "Customer Feedback"]
# A rise in DPMO this big (per million parcels) gets mentioned too
DPMO_RISE_ALERT = 1500
# A fleet-wide shift: this share of DAs dropping this much on one metric in a week
SHIFT_SHARE = 0.5
SHIFT_DROP = 3.0


def biggest_drop(da_rows, skip=()):
    """The percentage metric that fell most between a DA's first and latest week.
    Metrics in `skip` are left out, because the whole fleet dropped on them."""
    da_rows = da_rows.sort_values("Week")
    first, last = da_rows.iloc[0], da_rows.iloc[-1]
    drops = {}
    for col in PCT_METRICS:
        if col in skip:
            continue
        if col in da_rows.columns and pd.notna(first[col]) and pd.notna(last[col]):
            drops[col] = first[col] - last[col]
    if not drops:
        return None, 0.0
    worst = max(drops, key=drops.get)
    return worst, drops[worst]


def coaching_flag(row, da_rows, skip=()):
    """Turn one DA's numbers into a sentence a manager can act on."""
    da = row["Transporter ID"]
    weeks_n = row["Weeks seen"]
    status = row["Latest status"]
    metric, fall = biggest_drop(da_rows, skip)

    if row["Trend"] == "Declining":
        if status in OK_TIERS:
            opening = f"**{da}** still shows as {status}, but has dropped {abs(row['Change'])} points over {weeks_n} weeks."
        else:
            opening = f"**{da}** has dropped {abs(row['Change'])} points over {weeks_n} weeks and is now on {status}."
        reason = f" Biggest drop: {metric}, down {fall:.1f} points." if metric and fall > 0 else ""

        first_dpmo = da_rows.sort_values("Week")["DPMO concessions"].iloc[0] if "DPMO concessions" in da_rows else None
        last_dpmo = da_rows.sort_values("Week")["DPMO concessions"].iloc[-1] if "DPMO concessions" in da_rows else None
        dpmo = ""
        if first_dpmo is not None and pd.notna(first_dpmo) and pd.notna(last_dpmo) and last_dpmo - first_dpmo >= DPMO_RISE_ALERT:
            dpmo = f" Concessions are up too (DPMO {int(first_dpmo):,} to {int(last_dpmo):,})."
        return "warning", opening + reason + dpmo + " Recommend a 1-1 this week."

    if row["Trend"] == "Improving":
        return "success", (f"**{da}** is up {row['Change']} points over {weeks_n} weeks, now {status}. "
                           "Worth recognising, and a good candidate for more days.")
    if row["Trend"] == "Up and down":
        return "info", (f"**{da}** swings a lot week to week (latest {status}). "
                        "Check whether it follows certain routes or days.")
    return None, None


def fleet_shifts(long_df):
    """Metrics where most DAs dropped at the same time in the latest week."""
    if len(weeks) < 2:
        return []
    prev, now = weeks[-2], weeks[-1]
    a = long_df[long_df["Week"] == prev].set_index("Transporter ID")
    b = long_df[long_df["Week"] == now].set_index("Transporter ID")
    both = a.index.intersection(b.index)
    shifts = []
    for col in PCT_METRICS:
        if col not in long_df.columns:
            continue
        change = (b.loc[both, col] - a.loc[both, col]).dropna()
        if len(change) == 0:
            continue
        dropped = (change <= -SHIFT_DROP).sum()
        if dropped / len(change) >= SHIFT_SHARE:
            shifts.append((col, int(dropped), len(change), change.mean()))
    return shifts


st.subheader("📝 Coaching flags")
st.markdown("Plain English notes for this week, so you know who to talk to and what about.")

shifts = fleet_shifts(long)
shifted_cols = [s[0] for s in shifts]
for col, dropped, total, avg in shifts:
    st.error(
        f"**Fleet-wide: {dropped} of {total} DAs dropped on {col} this week** "
        f"(average {avg:+.1f} points). When this many drop together it's usually not the drivers. "
        "Check for a change at the depot, a new rule or a scorecard change, and consider one "
        "briefing for everyone instead of separate 1-1s."
    )

flag_order = {"Declining": 0, "Up and down": 1, "Improving": 2}
flag_rows = current[current["Trend"].isin(flag_order)]
flag_rows = flag_rows.assign(
    o=flag_rows["Trend"].map(flag_order),
    hidden_first=~flag_rows["Latest status"].isin(OK_TIERS),   # sliding-but-OK DAs at the very top
).sort_values(["o", "hidden_first", "Points per week"])

show_types = st.multiselect(
    "Show flags for", options=["Declining", "Up and down", "Improving"],
    default=["Declining", "Improving"],
)

shown = 0
for _, r in flag_rows[flag_rows["Trend"].isin(show_types)].iterrows():
    kind, text = coaching_flag(r, long[long["Transporter ID"] == r["Transporter ID"]], skip=shifted_cols)
    if kind:
        getattr(st, kind)(text)
        shown += 1
if shown == 0:
    st.success("No coaching flags this week.")

st.divider()

# ── Fleet picture ─────────────────────────────────────────────────────────────
left, right = st.columns(2)

with left:
    st.subheader("Fleet average score by week")
    fig_avg = px.line(
        fleet_avg.reset_index(), x="Week", y="Total Score", markers=True,
        labels={"Total Score": "Average total score"},
    )
    fig_avg.update_xaxes(dtick=1)
    fig_avg.update_yaxes(range=[0, 100])  # full scale, so small wobbles don't look like a crash
    st.plotly_chart(fig_avg, use_container_width=True)

with right:
    st.subheader("DAs by trend")
    counts = current["Trend"].value_counts().reindex(TREND_COLOURS.keys()).dropna().reset_index()
    counts.columns = ["Trend", "DAs"]
    fig_counts = px.bar(counts, x="Trend", y="DAs", color="Trend", color_discrete_map=TREND_COLOURS)
    fig_counts.update_layout(showlegend=False)
    st.plotly_chart(fig_counts, use_container_width=True)

st.divider()

# ── One DA, week by week ──────────────────────────────────────────────────────
st.subheader("🔍 One DA, week by week")

order = {"Declining": 0, "Up and down": 1, "Flat": 2, "Improving": 3, "Not enough weeks": 4}
picker = summary.assign(o=summary["Trend"].map(order)).sort_values(["o", "Points per week"])
labels = {
    row["Transporter ID"]: f'{row["Transporter ID"]}  ({row["Trend"]}, {row["Change"]:+d} pts)'
    for _, row in picker.iterrows()
}

col_a, col_b = st.columns([2, 1])
with col_a:
    options = list(labels.keys())
    # Open on the first "sliding but looks OK" DA, as that's the story to show
    start = options.index(hidden.sort_values("Points per week").iloc[0]["Transporter ID"]) if not hidden.empty else 0
    chosen = st.selectbox("Choose a DA (declining DAs are listed first)",
                          options=options, index=start, format_func=lambda x: labels[x])
with col_b:
    available = [m for m in METRICS if m in long.columns]
    metric = st.selectbox("Metric", options=available)

da = long[long["Transporter ID"] == chosen].sort_values("Week")
fleet_metric = long.groupby("Week")[metric].mean().reset_index()

fig_da = px.line(da, x="Week", y=metric, markers=True, hover_data=["Status"] if "Status" in da else None)
fig_da.add_scatter(x=fleet_metric["Week"], y=fleet_metric[metric], mode="lines",
                   name="Fleet average", line=dict(dash="dash", color="#9ca3af"))
fig_da.data[0].name = chosen
fig_da.data[0].showlegend = True
fig_da.update_xaxes(dtick=1)
fig_da.update_layout(legend=dict(orientation="h", y=-0.2))
st.plotly_chart(fig_da, use_container_width=True)

row = summary[summary["Transporter ID"] == chosen].iloc[0]
st.markdown(
    f"**Trend:** {row['Trend']} · **Total score:** {row['First score']} → {row['Latest score']} "
    f"({row['Change']:+d}) over {row['Weeks seen']} weeks · **Latest status:** {row['Latest status']}"
)

st.divider()

# ── Everyone ──────────────────────────────────────────────────────────────────
st.subheader("📋 All DAs")
trend_filter = st.multiselect("Show trends", options=list(TREND_COLOURS.keys()),
                              default=list(TREND_COLOURS.keys()))
table = summary[summary["Trend"].isin(trend_filter)]
st.dataframe(
    table.assign(o=table["Trend"].map(order)).sort_values(["o", "Points per week"])
    .drop(columns=["o", "In latest week"]).reset_index(drop=True),
        hide_index=True,
    use_container_width=True,
)

with st.expander("How is the trend worked out?"):
    st.markdown(
        f"For each DA the dashboard fits a straight line through their total score "
        f"across the weeks. If it goes down by {TREND_THRESHOLD:.0f} or more points a week "
        f"they are **Declining**, and up by {TREND_THRESHOLD:.0f} or more is **Improving**. "
        f"If the line is flat but the weekly scores jump around by more than "
        f"{VOLATILE_THRESHOLD:.0f} points, they are **Up and down**. A DA needs at least "
        f"{MIN_WEEKS} weeks of data to get a trend."
    )
