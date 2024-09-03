import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from cartopy import crs as ccrs
import folium
from folium import plugins
import geopandas as gpd
from shapely.geometry import LineString


FIELDS={"Line": ["bus0", "bus1", "s_nom", "length", "build_year"],"Link": ["bus0", "bus1", "p_nom", "length", "build_year"], "Bus": ["v_nom", "country", "carrier"]}
ALIASES={"Line": ["Bus 0", "Bus 1", "Capacity (MVA)", "Length (km)", "Commissioned"], "Link": ["Bus 0", "Bus 1", "P (nom.) (MW)", "Length (km)", "Commissioned"], "Bus": ["Nominal voltage (kV)", "Country", "Carrier"]}

# Define tooltip that is shown when hovering over lines and links
def _tooltip(fields, aliases):
    _tooltip = folium.GeoJson_tooltip(
        fields=fields,
        aliases=aliases,
        labels = True,
        localize = True,
        sticky = False
    )
    return _tooltip

def _get_linestring_from_buscoords(n):
    for branch in ["Line", "Link"]:
        n.df(branch).loc[:,"geometry"] = n.df(branch).apply(lambda x: LineString([n.buses.loc[x.bus0, ["x", "y"]], n.buses.loc[x.bus1, ["x", "y"]]]), axis = 1)

# Create popup content function
def _popup_content(feature, fields, aliases):
    content = ""
    for field, alias in zip(fields, aliases):
        content += f"{alias} {feature['properties'][field]}<br>"
    return folium.Popup(content)
    
# define crs
crs = 4326


#create maps
def plot_interactive_grid(n, tiles="CartoDB positron"):
    """
    Function to plot an interactive map of a PyPSA network.
    Parameters:
    n: PyPSA network
    tiles: string, default "CartoDB positron"
    Returns:
    m: folium map
    """
    #get lines, links and buses as geodataframes
    _get_linestring_from_buscoords(n)
    lines= n.lines
    links= n.links.query("carrier=='DC'")
    buses= n.buses.query("carrier=='AC'")
    
    lines_gdf = gpd.GeoDataFrame(lines, geometry = "geometry", crs=crs)
    links_gdf = gpd.GeoDataFrame(links, geometry = "geometry", crs=crs)
    buses_gdf = gpd.GeoDataFrame(buses, geometry = gpd.points_from_xy(buses.x, buses.y), crs=crs)


    # Determine the center of the map
    loc_x = np.array([n.buses.x.min(), n.buses.x.max()]).mean()
    loc_y = np.array([n.buses.y.min(), n.buses.y.max()]).mean()
    
    # Create the folium map using the center coordinates
    m = folium.Map(location=(loc_y, loc_x), zoom_start=3, tiles = tiles)


    # Add the feature groups to the map
    fg_lines = folium.FeatureGroup(name = f"Lines").add_to(m)
    fg_links = folium.FeatureGroup(name = f"Links").add_to(m)
    fg_buses = folium.FeatureGroup(name = f"Buses").add_to(m)


    # Define the callback function for the FastMarkerCluster
    callback = (
        'function (row) {'
        'var circle = L.circle(new L.LatLng(row[0], row[1]), {color: "black",  radius: 1500});'
        'return circle};'
        )

    # Add the layer control to the map
    folium.LayerControl(collapsed = False).add_to(m)

    # Add the buses to map
    folium.plugins.FastMarkerCluster(
        buses[["y", "x"]].values.tolist(), 
        callback = callback, disableClusteringAtZoom = 5,
        fill_opacity = 0.1
        ).add_to(fg_buses)



    # Add the lines and links to the map
    folium.GeoJson(
        lines_gdf, 
        style_function = lambda feature: {
            "color": "red",
            "weight": 2,
            "opacity": 0.8,
            },
        _tooltip = _tooltip(fields=FIELDS["Line"], aliases=ALIASES["Line"]),
        popup=lambda feature: _popup_content(feature=feature, fields=FIELDS["Line"], aliases=ALIASES["Line"]),
        ).add_to(fg_lines)


    folium.GeoJson(
        links_gdf, 
        style_function = lambda feature: {
            "color": "green",
            "weight": 2,
            "opacity": 0.8,
            },
        _tooltip = _tooltip(fields=FIELDS["Link"], aliases=ALIASES["Link"]),
        popup=lambda feature: _popup_content(feature=feature, fields=FIELDS["Link"], aliases=ALIASES["Link"]),
        ).add_to(fg_links)
    return m