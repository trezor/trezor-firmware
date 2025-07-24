"""
This library provides the set of functions to extract battery model parameters from the measured data
and to fit the them with different kinds of functions.

Battery model:

Battery is modeled with simple equivalent circuit model with single internal resistance R_int

             R_INT
              ___
   Ocv  +----|___|------o V_t
        |
        |
       BAT
        |
        |
        +---------------o GND

Key estimated parameters:
    - Open circuit voltage profile for charge and discharge mode(Ocv)
    - Internal resistance (R_int)
    - Battery capacity (mAh) for charge and discharge mode

"""

import copy

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit
from scipy.signal import convolve, find_peaks

from .debug_plots import identify_ocv_curve_debug_plot, identify_r_int_debug_plot


def low_pass_ma_filter(x: np.ndarray, ma_len: int = 40) -> np.ndarray:
    """
    Apply moving average filter to the vector x.
    Returns filtered vector.
    """

    x_ma = copy.copy(x)

    for i in range(len(x)):
        if i < ma_len:
            x_ma[i] = sum(x[: i + 1] / (i + 1))
        else:
            x_ma[i] = sum(x[i - ma_len : i] / (ma_len))

    return x_ma


def find_signal_transitions(x: np.ndarray, fir_len: int = 40) -> np.ndarray:
    """
    Use convolution with correlation filter of "step" shape to extract sharp transitions in x.
    Returns vector of transition indeces.
    """

    corr_filter = np.concatenate(
        (
            np.zeros((int)(fir_len / 2), dtype=int) - 1,
            np.zeros((int)(fir_len / 2), dtype=int) + 1,
        ),
        axis=None,
    )
    conv_x = convolve(x, corr_filter, mode="same", method="direct")
    peaks, _ = find_peaks(abs(conv_x), prominence=300)
    return peaks


def coulomb_counter(time, ibat):
    """
    Provide ibat(mA) ant time(s) vectors to calculate the total
    charged or discharged current.

    returns total integrated value in mAh
    """
    curr_acc = 0

    for i in range(len(time)):

        # Nothing to add in first cycle
        if i == 0:
            continue

        # Linear interpolation mAstime
        curr_acc += abs((ibat[i - 1] + ibat[i]) / 2) * ((time[i] - time[i - 1]) / 1000)

    # convert from mAs to mAh
    return curr_acc / 3600


def sample_ocv_curve(time, ocv, ibat, bat_capacity, num_of_samples, ascending=False):
    """
    Use the measured capacity from the constant current load curve and estimated V_oc
    to split the V_oc into equidistant intervals and calculate the SOC points
    returns list of index
    """

    # Calculate SoC presets according to num_of_intervals
    intervals = np.linspace(0, 1, num_of_samples)

    # First row is SoC, second is V_OC
    ocv_curve = np.zeros((2, num_of_samples))
    indices = np.zeros(num_of_samples, dtype=int)

    for i in range(len(intervals)):
        idx = 0
        cusum = 0
        current = intervals[i] * bat_capacity

        for j in range(len(ibat)):

            if ascending:
                idx = j
            else:
                idx = len(ibat) - j - 1

            if j == 0:
                continue

            # Interpolate the current
            cur_incr = ((ibat[idx - 1] + ibat[idx]) / 2) * (
                (time[idx] - time[idx - 1]) / 1000
            )
            cusum += abs(cur_incr) / 3600

            if cusum >= current:
                break

        ocv_curve[0][i] = intervals[i]
        ocv_curve[1][i] = ocv[idx]
        indices[i] = idx

    return ocv_curve, indices


