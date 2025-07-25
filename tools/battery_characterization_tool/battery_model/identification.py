
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
                       max_chg_voltage: float, max_dischg_voltage: float,
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

    # Cut the curves edges with max discharge voltage and max charge voltage
    max_chg_v_idx = 0
    max_dischg_v_idx = len(vbat_filtered)

    # This cannot be done vector wise, since we want to take a continous set which within the given thresholds.
    for i in range(len(vbat_filtered)):

        # Sweeping from the end to the beginning
        x = vbat_filtered[len(vbat_filtered) - i - 1]
        if(x > max_chg_voltage):
            max_chg_v_idx = len(vbat_filtered) - i
            break

    for i in range(len(vbat_filtered)):

        x = vbat_filtered[i]
        if(x < max_dischg_voltage):
            max_dischg_v_idx = i + 1
            break

    # Take only the part which is within the given voltage thresholds
    time_cut = time[max_chg_v_idx:max_dischg_v_idx]
    ocv_cut = ocv[max_chg_v_idx:max_dischg_v_idx]
    ibat_cut = ibat_filtered[max_chg_v_idx:max_dischg_v_idx]

    # Measure current capacity over the full profileintervals
    total_capacity     = coulomb_counter(time, ibat)
    effective_capacity = coulomb_counter(time_cut, ibat_cut)

    # Sample ocv curve (relation between SoC and OCV)
    ocv_curve, indices = sample_ocv_curve(time, ocv, ibat, effective_capacity, num_of_samples, ascending=False)

    if debug:
        pass

    return ocv_curve, total_capacity, effective_capacity

def poly_2ord(x, a, b, c):
    return a*x**2 + b*x + c

def rational_fit(x, a, b, c, d):
    return (a + b*x) / (c + d*x)

def rational_fit_split(x, a, b, c, d, e, f, g, h):

    result = np.zeros_like(x, dtype=float)

    mask1 = x < 0.5
    mask2 = x >= 0.5

    result[mask1] = (a + b*x[mask1]) / (c + d*x[mask1])
    result[mask2] = (e + f*x[mask2]) / (g + h*x[mask2])

def rational_fit(x, a, b, c, d):

    return result

def rational_fit_split(x, a, b, c, d, e, f, g, h):

    result = np.zeros_like(x, dtype=float)

    mask1 = x < 0.5
    mask2 = x >= 0.5

    result[mask1] = (a + b*x[mask1]) / (c + d*x[mask1])
    result[mask2] = (e + f*x[mask2]) / (g + h*x[mask2])

    return result

def continuous_rational_split(x, a1, b1, c1, d1, a2, b2, c2, d2):
    """
    Two rational functions with continuity at x_break
    Parameters reduced by 1 as d2 is derived to ensure continuity
    """
    result = np.zeros_like(x, dtype=float)

    x_break = 0.5

    # First segment
    mask1 = x < x_break
    result[mask1] = (a1 + b1*x[mask1]) / (c1 + d1*x[mask1])

    # Calculate value at breakpoint
    f_break = (a1 + b1*x_break) / (c1 + d1*x_break)

    # Calculate d2 to ensure continuity at x_break
    # Solve: f_break = (a2 + b2*x_break) / (c2 + d2*x_break) for d2
    d2 = ((a2 + b2*x_break) / f_break - c2) / x_break

    # Second segment
    mask2 = x >= x_break
    result[mask2] = (a2 + b2*x[mask2]) / (c2 + d2*x[mask2])

    return result






















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

