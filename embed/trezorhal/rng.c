#include STM32_HAL_H

int rng_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_RNGEN; // enable TRNG peripheral clock
    RNG->CR = RNG_CR_RNGEN; // enable TRNG
    return 0;
}

uint32_t rng_read(const uint32_t previous, const uint32_t compare_previous)
{
    uint32_t temp = previous;
    do {
        while ((RNG->SR & (RNG_SR_SECS | RNG_SR_CECS | RNG_SR_DRDY)) != RNG_SR_DRDY) {
            ; // wait until TRNG is ready
        }
        temp = RNG->DR; // read the data from the TRNG
    } while (compare_previous && (temp == previous)); // RM0090 section 24.3.1 FIPS continuous random number generator test
    return temp;
}

uint32_t rng_get(void)
{
    // reason for keeping history: RM0090 section 24.3.1 FIPS continuous random number generator test
    static uint32_t previous = 0, current = 0;
    if (previous == current) {
        previous = rng_read(previous, 0);
    } else {
        previous = current;
    }
    current = rng_read(previous, 1);
    return current;
}
