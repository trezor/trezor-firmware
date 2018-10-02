#define BTN_PIN_LEFT    GPIO_PIN_5
#define BTN_PIN_RIGHT   GPIO_PIN_2

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
            return TOUCH_START | touch_pack_xy(0, 63);
        } else {
            return TOUCH_END | touch_pack_xy(0, 63);
        }
    }
    if (last_right != right) {
        last_right = right;
        if (right) {
            return TOUCH_START | touch_pack_xy(127, 63);
        } else {
            return TOUCH_END | touch_pack_xy(127, 63);
        }
    }
    return 0;
}

uint32_t touch_is_detected(void)
{
    return (GPIO_PIN_RESET == HAL_GPIO_ReadPin(GPIOC, BTN_PIN_LEFT)) || (GPIO_PIN_RESET == HAL_GPIO_ReadPin(GPIOC, BTN_PIN_RIGHT));
}
