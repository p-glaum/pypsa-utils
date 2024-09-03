# this is just a preliminary version, because currently pypsa topo does not support plots in jupyter notebooks
import pypsatopo
from IPython.display import SVG

def plot_topo(network, buses, neighbors):
    with tempfile.NamedTemporaryFile(delete=True) as temp_file:
        temp_file_name = temp_file.name
        pypsatopo.generate(network, bus_filter=buses, neighbourhood=neighbors, file_output=temp_file_name)
        graph=SVG(temp_file_name)
    return graph