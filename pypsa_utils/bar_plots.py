import matplotlib.pyplot as plt


def plot_carrier_statistics(
    n,
    bus_carrier: str,
    metric: str,
    ax: plt.Axes = None,
    nice_names: bool = True,
    stacked: bool = True,
    show_legend: bool = True,
    threshold: float = 1e3,
):
    """
    Plot barplot for a given network and metric.

    Parameters
    ----------
    n : pypsa.Network
        The PyPSA network object containing the data.
    bus_carrier : str
        Bus carrier to plot.
    metric : str
        The metric to be evaluated and plotted. This should be a valid method of the statistics object.
    ax : matplotlib.axes.Axes, optional
        The matplotlib axes object to plot on. If None, the current axes will be used.
    nice_names : bool, optional
        If True, names from network.carrier.nice_names are taken. Default is True.
    stacked : bool, optional
        If True, the bar plot will be stacked. Default is True.
    show_legend : bool, optional
        If True, the legend will be shown. Default is True.
    threshold : float, optional
        The threshold value to filter out small values. Default is 1e3.

    Returns
    -------
    None
    """

    n = n.copy()
    s = n.statistics
    s.set_parameters(round=2, nice_names=False)
    ds = eval("s." + metric)(bus_carrier=bus_carrier).groupby(level="carrier").sum()
    ds = ds[ds.abs() > threshold]
    colors = ds.index.map(n.carriers.color)
    if nice_names:
        ds.index = n.carriers.nice_name.loc[ds.index]
    if ax is None:
        ax = plt.gca()
    df = ds.to_frame(metric)
    df.T.plot.bar(ax=ax, color=colors.values, stacked=stacked, legend=show_legend)
