#%%
import pypsa
from pypsa.statistics import get_transmission_branches, get_transmission_carriers
from pypsa.plot import add_legend_semicircles, add_legend_lines, add_legend_patches
import numpy as np
import matplotlib.pyplot as plt
from cartopy import crs as ccrs
from pypsa_utils.helper import rename_techs
import yaml
#%%
config = yaml.safe_load(open("config.yaml"))
tech_colors = config["plotting"]["tech_colors"]
crs = ccrs.EqualEarth()
fig, ax = plt.subplots(figsize=figsize, subplot_kw={"projection": crs})
plot_carrier_map(network, ax, tech_colors, bus_carrier)

#%%

def plot_carrier_map(ax, n, bus_carrier, tech_colors, branch_threshold=3e2, bus_threshold=1e6, flow=False):
    n = n.copy()
    n.buses.x = n.buses.location.map(n.buses.x)
    n.buses.y = n.buses.location.map(n.buses.y)

    # bus sizes according to supply and demand
    s = n.statistics
    g = s.groupers
    df = s.energy_balance(nice_names=False, bus_carrier=bus_carrier, groupby=g.get_bus_and_carrier)
    transmission_carriers = get_transmission_carriers(n, bus_carrier=bus_carrier)
    df.drop(transmission_carriers, inplace=True)
    bus_sizes = (
        df.drop("EU", level="bus", errors="ignore")
        .groupby(level=["bus", "carrier"])
        .sum()
        .div(bus_threshold)
    )
    # filter supply or demand higher than than 2TWh
    filter_supply = bus_sizes.clip(lower=0).groupby("bus").sum()
    filter_demand = bus_sizes.clip(upper=0).groupby("bus").sum()
    filter_bus = filter_supply[(filter_supply > 2) | (filter_demand < -2)].index
    bus_sizes = bus_sizes[filter_bus]
    # drop individual entry below 1TWh
    bus_sizes = bus_sizes[bus_sizes.abs() >= 1]

    # get bus colors
    bus_colors = (
        bus_sizes.index.get_level_values(1)
        .unique()
        .to_series()
        .map(tech_colors)
        .groupby(rename_techs)
        .first()
    )
    bus_sizes = bus_sizes.groupby(
        [
            bus_sizes.index.get_level_values("bus"),
            bus_sizes.index.get_level_values("carrier").map(rename_techs),
        ]
    ).sum()

    # link cmap according to average loading
    transmission_branches = get_transmission_branches(n, bus_carrier=bus_carrier)
    branch_capacity_factors = s.capacity_factor(
        comps=["Line", "Link"], bus_carrier=bus_carrier, groupby=False, nice_names=False
    )
    branch_cmap = branch_capacity_factors.loc[transmission_branches]
    line_cmap = (
        branch_cmap.Line
        if "Line" in branch_cmap.index.get_level_values("component")
        else pd.Series()
    )
    link_cmap = branch_cmap.Link.groupby(lambda x: x.replace("-reversed", "")).max()

    # cmap norm and scalar mappable
    cmap = plt.cm.viridis
    params = (
        pd.concat([s for s in [line_cmap, link_cmap] if not s.empty])
        .describe()
        .loc[["min", "50%", "max"]]
        .round(1)
        .rename({"min": "vmin", "50%": "vcenter", "max": "vmax"})
    )
    norm = mcolors.TwoSlopeNorm(**params)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)

    # line and links widths according to capacity
    optimal_branch_capacity = s.optimal_capacity(
        comps=["Link", "Line"], groupby=False, nice_names=False
    )
    optimal_branch_capacity = optimal_branch_capacity.loc[transmission_branches]
    optimal_branch_capacity = optimal_branch_capacity[
        ~optimal_branch_capacity.index.get_level_values("name").str.contains("reversed")
    ]
    optimal_branch_capacity = optimal_branch_capacity[optimal_branch_capacity > branch_threshold]
    line_width = (
        optimal_branch_capacity.Line
        if "Line" in optimal_branch_capacity.index.get_level_values("component")
        else pd.Series()
    )
    link_width = (
        optimal_branch_capacity.Link
        if "Link" in optimal_branch_capacity.index.get_level_values("component")
        else pd.Series()
    )
    link_cmap = link_cmap.loc[link_width.index]

    if flow:
        # flow according to net transmission
        flow = n.statistics.transmission(groupby=False, bus_carrier=bus_carrier)
        flow_reversed_mask = flow.index.get_level_values("name").str.contains("reversed")
        flow_reversed = flow[flow_reversed_mask].rename(
            lambda x: x.replace("-reversed", "")
        )
        flow = flow[~flow_reversed_mask].subtract(flow_reversed, fill_value=0)
        flow = flow.loc[optimal_branch_capacity.index]
        flow = np.sign(flow) * 5e2
    else:
        flow = None

    max_bus_size = 0.8
    bus_size_factor = (bus_sizes.abs() / max_bus_size).fillna(0).max()
    max_line_width = 10 if bus_carrier == "H2" else 8
    line_width_factor = np.nanmax(
        [
            (line_width / max_line_width).fillna(0).max(),
            (link_width / max_line_width).fillna(0).max(),
        ]
    )

    n.plot(
        ax=ax,
        bus_sizes=bus_sizes / bus_size_factor,
        bus_split_circles=True,
        bus_colors=bus_colors,
        line_widths=line_width / line_width_factor,
        line_colors=line_cmap,
        line_cmap=cmap,
        line_norm=norm,
        link_widths=link_width / line_width_factor,
        link_colors=link_cmap,
        link_cmap=cmap,
        link_norm=norm,
        flow=flow,
        color_geomap=True,
    )

    if flow:
        ARROW_COLOR = (0.4, 0.4, 0.4)
        # PatchCollection [1] or [3] corresponds to flow which is not color coded
        ax.collections[1].set_array(None)
        ax.collections[1].set_fc(ARROW_COLOR)
        ax.collections[1].set_linewidth(0)
        if len(branch_cmap.index.get_level_values("component").unique()) == 2:
            ax.collections[3].set_array(None)
            ax.collections[3].set_fc(ARROW_COLOR)
            ax.collections[3].set_linewidth(0)

        cbar = plt.colorbar(
            sm,
            location="right",
            orientation="vertical",
            pad=0.004,
            shrink=0.2,
            anchor=(0, 0.33),
            ax=ax,
            extend="both",
            format=mpl.ticker.PercentFormatter(1),
            label="Average line loading",
        )

    unit = "{el}" if bus_carrier == "AC" else f"{{{bus_carrier}}}"
    # bus capacity legend
    add_legend_semicircles(
        ax,
        [
            1,
            -1,
            100 / bus_size_factor,
            300 / bus_size_factor,
            500 / bus_size_factor,
        ],
        ["Supply", "Demand", "100", "300", "500"],
        legend_kw=dict(
            title=f"Energy [TWh$_{unit}$]",
            labelspacing=1.1,
            bbox_to_anchor=(1, 0.68),
            loc="lower left",
            borderpad=0,
            alignment="left",
        ),
        patch_kw=dict(facecolor="lightgrey", edgecolor="k"),
    )

    # line width legend
    line_sizes = [10, 20, 50]
    pypsa.plot.add_legend_lines(
        ax,
        [s * 1e3 / line_width_factor for s in line_sizes],
        [f"{s}" for s in line_sizes],
        legend_kw=dict(
            title=f"Lines [GW$_{unit}$]",
            bbox_to_anchor=(1, 0.68),
            loc="upper left",
            borderpad=0,
            alignment="left",
        ),
        patch_kw=dict(color="lightgrey"),
    )

    # carrier color codes
    pypsa.plot.add_legend_patches(
        ax,
        colors=bus_colors,
        labels=bus_colors.index.values,
        legend_kw=dict(
            bbox_to_anchor=(0.5, 0), loc="upper center", ncol=3, borderpad=0
        ),
    )
# %%
