from trezor.crypto import random

maximum_used_memory_in_bytes = 10 * 1024


# Round a float to 2 significant digits and return it as a string, do not use scientific notation
def format_float(value: float) -> str:
    def get_magnitude(value: float) -> int:
        if value == 0:
            return 0

        if value < 0:
            value = -value

        magnitude = 0
        if value < 1:
            while value < 1:
                value = 10 * value
                magnitude -= 1
        else:
            while value >= 10:
                value = value / 10
                magnitude += 1
        return magnitude

    significant_digits = 2
    precision_digits = significant_digits - get_magnitude(value) - 1
    rounded_value = round(value, precision_digits)

    return f"{rounded_value:.{max(0, precision_digits)}f}"


def random_bytes(length: int) -> bytes:
    # Fast linear congruential generator from Numerical Recipes
    def lcg(seed: int) -> int:
        return (1664525 * seed + 1013904223) & 0xFFFFFFFF

    array = bytearray(length)
    seed = random.uniform(0xFFFFFFFF)
    for i in range(length):
        seed = lcg(seed)
        array[i] = seed & 0xFF
    return bytes(array)
