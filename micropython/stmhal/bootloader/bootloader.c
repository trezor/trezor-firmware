#include STM32_HAL_H

#include "crypto.h"
#include "ui.h"
#include "display.h"

void SystemClock_Config(void);

int main(void) {

    HAL_Init();

    SystemClock_Config();

    __GPIOA_CLK_ENABLE();
    __GPIOB_CLK_ENABLE();
    __GPIOC_CLK_ENABLE();
    __GPIOD_CLK_ENABLE();

    display_init();
    display_clear();

    uint8_t hash[32];
    hash_flash(hash);

    screen_welcome();

    uint8_t *pubkey = (uint8_t *)"ThisIsJustAFakePublicKeyForTest!";
    uint8_t *signature = (uint8_t *)"ThisIsJustAFakeSignatureToTestTheVerifyMechanismInTRZRBootloader";
    ed25519_verify(hash, 32, pubkey, signature);

    for (;;) {
        display_backlight(255);
        HAL_Delay(250);
        display_backlight(0);
        HAL_Delay(250);
    }

    return 0;
}