def identify_r_int(
    time: np.ndarray,
    ibat: np.ndarray,
    vbat: np.ndarray,
    temp: np.ndarray,
    debug=False,
    test_description=None,
):
    """
    Identify internal resistance of the battery from the measured voltage and current data.

    internal resistance could be estimated only if battery is discharged with several different loads. Script will
    identify the load transition and for every such transition it will do a single r_int estimation. Final estimation
    is an average of all the single estimations. To get best estimation results, feed the discharge waveform with
    sufficient number of load transitions.
    """

    ma_len = 40
    offset_left = 10
    offset_right = 45

    # Low pass filter current and voltage
    ibat_filtered = low_pass_ma_filter(ibat, ma_len=ma_len)
    vbat_filtered = low_pass_ma_filter(vbat, ma_len=ma_len)

    # Filter out signal transitions, use same filter len as for low pass filter
    # and unfiltered signal identify transitions precisely
    i_bat_transitions = find_signal_transitions(ibat, fir_len=ma_len)

    # Filter out transitions which are too close to the edge and have no left/right offset
    valid_transitions = i_bat_transitions[
        np.logical_and(
            i_bat_transitions - offset_left > 0,
            i_bat_transitions + offset_right < len(ibat),
        )
    ]

    # Look left and right by given offset from identified transitions
    m1_idx = valid_transitions - offset_left  # Marks 1
    m2_idx = valid_transitions + offset_right  # Marks 2

    r_int = np.zeros(len(valid_transitions), dtype=float)

    for i in range(0, len(valid_transitions)):
        r_int[i] = (vbat_filtered[m2_idx[i]] - vbat_filtered[m1_idx[i]]) / (
            (ibat_filtered[m1_idx[i]]) / 1000 - (ibat_filtered[m2_idx[i]]) / 1000
        )

    # make r_int estimation by averaging the values estimation from every transition, consider only half of the
    # estimation values from the middle of the waveforms to avoid calculation with the ugly edges of the discharging
    # profile where r_int drfts away from typial value.
    r_int_cons_indices = valid_transitions[
        int(len(valid_transitions) / 4) : int(len(valid_transitions) * 3 / 4)
    ]
    r_int_cons = r_int[
        int(len(valid_transitions) / 4) : int(len(valid_transitions) * 3 / 4)
    ]
    if len(r_int_cons) == 0:
        return None

    r_int_est = sum(r_int_cons) / len(r_int_cons)

    if debug:
        identify_r_int_debug_plot(
            time,
            vbat_filtered,
            ibat_filtered,
            valid_transitions,
            m1_idx,
            m2_idx,
            r_int,
            r_int_cons_indices,
            r_int_cons,
            r_int_est,
            name=test_description,
        )
    return r_int_est


def identify_ocv_curve(
    time: np.ndarray,
    vbat: np.ndarray,
    ibat: np.ndarray,
    r_int: float,
    max_curve_v: float,
    min_curve_v: float,
    num_of_samples: int = 100,
    debug=False,
    test_description=None,
):
    """
    Extract the SOC curve as relation between battery open-circuit voltage and state of charge from
    the measured data of constant load discharge profile.
    """

    fir_len = 20

    # Low pass filter current and voltage
    ibat_filtered = low_pass_ma_filter(ibat, fir_len)
    vbat_filtered = low_pass_ma_filter(vbat, fir_len)

    # Translate the voltage into OCV using the internal resistance
    ocv = vbat_filtered + ((ibat_filtered / 1000) * r_int)

    curve_ascending = False
    if ocv[0] < ocv[-1]:
        curve_ascending = True

    # Initialize min/max voltage indices
    if curve_ascending:
        min_curve_v_idx = 0
        max_curve_v_idx = len(vbat_filtered)
    else:
        min_curve_v_idx = len(vbat_filtered)
        max_curve_v_idx = 0

    # Find min_voltage index
    for i in range(1, len(vbat_filtered)):

        if curve_ascending:
            x = vbat_filtered[-(i + 1)]  # Sweep backwards
            if x < min_curve_v:
                min_curve_v_idx = len(vbat_filtered) - i
                break

        else:
            x = vbat_filtered[i]
            if x < min_curve_v:
                min_curve_v_idx = i - 1
                break

    # Find max_voltage index
    for i in range(1, len(vbat_filtered)):

        if curve_ascending:
            x = vbat_filtered[i]
            if x > max_curve_v:
                max_curve_v_idx = i - 1
                break

        else:
            x = vbat_filtered[-(i + 1)]  # Sweep backwards
            if x > max_curve_v:
                max_curve_v_idx = len(vbat_filtered) - i
                break

    # Take only the part which is within the given voltage thresholds
    if curve_ascending:
        time_cut = time[min_curve_v_idx:max_curve_v_idx]
        ocv_cut = ocv[min_curve_v_idx:max_curve_v_idx]
        vbat_cut = vbat_filtered[min_curve_v_idx:max_curve_v_idx]
        ibat_cut = ibat_filtered[min_curve_v_idx:max_curve_v_idx]
    else:
        time_cut = time[max_curve_v_idx:min_curve_v_idx]
        ocv_cut = ocv[max_curve_v_idx:min_curve_v_idx]
        vbat_cut = vbat_filtered[max_curve_v_idx:min_curve_v_idx]
        ibat_cut = ibat_filtered[max_curve_v_idx:min_curve_v_idx]

    # Measure current capacity over the full profileintervals
    total_capacity = coulomb_counter(time, ibat)
    effective_capacity = coulomb_counter(time_cut, ibat_cut)

    # Sample ocv curve (relation between SoC and OCV)
    ocv_curve, indices = sample_ocv_curve(
        time_cut,
        ocv_cut,
        ibat_cut,
        effective_capacity,
        num_of_samples,
        ascending=curve_ascending,
    )

    if debug:
        identify_ocv_curve_debug_plot(
            time_cut, vbat_cut, ibat_cut, ocv_cut, indices, name=test_description
        )

    return ocv_curve, total_capacity, effective_capacity


