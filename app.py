"""
Sales Analytics Dashboard
=========================
Interactive Dash + Plotly dashboard for the sales_dashboard_task dataset.

Run:
    python app.py
    -> open http://127.0.0.1:8050
"""

import re
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "sales_dashboard_task.csv"

CATEGORY_COLORS = {
    "Electronics": "#4f46e5",
    "Furniture": "#f59e0b",
    "Accessories": "#0ea5e9",
    "Stationery": "#ec4899",
}
PAYMENT_COLORS = ["#4f46e5", "#0ea5e9", "#f59e0b", "#10b981"]
REGION_COLOR = "#4f46e5"
UNITS_COLOR = "#f59e0b"

PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}
CHART_LAYOUT = dict(
    template="plotly_white",
    margin=dict(l=10, r=10, t=10, b=10),
    font=dict(family="Inter, Segoe UI, sans-serif", size=12, color="#475569"),
    hoverlabel=dict(bgcolor="white", font_size=12, bordercolor="#e2e8f0"),
)


# ----------------------------------------------------------------------------
# 1. Data loading & transformation (Pandas)
# ----------------------------------------------------------------------------
def load_data(path: Path = DATA_PATH) -> pd.DataFrame:
    """Load the CSV, parse dates and derive the Revenue column."""
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Revenue"] = df["Quantity"] * df["Unit_Price"]
    return df


df = load_data()

MIN_DATE, MAX_DATE = df["Date"].min().date(), df["Date"].max().date()
ALL_CATEGORIES = sorted(df["Category"].unique())
ALL_REGIONS = sorted(df["Region"].unique())


# ----------------------------------------------------------------------------
# 2. Formatting helpers
# ----------------------------------------------------------------------------
def money(value: float) -> str:
    return f"EGP {value:,.0f}"


def money_compact(value: float) -> str:
    if value >= 1_000_000:
        return f"EGP {value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"EGP {value / 1_000:.1f}K"
    return f"EGP {value:,.0f}"


def empty_figure(message: str = "No data for the selected filters") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=13, color="#94a3b8"),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(**CHART_LAYOUT, height=300)
    return fig


def apply_filters(categories, regions, start_date, end_date) -> pd.DataFrame:
    d = df.copy()
    if categories:
        d = d[d["Category"].isin(categories)]
    if regions:
        d = d[d["Region"].isin(regions)]
    if start_date:
        d = d[d["Date"] >= pd.to_datetime(start_date)]
    if end_date:
        d = d[d["Date"] <= pd.to_datetime(end_date)]
    return d


def render_rich(text: str) -> list:
    """Turn `<b>...</b>` markup into Dash components without escaping HTML."""
    parts = []
    for chunk in re.split(r"(<b>.*?</b>)", text):
        if not chunk:
            continue
        if chunk.startswith("<b>") and chunk.endswith("</b>"):
            parts.append(html.B(chunk[3:-4]))
        else:
            parts.append(chunk)
    return parts


