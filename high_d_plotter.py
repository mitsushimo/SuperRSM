"""
Copyright Mitsuki Shimomura & Michigan Technological University, 2026.
"""

"""
This is the backend code for a software that achieves effective visualization of 
multidimensional data (i.e., with more than three dimensions) using multiple 
contour or surface plots with high user flexibility. 
"""

import numpy as np 
import matplotlib.pyplot as plt 
import seaborn as sns 

sns.set_theme(style="whitegrid")

def validate_multi_contour_inputs(X, Y, Z_array, label_array=None, scatter_array=None):
    """
    Validates the inputs for plot_multi_contour.
    Returns:
        tuple[bool, str | None]: (True, None) if valid, (False, "error message") if invalid.
    """
    try:
        X_np = np.asarray(X)
        Y_np = np.asarray(Y)
    except Exception as e:
        return False, f"X and Y must be array-like: {str(e)}"
    
    if X_np.ndim != 2 or Y_np.ndim != 2:
        return False, f"X and Y must be 2D arrays. Got X ndim: {X_np.ndim}, Y ndim: {Y_np.ndim}."
    
    if X_np.shape != Y_np.shape:
        return False, f"X and Y must have the exact same shape. Got X: {X_np.shape}, Y: {Y_np.shape}."
    
    ny, nx = X_np.shape
    
    try:
        m = len(Z_array)
        if m == 0:
            return False, "Z_array cannot be empty."
        n = len(Z_array[0])
    except Exception:
        return False, "Z_array must be a 2D grid (nested list or array) of 2D data arrays."
    
    for i in range(m):
        try:
            row_len = len(Z_array[i])
        except Exception:
            return False, f"Z_array row {i} is not a sequence."
        
        if row_len != n:
            return False, f"Z_array rows have inconsistent lengths. Row 0 has {n}, row {i} has {row_len}."
        
        for j in range(n):
            try:
                Z_ij = np.asarray(Z_array[i][j])
            except Exception:
                return False, f"Element at Z_array[{i}][{j}] cannot be converted to a NumPy array."
            
            if Z_ij.shape != (ny, nx):
                return False, f"Z_array[{i}][{j}] shape {Z_ij.shape} does not match X and Y shape {(ny, nx)}."
    
    if label_array is not None:
        try:
            if len(label_array) != m:
                return False, f"label_array must have {m} rows, matching Z_array's outer grid."
            for i in range(m):
                if len(label_array[i]) != n:
                    return False, f"label_array row {i} must have {n} columns, matching Z_array's outer grid."
        except Exception:
            return False, "label_array must be a 2D nested list or array matching the outer dimensions of Z_array."

    if scatter_array is not None:
        try:
            if len(scatter_array) != m:
                return False, f"scatter_array must have {m} rows, matching Z_array's outer grid."
            for i in range(m):
                if len(scatter_array[i]) != n:
                    return False, f"scatter_array row {i} must have {n} columns, matching Z_array's outer grid."
        except Exception:
            return False, "scatter_array must be a 2D nested list or array matching the outer dimensions of Z_array."
            
    return True, None


default_plot_settings = {
    "cmap": "plasma", # Colormap for filled contours
    "alpha": 0.85, # Transparency for filled contours
    "fill_levels":100, # Number of levels for filled contours
    "line_levels": 10, # Number of levels for contour lines
    "line_color": "white", # Color for contour lines
    "inline_color": "white", # Color for inline labels on contour lines
    "inline_fontsize": 9, # Font size for inline labels on contour lines
    "grid_color": "gray", # Color for grid lines
    "grid_linestyle": "--", # Linestyle for grid lines
    "inline_format": '%1.1f', # Format for inline labels on contour lines
    "uniform_cmap": True,  # If True, all subplots will share the same color scale based on the global min and max of Z_array
    "show_colorbar": False, # If True, displays a colorbar to the right of the subplots
    "colorbar_label": "", # Label for the colorbar
    "scatter_data": False, # If True, scatter-plots measurement data on top of contour plots
    "scatter_size": 30.0, # Marker size for scatter-plotted data
    "scatter_color_mode": "Fixed Color", # "Fixed Color" or "Output Value (Colormap)"
    "scatter_color": "white", # Marker face color for scatter-plotted data when mode is "Fixed Color"
    "scatter_cmap": "plasma", # Colormap for scatter-plotted data when mode is "Output Value (Colormap)"
    "scatter_edgecolor": "black", # Marker edge color for scatter-plotted data
    "scatter_marker": "o", # Marker style for scatter-plotted data
    "show_plot": True # If True, calls plt.show() at the end
}