def continuous_rational_split_two_breaks(x, a1, b1, c1, d1, a2,
                                         b2, c2, d2, a3, b3, c3):
    """
    Three rational functions with continuity at two breakpoints
    Parameters reduced by 2 as d2 and d3 are derived to ensure continuity

    Arguments:
        x: Independent variable
        a1,b1,c1,d1: Parameters for first segment (0 to x_break1)
        a2,b2,c2,d2: Parameters for second segment (x_break1 to x_break2)
        a3,b3,c3: Parameters for third segment (x_break2 to 1)
        x_break1, x_break2: Breakpoint positions (optional, default 0.3 and 0.7)
    """
    result = np.zeros_like(x, dtype=float)

    x_break1=0.3
    x_break2=0.7

    # First segment (0 to x_break1)
    mask1 = x < x_break1
    result[mask1] = (a1 + b1*x[mask1]) / (c1 + d1*x[mask1])

    # Calculate value at first breakpoint for continuity
    f_break1 = (a1 + b1*x_break1) / (c1 + d1*x_break1)

    # Calculate d2 to ensure continuity at x_break1
    d2 = ((a2 + b2*x_break1) / f_break1 - c2) / x_break1

    # Second segment (x_break1 to x_break2)
    mask2 = (x >= x_break1) & (x < x_break2)
    result[mask2] = (a2 + b2*x[mask2]) / (c2 + d2*x[mask2])

    # Calculate value at second breakpoint for continuity
    f_break2 = (a2 + b2*x_break2) / (c2 + d2*x_break2)

    # Calculate d3 to ensure continuity at x_break2
    d3 = ((a3 + b3*x_break2) / f_break2 - c3) / x_break2

    # Third segment (x_break2 to 1.0)
    mask3 = x >= x_break2
    result[mask3] = (a3 + b3*x[mask3]) / (c3 + d3*x[mask3])

    return result

def ocv_piecewise_vec(x, v0, v1, v2, v3, v4, k1, k2):
    """Vectorized piecewise function for OCV-SOC curve fitting"""
    result = np.zeros_like(x, dtype=float)

    # Segment 1: 0 to k1 (steep beginning)
    mask1 = x < k1
    result[mask1] = v0 + (v1-v0)*(x[mask1]/k1)

    # Segment 2: k1 to 0.5 (first plateau)
    mask2 = (x >= k1) & (x < 0.5)
    result[mask2] = v1 + (v2-v1)*((x[mask2]-k1)/(0.5-k1))

    # Segment 3: 0.5 to k2 (second plateau)
    mask3 = (x >= 0.5) & (x < k2)
    result[mask3] = v2 + (v3-v2)*((x[mask3]-0.5)/(k2-0.5))

    # Segment 4: k2 to 1.0 (steep end)
    mask4 = x >= k2
    result[mask4] = v3 + (v4-v3)*((x[mask4]-k2)/(1-k2))

    return result

def ocv_rational(x, a, b, c, d, e, f):
    return a + (b + c*x)/(d + e*x + f*x**2)




def time_to_minutes(time, offset=None):
    if(offset is None):
        return (time - time[0]) / 60000
    else:
        return (time-offset) / 60000

def fit_R_int_curve(r_int_arr, temp_arr):
    """
    Fit the internal resistance curve with polynomial
    """

    # Fit the curve with polynomial
    popt, pcov = curve_fit(poly_2ord, temp_arr, r_int_arr)
    poptr, pcovr = curve_fit(rational_fit, temp_arr, r_int_arr)

    fig, ax = plt.subplots()

    print(popt)

    temp = np.arange(0, 35, 0.01)

    ax.plot(temp_arr, r_int_arr, marker='+', label="R_int_measurements")
    ax.plot(temp, poly_2ord(temp, *popt), label="R_int_fitted")
    ax.plot(temp, rational_fit(temp, *poptr), label="R_int_rational_fit")

    ax.legend()

    plt.show()

    return poptr


def fit_soc_curve(soc_curve):

    # popt_seg, pcov_seg = curve_fit(ocv_piecewise_vec,
    #                                soc_curve[0], soc_curve[1],
    #                                bounds=([-10000,-10000,-10000,-10000,-10000, 0, 0.5  ],[10000,10000 ,10000,10000,10000,0.5,1]))

    popt_rlr, pcov_rlr = curve_fit(rational_linear_rational, soc_curve[0], soc_curve[1])

    lin = np.arange(0,1,0.01)

    fig, ax = plt.subplots()
    ax.plot(soc_curve[0], soc_curve[1], marker='+', linestyle='None', label="SoC_measurements")
    ax.plot(lin, rational_linear_rational(lin, *popt_rlr), label="SoC_rational_split")
    ax.legend()

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

    return popt_rlr, popt_rlr_complete

