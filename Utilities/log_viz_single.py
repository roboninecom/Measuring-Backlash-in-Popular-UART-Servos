import argparse
import pandas as pd
import numpy as np
import plotly.express as px

HOME = 2047

parser = argparse.ArgumentParser()
parser.add_argument("csv_path")
args = parser.parse_args()

df = pd.read_csv(args.csv_path)
df["timestamp"] = pd.to_datetime(df["timestamp"])

# --------------------------
# Generate t_sec (seconds since test start)
# --------------------------
if "timestamp" in df.columns and pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
    df["t_sec"] = (df["timestamp"] - df["timestamp"].iloc[0]).dt.total_seconds()
else:
    df["t_sec"] = np.arange(len(df))  # fallback if timestamps are bad

plot_df = pd.DataFrame({
    "Time (seconds)": df["t_sec"],
    "Motor Target": df['target pos (5)'],
    "Motor Position": df['pos (5)'],
})

long = plot_df.melt(id_vars="Time (seconds)", var_name="Series", value_name="Position")
fig = px.line(long, x="Time (seconds)", y="Position", color="Series", title="Motor Target/Position")
fig.update_traces(mode="lines")
fig.update_layout(
    hovermode="x unified",
    plot_bgcolor="#ffffff",
)

fig.update_xaxes(
    showgrid=True,
    gridcolor="gray",
    gridwidth=1,
    griddash="dot"
)

fig.update_yaxes(
    showgrid=True,
    gridcolor="gray",
    gridwidth=1,
    griddash="dot"
)

fig.show()