class EkfEstimator:

    def __init__(
        self,
        battery_model,
        R=None,
        Q=None,
        R_agressive=None,
        Q_agressive=None,
        P_init=None,
        label=None,
    ):

        self.name = "EKF estimator"
        if label is not None:
            self.name = self.name + ": " + label

        # Battery model consists of characterized battery data
        self.bm = battery_model

        if R is None or Q is None or P_init is None:
            raise ValueError("Some of the EKF parameters are missing")

        self.R_default = R
        self.Q_default = Q
        self.R_agressive_default = R_agressive
        self.Q_agressive_default = Q_agressive
        self.P_init_default = P_init

        self.reset()

    def reset(self):

        self.R = self.R_default
        self.Q = self.Q_default
        self.R_agressive = self.R_agressive_default
        self.Q_agressive = self.Q_agressive_default
        self.P_init = self.P_init_default
        self.P = self.P_init_default

        self.v_meas_history = []
        self.i_meas_history = []
        self.filter_window = 5  # Number of samples to average

        # Reset default state
        self.x = 0  # SoC
        self.x_latched = self.x

    def _filter_measurement(self, new_value, history):
        """Simple moving average filter for measurements"""
        history.append(new_value)
        if len(history) > self.filter_window:
            history.pop(0)

        return sum(history) / len(history)

    def initial_guess(self, voltage_V, current_mA, temp_deg):
        """
        Use the very first measurement to initialize the state of charge
        just by interpolation on the SoC curve.
        """

        discharge_mode = True
        if current_mA < 0:
            discharge_mode = False

        ocv = self.bm._meas_to_ocv(voltage_V, current_mA, temp_deg)
        self.x = self.bm._interpolate_soc_at_temp(ocv, temp_deg, discharge_mode)
        self.x_latched = self.x

        return

    def update(self, dt, voltage_V, current_mA, temp_deg):

        # voltage_V  = self._filter_measurement(voltage_V, self.v_meas_history)
        # current_mA = self._filter_measurement(current_mA, self.i_meas_history)

        if current_mA == 0:
            # If the current is zero, we cannot estimate the SoC
            # We can only use the last known value
            return self.x_latched, self.P

        # Select between charge or /discharge mode
        discharge_mode = True
        if current_mA < 0:
            discharge_mode = False

        self.R = self.R_default
        self.Q = self.Q_default

        if discharge_mode:
            if self.x_latched < 0.2:
                self.R = self.R_agressive_default
                self.Q = self.Q_agressive_default
        else:
            if self.x_latched > 0.8:
                self.R = self.R_agressive_default
                self.Q = self.Q_agressive_default

        # Convert dt to seconds
        dt_sec = dt

        # State prediction (coulomb counting)
        x_k1_k = (
            self.x
            - (current_mA / (3600 * self.bm._total_capacity(temp_deg, discharge_mode)))
            * dt_sec
        )

        # Calculate Jacobian of measurement function h(x) with respect to x
        # For the battery model: h(x) = OCV(x) - R*I
        # So h'(x) = dOCV/dx
        h_jacobian = self.bm._intrepolate_ocv_slope_at_temp(
            x_k1_k, temp_deg, discharge_mode
        )
        # h_jacobian = 1

        # Error covariance prediction
        P_k1_k = self.P + self.Q

        # Calculate innovation covariance
        S = h_jacobian * P_k1_k * h_jacobian + self.R

        # Calculate Kalman gain
        K_k1_k = P_k1_k * h_jacobian / S

        # Calculate predicted terminal voltage
        v_pred = self.bm._interpolate_ocv_at_temp(x_k1_k, temp_deg, discharge_mode) - (
            current_mA / 1000
        ) * self.bm._rint(temp_deg)

        # State update
        x_k1_k1 = x_k1_k + K_k1_k * (voltage_V - v_pred)

        # Error covariance update
        P_k1_k1 = (1 - K_k1_k * h_jacobian) * P_k1_k

        # Enforce SoC boundaries
        self.x = max(0.0, min(1.0, x_k1_k1))
        self.P = P_k1_k1

        if abs(self.x_latched) > 0.1 and self.x == 0:
            # If the difference between the last and current SoC is too big,
            # we need to latch the current value
            print("Big hop")

        # Based on the current directon decide what to latch
        if current_mA > 0:
            # Discharging, Soc should move only in negative direction
            if self.x < self.x_latched:
                self.x_latched = self.x
        else:
            if self.x > self.x_latched:
                self.x_latched = self.x

        return self.x_latched, self.P
