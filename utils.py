# Utils for data cleaning and vis.ipynb and predictions_vis.ipynb


import branca

'''
Id to pollutant mapping
'''
map_id_to_pollutant = {
    1: "SO2",
    5: "PM10",
    6: "NOy",
    7: "O3",
    10: "CO",
    20: "C6H6",
    6001: "PM2.5"
}


'''
Define colormaps to map pollution values directly to a health index
[Good,  Fair,   Moderate,   Poor,   Very Poor,  Extremely Poor]
[min,   green,  yellow,     red,    purple,     max]
'''
BOUNDARY_COLORS = ["green", "green", "yellow", "red", "purple", "purple"]
BOUNDARY_HEALTH = ["Good", "Fair", "Moderate", "Poor", "Very poor", "Extremely poor"]

cmap_boundaries = {
    "PM2.5": [5, 11, 33, 71, 116,  140],
    "PM10": [15, 31, 83, 158, 233, 270],
    "O3": [60, 81, 111, 141, 171, 180],
    "NOy": [10, 18, 43, 81, 126, 150],
    "SO2": [20, 31, 83, 158, 233, 275],
    "CO": [0, 0, 5, 7, 10, 10],
    "Pb": [0, 0, 0.25, 0.35, 0.5],
    "C6H6": [0, 0, 2, 3.5, 5, 5]
}
cmaps = {
    pollutant: branca.colormap.LinearColormap(
        colors=BOUNDARY_COLORS, 
        index=boundaries,
        vmin=boundaries[0], vmax=boundaries[-1],
        caption=f"{pollutant} ug.m-3",
    )
    for pollutant, boundaries in cmap_boundaries.items()
}

# health_boundaries = {
    
# }