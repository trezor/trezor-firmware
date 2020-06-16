import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

df = pd.read_csv("src/.memprofile", sep=";")

fig = go.Figure()

fig.add_trace(go.Scatter(x=df.trace, y=df.mem_total, name="mem_total"))
fig.add_trace(go.Scatter(x=df.trace, y=df.mem_current, name="mem_current"))
fig.add_trace(go.Scatter(x=df.trace, y=df.mem_peak, name="mem_peak"))

fig.show()
