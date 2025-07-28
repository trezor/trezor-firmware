
import copy
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit
from scipy.signal import convolve, find_peaks
from .debug_plots import identify_r_int_debug_plot

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

def low_pass_ma_filter(x : np.ndarray, ma_len: int =40) -> np.ndarray:
    """
    Apply moving average filter to the vector x.
    Returns filtered vector.
    """

    x_ma = copy.copy(x)

    for i, sample in enumerate(x):
        if(i < ma_len):
            x_ma[i] = sum(x[:i+1]/(i+1))
        else:
            x_ma[i] = sum(x[i-ma_len:i]/(ma_len))

    return x_ma

def find_signal_transitions(x: np.ndarray, fir_len: int =40) -> np.ndarray:
    """
    Use convolution with correlation filter of "step" shape to extract sharp transitions in x.
    Returns vector of transition indeces.
    """

    corr_filter = np.concat((np.zeros(fir_len/2, dtype=int)-1,np.zeros(fir_len/2, dtype=int)+1), axis=None)
    conv_x = convolve(x, corr_filter, mode='same', method='direct')
    return find_peaks(abs(conv_x), prominence=300)

def coulomb_counter(time, ibat):
    """
    Provide ibat(mA) ant time(s) vectors to calculate the total
    charged or discharged current.

    returns total integrated value in mAh
    """
    curr_acc = 0

    for i, t in enumerate(time):

        # Nothing to add in first cycle
        if(i == 0):
            continue

        # Linear interpolation mAstime
        curr_acc += (abs((ibat[i-1] + ibat[i])/2)*((time[i]-time[i-1])/1000))

    # convert from mAs to mAh
    return curr_acc/3600

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

        delta = bat_capacity # Just and ultimately largest options
        idx = 0
        cusum = 0
        current = intervals[i]*bat_capacity

        for j in range(len(ibat)):

            if ascending:
                idx = j
            else:
                idx = len(ibat) - j - 1

            if j == 0:
                continue

            # Interpolate the current
            cur_incr = (((ibat[idx-1] + ibat[idx])/2)*((time[idx]-time[idx-1])/1000))
            cusum += abs(cur_incr)/3600

            if(abs(cusum - current) < delta):
                delta = abs(cusum - current)
                idx = idx

        ocv_curve[0][i] = intervals[i]
        try:
            ocv_curve[1][i] = ocv[idx]
        except:
            raise ValueError(f"Index {idx} out of bounds for OCV vector of length {len(ocv)}")

        indices[i] = idx

    return ocv_curve, indices


def identify_r_int(time: np.ndarray, ibat: np.ndarray, vbat: np.ndarray, temp: np.ndarray, debug=False):
    """
    Identify internal resistance of the battery from the measured voltage and current data.

    internal resistance could be estimated only if battery is discharged with several different loads. Script will
    identify the load transition and for every such transition it will do a single r_int estimation. Final estimation
    is an average of all the single estimations. To get best estimation results, feed the discharge waveform with
    sufficient number of load transitions.
    """

    ma_len=40
    offset_left  = 10
    offset_right = 45

    # Low pass filter current and voltage
    ibat_filtered = low_pass_ma_filter(ibat, ma_len=ma_len)
    vbat_filtered = low_pass_ma_filter(vbat, ma_len=ma_len)

    # Filter out signal transitions, use same filter len as for low pass filter
    i_bat_transitions = find_signal_transitions(ibat_filtered, fir_len=ma_len)

    # Filter out transitions which are too close to the edge and have no left/right offset
    valid_transitions = i_bat_transitions[np.logical_and(i_bat_transitions - offset_left > 0, i_bat_transitions + offset_right < len(ibat))]

    # Look left and right by given offset from identified transitions
    m1_idx = valid_transitions - offset_left   # Marks 1
    m2_idx = valid_transitions + offset_right  # Marks 2

    r_int = np.zeros(len(valid_transitions), dtype=float)

    for i in range(0, len(valid_transitions)):
        r_int[i] = (vbat_filtered[m2_idx[i]] - vbat_filtered[m1_idx[i]]) / ((ibat_filtered[m1_idx[i]])/1000 - (ibat_filtered[m2_idx[i]])/1000)

    # Average the R_int, do not consider the data on edges
    if(len(r_int) < 5):
        r_int_est = sum(r_int)/len(r_int)
    else:
        r_int_est = sum(r_int[2:-2])/len(r_int[2:-2])

    if debug:
        identify_r_int_debug_plot(time, vbat_filtered, ibat_filtered, r_int,
                                  r_int_est,
                                  valid_transitions,
                                  m1_idx,
                                  m2_idx)
    return r_int_est