def plot_multi_contour(X, Y, Z_array, label_array=None, title="Multi-Contour Visualization", xlabel="X", ylabel="Y", plot_settings=None, scatter_array=None):
    """
    Plots multiple contour plots for given Z values over a grid defined by X and Y.

    Parameters:
    - X: 2D array of x-coordinates (such as meshgrid output).
    - Y: 2D array of y-coordinates (such as meshgrid output).
    - Z_array: A 1D or 2D array of 2D arrays representing the Z values corresponding to X and Y coordinates. 
    - label_array: An optional array for labels for each contour plot. 
    - title: Title of the plot.
    - xlabel: Label for the x-axis.
    - ylabel: Label for the y-axis.
    - plot_settings: Dictionary of plot configuration settings.
    - scatter_array: Optional 2D grid (m x n) of (x_points, y_points) or (x_points, y_points, z_points) tuples to scatter-plot on each subplot.
    """
    is_valid, error_msg = validate_multi_contour_inputs(X, Y, Z_array, label_array, scatter_array)
    if not is_valid:
        raise ValueError(error_msg)

    if plot_settings is None: 
        plot_settings = default_plot_settings
    else: 
        plot_settings = default_plot_settings | plot_settings # Merge with defaults, user settings take precedence

    m, n = len(Z_array), len(Z_array[0]) # m=number of rows, n=number of columns 

    # Determine global minimum and maximum Z values across all subplots
    z_min = plot_settings.get("vmin")
    if z_min is None:
        z_min = min(np.min(Z_array[i][j]) for i in range(m) for j in range(n))
    z_max = plot_settings.get("vmax")
    if z_max is None:
        z_max = max(np.max(Z_array[i][j]) for i in range(m) for j in range(n))

    if np.isclose(z_min, z_max):
        z_min -= 1e-6
        z_max += 1e-6

    use_uniform = plot_settings.get("uniform_cmap", True) or plot_settings.get("show_colorbar", False)
    if use_uniform:
        fill_levels = np.linspace(z_min, z_max, plot_settings["fill_levels"])
        line_levels = np.linspace(z_min, z_max, plot_settings["line_levels"])
    else:
        fill_levels = plot_settings["fill_levels"]
        line_levels = plot_settings["line_levels"]

    fig, axes = plt.subplots(m, n, sharex=True, sharey=True, squeeze=False) 
    for i in range(m): 
        for j in range(n): 
            ax = axes[i, j]
            if use_uniform: 
                contour = ax.contourf(X, Y, Z_array[i][j], cmap=plot_settings["cmap"], alpha=plot_settings["alpha"], levels=fill_levels, vmin=z_min, vmax=z_max)
            else: 
                contour = ax.contourf(X, Y, Z_array[i][j], cmap=plot_settings["cmap"], alpha=plot_settings["alpha"], levels=fill_levels)
            lines = ax.contour(X, Y, Z_array[i][j], levels=line_levels, colors=plot_settings["line_color"], linewidths=0.5)
            ax.clabel(lines, inline=True, fontsize=plot_settings["inline_fontsize"], fmt=plot_settings["inline_format"], colors=plot_settings["inline_color"])
            if plot_settings.get("scatter_data", False) and scatter_array is not None:
                pts = scatter_array[i][j]
                if pts is not None and len(pts) >= 2 and len(pts[0]) > 0:
                    color_mode = plot_settings.get("scatter_color_mode", "Fixed Color")
                    if color_mode == "Output Value (Colormap)" and len(pts) >= 3 and pts[2] is not None and len(pts[2]) > 0:
                        scatter_cmap = plot_settings.get("scatter_cmap") or plot_settings["cmap"]
                        if plot_settings.get("scatter_vmin") is not None and plot_settings.get("scatter_vmax") is not None:
                            s_vmin = plot_settings["scatter_vmin"]
                            s_vmax = plot_settings["scatter_vmax"]
                        elif use_uniform:
                            s_vmin, s_vmax = z_min, z_max
                        else:
                            s_vmin = float(np.min(Z_array[i][j]))
                            s_vmax = float(np.max(Z_array[i][j]))
                            if np.isclose(s_vmin, s_vmax):
                                s_vmin -= 1e-6
                                s_vmax += 1e-6
                        ax.scatter(
                            pts[0],
                            pts[1],
                            s=plot_settings["scatter_size"],
                            c=pts[2],
                            cmap=scatter_cmap,
                            vmin=s_vmin,
                            vmax=s_vmax,
                            edgecolors=plot_settings["scatter_edgecolor"],
                            marker=plot_settings["scatter_marker"],
                            zorder=5
                        )
                    else:
                        ax.scatter(
                            pts[0],
                            pts[1],
                            s=plot_settings["scatter_size"],
                            c=plot_settings["scatter_color"],
                            edgecolors=plot_settings["scatter_edgecolor"],
                            marker=plot_settings["scatter_marker"],
                            zorder=5
                        )
                ax.set_xlim(np.min(X), np.max(X))
                ax.set_ylim(np.min(Y), np.max(Y))
            if label_array is not None:
                ax.set_title(label_array[i][j])
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            ax.grid(True, color=plot_settings["grid_color"], linestyle=plot_settings["grid_linestyle"])
            
    if plot_settings.get("show_colorbar", False) and 'contour' in locals():
        cbar = fig.colorbar(contour, ax=axes.ravel().tolist())
        cbar_label = plot_settings.get("colorbar_label", "")
        if cbar_label:
            cbar.set_label(cbar_label)
        
    plt.suptitle(title)
    if plot_settings.get("show_plot", True):
        plt.show() 



def plot_a_function(func, x_range, y_range, p_range, q_range, title="Function Visualization", xlabel="X", ylabel="Y", label_array=None, plot_settings=None):
    """
    Plots a function of the form f(x, y, p, q) over the given points of x, y, p, and q.
    The contour plots will use x and y as the axes, while p and q will be correspond to the different contour plots. 
    x, y, p and q should be given as 1D iterables. 
    """
    x = np.asarray(x_range)
    y = np.asarray(y_range)
    p = np.asarray(p_range)
    q = np.asarray(q_range)

    X, Y = np.meshgrid(x, y) 
    Z_array = [[func(X, Y, p_i, q_j) for q_j in q] for p_i in p] 

    if label_array is None:
        label_array = [[f"p={p_i}, q={q_j}" for q_j in q] for p_i in p]

    plot_multi_contour(X, Y, Z_array, label_array=label_array, title=title, xlabel=xlabel, ylabel=ylabel, plot_settings=plot_settings)