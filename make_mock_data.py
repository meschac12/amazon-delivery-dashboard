"""
Generates fake weekly Amazon DSP scorecards for demos.

No real driver data is used. Every Transporter ID starts with DEMO so it can
never be mistaken for a real Amazon ID.

Each driver gets a hidden "quality" level and a trend (improving, declining,
flat or up-and-down). Their weekly metrics are built from that, so the
multi-week view has real stories in it to find.

Run:  python make_mock_data.py
Out:  data/mock_week_01.csv ... data/mock_week_06.csv
      sample_scorecard.csv (a copy of the latest week, used by app.py)
"""

import os
import random
import string

import numpy as np
import pandas as pd

SEED = 42          # same seed = same data every time you run it
N_DRIVERS = 40
N_WEEKS = 6
OUT_DIR = "data"

rng = np.random.default_rng(SEED)
random.seed(SEED)

COLUMNS = [
    "Transporter ID", "Status", "Total Score", "Delivered Parcels",
    "Delivery Success", "DPMO concessions", "Photo on delivery",
    "Contact Compliance", "Customer Escalation", "Customer Feedback",
]


def fake_id():
    chars = string.ascii_uppercase + string.digits
    return "DEMO" + "".join(random.choices(chars, k=10))


def status_from_score(score):
    # Demo thresholds, roughly how the tiers feel on a real scorecard
    if score >= 93:
        return "Fantastic Plus"
    if score >= 85:
        return "Fantastic"
    if score >= 75:
        return "Great"
    if score >= 60:
        return "Fair"
    return "Poor"


def pct(x):
    return f"{x:.2f}%"


# ── Build the driver roster ───────────────────────────────────────────────────
trends = (["improving"] * 8 + ["declining"] * 8 +
          ["flat"] * 18 + ["volatile"] * 6)
random.shuffle(trends)

drivers = []
for i in range(N_DRIVERS):
    drivers.append({
        "id": fake_id(),
        "quality": rng.uniform(0.55, 0.97),   # 0 = struggling, 1 = elite
        "trend": trends[i],
        "volume": rng.integers(450, 1500),     # typical parcels per week
        # each driver has one area they tend to slip on
        "weak_spot": random.choice(["contact", "photo", "feedback", "dpmo"]),
    })


def quality_this_week(d, week):
    step = week / (N_WEEKS - 1)                # 0.0 in week 1, 1.0 in week 6
    q = d["quality"]
    if d["trend"] == "improving":
        q += 0.30 * step
    elif d["trend"] == "declining":
        q -= 0.35 * step
    elif d["trend"] == "volatile":
        q += rng.choice([-0.2, 0.2])
    q += rng.normal(0, 0.03)                   # normal week-to-week noise
    return float(np.clip(q, 0.05, 1.0))


def make_week(week):
    rows = []
    for d in drivers:
        q = quality_this_week(d, week)
        weak = d["weak_spot"]

        parcels = int(d["volume"] * rng.uniform(0.85, 1.1))
        success = 100 - (1 - q) * rng.uniform(4, 12)
        photo = 100 - (1 - q) * rng.uniform(2, 20) - (15 * (1 - q) if weak == "photo" else 0)
        feedback = 100 - (1 - q) * rng.uniform(10, 25) - (10 * (1 - q) if weak == "feedback" else 0)
        dpmo = int(max(0, (1 - q) * rng.uniform(0, 9000) + (6000 * (1 - q) if weak == "dpmo" else 0)))
        escalations = int(rng.random() < (1 - q) * 0.4) + int(rng.random() < (1 - q) * 0.15)

        if rng.random() < 0.06:
            contact = ""                       # real scorecards sometimes leave this blank
        else:
            contact_val = 100 - (1 - q) * rng.uniform(0, 30) - (35 * (1 - q) if weak == "contact" else 0)
            contact = pct(float(np.clip(contact_val, 0, 100)))

        score = int(np.clip(round(q * 100 + rng.normal(0, 3)), 20, 100))

        rows.append({
            "Transporter ID": d["id"],
            "Status": status_from_score(score),
            "Total Score": score,
            "Delivered Parcels": parcels,
            "Delivery Success": pct(float(np.clip(success, 70, 100))),
            "DPMO concessions": dpmo,
            "Photo on delivery": pct(float(np.clip(photo, 25, 100))),
            "Contact Compliance": contact,
            "Customer Escalation": escalations,
            "Customer Feedback": pct(float(np.clip(feedback, 60, 100))),
        })
    return pd.DataFrame(rows, columns=COLUMNS)


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    for w in range(N_WEEKS):
        df = make_week(w)
        path = os.path.join(OUT_DIR, f"mock_week_{w + 1:02d}.csv")
        df.to_csv(path, index=False)
        print(f"Wrote {path}  (avg score {df['Total Score'].mean():.1f})")

    # the app's default demo file is the latest week
    df.to_csv("sample_scorecard.csv", index=False)
    print("Wrote sample_scorecard.csv (copy of the latest week)")
