import matplotlib.pyplot as plt
from dataset.battery_profile import time_to_minutes

# Plot settings

FIG_SIZE_INCHES = (6, 4)
FIG_DPI = 300
FIG_FONT_SIZE = 6
FIG_LINE_WIDTH = 0.7


def fig_general_config(fig):

    fig.set_size_inches(FIG_SIZE_INCHES)
    fig.set_dpi(FIG_DPI)


def plot_general_config(ax, title, xlabel, ylabel):

    ax.set_xlabel(xlabel, fontsize=FIG_FONT_SIZE)
    ax.set_ylabel(ylabel, fontsize=FIG_FONT_SIZE)
    ax.legend()
    ax.tick_params(axis="both", which="major", labelsize=FIG_FONT_SIZE)
    x_data = ax.lines[0].get_xdata()
    ax.set_xlim([0, x_data[-1]])
    ax.set_title(title, fontsize=FIG_FONT_SIZE)

    for l in ax.lines:
        l.set_linewidth(FIG_LINE_WIDTH)


def identify_r_int_debug_plot(
    time,
    vbat,
    ibat,
    transition_indeces,
    transition_indeces_m1,
    transition_indeces_m2,
    r_int,
    r_int_cons_indices,
    r_int_cons,
    r_int_est,
    name=None,
):

    fig, ax = plt.subplots(3, 1)
    fig_general_config(fig)

    fig.suptitle(
        "R_int identification on switching load profile "
        + (": " + name if name is not None else ""),
        fontsize=FIG_FONT_SIZE,
    )

    ax[0].plot(time_to_minutes(time), vbat, label="V_bat")
    plot_general_config(ax[0], "Battery voltage", "Time [min]", "Voltage [V]")

    ax[1].plot(time_to_minutes(time), ibat, label="I_bat")
    ax[1].plot(
        time_to_minutes(time[transition_indeces], time[0]),
        ibat[transition_indeces],
        "x",
        markersize=3,
        color="red",
        label="Load transitions",
    )
    ax[1].plot(
        time_to_minutes(time[transition_indeces_m1], time[0]),
        ibat[transition_indeces_m1],
        "x",
        markersize=3,
        color="magenta",
        label="V_t1",
    )
    ax[1].plot(
        time_to_minutes(time[transition_indeces_m2], time[0]),
        ibat[transition_indeces_m2],
        "x",
        markersize=3,
        color="lime",
        label="V_t2",
    )
    plot_general_config(
        ax[1],
        "Battery current with r_int identification marks",
        "Time [min]",
        "Current [mA]",
    )

    ax[2].plot(
        time_to_minutes(time[transition_indeces], time[0]),
        r_int,
        marker="o",
        markersize=3,
        label="R_int",
    )
    ax[2].plot(
        time_to_minutes(time[r_int_cons_indices], time[0]),
        r_int_cons,
        marker="o",
        markersize=3,
        label="R_int (cons.)",
    )
    ax[2].axhline(
        y=r_int_est,
        color="r",
        linestyle="--",
        label=f"identified r_int: {r_int_est:.2f} ohms",
    )
    plot_general_config(ax[2], "R_int estimation", "Time [min]", "Resistance [ohms]")


def identify_ocv_curve_debug_plot(time, vbat, ibat, ocv, ocv_curve_indeces, name=None):

    fig, ax = plt.subplots(2, 1)
    fig_general_config(fig)

    fig.suptitle(
        "ocv curve identification" + (": " + name if name is not None else ""),
        fontsize=FIG_FONT_SIZE,
    )

    ax[0].plot(time_to_minutes(time), ocv, label="open-circuit voltage")
    ax[0].plot(time_to_minutes(time), vbat, label="vbat")
    plot_general_config(ax[0], "Open-circuit voltage", "Time [min]", "Voltage [V]")

    for ix in ocv_curve_indeces:
        ax[0].axvline(
            x=time_to_minutes(time[ix], time[0]),
            color="gray",
            linestyle="--",
            linewidth=0.5,
            alpha=0.3,
        )
        ax[0].legend()

    ax[1].plot(time_to_minutes(time), ibat, label="ibat")
    plot_general_config(ax[1], "Effective area of I_bat", "Time [min]", "Current [mA]")