def rational_f(x, a, b, c, d):
    return (a + b * x) / (c + d * x)


def fit_r_int_curve(r_int_arr, temp_arr, debug=False):
    """
    Fit the internal resistance curve with rational funtion.
    returns fitted parameters
    """
    poptr, pcovr = curve_fit(rational_f, temp_arr, r_int_arr)

    if debug:
        # Plot the fitted curve
        plt.figure()
        plt.scatter(
            temp_arr, r_int_arr, label="estimated r_int data points", color="blue"
        )
        x_fit = np.linspace(min(temp_arr), max(temp_arr), 100)
        y_fit = rational_f(x_fit, *poptr)
        plt.plot(x_fit, y_fit, label="fitted r_int curve", color="red")
        plt.xlabel("Temperature [°C]")
        plt.ylabel("Internal resistance [Ohm]")
        plt.title("Fitted Internal Resistance Curve")
        plt.legend()
        plt.grid()

    return poptr, pcovr


def estimate_r_int(temp, r_int_params):
    """
    Estimate the internal resistance for given temperature using fitted parameters.
    """
    a, b, c, d = r_int_params
    return rational_f(temp, a, b, c, d)


def estimate_ocv_curve(x, ocv_params):
    """
    Estimate the OCV for given SoC using fitted parameters.
    """
    m, b, a1, b1, c1, a3, b3, c3 = ocv_params
    return rational_linear_rational(x, m, b, a1, b1, c1, a3, b3, c3)


def rational_linear_rational(x, m, b, a1, b1, c1, a3, b3, c3):
    """
    Three-segment function with continuity at breakpoints:
    - First segment (0 to x_break1): rational function
    - Middle segment (x_break1 to x_break2): linear function f(x) = mx + b
    - Third segment (x_break2 to 1.0): rational function

    Parameters:
        m, b: Linear segment parameters (middle segment)
        a1, b1, c1: First rational segment parameters (start segment)
        a3, b3, c3: Last rational segment parameters (end segment)
        x_break1, x_break2: Breakpoints between segments
    """
    result = np.zeros_like(x, dtype=float)

    x_break1 = 0.25
    x_break2 = 0.8

    # Middle segment (linear)
    mask2 = (x >= x_break1) & (x < x_break2)
    result[mask2] = m * x[mask2] + b

    # Calculate values at breakpoints
    f_break1 = m * x_break1 + b
    f_break2 = m * x_break2 + b

    # Calculate d1 to ensure continuity at x_break1
    d1 = ((a1 + b1 * x_break1) / f_break1 - c1) / x_break1

    # First segment (rational)
    mask1 = x < x_break1
    result[mask1] = (a1 + b1 * x[mask1]) / (c1 + d1 * x[mask1])

    # Calculate d3 to ensure continuity at x_break2
    d3 = ((a3 + b3 * x_break2) / f_break2 - c3) / x_break2

    # Third segment (rational)
    mask3 = x >= x_break2
    result[mask3] = (a3 + b3 * x[mask3]) / (c3 + d3 * x[mask3])

    return result


def fit_ocv_curve(ocv_curve):
    """
    Fit an OCV curve (SoC/ocv relation) using a rational-linear-rational model

    Parameters:
    - soc_curve: 2D array [SoC, OCV]

    Returns:
    - popt_rlr: Fitted parameters for rational_linear_rational function
    - popt_rlr_complete: Fitted parameters including continuity terms d1 and d3
    """

    p0 = [1.0] * 8

    popt_rlr, _ = curve_fit(rational_linear_rational, ocv_curve[0], ocv_curve[1], p0=p0)

    [m, b, a1, b1, c1, a3, b3, c3] = popt_rlr

    # Precalculate d parameters
    x_break1 = 0.25
    x_break2 = 0.8
    # Calculate values at breakpoints
    f_break1 = m * x_break1 + b
    f_break2 = m * x_break2 + b

    # Calculate d1 to ensure continuity at x_break1
    d1 = ((a1 + b1 * x_break1) / f_break1 - c1) / x_break1
    # Calculate d3 to ensure continuity at x_break2
    d3 = ((a3 + b3 * x_break2) / f_break2 - c3) / x_break2

    popt_rlr_complete = [m, b, a1, b1, c1, d1, a3, b3, c3, d3]

    return popt_rlr, popt_rlr_complete
