class CoulombCounterEstimator:

    def __init__(self, battery_model, label=None):

        self.name = "Coulomb Counter Estimator"
        if label is not None:
            self.name = self.name + ": " + label
        self.bm = battery_model
        self.reset()

    def initial_guess(self, voltage_V, current_mA, temp_deg):

        discharge_mode = True
        if current_mA < 0:
            discharge_mode = False

        ocv = self.bm._meas_to_ocv(voltage_V, current_mA, temp_deg)
        self.SoC = self.bm._interpolate_soc_at_temp(ocv, temp_deg, discharge_mode)
        return

    def reset(self):
        self.SoC = 0

    def set_soc(self, SoC):
        self.SoC = SoC

    def update(self, dt, voltage_V, current_mA, temp_deg):

        discharge_mode = True
        if current_mA < 0:
            discharge_mode = False

        self.SoC -= (
            current_mA / (3600 * self.bm._total_capacity(temp_deg, discharge_mode))
        ) * dt
        self.SoC = min(1, max(0, self.SoC))

        # Return SoC, covariance not tracked
        return self.SoC, None