def extract_SoC_curve_charging(test_name, linear_dischg_data, Rint, max_chg_voltage, max_dischg_voltage, num_of_points, debug=False):

    """
    Extract the SOC curve as relation between battery open-circuit voltage and state of charge from
    the measured data of constant load discharge profile.
    """
    fir_len = 20

    # Low pass filter current and voltage
    ibat_filtered = low_pass_ma_filter(linear_dischg_data.ibat, fir_len)
    vbat_filtered = low_pass_ma_filter(linear_dischg_data.vbat, fir_len)

    # Translate the voltage into OCV using the internal resistance
    V_oc = vbat_filtered + ((ibat_filtered/1000) * Rint)

    # Cut the curves edges with max discharge voltage and max charge voltage
    max_chg_v_idx = len(vbat_filtered)
    max_dischg_v_idx = 0

    for i in range(len(vbat_filtered)):

        sample = vbat_filtered[len(vbat_filtered) - i - 1]

        if(i < 2):
            continue


        if(sample > max_chg_voltage):
            max_chg_v_idx = len(vbat_filtered) - i
            break

    for i in range(len(vbat_filtered)):

        sample = vbat_filtered[i]

        if(i < 2):
            continue

        if(sample < max_dischg_voltage):
            max_dischg_v_idx = i + 1

    # max_dischg_v_idx = int(len(vbat_filtered)*0.95)

    cut_time = linear_dischg_data.time[max_dischg_v_idx:max_chg_v_idx]
    V_oc_cut = V_oc[max_dischg_v_idx:max_chg_v_idx]
    I_oc_cut = ibat_filtered[max_dischg_v_idx:max_chg_v_idx]

    # Measure current capacity over the full profile intervals
    total_capacity     = coulomb_counter(linear_dischg_data.time, linear_dischg_data.ibat)
    effective_capacity = coulomb_counter(cut_time, I_oc_cut)
    #effective_capacity = total_capacity

    # Find the curve interpolation points
    SoC_curve, SoC_curve_indeces = extract_SoC_interpolation_points(V_oc_cut, I_oc_cut, cut_time, effective_capacity, num_of_points, profile_ascending=True)
    #SoC_curve, SoC_curve_indeces = extract_SoC_interpolation_points(V_oc, linear_dischg_data.ibat, linear_dischg_data.time , effective_capacity, num_of_points)

    intervals = np.array(SoC_curve)

    if debug:

        # fit with spline??
        #popt, pcov = curve_fit(poly, intervals[:,0], V_oc_cut[SoC_curve_indeces])
        #V_oc_fitted = poly(intervals[:,0], *popt)

        fig, ax = plt.subplots(2,1)
        fig.set_size_inches(6,4)
        fig.set_dpi(300)

        fig.suptitle("Linear discharge profile")

        ax[0].set_title("Open-circuit voltage", fontsize=6)
        ax[0].plot(time_to_minutes(linear_dischg_data.time), V_oc, linewidth=0.7, label="V_oc")
        ax[0].plot(time_to_minutes(linear_dischg_data.time), linear_dischg_data.vbat, linewidth=0.7, label="V_bat")
        ax[0].plot(time_to_minutes(cut_time), V_oc_cut, linewidth=0.7, label="V_oc effective area", color="red")
        ax[0].set_xlabel("Time [min]", fontsize=6)
        ax[0].set_ylabel("Voltage [V]", fontsize=6)
        ax[0].set_xlim([0, time_to_minutes(linear_dischg_data.time[-1], linear_dischg_data.time[0])])

        for ip in SoC_curve_indeces:
            ax[0].axvline(x=time_to_minutes(cut_time[ip], cut_time[0]), color='gray', linestyle='--', linewidth=0.5,alpha=0.3)

        ax[0].legend()

        ax[1].set_title("Battery current", fontsize=6)
        ax[1].plot(time_to_minutes(linear_dischg_data.time), linear_dischg_data.ibat, linewidth=0.7,  label="I_bat")
        ax[1].plot(time_to_minutes(cut_time), I_oc_cut, label="I_bat_filtered effective area", linewidth=0.7, color="red")
        ax[1].set_xlabel("Time [min]", fontsize=6)
        ax[1].set_ylabel("Current [mA]", fontsize=6)
        ax[1].set_xlim([0, time_to_minutes(linear_dischg_data.time[-1], linear_dischg_data.time[0])])

        ax[1].legend()

        #fig, ax = plt.subplots()
        #ax.plot(intervals[:,0], V_oc_cut[SoC_curve_indeces], label="V_OC")
        #ax.plot(intervals[:,0], V_oc_fitted, label="V_OC_fitted")

    return SoC_curve, total_capacity, effective_capacity