# ----------------------------------------------------------------------------
# 3. Figures
# ----------------------------------------------------------------------------
def monthly_revenue_figure(d: pd.DataFrame) -> go.Figure:
    if d.empty:
        return empty_figure()

    monthly = (
        d.set_index("Date")
        .resample("MS")
        .agg(revenue=("Revenue", "sum"), units=("Quantity", "sum"), orders=("Order_ID", "count"))
    )
    labels = monthly.index.strftime("%b %y")
    full_months = monthly.index.strftime("%B %Y")

    fig = go.Figure(
        go.Scatter(
            x=labels,
            y=monthly["revenue"],
            mode="lines+markers",
            line=dict(color=REGION_COLOR, width=3, shape="spline"),
            marker=dict(size=8, color="white", line=dict(width=2, color=REGION_COLOR)),
            fill="tozeroy",
            fillcolor="rgba(79, 70, 229, 0.08)",
            customdata=list(zip(monthly["units"], monthly["orders"], full_months)),
            hovertemplate=(
                "<b>%{customdata[2]}</b><br>"
                "Revenue: EGP %{y:,.0f}<br>"
                "Units: %{customdata[0]}<br>"
                "Orders: %{customdata[1]}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        **CHART_LAYOUT,
        height=320,
        showlegend=False,
        hovermode="x unified",
        yaxis=dict(title=None, tickprefix="EGP ", separatethousands=True, gridcolor="#eef2f7", zeroline=False),
        xaxis=dict(type="category", tickmode="array", tickvals=labels, ticktext=labels,
                   showgrid=False, showline=True, linecolor="#e2e8f0"),
    )
    return fig


def category_figure(d: pd.DataFrame) -> go.Figure:
    if d.empty:
        return empty_figure()

    cat = (
        d.groupby("Category")
        .agg(revenue=("Revenue", "sum"), units=("Quantity", "sum"))
        .sort_values("revenue", ascending=False)
    )
    colors = [CATEGORY_COLORS.get(c, "#94a3b8") for c in cat.index]

    fig = go.Figure(
        go.Bar(
            x=cat.index,
            y=cat["revenue"],
            marker=dict(color=colors, cornerradius=6),
            customdata=cat[["units"]].values,
            text=[money_compact(v) for v in cat["revenue"]],
            textposition="outside",
            textfont=dict(size=11, color="#64748b"),
            hovertemplate=(
                "<b>%{x}</b><br>Revenue: EGP %{y:,.0f}<br>Units: %{customdata[0]}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        **CHART_LAYOUT,
        height=320,
        showlegend=False,
        bargap=0.45,
        yaxis=dict(tickprefix="EGP ", separatethousands=True, gridcolor="#eef2f7", zeroline=False),
        xaxis=dict(showgrid=False),
    )
    return fig


def payment_figure(d: pd.DataFrame) -> go.Figure:
    if d.empty:
        return empty_figure()

    pay = d["Payment_Method"].value_counts()

    fig = go.Figure(
        go.Pie(
            labels=pay.index,
            values=pay.values,
            hole=0.58,
            marker=dict(colors=PAYMENT_COLORS, line=dict(color="white", width=2)),
            textinfo="percent",
            textfont=dict(size=12, color="white"),
            hovertemplate="<b>%{label}</b><br>%{value} orders (%{percent})<extra></extra>",
            sort=False,
        )
    )
    fig.update_layout(
        **CHART_LAYOUT,
        height=320,
        legend=dict(orientation="h", yanchor="bottom", y=-0.18, x=0.5, xanchor="center"),
        annotations=[
            dict(
                text=f"<b>{len(d)}</b><br><span style='font-size:11px;color:#94a3b8'>orders</span>",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=20, color="#0f172a"),
            )
        ],
    )
    return fig


def top_products_figure(d: pd.DataFrame) -> go.Figure:
    if d.empty:
        return empty_figure()

    top = (
        d.groupby("Product")
        .agg(revenue=("Revenue", "sum"), units=("Quantity", "sum"))
        .nlargest(5, "revenue")
        .sort_values("revenue")
    )
    shades = ["#c7d2fe", "#a5b4fc", "#818cf8", "#6366f1", "#4f46e5"][-len(top):]

    fig = go.Figure(
        go.Bar(
            x=top["revenue"],
            y=top.index,
            orientation="h",
            marker=dict(color=shades, cornerradius=6),
            customdata=top[["units"]].values,
            text=[money_compact(v) for v in top["revenue"]],
            textposition="outside",
            textfont=dict(size=11, color="#64748b"),
            cliponaxis=False,
            hovertemplate=(
                "<b>%{y}</b><br>Revenue: EGP %{x:,.0f}<br>Units: %{customdata[0]}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        **CHART_LAYOUT,
        height=320,
        showlegend=False,
        bargap=0.45,
        xaxis=dict(tickprefix="EGP ", separatethousands=True, showgrid=True, gridcolor="#eef2f7",
                   zeroline=False, rangemode="tozero", range=[0, top["revenue"].max() * 1.24]),
        yaxis=dict(showgrid=False, tickfont=dict(size=12, color="#334155")),
    )
    return fig


def region_figure(d: pd.DataFrame) -> go.Figure:
    if d.empty:
        return empty_figure()

    reg = (
        d.groupby("Region")
        .agg(revenue=("Revenue", "sum"), units=("Quantity", "sum"), orders=("Order_ID", "count"))
        .sort_values("revenue", ascending=False)
    )

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=reg.index,
            y=reg["revenue"],
            name="Revenue",
            marker=dict(color=REGION_COLOR, cornerradius=6, opacity=0.9),
            customdata=reg[["orders"]].values,
            hovertemplate=(
                "<b>%{x}</b><br>Revenue: EGP %{y:,.0f}<br>Orders: %{customdata[0]}<extra></extra>"
            ),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=reg.index,
            y=reg["units"],
            name="Units sold",
            mode="lines+markers",
            yaxis="y2",
            line=dict(color=UNITS_COLOR, width=2.5),
            marker=dict(size=8, color="white", line=dict(width=2, color=UNITS_COLOR)),
            hovertemplate="<b>%{x}</b><br>Units: %{y}<extra></extra>",
        )
    )
    fig.update_layout(
        **CHART_LAYOUT,
        height=320,
        bargap=0.5,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=1, xanchor="right"),
        yaxis=dict(title="Revenue (EGP)", tickprefix="EGP ", separatethousands=True,
                   gridcolor="#eef2f7", zeroline=False),
        yaxis2=dict(overlaying="y", side="right", showgrid=False, rangemode="tozero",
                    tickfont=dict(color=UNITS_COLOR), tickformat=",.0f"),
        xaxis=dict(showgrid=False),
    )
    return fig


# ----------------------------------------------------------------------------
# 4. KPIs & business insights (all derived from the filtered data)
# ----------------------------------------------------------------------------
def kpi_values(d: pd.DataFrame) -> list:
    total_rev = d["Revenue"].sum()
    total_qty = int(d["Quantity"].sum())
    total_orders = len(d)

    if d.empty:
        return [
            ("Total Revenue", "EGP 0", "no orders in range", "#e2e8f0"),
            ("Units Sold", "0", "no orders in range", "#e2e8f0"),
            ("Total Orders", "0", "no orders in range", "#e2e8f0"),
            ("Top Region", "—", "no orders in range", "#e2e8f0"),
        ]

    by_region = d.groupby("Region")["Revenue"].sum().sort_values(ascending=False)
    top_region, top_region_rev = by_region.index[0], by_region.iloc[0]
    share = top_region_rev / total_rev * 100

    return [
        ("Total Revenue", money_compact(total_rev), money(total_rev), "#4f46e5"),
        ("Units Sold", f"{total_qty:,}", f"across {total_orders} orders", "#0ea5e9"),
        ("Total Orders", f"{total_orders}", f"avg {money_compact(total_rev / total_orders)} / order", "#f59e0b"),
        ("Top Region", top_region, f"{money_compact(top_region_rev)} · {share:.1f}% of revenue", "#10b981"),
    ]


def build_insights(d: pd.DataFrame) -> list:
    if d.empty:
        return ["No orders match the current filters — widen the period, category or region."]

    total_rev = d["Revenue"].sum()
    total_qty = d["Quantity"].sum()
    insights = []

    cat = d.groupby("Category").agg(revenue=("Revenue", "sum"), units=("Quantity", "sum"))
    cat_rev = cat["revenue"].sort_values(ascending=False)
    cat_units = cat["units"].sort_values(ascending=False)

    # 1. Revenue concentration in a category
    top_cat = cat_rev.index[0]
    if len(cat_rev) == 1:
        insights.append(
            f"Only <b>{top_cat}</b> is in scope: {money(total_rev)} from {total_qty} units "
            f"across {len(d)} orders (average unit price {money(total_rev / total_qty)})."
        )
    else:
        cat_share = cat_rev.iloc[0] / total_rev * 100
        unit_share = cat.loc[top_cat, "units"] / total_qty * 100
        insights.append(
            f"<b>{top_cat}</b> drives <b>{cat_share:.1f}%</b> of revenue "
            f"({money(cat_rev.iloc[0])}) from only {unit_share:.1f}% of the units sold — "
            "revenue is highly dependent on a few high-ticket items."
        )

    # 2. Single-product dependency
    prod = d.groupby("Product").agg(revenue=("Revenue", "sum"), orders=("Order_ID", "count"))
    top_prod = prod["revenue"].idxmax()
    prod_share = prod.loc[top_prod, "revenue"] / total_rev * 100
    if len(prod) == 1:
        insights.append(
            f"All revenue in this view comes from <b>{top_prod}</b> "
            f"({money(prod.loc[top_prod, 'revenue'])} across {int(prod.loc[top_prod, 'orders'])} orders) — "
            "a single product with no diversification."
        )
    else:
        insights.append(
            f"<b>{top_prod}</b> alone generates <b>{prod_share:.1f}%</b> of total revenue across "
            f"{int(prod.loc[top_prod, 'orders'])} orders. Losing a couple of large {top_prod} deals "
            "would hit the top line immediately — a real concentration risk."
        )

    # 3. Volume vs. value gap
    if len(cat_rev) >= 2:
        low_rev_cat = cat_rev.index[-1]
        low_share = cat_rev.iloc[-1] / total_rev * 100
        low_unit_share = cat.loc[low_rev_cat, "units"] / total_qty * 100
        insights.append(
            f"<b>{low_rev_cat}</b> accounts for {low_unit_share:.0f}% of the units but just "
            f"<b>{low_share:.1f}%</b> of revenue — bundling low-value items with high-ticket "
            "products is the fastest way to lift basket size."
        )

    # 4. Regional gap: revenue leader vs. volume leader
    reg = d.groupby("Region").agg(revenue=("Revenue", "sum"), units=("Quantity", "sum"))
    reg_rev = reg["revenue"].sort_values(ascending=False)
    if len(reg_rev) >= 2:
        leader = reg_rev.index[0]
        trailer = reg_rev.index[-1]
        vol_leader = reg["units"].idxmax()
        vol_rank = list(reg_rev.index).index(vol_leader) + 1
        if vol_leader == leader:
            insights.append(
                f"<b>{leader}</b> leads on both revenue ({money_compact(reg_rev.iloc[0])}, "
                f"{reg_rev.iloc[0] / total_rev * 100:.1f}%) and volume, while <b>{trailer}</b> "
                f"is the weakest market ({money_compact(reg_rev.iloc[-1])}) — the clearest growth gap."
            )
        else:
            insights.append(
                f"<b>{leader}</b> leads on revenue ({money_compact(reg_rev.iloc[0])}, "
                f"{reg_rev.iloc[0] / total_rev * 100:.1f}%), but <b>{vol_leader}</b> sells the most "
                f"units ({int(reg.loc[vol_leader, 'units'])}) and still ranks #{vol_rank} — "
                "a pricing / product-mix opportunity."
            )

    # 5. Payment behaviour & monthly volatility
    pay = d["Payment_Method"].value_counts(normalize=True) * 100
    cashless = pay.get("Cash", 0) + pay.get("Wallet", 0)
    month = d.set_index("Date").resample("MS")["Revenue"].sum()
    month = month[month > 0]
    if len(month) >= 2:
        peak, trough = month.idxmax(), month.idxmin()
        insights.append(
            f"<b>{cashless:.0f}%</b> of orders are paid by Cash or Wallet, and revenue peaked in "
            f"<b>{peak:%B}</b> ({money_compact(month.max())}) versus a <b>{trough:%B}</b> low of "
            f"{money_compact(month.min())} — demand is lumpy and driven by large-ticket order timing."
        )

    return insights[:5]


# ----------------------------------------------------------------------------
# 5. Layout
# ----------------------------------------------------------------------------
def kpi_card(title: str, value: str, sub: str, accent: str) -> html.Div:
    return html.Div(
        className="kpi-card",
        style={"--accent": accent},
        children=[
            html.Div(title, className="kpi-title"),
            html.Div(value, className="kpi-value"),
            html.Div(sub, className="kpi-sub"),
        ],
    )


def chart_card(title: str, subtitle: str, graph_id: str, span: int) -> html.Div:
    return html.Div(
        className=f"chart-card span-{span}",
        children=[
            html.Div(
                className="chart-head",
                children=[
                    html.Div(title, className="chart-title"),
                    html.Div(subtitle, className="chart-sub"),
                ],
            ),
            dcc.Graph(id=graph_id, config=PLOTLY_CONFIG, style={"height": "320px"}),
        ],
    )


app = Dash(__name__, title="Sales Analytics Dashboard")
server = app.server

app.layout = html.Div(
    className="page",
    children=[
        # ---- Header ----
        html.Header(
            className="header",
            children=[
                html.Div(
                    children=[
                        html.H1("Sales Analytics Dashboard", className="header-title"),
                        html.P(
                            "Revenue, product mix and regional performance — FY 2025",
                            className="header-sub",
                        ),
                    ]
                ),
                html.Div(
                    className="header-meta",
                    children=[
                        html.Span("Data range", className="meta-label"),
                        html.Span(f"{MIN_DATE:%d %b %Y} – {MAX_DATE:%d %b %Y}", className="meta-value"),
                    ],
                ),
            ],
        ),

        # ---- Filters ----
        html.Div(
            className="filters",
            children=[
                html.Div(
                    className="filter-field",
                    children=[
                        html.Label("Product category", className="filter-label"),
                        dcc.Dropdown(
                            id="filter-category",
                            options=[{"label": c, "value": c} for c in ALL_CATEGORIES],
                            value=ALL_CATEGORIES,
                            multi=True,
                            clearable=False,
                            placeholder="All categories",
                            className="dropdown",
                        ),
                    ],
                ),
                html.Div(
                    className="filter-field",
                    children=[
                        html.Label("Region", className="filter-label"),
                        dcc.Dropdown(
                            id="filter-region",
                            options=[{"label": r, "value": r} for r in ALL_REGIONS],
                            value=ALL_REGIONS,
                            multi=True,
                            clearable=False,
                            placeholder="All regions",
                            className="dropdown",
                        ),
                    ],
                ),
                html.Div(
                    className="filter-field date-field",
                    children=[
                        html.Label("Analysis period", className="filter-label"),
                        dcc.DatePickerRange(
                            id="filter-date",
                            min_date_allowed=MIN_DATE,
                            max_date_allowed=MAX_DATE,
                            start_date=MIN_DATE,
                            end_date=MAX_DATE,
                            display_format="DD MMM YYYY",
                            minimum_nights=0,
                            updatemode="bothdates",
                            className="datepicker",
                        ),
                    ],
                ),
                html.Button("Reset filters", id="reset-btn", n_clicks=0, className="reset-btn"),
            ],
        ),

        # ---- KPI cards ----
        html.Div(id="kpi-row", className="kpi-row"),

        # ---- Charts ----
        html.Div(
            className="grid",
            children=[
                chart_card("Monthly revenue", "Trend across the selected period", "fig-monthly", 8),
                chart_card("Orders by payment method", "Share of orders", "fig-payment", 4),
                chart_card("Revenue by product category", "Contribution to total revenue", "fig-category", 7),
                chart_card("Top 5 products by revenue", "Best sellers, highest revenue first", "fig-top", 5),
                chart_card("Regional performance", "Revenue (bars) vs. units sold (line)", "fig-region", 7),
                html.Div(
                    className="chart-card span-5 insights-card",
                    children=[
                        html.Div(
                            className="chart-head",
                            children=[
                                html.Div("Business insights", className="chart-title"),
                                html.Div("Recalculated from the filtered data", className="chart-sub"),
                            ],
                        ),
                        html.Ol(id="insights-list", className="insights"),
                    ],
                ),
            ],
        ),

        html.Footer(
            className="footer",
            children=[
                html.Span("Built with Pandas · Plotly · Dash"),
                html.Span(id="footer-note", className="footer-note"),
            ],
        ),

        dcc.Store(id="dummy-store"),
    ],
)


# ----------------------------------------------------------------------------
# 6. Callbacks
# ----------------------------------------------------------------------------
@app.callback(
    Output("kpi-row", "children"),
    Output("fig-monthly", "figure"),
    Output("fig-payment", "figure"),
    Output("fig-category", "figure"),
    Output("fig-top", "figure"),
    Output("fig-region", "figure"),
    Output("insights-list", "children"),
    Output("footer-note", "children"),
    Input("filter-category", "value"),
    Input("filter-region", "value"),
    Input("filter-date", "start_date"),
    Input("filter-date", "end_date"),
)
def update_dashboard(categories, regions, start_date, end_date):
    d = apply_filters(categories, regions, start_date, end_date)

    kpis = [kpi_card(*k) for k in kpi_values(d)]
    insights = [html.Li(html.Span(render_rich(i), className="insight-text"), className="insight-item")
                for i in build_insights(d)]

    period = "—"
    if not d.empty:
        period = f"{d['Date'].min():%d %b %Y} – {d['Date'].max():%d %b %Y} · {len(d)} orders"
    elif start_date and end_date:
        period = f"{pd.to_datetime(start_date):%d %b %Y} – {pd.to_datetime(end_date):%d %b %Y} · 0 orders"

    return (
        kpis,
        monthly_revenue_figure(d),
        payment_figure(d),
        category_figure(d),
        top_products_figure(d),
        region_figure(d),
        insights,
        period,
    )


@app.callback(
    Output("filter-category", "value"),
    Output("filter-region", "value"),
    Output("filter-date", "start_date"),
    Output("filter-date", "end_date"),
    Input("reset-btn", "n_clicks"),
    prevent_initial_call=True,
)
def reset_filters(_):
    return ALL_CATEGORIES, ALL_REGIONS, MIN_DATE, MAX_DATE


if __name__ == "__main__":
    app.run(debug=False, port=8050)
