#define BTN_PIN_LEFT    GPIO_PIN_5
#define BTN_PIN_RIGHT   GPIO_PIN_2

#define DISPLAY_RESX        128
#define DISPLAY_RESY        64
#define BTN_LEFT_COORDS     touch_pack_xy(0, DISPLAY_RESY - 1)
#define BTN_RIGHT_COORDS    touch_pack_xy(DISPLAY_RESX - 1, DISPLAY_RESY - 1)

void touch_init(void) {
    __HAL_RCC_GPIOC_CLK_ENABLE();

    GPIO_InitTypeDef GPIO_InitStructure;

    // PC4 capacitive touch panel module (CTPM) interrupt (INT) input
    GPIO_InitStructure.Mode  = GPIO_MODE_INPUT;
    GPIO_InitStructure.Pull  = GPIO_PULLUP;
    GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
    GPIO_InitStructure.Pin   = BTN_PIN_LEFT | BTN_PIN_RIGHT;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStructure);
}

void touch_power_on(void) { }

void touch_power_off(void) { }

uint32_t touch_read(void)
{
    static char last_left = 0, last_right = 0;
    char left  = (GPIO_PIN_RESET == HAL_GPIO_ReadPin(GPIOC, BTN_PIN_LEFT));
    char right = (GPIO_PIN_RESET == HAL_GPIO_ReadPin(GPIOC, BTN_PIN_RIGHT));
    if (last_left != left) {
        last_left = left;
        if (left) {
            return TOUCH_START | BTN_LEFT_COORDS;
        } else {
            return TOUCH_END | BTN_LEFT_COORDS;
        }
    }
    if (last_right != right) {
        last_right = right;
        if (right) {
            return TOUCH_START | BTN_RIGHT_COORDS;
        } else {
            return TOUCH_END | BTN_RIGHT_COORDS;
        }
    }
    return 0;
}

uint32_t touch_is_detected(void)
{
    return (GPIO_PIN_RESET == HAL_GPIO_ReadPin(GPIOC, BTN_PIN_LEFT)) || (GPIO_PIN_RESET == HAL_GPIO_ReadPin(GPIOC, BTN_PIN_RIGHT));
}
