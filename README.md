# Amazon DSP Driver Performance Dashboard

A Streamlit dashboard that turns Amazon's weekly DSP scorecards into early warnings. It shows which delivery associates (DAs) are sliding before it shows up in their tier, what to talk to them about, and when a drop is really a depot-wide change rather than the drivers.

**Live app:** https://amazon-delivery-dashboard-dadt4ftmsbv29om9si2uib.streamlit.app/

> **About the data:** everything in this repo is generated demo data. Every Transporter ID starts with `DEMO`, and no real driver data is included. See [Data and privacy](#data-and-privacy).

---

## The problem

DSP managers get a scorecard each week with a total score and a tier (Fantastic Plus, Fantastic, Great, Fair, Poor) for every DA. That's a snapshot. It has three gaps:

- **Tiers only show a problem after it has happened.** A DA who drops from 95 to 80 over six weeks still shows as Great every week, so nobody looks until they reach Fair or Poor.
- **A tier doesn't say what to fix.** "Poor" could be concessions, photos, contact compliance or customer feedback.
- **One week can't tell a driver problem from a depot problem.** If most of the team drops on the same metric at once, it's usually a new rule or a change at the depot, not 30 separate 1-1s.

## What it does

The app has two pages.

### 1. Trends Over Time (main feature)

Upload several weekly scorecard CSVs at once.

- **Trend per DA.** Each DA is labelled Improving, Declining, Flat or Up and down.
- **Sliding but still look OK.** DAs who are Declining but still on Fantastic Plus, Fantastic or Great. These are the ones a weekly scorecard alone would miss.
- **Coaching flags.** A plain English note per DA, for example: *"DEMOQ2Y9V86WZS still shows as Great, but has dropped 19 points over 6 weeks. Biggest drop: Contact Compliance, down 5.1 points. Concessions are up too. Recommend a 1-1 this week."* Improving DAs are flagged as worth recognising.
- **Fleet-wide alert.** When most DAs drop on the same metric in the same week, it says so and suggests one briefing for everyone.
- **One DA, week by week.** A chart of any DA on any metric, against the fleet average.

### 2. Single-week analysis

Upload one week's scorecard to group DAs with similar performance patterns and flag unusual ones.

---

## How it works

### Trends (Trends Over Time page)

| Step | What happens |
|---|---|
| Load | Each CSV becomes one week. The week number comes from the file name (`week_07.csv`, `Wk7.csv`), or the upload order if there isn't one. |
| Clean | Column names are stripped and old spellings unified (`Delivery success` becomes `Delivery Success`). `%` signs and commas are removed. Blanks become missing values, never 0. |
| Combine | All weeks are stacked into one long table: one row per DA per week. |
| Trend | For each DA, a straight line of best fit (`numpy.polyfit`) is drawn through their total score across the weeks. The slope is their points per week. |
| Label | Fewer than 3 weeks: **Not enough weeks**. Slope of -2 or lower: **Declining**. +2 or higher: **Improving**. Otherwise, if scores sit more than 7 points off the line on average (standard deviation of the residuals): **Up and down**. Otherwise **Flat**. Checks run in that order. |

A line of best fit is used instead of "latest minus first" so one unusual week at either end can't swing the result. The thresholds are settings at the top of the file, so they can be made stricter or looser in one place.

### Coaching flags

- **Biggest drop** compares a DA's first and latest week on four percentage metrics (Delivery Success, Photo on delivery, Contact Compliance, Customer Feedback) and names the one that fell most.
- **Concessions** are mentioned separately when DPMO rises by 1,500 or more, as DPMO is on a different scale to the percentages.
- **Fleet-wide shift:** if at least half of the DAs who appear in both of the last two weeks dropped 3 points or more on the same metric, it's flagged as fleet-wide. That metric is then left out of individual DAs' "biggest drop", so nobody is blamed for something that happened to everyone.

### Single-week analysis (main page)

- **Features:** Total Score, Delivered Parcels, Delivery Success, DPMO concessions, Photo on delivery, Contact Compliance, Customer Escalation and Customer Feedback, scaled with `StandardScaler`.
- **Blank cells:** scorecards sometimes leave a metric blank. Those DAs are kept, and the gap is filled with the fleet median for the models only.
- **K-Means** groups DAs into 3 clusters with similar patterns. **PCA** reduces the 8 features to 2 so the clusters can be plotted.
- **DBSCAN** flags DAs who don't fit any group. How close counts as "near" (`eps`) is set from each week's data: the distance within which 85% of DAs have at least 4 other DAs nearby (5 points including themselves, which is how DBSCAN counts). A fixed value flagged far too many DAs on some weeks and none on others.

---

## Data and privacy

The first version of this dashboard was built on real scorecard data while I worked at a DSP. That data is not in this repo.

The demo data is generated by [`make_mock_data.py`](make_mock_data.py):

- 40 fake DAs over 6 weeks, all with `DEMO` IDs
- Each DA has a hidden trend (improving, declining, slipping slowly, flat or up and down) and one weak metric, so the dashboard has real patterns to find
- In week 6, nearly every DA drops on Photo on delivery, to show the fleet-wide alert
- A fixed random seed (42), so it produces the same data every time

To use real scorecards, upload them in the app. Nothing is stored after you close the page.

---

## Project structure

```
app.py                          Single-week analysis (main page)
pages/1_Trends_Over_Time.py     Multi-week trends and coaching flags
make_mock_data.py               Generates the demo data
data/mock_week_01-06.csv        Six weeks of demo scorecards
sample_scorecard.csv            Copy of the latest demo week, used by app.py
requirements.txt
```

## Tech stack

| Tool | Used for |
|---|---|
| Python | Core language |
| Pandas, NumPy | Cleaning, reshaping, trend lines |
| Scikit-learn | K-Means, DBSCAN, PCA, StandardScaler, nearest neighbours |
| Plotly | Interactive charts |
| Streamlit | The app, file uploads and multi-page layout |

## Run it locally

```bash
git clone https://github.com/meschac12/amazon-delivery-dashboard
cd amazon-delivery-dashboard
pip install -r requirements.txt
streamlit run app.py
```

To regenerate the demo data: `python make_mock_data.py`

---

## Background

I spotted the need for this while working as a delivery associate at an Amazon DSP with 52 drivers. Managers had the weekly scorecard totals but no easy way to see patterns over time or across metrics. I built the first version on my own initiative, outside my role, and have since rebuilt it with multi-week tracking, coaching flags and generated demo data.

*Built by Meschac Goredji, MSc Computer Science, University of Kent.*
