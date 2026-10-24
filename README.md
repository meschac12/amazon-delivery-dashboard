# Amazon Delivery Driver Performance Analytics

An interactive data science dashboard built to analyse delivery driver performance across a fleet of 52 associates. Built using real operational scorecard data from an Amazon DSP (Delivery Service Partner), this tool applies unsupervised machine learning to surface performance patterns and flag unusual behaviour that would not be visible from raw scores alone.

**Live app:** [Driver Performance Dashboard](https://your-streamlit-link-here)

---

## What it does

Amazon DSP managers receive weekly scorecard CSVs covering metrics like delivery success rate, customer feedback, contact compliance, and DPMO concessions. Manually reviewing 52 rows to identify who needs support and who is underperforming is time-consuming and prone to missing patterns across multiple KPIs at once.

This dashboard automates that analysis:

- Groups drivers into performance clusters so managers can see at a glance which drivers share similar patterns
- Flags anomalous drivers whose behaviour does not fit any cluster, even if their total score looks acceptable
- Breaks down individual KPIs visually so the source of a performance issue is immediately clear
- Works with any weekly scorecard CSV, not just one specific week

---

## Techniques used

**K-Means Clustering**
Groups the 52 drivers into 3 clusters based on their performance across 8 KPIs simultaneously. PCA (Principal Component Analysis) reduces the 8-dimensional feature space to 2 dimensions so the clusters can be visualised in a scatter plot. Each point is a driver, and proximity means similar performance patterns.

**DBSCAN Anomaly Detection**
Identifies drivers whose performance profile sits outside all clusters. These are not necessarily the lowest scorers. A driver who performs unusually well in one area but unusually poorly in another can be flagged even if their total score looks normal. DBSCAN does not require you to specify the number of anomalies in advance.

**Preprocessing**
Raw scorecard data includes percentage symbols, inconsistent column naming across weeks, and missing values. The pipeline strips and normalises all inputs before scaling with StandardScaler, making the model robust to week-on-week format variations.

---

## Tech stack

| Tool | Purpose |
|------|---------|
| Python | Core language |
| Pandas / NumPy | Data cleaning and transformation |
| Scikit-learn | K-Means, DBSCAN, PCA, StandardScaler |
| Plotly | Interactive charts and scatter plots |
| Streamlit | Dashboard interface and CSV upload |

---

## How to run it locally

```bash
git clone https://github.com/meschac12/amazon-delivery-dashboard
cd amazon-delivery-dashboard
pip install -r requirements.txt
streamlit run app.py
```

The app loads with sample Week 9 data by default. Upload any weekly scorecard CSV using the sidebar to run the analysis on a different week.

---

## Project background

I identified the need for this tool while working as a Delivery Associate at an Amazon DSP managing 52 drivers. No tooling existed to analyse performance patterns across the fleet beyond raw scorecard totals. I built this independently, outside of my core role, using live operational data to give management a clearer picture of driver behaviour.

---

*Built by Meschac Goredji )*
