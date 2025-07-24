
import matplotlib.pyplot as plt
import numpy as np

class BatteryModel():

    def __init__(self, battery_model_data):

        self.battery_model_data = battery_model_data
        self.temp_keys_list = sorted(list(
                              self.battery_model_data['ocv_curves'].keys()))

        self.soc_breakpoint_1 = 0.25
        self.soc_breakpoint_2 = 0.8

    def _meas_to_ocv(self, voltage_V, current_mA, temp_deg):
        ocv_V = voltage_V + ((current_mA/1000) * self._rint(temp_deg))
        return ocv_V

    def _rint(self, temp_deg):

        temp_deg = max(min(temp_deg, self.temp_keys_list[-1]),
                       self.temp_keys_list[0])

        [a, b, c, d] = self.battery_model_data['r_int']
        return (a + b*temp_deg) / (c + d*temp_deg)

    def _total_capacity(self, temp_deg, discharging_mode):

        temp_deg = max(min(temp_deg, self.temp_keys_list[-1]),
                       self.temp_keys_list[0])

        ocv_curves = self.battery_model_data['ocv_curves']

        for i, curve_temp in enumerate(self.temp_keys_list):

            if(curve_temp >= temp_deg):
                # Linear interpolation
                t2 = curve_temp
                t1 = self.temp_keys_list[i-1]
                if discharging_mode:
                    AH2 = ocv_curves[t2]['total_capacity']
                    AH1 = ocv_curves[t1]['total_capacity']
                else:
                    AH2 = ocv_curves[t2]['total_capacity_charge']
                    AH1 = ocv_curves[t1]['total_capacity_charge']

                return self._linear_interpolation(AH1, AH2, t1, t2, temp_deg)

    def _linear_interpolation(self, y1, y2, x1, x2, x):
        """
        Linear interpolation between two points and given x between them.
        (x1,y1) - First known point on the line
        (x2,y2) - Secodnf known point on the line
        x - Interpolated value, following rule have to apply (x1 < x < x2)
        """
        a = (y2-y1)/(x2-x1)
        b = y2 - a*x2
        return a*x + b

    def _interpolate_ocv_at_temp(self, soc, temp,discharge_mode):

        temp = max(min(temp, self.temp_keys_list[-1]), self.temp_keys_list[0])

        for i, curve_temp in enumerate(self.temp_keys_list):

            if(curve_temp >= temp):
                # Linear interpolation
                t2 = curve_temp
                t1 = self.temp_keys_list[i-1]
                voc2 = self._ocv(self.battery_model_data['ocv_curves'][t2], soc, discharge_mode)
                voc1 = self._ocv(self.battery_model_data['ocv_curves'][t1], soc, discharge_mode)
                return self._linear_interpolation(voc1, voc2, t1, t2, temp)

        pass

    def _interpolate_soc_at_temp(self, ocv, temp, discharge_mode):

        temp = max(min(temp, self.temp_keys_list[-1]), self.temp_keys_list[0])

        ocv_curves = self.battery_model_data['ocv_curves']

        for i, curve_temp in enumerate(self.temp_keys_list):

            if(curve_temp >= temp):

                # Linear interpolation
                t2 = curve_temp
                t1 = self.temp_keys_list[i-1]

                soc2 = self._soc(ocv_curves[t2], ocv, discharge_mode)
                soc1 = self._soc(ocv_curves[t1], ocv, discharge_mode)

                soc_inter = self._linear_interpolation(soc2, soc1, t2, t1, temp)

                return soc_inter

        pass

    def _intrepolate_ocv_slope_at_temp(self, soc, temp, discharge_mode):
        """
        Calculate the slope of the SOC curve at a given SOC and temperature.
        The slope is calculated as the derivative of the SOC function.
        The derivative is piecewise defined, so we need to check which
        segment the SOC falls into and calculate the slope accordingly.
        """

        temp = max(min(temp, self.temp_keys_list[-1]), self.temp_keys_list[0])

        ocv_curves = self.battery_model_data['ocv_curves']

        for i, curve_temp in enumerate(self.temp_keys_list):

            if(curve_temp >= temp):
                # Linear interpolation
                t2 = curve_temp
                t1 = self.temp_keys_list[i-1]

                slope2 = self._ocv_slope(ocv_curves[t2], soc, discharge_mode)
                slope1 = self._ocv_slope(ocv_curves[t1], soc, discharge_mode)

                return self._linear_interpolation(slope2, slope1, t2, t1, temp)

        pass

    def _ocv(self, ocv_curve, soc, discharge_mode):

        soc = max(min(soc, 1), 0)

        if(discharge_mode):
            [m, b, a1, b1, c1, d1, a3, b3, c3, d3] = ocv_curve['ocv_discharge']
        else:
            [m, b, a1, b1, c1, d1, a3, b3, c3, d3] = ocv_curve['ocv_charge']

        if(soc < self.soc_breakpoint_1):
            # First segment (rational)
            return (a1 + b1*soc) / (c1 + d1*soc)
        elif(soc >= self.soc_breakpoint_1 and soc <= self.soc_breakpoint_2):
            # Middle segment (linear)
            return m*soc + b
        elif(soc > self.soc_breakpoint_2):
            # Third segment (rational)
            return (a3 + b3*soc) / (c3 + d3*soc)

        raise ValueError("SOC if out of range")


    def _ocv_slope(self, ocv_curve, soc, discharge_mode):
        """
        Calculate the slope of the OCV curve at a given SOC.
        The slope is calculated as the derivative of the OCV function.
        The derivative is piecewise defined, so we need to check which
        segment the SOC falls into and calculate the slope accordingly.
        """

        if(discharge_mode):
            [m, b, a1, b1, c1, d1, a3, b3, c3, d3] = ocv_curve['ocv_discharge']
        else:
            [m, b, a1, b1, c1, d1, a3, b3, c3, d3] = ocv_curve['ocv_charge']


        if(soc < self.soc_breakpoint_1):
            # First segment (rational)
            return (b1*c1 - a1*d1) / ((c1 + d1*soc)**2)
        elif(soc >= self.soc_breakpoint_1 and soc <= self.soc_breakpoint_2):
            # Middle segment (linear)
            return m
        elif(soc > self.soc_breakpoint_2):
            # Third segment (rational)
            return (b3*c3 - a3*d3) / ((c3 + d3*soc)**2)
        raise ValueError("SOC is out of range")


    def _soc(self, ocv_curve, ocv, discharge_mode):

        ocv_breakpoint_1 = self._ocv(ocv_curve, self.soc_breakpoint_1, discharge_mode)
        ocv_breakpoint_2 = self._ocv(ocv_curve, self.soc_breakpoint_2, discharge_mode)

        if(discharge_mode):
            [m, b, a1, b1, c1, d1, a3, b3, c3, d3] = ocv_curve['ocv_discharge']
        else:
            [m, b, a1, b1, c1, d1, a3, b3, c3, d3] = ocv_curve['ocv_charge']

        if(ocv < ocv_breakpoint_1):
            # First segment (rational)
            return (a1 - c1*ocv)/(d1*ocv - b1)
        elif(ocv >= ocv_breakpoint_1 and ocv <= ocv_breakpoint_2):
            # Middle segment (linear)
            return (ocv - b)/m
        elif(ocv > ocv_breakpoint_2):
            # Third segment (rational)
            return (a3 - c3*ocv)/(d3*ocv - b3)

        raise ValueError("OCV is out of range")
