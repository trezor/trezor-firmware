import numpy as np


class SimulationResult:
    def __init__(self, time, soc, covariance, start_idx, end_idx, model_name=None):
        self.time: np.ndarray = time
        self.soc: np.ndarray = soc
        self.covariance: np.ndarray = covariance
        self.start_idx: int = start_idx
        self.end_idx: int = end_idx
        self.model_name: str = model_name


def mean_filter(data):
    return sum(data) / len(data)


def run_battery_simulation(
    waveform, soc_estim_model, sim_start_idx=0, initial_soc=None, init_filter_length=10
):

    soc = np.zeros((len(waveform.time)))
    covariance = np.zeros((len(waveform.time)))

    if sim_start_idx >= len(waveform.time):
        raise ValueError(
            "simulation start index is greater than the length of the waveform"
        )

    # Reset Estimator to default
    soc_estim_model.reset()

    if initial_soc is not None:
        # Initialize SoC manually
        soc_estim_model.set_soc(initial_soc)
    else:

        vbat_init = mean_filter(
            waveform.vbat[sim_start_idx : sim_start_idx + init_filter_length]
        )
        ibat_init = mean_filter(
            waveform.ibat[sim_start_idx : sim_start_idx + init_filter_length]
        )
        ntc_temp_init = mean_filter(
            waveform.ntc_temp[sim_start_idx : sim_start_idx + init_filter_length]
        )

        # Make Initial SoC guess
        soc_estim_model.initial_guess(vbat_init, ibat_init, ntc_temp_init)

    sim_end_idx = 0
    for i in range(sim_start_idx + 1 + init_filter_length, len(waveform.time)):

        soc[i], covariance[i] = soc_estim_model.update(
            waveform.time[i] - waveform.time[i - 1],
            waveform.vbat[i],
            waveform.ibat[i],
            waveform.ntc_temp[i],
        )
        sim_end_idx = i

    sim_result = SimulationResult(
        waveform.time, soc, covariance, sim_start_idx, sim_end_idx, soc_estim_model.name
    )

    return sim_result
