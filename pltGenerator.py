fig, ax = plt.subplots(figsize=(19.2, 10.8), layout='constrained')
ax.set_aspect('equal')
ax.set_xlim(min_lon, max_lon)
ax.set_ylim(min_lat, max_lat)
ax.set_xticks([])
ax.set_yticks([])
ctx.add_basemap(ax, source=ctx.providers.Esri.WorldImagery, crs='EPSG:4326', attribution=False)

# Save just the basemap as an image
plt.savefig("basemap.png", dpi=100, bbox_inches='tight', pad_inches=0)
plt.close()

for step in range(0,20):

    print(step)

    """
    fig, ax = plt.subplots(figsize=(18, 10), layout='constrained')
    ax.set_aspect('equal')

    # Set map bounds
    ax.set_xlim(min_lon, max_lon)
    ax.set_ylim(min_lat, max_lat)

    # Add basemap - using Web Mercator (EPSG:3857) for proper projection
    ctx.add_basemap(ax,
                    source=ctx.providers.Esri.WorldImagery,
                    crs='EPSG:4326',  # Our coordinates are in WGS84
                    attribution=False)
                    """
    fig, ax = plt.subplots(figsize=(19.2, 10.8), layout='constrained')
    img = plt.imread("basemap.png")
    ax.imshow(img, extent=[min_lon, max_lon, min_lat, max_lat])
    ax.set_xlim(min_lon, max_lon)
    ax.set_ylim(min_lat, max_lat)


    for igc in igcs:

        time_step = 30
        lats = igc.lats[::time_step]
        lons = igc.lons[::time_step]
        alts = igc.alts[::time_step]

        alts_norm = ((alts - 2000) / (np.max(alts) - 2000))

        ax.plot(lons[:step + 1], lats[:step + 1],
                color='red' if igc.name == "PG" else 'blue',
                # linestyle=line_styles[0],
                linewidth=2,
                # label=labels[0],
                alpha=0.3)


        ax.plot(lons[step], lats[step],
                marker='o',
                color='red' if igc.name == "PG" else 'blue',
                markersize=5 + alts_norm[step] * 20,
                # label=labels[i],
                alpha=0.75,
                markeredgecolor='white',
                markeredgewidth=2)

    plt.savefig("frames/" + str(step).zfill(3) + ".png", dpi=100)
    #plt.show()
    plt.close()