from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Telemetry, TelemetryGet


async def get_telemetry(msg: TelemetryGet) -> Telemetry:
    from trezor.messages import Telemetry
    from trezor.utils import telemetry_get

    data = telemetry_get()
    if data:
        min_temp_c, max_temp_c, battery_errors, battery_cycles = data
        return Telemetry(
            min_temp_c=min_temp_c,
            max_temp_c=max_temp_c,
            battery_errors=battery_errors,
            battery_cycles=battery_cycles,
        )
    else:
        return Telemetry()