def identify_ocv_curve(time : np.ndarray, vbat : np.ndarray, ibat: np.ndarray, r_int: float,
                       max_curve_v: float, min_curve_v: float,
                       num_of_samples: int = 100, debug=False):
    """
    Extract the SOC curve as relation between battery open-circuit voltage and state of charge from
    the measured data of constant load discharge profile.
    """

    fir_len = 20

    # Low pass filter current and voltage
    ibat_filtered = low_pass_ma_filter(ibat, fir_len)
    vbat_filtered = low_pass_ma_filter(vbat, fir_len)

    # Translate the voltage into OCV using the internal resistance
    ocv = vbat_filtered + ((ibat_filtered/1000) * r_int)

    if(ocv[0] < ocv[-1]):
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
            x = vbat_filtered[-(i + 1)] # Sweep backwards
            if(x < min_curve_v):
                min_curve_v_idx = vbat_filtered[-(i)]
                break

        else:
            x = vbat_filtered[i]
            if(x < min_curve_v):
                min_curve_v_idx = vbat_filtered[(i-1)]
                break

    # Find max_voltage index
    for i in range(1, len(vbat_filtered)):

        if curve_ascending:
            x = vbat_filtered[i]
            if(x > max_curve_v):
                max_curve_v_idx = vbat_filtered[i-1]
                break

        else:
            x = vbat_filtered[-(i + 1)]  # Sweep backwards
            if(x > max_curve_v):
                max_curve_v_idx = vbat_filtered[-(i)]
                break


    # Take only the part which is within the given voltage thresholds
    if curve_ascending:
        time_cut = time[min_curve_v_idx:max_curve_v_idx]
        ocv_cut = ocv[min_curve_v_idx:max_curve_v_idx]
        ibat_cut = ibat_filtered[min_curve_v_idx:max_curve_v_idx]
    else:
        time_cut = time[max_curve_v_idx:max_curve_v_idx]
        ocv_cut = ocv[max_curve_v_idx:max_curve_v_idx]
        ibat_cut = ibat_filtered[max_curve_v_idx:max_curve_v_idx]

    # Measure current capacity over the full profileintervals
    total_capacity     = coulomb_counter(time, ibat)
    effective_capacity = coulomb_counter(time_cut, ibat_cut)

    # Sample ocv curve (relation between SoC and OCV)
    ocv_curve, indices = sample_ocv_curve(time, ocv, ibat, effective_capacity, num_of_samples, ascending=curve_ascending)

    if debug:
        pass

    return ocv_curve, total_capacity, effective_capacity

def rational_f(x, a, b, c, d):
    return (a + b*x) / (c + d*x)

def fit_r_int_curve(r_int_arr, temp_arr, debug=False):
    """
    Fit the internal resistance curve with rational funtion.
    returns fitted parameters
    """

    poptr, pcovr = curve_fit(rational_f, temp_arr, r_int_arr)
    return poptr, pcovr

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
    result[mask2] = m*x[mask2] + b

    # Calculate values at breakpoints
    f_break1 = m*x_break1 + b
    f_break2 = m*x_break2 + b

    # Calculate d1 to ensure continuity at x_break1
    d1 = ((a1 + b1*x_break1)/f_break1 - c1)/x_break1

    # First segment (rational)
    mask1 = x < x_break1
    result[mask1] = (a1 + b1*x[mask1]) / (c1 + d1*x[mask1])

    # Calculate d3 to ensure continuity at x_break2
    d3 = ((a3 + b3*x_break2)/f_break2 - c3)/x_break2

    # Third segment (rational)
    mask3 = x >= x_break2
    result[mask3] = (a3 + b3*x[mask3]) / (c3 + d3*x[mask3])

    return result

def fit_ocv_curve(ocv_curve):

    popt_rlr, pcov_rlr = curve_fit(rational_linear_rational, ocv_curve[0], ocv_curve[1])

    [m, b, a1, b1, c1, a3, b3, c3] = popt_rlr

    # Precalculate d parameters
    x_break1 = 0.25
    x_break2 = 0.8
    # Calculate values at breakpoints
    f_break1 = m*x_break1 + b
    f_break2 = m*x_break2 + b

    # Calculate d1 to ensure continuity at x_break1
    d1 = ((a1 + b1*x_break1)/f_break1 - c1)/x_break1
    # Calculate d3 to ensure continuity at x_break2
    d3 = ((a3 + b3*x_break2)/f_break2 - c3)/x_break2

    popt_rlr_complete = [m, b, a1, b1, c1, d1, a3, b3, c3, d3]

    return popt_rlr_complete





















