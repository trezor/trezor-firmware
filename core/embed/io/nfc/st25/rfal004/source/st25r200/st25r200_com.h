
/******************************************************************************
  * @attention
  *
  * COPYRIGHT 2022 STMicroelectronics, all rights reserved
  *
  * Unless required by applicable law or agreed to in writing, software
  * distributed under the License is distributed on an "AS IS" BASIS,
  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied,
  * AND SPECIFICALLY DISCLAIMING THE IMPLIED WARRANTIES OF MERCHANTABILITY,
  * FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
  * See the License for the specific language governing permissions and
  * limitations under the License.
  *
******************************************************************************/



/*
 *      PROJECT:   ST25R200 firmware
 *      Revision: 
 *      LANGUAGE:  ISO C99
 */

/*! \file st25r200_com.h
 *
 *  \author Gustavo Patricio
 *
 *  \brief ST25R200 communication declaration file
 *  
 *  This driver provides basic abstraction for communication with the ST25R200
 *  
 *
 * \addtogroup RFAL
 * @{
 *
 * \addtogroup RFAL-HAL
 * \brief RFAL Hardware Abstraction Layer
 * @{
 *
 * \addtogroup ST25R200
 * \brief RFAL ST25R200 Driver
 * @{
 * 
 * \addtogroup ST25R200_COM
 * \brief RFAL ST25R200 Communications
 * @{
 * 
 */


#ifndef ST25R200_COM_H
#define ST25R200_COM_H

/*
******************************************************************************
* INCLUDES
******************************************************************************
*/
#include "rfal_platform.h"
#include "rfal_utils.h"

/*
******************************************************************************
* GLOBAL DEFINES
******************************************************************************
*/
#define ST25R200_FIFO_STATUS_LEN                           2        /*!< Number of FIFO Status Register                                    */
#define ST25R200_OBS_MODE_LEN                              2        /*!< Number of Observation Mode Config Registers                       */

#define ST25R200_REG_OPERATION                             0x00U    /*!< RW Operation Register                                             */
#define ST25R200_REG_GENERAL                               0x01U    /*!< RW General Register                                               */
#define ST25R200_REG_REGULATOR                             0x02U    /*!< RW Regulator Register                                             */
#define ST25R200_REG_TX_DRIVER                             0x03U    /*!< RW TX Driver Register                                             */
#define ST25R200_REG_TX_MOD                                0x04U    /*!< RW TX Modulation Register                                         */
#define ST25R200_REG_TX_RES_MOD                            0x05U    /*!< RW TX Resistive Modulation Register                               */
#define ST25R200_REG_RX_ANA1                               0x06U    /*!< RW RX Path Analog Register 1                                      */
#define ST25R200_REG_RX_ANA2                               0x07U    /*!< RW RX Path Analog Register 2                                      */
#define ST25R200_REG_RX_DIG                                0x08U    /*!< RW RX Path Digital Register                                       */
#define ST25R200_REG_CORR1                                 0x09U    /*!< RW Correlator Register 1                                          */
#define ST25R200_REG_CORR2                                 0x0AU    /*!< RW Correlator Register 2                                          */
#define ST25R200_REG_CORR3                                 0x0BU    /*!< RW Correlator Register 3                                          */
#define ST25R200_REG_CORR4                                 0x0CU    /*!< RW Correlator Register 4                                          */
#define ST25R200_REG_CORR5                                 0x0DU    /*!< RW Correlator Register 5                                          */
#define ST25R200_REG_CORR6                                 0x0EU    /*!< RW Correlator Register 6                                          */
#define ST25R200_REG_DISPLAY1                              0x0FU    /*!< RW Correlator Register 7                                          */
#define ST25R200_REG_DISPLAY2                              0x10U    /*!< RO Regulator and Gain Display Register                            */
#define ST25R200_REG_STATUS                                0x11U    /*!< RO Status Register                                                */
#define ST25R200_REG_PROTOCOL                              0x12U    /*!< RW Protocol Register                                              */
#define ST25R200_REG_PROTOCOL_TX1                          0x13U    /*!< RW Protocol TX Register 1                                         */
#define ST25R200_REG_PROTOCOL_TX2                          0x14U    /*!< RW Protocol TX Register 2                                         */
#define ST25R200_REG_PROTOCOL_TX3                          0x15U    /*!< RW Protocol TX Register 3                                         */
#define ST25R200_REG_PROTOCOL_RX1                          0x16U    /*!< RW Protocol RX Register 1                                         */
#define ST25R200_REG_PROTOCOL_RX2                          0x17U    /*!< RW Protocol RX Register 2                                         */
#define ST25R200_REG_PROTOCOL_RX3                          0x18U    /*!< RW Protocol RX Register 3                                         */
#define ST25R200_REG_EMD1                                  0x19U    /*!< RW Protocol EMD Register 1                                        */
#define ST25R200_REG_EMD2                                  0x1AU    /*!< RW Protocol EMD Register 2                                        */
#define ST25R200_REG_MRT_SQT_CONF                          0x1BU    /*!< RW Mask Receive and Squelch Timer Configuration Register          */
#define ST25R200_REG_MRT                                   0x1CU    /*!< RW Mask Receive Timer Register                                    */
#define ST25R200_REG_SQT                                   0x1DU    /*!< RW Squelch Timer Register                                         */
#define ST25R200_REG_NRT_GPT_CONF                          0x1EU    /*!< RW No Response and Genereal Purpose Timer Configuration Register  */
#define ST25R200_REG_NRT1                                  0x1FU    /*!< RW No Response Timer (MSB) Register 1                             */
#define ST25R200_REG_NRT2                                  0x20U    /*!< RW No Response Timer (LSB) Register 2                             */
#define ST25R200_REG_GPT1                                  0x21U    /*!< RW General Purpose Timer (MSB) Register 1                         */
#define ST25R200_REG_GPT2                                  0x22U    /*!< RW General Purpose Timer (LSB) Register 2                         */
#define ST25R200_REG_DISPLAY3                              0x23U    /*!< RO Display Register 2                                             */
#define ST25R200_REG_DISPLAY4                              0x24U    /*!< RO Display Register 3                                             */
#define ST25R200_REG_OVUNSHOOT_CONF                        0x25U    /*!< RW Overshoot and Undershoot Configuration Register                */
#define ST25R200_REG_OVERSHOOT_CONF                        0x26U    /*!< RW Overshoot Pattern Register                                     */
#define ST25R200_REG_UNDERSHOOT_CONF                       0x27U    /*!< RW Undershoot Pattern Register                                    */
#define ST25R200_REG_WAKEUP_CONF1                          0x28U    /*!< RW Wake-up COnfiguration Register 1                               */
#define ST25R200_REG_WAKEUP_CONF2                          0x29U    /*!< RW Wake-up COnfiguration Register 2                               */
#define ST25R200_REG_WU_I_CONF                             0x2AU    /*!< RW Wake-up I-Channel Configuration Register                       */
#define ST25R200_REG_WU_I_DELTA                            0x2BU    /*!< RW Wake-up I-Channel Delta Register                               */
#define ST25R200_REG_WU_I_ADC                              0x2CU    /*!< RO Wake-up I-Channel Calibration Display Register                 */
#define ST25R200_REG_WU_I_REF                              0x2DU    /*!< RO Wake-up I-Channel Reference Display Register                   */
#define ST25R200_REG_WU_I_CAL                              0x2EU    /*!< RO Wake-up I-Channel Calibration Display Register                 */
#define ST25R200_REG_WU_Q_CONF                             0x2FU    /*!< RW Wake-up Q-Channel Configuration Register                       */
#define ST25R200_REG_WU_Q_DELTA                            0x30U    /*!< RW Wake-up Q-Channel Delta Register                               */
#define ST25R200_REG_WU_Q_ADC                              0x31U    /*!< RO Wake-up Q-Channel ADC Display Register                         */
#define ST25R200_REG_WU_Q_REF                              0x32U    /*!< RO Wake-up Q-Channel Reference Display Register                   */
#define ST25R200_REG_WU_Q_CAL                              0x33U    /*!< RO Wake-up Q-Channel Calibration Display Register                 */
#define ST25R200_REG_TX_FRAME1                             0x34U    /*!< RW TX Frame Register 1                                            */
#define ST25R200_REG_TX_FRAME2                             0x35U    /*!< RW TX Frame Register 2                                            */
#define ST25R200_REG_FIFO_STATUS1                          0x36U    /*!< RO FIFO Status Register 1                                         */
#define ST25R200_REG_FIFO_STATUS2                          0x37U    /*!< RO FIFO Status Register 2                                         */
#define ST25R200_REG_COLLISION                             0x38U    /*!< RO Collision Register 2                                           */
#define ST25R200_REG_IRQ_MASK1                             0x39U    /*!< RO IRQ Mask Register 1                                            */
#define ST25R200_REG_IRQ_MASK2                             0x3AU    /*!< RO IRQ Mask Register 2                                            */
#define ST25R200_REG_IRQ_MASK3                             0x3BU    /*!< RO IRQ Mask Register 3                                            */
#define ST25R200_REG_IRQ1                                  0x3CU    /*!< RO IRQ Register 1                                                 */
#define ST25R200_REG_IRQ2                                  0x3DU    /*!< RO IRQ Register 2                                                 */
#define ST25R200_REG_IRQ3                                  0x3EU    /*!< RO IRQ Register 3                                                 */
#define ST25R200_REG_IC_ID                                 0x3FU    /*!< RO IC Identity Register                                           */


/*! Register bit definitions  \cond DOXYGEN_SUPPRESS */

#define ST25R200_REG_OPERATION_rfu2                           (1U<<7)
#define ST25R200_REG_OPERATION_rfu1                           (1U<<6)
#define ST25R200_REG_OPERATION_tx_en                          (1U<<5)
#define ST25R200_REG_OPERATION_rx_en                          (1U<<4)
#define ST25R200_REG_OPERATION_am_en                          (1U<<3)
#define ST25R200_REG_OPERATION_rfu0                           (1U<<2)
#define ST25R200_REG_OPERATION_en                             (1U<<1)
#define ST25R200_REG_OPERATION_wu_en                          (1U<<0)
                                                               
#define ST25R200_REG_GENERAL_rfu1                             (1U<<7)
#define ST25R200_REG_GENERAL_sink_mode                        (1U<<6)
#define ST25R200_REG_GENERAL_single                           (1U<<5)
#define ST25R200_REG_GENERAL_rfo2                             (1U<<4)
#define ST25R200_REG_GENERAL_miso_pd2                         (1U<<3)
#define ST25R200_REG_GENERAL_miso_pd1                         (1U<<2)
#define ST25R200_REG_GENERAL_miso_pd_mask                     (0x3U<<2)
#define ST25R200_REG_GENERAL_miso_pd_shift                    (2U)
#define ST25R200_REG_GENERAL_rfu0                             (1U<<1)
#define ST25R200_REG_GENERAL_reg_s                            (1U<<0)

#define ST25R200_REG_REGULATOR_regd2                          (1U<<7)
#define ST25R200_REG_REGULATOR_regd1                          (1U<<6)
#define ST25R200_REG_REGULATOR_regd0                          (1U<<5)
#define ST25R200_REG_REGULATOR_regd_200mV                     (0U<<5)
#define ST25R200_REG_REGULATOR_regd_250mV                     (1U<<5)
#define ST25R200_REG_REGULATOR_regd_300mV                     (2U<<5)
#define ST25R200_REG_REGULATOR_regd_350mV                     (3U<<5)
#define ST25R200_REG_REGULATOR_regd_400mV                     (4U<<5)
#define ST25R200_REG_REGULATOR_regd_450mV                     (5U<<5)
#define ST25R200_REG_REGULATOR_regd_500mV                     (6U<<5)
#define ST25R200_REG_REGULATOR_regd_550mV                     (7U<<5)
#define ST25R200_REG_REGULATOR_regd_mask                      (7U<<5)
#define ST25R200_REG_REGULATOR_regd_shift                     (5U)
#define ST25R200_REG_REGULATOR_rege4                          (1U<<4)
#define ST25R200_REG_REGULATOR_rege3                          (1U<<3)
#define ST25R200_REG_REGULATOR_rege2                          (1U<<2)
#define ST25R200_REG_REGULATOR_rege1                          (1U<<1)
#define ST25R200_REG_REGULATOR_rege0                          (1U<<0)
#define ST25R200_REG_REGULATOR_rege_mask                      (0x1FU<<0)
#define ST25R200_REG_REGULATOR_rege_shift                     (0U)
#define ST25R200_REG_REGULATOR_rege_5100mV                    (0x1FU<<0)
#define ST25R200_REG_REGULATOR_rege_5002mV                    (0x1EU<<0)
#define ST25R200_REG_REGULATOR_rege_4940mV                    (0x1DU<<0)
#define ST25R200_REG_REGULATOR_rege_4860mV                    (0x1CU<<0)
#define ST25R200_REG_REGULATOR_rege_4780mV                    (0x1BU<<0)
#define ST25R200_REG_REGULATOR_rege_4000mV                    (0x1AU<<0)
#define ST25R200_REG_REGULATOR_rege_3420mV                    (0x0AU<<0)
#define ST25R200_REG_REGULATOR_rege_3340mV                    (0x09U<<0)
#define ST25R200_REG_REGULATOR_rege_2620mV                    (0x00U<<0)

#define ST25R200_REG_TX_DRIVER_rfu3                           (1U<<7)
#define ST25R200_REG_TX_DRIVER_rfu2                           (1U<<6)
#define ST25R200_REG_TX_DRIVER_rfu1                           (1U<<5)
#define ST25R200_REG_TX_DRIVER_rfu0                           (1U<<4)
#define ST25R200_REG_TX_DRIVER_d_res3                         (1U<<3)
#define ST25R200_REG_TX_DRIVER_d_res2                         (1U<<2)
#define ST25R200_REG_TX_DRIVER_d_res1                         (1U<<1)
#define ST25R200_REG_TX_DRIVER_d_res0                         (1U<<0)
#define ST25R200_REG_TX_DRIVER_d_res_mask                     (0xFU<<0)
#define ST25R200_REG_TX_DRIVER_d_res_shift                    (0U)
                           
#define ST25R200_REG_TX_MOD_am_mod3                           (1U<<7)
#define ST25R200_REG_TX_MOD_am_mod2                           (1U<<6)
#define ST25R200_REG_TX_MOD_am_mod1                           (1U<<5)
#define ST25R200_REG_TX_MOD_am_mod0                           (1U<<4)
#define ST25R200_REG_TX_MOD_am_mod_8percent                   (0x0U<<4)
#define ST25R200_REG_TX_MOD_am_mod_9percent                   (0x1U<<4)
#define ST25R200_REG_TX_MOD_am_mod_10percent                  (0x2U<<4)
#define ST25R200_REG_TX_MOD_am_mod_11percent                  (0x3U<<4)
#define ST25R200_REG_TX_MOD_am_mod_12percent                  (0x4U<<4)
#define ST25R200_REG_TX_MOD_am_mod_13percent                  (0x5U<<4)
#define ST25R200_REG_TX_MOD_am_mod_14percent                  (0x6U<<4)
#define ST25R200_REG_TX_MOD_am_mod_15percent                  (0x7U<<4)
#define ST25R200_REG_TX_MOD_am_mod_17percent                  (0x8U<<4)
#define ST25R200_REG_TX_MOD_am_mod_19percent                  (0x9U<<4)
#define ST25R200_REG_TX_MOD_am_mod_22percent                  (0xAU<<4)
#define ST25R200_REG_TX_MOD_am_mod_26percent                  (0xBU<<4)
#define ST25R200_REG_TX_MOD_am_mod_30percent                  (0xCU<<4)
#define ST25R200_REG_TX_MOD_am_mod_35percent                  (0xDU<<4)
#define ST25R200_REG_TX_MOD_am_mod_45percent                  (0xEU<<4)
#define ST25R200_REG_TX_MOD_am_mod_55percent                  (0xFU<<4)
#define ST25R200_REG_TX_MOD_am_mod_mask                       (0xFU<<4)
#define ST25R200_REG_TX_MOD_am_mod_shift                      (4U)
#define ST25R200_REG_TX_MOD_mod_state                         (1U<<3)
#define ST25R200_REG_TX_MOD_rfu                               (1U<<2)
#define ST25R200_REG_TX_MOD_res_am                            (1U<<1)
#define ST25R200_REG_TX_MOD_reg_am                            (1U<<0)

#define ST25R200_REG_TX_RES_MOD_am_ref_sel                    (1U<<7)
#define ST25R200_REG_TX_RES_MOD_md_res6                       (1U<<6)
#define ST25R200_REG_TX_RES_MOD_md_res5                       (1U<<5)
#define ST25R200_REG_TX_RES_MOD_md_res4                       (1U<<4)
#define ST25R200_REG_TX_RES_MOD_md_res3                       (1U<<3)
#define ST25R200_REG_TX_RES_MOD_md_res2                       (1U<<2)
#define ST25R200_REG_TX_RES_MOD_md_res1                       (1U<<1)
#define ST25R200_REG_TX_RES_MOD_md_res0                       (1U<<0)
#define ST25R200_REG_TX_RES_MOD_md_res_mask                   (3U<<0)
#define ST25R200_REG_TX_RES_MOD_md_res_shift                  (0U)

#define ST25R200_REG_RX_ANA1_rfu5                             (1U<<7)
#define ST25R200_REG_RX_ANA1_rfu4                             (1U<<6)
#define ST25R200_REG_RX_ANA1_rfu3                             (1U<<5)
#define ST25R200_REG_RX_ANA1_rfu2                             (1U<<4)
#define ST25R200_REG_RX_ANA1_rfu1                             (1U<<3)
#define ST25R200_REG_RX_ANA1_rfu0                             (1U<<2)
#define ST25R200_REG_RX_ANA1_hpf_ctrl1                        (1U<<1)
#define ST25R200_REG_RX_ANA1_hpf_ctrl0                        (1U<<0)
#define ST25R200_REG_RX_ANA1_hpf_ctrl_mask                    (3U<<0)
#define ST25R200_REG_RX_ANA1_hpf_ctrl_shift                   (0U)
                                                              
#define ST25R200_REG_RX_ANA2_afe_gain_rw3                     (1U<<7)
#define ST25R200_REG_RX_ANA2_afe_gain_rw2                     (1U<<6)
#define ST25R200_REG_RX_ANA2_afe_gain_rw1                     (1U<<5)
#define ST25R200_REG_RX_ANA2_afe_gain_rw0                     (1U<<4)
#define ST25R200_REG_RX_ANA2_afe_gain_rw_mask                 (0x0FU<<4)
#define ST25R200_REG_RX_ANA2_afe_gain_rw_shift                (4U)
#define ST25R200_REG_RX_ANA2_afe_gain_td3                     (1U<<3)
#define ST25R200_REG_RX_ANA2_afe_gain_td2                     (1U<<2)
#define ST25R200_REG_RX_ANA2_afe_gain_td1                     (1U<<1)
#define ST25R200_REG_RX_ANA2_afe_gain_td0                     (1U<<0)
#define ST25R200_REG_RX_ANA2_afe_gain_td_mask                 (0x0FU<<0)
#define ST25R200_REG_RX_ANA2_afe_gain_td_shift                (0U)
                                                              
#define ST25R200_REG_RX_DIG_agc_en                            (1U<<7)
#define ST25R200_REG_RX_DIG_lpf_coef2                         (1U<<6)
#define ST25R200_REG_RX_DIG_lpf_coef1                         (1U<<5)
#define ST25R200_REG_RX_DIG_lpf_coef0                         (1U<<4)
#define ST25R200_REG_RX_DIG_lpf_coef_mask                     (7U<<4)
#define ST25R200_REG_RX_DIG_lpf_coef_shift                    (4U)
#define ST25R200_REG_RX_DIG_hpf_coef1                         (1U<<3)
#define ST25R200_REG_RX_DIG_hpf_coef0                         (1U<<2)
#define ST25R200_REG_RX_DIG_hpf_coef_mask                     (3U<<2)
#define ST25R200_REG_RX_DIG_hpf_coef_shift                    (2U)
#define ST25R200_REG_RX_DIG_hpf_rfu                           (1U<<1)
#define ST25R200_REG_RX_DIG_hpf_dis_corr                      (1U<<0)

#define ST25R200_REG_CORR1_iir_coef2_3                        (1U<<7)
#define ST25R200_REG_CORR1_iir_coef2_2                        (1U<<6)
#define ST25R200_REG_CORR1_iir_coef2_1                        (1U<<5)
#define ST25R200_REG_CORR1_iir_coef2_0                        (1U<<4)
#define ST25R200_REG_CORR1_iir_coef2_mask                     (0x0FU<<4)
#define ST25R200_REG_CORR1_iir_coef2_shift                    (4U)
#define ST25R200_REG_CORR1_iir_coef1_3                        (1U<<3)
#define ST25R200_REG_CORR1_iir_coef1_2                        (1U<<2)
#define ST25R200_REG_CORR1_iir_coef1_1                        (1U<<1)
#define ST25R200_REG_CORR1_iir_coef1_0                        (1U<<0)
#define ST25R200_REG_CORR1_iir_coef1_mask                     (0x0FU<<0)
#define ST25R200_REG_CORR1_iir_coef1_shift                    (0U)

#define ST25R200_REG_CORR2_agc_thr_squelch_3                  (1U<<7)
#define ST25R200_REG_CORR2_agc_thr_squelch_2                  (1U<<6)
#define ST25R200_REG_CORR2_agc_thr_squelch_1                  (1U<<5)
#define ST25R200_REG_CORR2_agc_thr_squelch_0                  (1U<<4)
#define ST25R200_REG_CORR2_agc_thr_squelch_mask               (0x0FU<<4)
#define ST25R200_REG_CORR2_agc_thr_squelch_shift              (4U)
#define ST25R200_REG_CORR2_agc_thr_3                          (1U<<3)
#define ST25R200_REG_CORR2_agc_thr_2                          (1U<<2)
#define ST25R200_REG_CORR2_agc_thr_1                          (1U<<1)
#define ST25R200_REG_CORR2_agc_thr_0                          (1U<<0)
#define ST25R200_REG_CORR2_agc_thr_mask                       (0x0FU<<0)
#define ST25R200_REG_CORR2_agc_thr_shift                      (0U)

#define ST25R200_REG_CORR3_rfu1                               (1U<<7)
#define ST25R200_REG_CORR3_rfu0                               (1U<<6)
#define ST25R200_REG_CORR3_start_wait5                        (1U<<5)
#define ST25R200_REG_CORR3_start_wait4                        (1U<<4)
#define ST25R200_REG_CORR3_start_wait3                        (1U<<3)
#define ST25R200_REG_CORR3_start_wait2                        (1U<<2)
#define ST25R200_REG_CORR3_start_wait1                        (1U<<1)
#define ST25R200_REG_CORR3_start_wait0                        (1U<<0)
#define ST25R200_REG_CORR3_start_wait_mask                    (0x3FU<<0)
#define ST25R200_REG_CORR3_start_wait_shift                   (0U)

#define ST25R200_REG_CORR4_coll_lvl3                          (1U<<7)
#define ST25R200_REG_CORR4_coll_lvl2                          (1U<<6)
#define ST25R200_REG_CORR4_coll_lvl1                          (1U<<5)
#define ST25R200_REG_CORR4_coll_lvl0                          (1U<<4)
#define ST25R200_REG_CORR4_coll_lvl_mask                      (0x0FU<<4)
#define ST25R200_REG_CORR4_coll_lvl_shift                     (4U)
#define ST25R200_REG_CORR4_data_lvl3                          (1U<<3)
#define ST25R200_REG_CORR4_data_lvl2                          (1U<<2)
#define ST25R200_REG_CORR4_data_lvl1                          (1U<<1)
#define ST25R200_REG_CORR4_data_lvl0                          (1U<<0)
#define ST25R200_REG_CORR4_data_lvl_mask                      (0x0FU<<0)
#define ST25R200_REG_CORR4_data_lvl_shift                     (0U)

#define ST25R200_REG_CORR5_rfu2                               (1U<<7)
#define ST25R200_REG_CORR5_rfu1                               (1U<<6)
#define ST25R200_REG_CORR5_rfu0                               (1U<<5)
#define ST25R200_REG_CORR5_en_subc_end                        (1U<<4)
#define ST25R200_REG_CORR5_no_phase                           (1U<<3)
#define ST25R200_REG_CORR5_dec_f2                             (1U<<2)
#define ST25R200_REG_CORR5_dec_f1                             (1U<<1)
#define ST25R200_REG_CORR5_dec_f0                             (1U<<0)
#define ST25R200_REG_CORR5_dec_f_mask                         (0x7U<<0)
#define ST25R200_REG_CORR5_dec_f_shift                        (0U)

#define ST25R200_REG_CORR6_init_noise_lvl3                    (1U<<7)
#define ST25R200_REG_CORR6_init_noise_lvl2                    (1U<<6)
#define ST25R200_REG_CORR6_init_noise_lvl1                    (1U<<5)
#define ST25R200_REG_CORR6_init_noise_lvl0                    (1U<<4)
#define ST25R200_REG_CORR6_init_noise_lvl_mask                (0x0FU<<4)
#define ST25R200_REG_CORR6_init_noise_lvl_shift               (4U)
#define ST25R200_REG_CORR6_rfu3                               (1U<<3)
#define ST25R200_REG_CORR6_rfu2                               (1U<<2)
#define ST25R200_REG_CORR6_rfu1                               (1U<<1)
#define ST25R200_REG_CORR6_rfu0                               (1U<<0)

#define ST25R200_REG_DISPLAY1_i_lim                           (1U<<7)
#define ST25R200_REG_DISPLAY1_agd_ok                          (1U<<6)
#define ST25R200_REG_DISPLAY1_osc_ok                          (1U<<5)
#define ST25R200_REG_DISPLAY1_regc4                           (1U<<4)
#define ST25R200_REG_DISPLAY1_regc3                           (1U<<7)
#define ST25R200_REG_DISPLAY1_regc2                           (1U<<6)
#define ST25R200_REG_DISPLAY1_regc1                           (1U<<5)
#define ST25R200_REG_DISPLAY1_regc0                           (1U<<4)
#define ST25R200_REG_DISPLAY1_regc_mask                       (0x1FU<<0)
#define ST25R200_REG_DISPLAY1_regc_shift                      (0U)

#define ST25R200_REG_DISPLAY2_rfu3                            (1U<<7)
#define ST25R200_REG_DISPLAY2_rfu2                            (1U<<6)
#define ST25R200_REG_DISPLAY2_rfu1                            (1U<<5)
#define ST25R200_REG_DISPLAY2_rfu0                            (1U<<4)
#define ST25R200_REG_DISPLAY2_afe_gain3                       (1U<<3)
#define ST25R200_REG_DISPLAY2_afe_gain2                       (1U<<2)
#define ST25R200_REG_DISPLAY2_afe_gain1                       (1U<<1)
#define ST25R200_REG_DISPLAY2_afe_gain0                       (1U<<0)
#define ST25R200_REG_DISPLAY2_afe_gain_mask                   (0x0FU<<0)
#define ST25R200_REG_DISPLAY2_afe_gain_shift                  (0U)

#define ST25R200_REG_STATUS_subc_on                           (1U<<7)
#define ST25R200_REG_STATUS_gpt_on                            (1U<<6)
#define ST25R200_REG_STATUS_nrt_on                            (1U<<5)
#define ST25R200_REG_STATUS_mrt_on                            (1U<<4)
#define ST25R200_REG_STATUS_rx_act                            (1U<<3)
#define ST25R200_REG_STATUS_rx_on                             (1U<<2)
#define ST25R200_REG_STATUS_tx_on                             (1U<<1)
#define ST25R200_REG_STATUS_rfu                               (1U<<0)

#define ST25R200_REG_PROTOCOL_rx_rate1                        (1U<<7)
#define ST25R200_REG_PROTOCOL_rx_rate0                        (1U<<6)
#define ST25R200_REG_PROTOCOL_rxrate_106_26                   (0x0U<<6)
#define ST25R200_REG_PROTOCOL_rxrate_53                       (0x2U<<6)
#define ST25R200_REG_PROTOCOL_rx_rate_mask                    (0x03U<<6)
#define ST25R200_REG_PROTOCOL_rx_rate_shift                   (6U)
#define ST25R200_REG_PROTOCOL_tx_rate1                        (1U<<5)
#define ST25R200_REG_PROTOCOL_tx_rate0                        (1U<<4)
#define ST25R200_REG_PROTOCOL_tx_rate_106                     (0x0U<<4)
#define ST25R200_REG_PROTOCOL_tx_rate_mask                    (0x03U<<4)
#define ST25R200_REG_PROTOCOL_tx_rate_shift                   (4U)
#define ST25R200_REG_PROTOCOL_om3                             (1U<<3)
#define ST25R200_REG_PROTOCOL_om2                             (1U<<2)
#define ST25R200_REG_PROTOCOL_om1                             (1U<<1)
#define ST25R200_REG_PROTOCOL_om0                             (1U<<0)
#define ST25R200_REG_PROTOCOL_om_iso14443a                    (0x01U<<0)
#define ST25R200_REG_PROTOCOL_om_iso14443b                    (0x02U<<0)
#define ST25R200_REG_PROTOCOL_om_rfu                          (0x03U<<0)
#define ST25R200_REG_PROTOCOL_om_topaz                        (0x04U<<0)
#define ST25R200_REG_PROTOCOL_om_iso15693                     (0x05U<<0)
#define ST25R200_REG_PROTOCOL_om_mask                         (0x0FU<<0)
#define ST25R200_REG_PROTOCOL_om_shift                        (0U)

#define ST25R200_REG_PROTOCOL_TX1_rfu                         (1U<<7)
#define ST25R200_REG_PROTOCOL_TX1_a_tx_par                    (1U<<6)
#define ST25R200_REG_PROTOCOL_TX1_a_tx_par_on                 (1U<<6)
#define ST25R200_REG_PROTOCOL_TX1_a_tx_par_off                (0U<<6)
#define ST25R200_REG_PROTOCOL_TX1_tx_crc                      (1U<<5)
#define ST25R200_REG_PROTOCOL_TX1_tx_crc_on                   (1U<<5)
#define ST25R200_REG_PROTOCOL_TX1_tx_crc_off                  (0U<<5)
#define ST25R200_REG_PROTOCOL_TX1_tr_am                       (1U<<4)
#define ST25R200_REG_PROTOCOL_TX1_p_len3                      (1U<<3)
#define ST25R200_REG_PROTOCOL_TX1_p_len2                      (1U<<2)
#define ST25R200_REG_PROTOCOL_TX1_p_len1                      (1U<<1)
#define ST25R200_REG_PROTOCOL_TX1_p_len0                      (1U<<0)
#define ST25R200_REG_PROTOCOL_TX1_p_len_mask                  (0x0FU<<0)
#define ST25R200_REG_PROTOCOL_TX1_p_len_shift                 (0U)

#define ST25R200_REG_PROTOCOL_TX2_rfu3                        (1U<<7)
#define ST25R200_REG_PROTOCOL_TX2_rfu2                        (1U<<6)
#define ST25R200_REG_PROTOCOL_TX2_rfu1                        (1U<<5)
#define ST25R200_REG_PROTOCOL_TX2_rfu0                        (1U<<4)
#define ST25R200_REG_PROTOCOL_TX2_b_tx_sof_0                  (1U<<3)
#define ST25R200_REG_PROTOCOL_TX2_b_tx_sof_1                  (1U<<2)
#define ST25R200_REG_PROTOCOL_TX2_b_tx_sof_0_10etu            (0U<<3)
#define ST25R200_REG_PROTOCOL_TX2_b_tx_sof_0_11etu            (1U<<3)
#define ST25R200_REG_PROTOCOL_TX2_b_tx_sof_1_2etu             (0U<<3)
#define ST25R200_REG_PROTOCOL_TX2_b_tx_sof_1_3etu             (1U<<3)
#define ST25R200_REG_PROTOCOL_TX2_b_tx_sof_mask               (3U<<2)
#define ST25R200_REG_PROTOCOL_TX2_b_tx_sof_shift              (2U)
#define ST25R200_REG_PROTOCOL_TX2_b_tx_eof                    (1U<<1)
#define ST25R200_REG_PROTOCOL_TX2_b_tx_eof_11etu              (1U<<1)
#define ST25R200_REG_PROTOCOL_TX2_b_tx_eof_10etu              (0U<<1)
#define ST25R200_REG_PROTOCOL_TX2_b_tx_half                   (1U<<0)

#define ST25R200_REG_PROTOCOL_TX3_rfu7                        (1U<<7)
#define ST25R200_REG_PROTOCOL_TX3_rfu6                        (1U<<6)
#define ST25R200_REG_PROTOCOL_TX3_rfu5                        (1U<<5)
#define ST25R200_REG_PROTOCOL_TX3_rfu4                        (1U<<4)
#define ST25R200_REG_PROTOCOL_TX3_rfu3                        (1U<<3)
#define ST25R200_REG_PROTOCOL_TX3_rfu2                        (1U<<2)
#define ST25R200_REG_PROTOCOL_TX3_rfu1                        (1U<<1)
#define ST25R200_REG_PROTOCOL_TX3_rfu0                        (1U<<0)

#define ST25R200_REG_PROTOCOL_RX1_rfu1                        (1U<<7)
#define ST25R200_REG_PROTOCOL_RX1_rfu0                        (1U<<6)
#define ST25R200_REG_PROTOCOL_RX1_b_rx_sof                    (1U<<5)
#define ST25R200_REG_PROTOCOL_RX1_b_rx_eof                    (1U<<4)
#define ST25R200_REG_PROTOCOL_RX1_a_rx_par                    (1U<<3)
#define ST25R200_REG_PROTOCOL_RX1_a_rx_par_on                 (1U<<3)
#define ST25R200_REG_PROTOCOL_RX1_a_rx_par_off                (0U<<3)
#define ST25R200_REG_PROTOCOL_RX1_rx_crc                      (1U<<2)
#define ST25R200_REG_PROTOCOL_RX1_rx_crc_on                   (1U<<2)
#define ST25R200_REG_PROTOCOL_RX1_rx_crc_off                  (0U<<2)
#define ST25R200_REG_PROTOCOL_RX1_rx_nbtx                     (1U<<1)
#define ST25R200_REG_PROTOCOL_RX1_antcl                       (1U<<0)
#define ST25R200_REG_PROTOCOL_RX1_antcl_on                    (1U<<0)
#define ST25R200_REG_PROTOCOL_RX1_antcl_off                   (0U<<0)

#define ST25R200_REG_PROTOCOL_RX2_rfu                         (1U<<7)
#define ST25R200_REG_PROTOCOL_RX2_tr1_min_len6                (1U<<6)
#define ST25R200_REG_PROTOCOL_RX2_tr1_min_len5                (1U<<5)
#define ST25R200_REG_PROTOCOL_RX2_tr1_min_len4                (1U<<4)
#define ST25R200_REG_PROTOCOL_RX2_tr1_min_len3                (1U<<3)
#define ST25R200_REG_PROTOCOL_RX2_tr1_min_len2                (1U<<2)
#define ST25R200_REG_PROTOCOL_RX2_tr1_min_len1                (1U<<1)
#define ST25R200_REG_PROTOCOL_RX2_tr1_min_len0                (1U<<0)
#define ST25R200_REG_PROTOCOL_RX2_tr1_min_len_mask            (0x7FU<<0)
#define ST25R200_REG_PROTOCOL_RX2_tr1_min_len_shift           (0U)

#define ST25R200_REG_PROTOCOL_RX3_tr1_max_len7                (1U<<7)
#define ST25R200_REG_PROTOCOL_RX3_tr1_max_len6                (1U<<6)
#define ST25R200_REG_PROTOCOL_RX3_tr1_max_len5                (1U<<5)
#define ST25R200_REG_PROTOCOL_RX3_tr1_max_len4                (1U<<4)
#define ST25R200_REG_PROTOCOL_RX3_tr1_max_len3                (1U<<3)
#define ST25R200_REG_PROTOCOL_RX3_tr1_max_len2                (1U<<2)
#define ST25R200_REG_PROTOCOL_RX3_tr1_max_len1                (1U<<1)
#define ST25R200_REG_PROTOCOL_RX3_tr1_max_len0                (1U<<0)
#define ST25R200_REG_PROTOCOL_RX3_tr1_max_len_mask            (0x7FU<<0)
#define ST25R200_REG_PROTOCOL_RX3_tr1_max_len_shift           (0U)

#define ST25R200_REG_EMD1_emd_thld3                           (1U<<7)
#define ST25R200_REG_EMD1_emd_thld2                           (1U<<6)
#define ST25R200_REG_EMD1_emd_thld1                           (1U<<5)
#define ST25R200_REG_EMD1_emd_thld0                           (1U<<4)
#define ST25R200_REG_EMD1_emd_thld_mask                       (0x0FU<<4)
#define ST25R200_REG_EMD1_emd_thld_shift                      (4U)
#define ST25R200_REG_EMD1_emd_thld_ff                         (1U<<3)
#define ST25R200_REG_EMD1_rfu1                                (1U<<2)
#define ST25R200_REG_EMD1_rfu0                                (1U<<1)
#define ST25R200_REG_EMD1_emd_en                              (1U<<0)
#define ST25R200_REG_EMD1_emd_en_on                           (1U<<0)
#define ST25R200_REG_EMD1_emd_en_off                          (0U<<0)
                                                          
#define ST25R200_REG_EMD2_rfu7                                (1U<<7)
#define ST25R200_REG_EMD2_rfu6                                (1U<<6)
#define ST25R200_REG_EMD2_rfu5                                (1U<<5)
#define ST25R200_REG_EMD2_rfu4                                (1U<<4)
#define ST25R200_REG_EMD2_rfu3                                (1U<<3)
#define ST25R200_REG_EMD2_rfu2                                (1U<<2)
#define ST25R200_REG_EMD2_rfu1                                (1U<<1)
#define ST25R200_REG_EMD2_rfu0                                (1U<<0)

#define ST25R200_REG_MRT_SQT_CONF_sq_del1                     (1U<<7)
#define ST25R200_REG_MRT_SQT_CONF_sq_del0                     (1U<<6)
#define ST25R200_REG_MRT_SQT_CONF_sq_del_mask                 (3U<<6)
#define ST25R200_REG_MRT_SQT_CONF_sq_del_shift                (6U)
#define ST25R200_REG_MRT_SQT_CONF_mrt_step1                   (1U<<5)
#define ST25R200_REG_MRT_SQT_CONF_mrt_step0                   (1U<<4)
#define ST25R200_REG_MRT_SQT_CONF_mrt_step_16fc               (0U<<4)
#define ST25R200_REG_MRT_SQT_CONF_mrt_step_32fc               (1U<<4)
#define ST25R200_REG_MRT_SQT_CONF_mrt_step_64fc               (2U<<4)
#define ST25R200_REG_MRT_SQT_CONF_mrt_step_512fc              (3U<<4)
#define ST25R200_REG_MRT_SQT_CONF_mrt_step_mask               (3U<<4)
#define ST25R200_REG_MRT_SQT_CONF_mrt_step_shift              (4U)
#define ST25R200_REG_MRT_SQT_CONF_rfu2                        (1U<<3)  
#define ST25R200_REG_MRT_SQT_CONF_rfu1                        (1U<<2)
#define ST25R200_REG_MRT_SQT_CONF_rfu0                        (1U<<1)
#define ST25R200_REG_MRT_SQT_CONF_sq_en                       (1U<<0)

#define ST25R200_REG_MRT_mrt7                                 (1U<<7)
#define ST25R200_REG_MRT_mrt6                                 (1U<<6)
#define ST25R200_REG_MRT_mrt5                                 (1U<<5)
#define ST25R200_REG_MRT_mrt4                                 (1U<<4)
#define ST25R200_REG_MRT_mrt3                                 (1U<<3)
#define ST25R200_REG_MRT_mrt2                                 (1U<<2)
#define ST25R200_REG_MRT_mrt1                                 (1U<<1)
#define ST25R200_REG_MRT_mrt0                                 (1U<<0)
                                                               
#define ST25R200_REG_SQT_sqt7                                 (1U<<7)
#define ST25R200_REG_SQT_sqt6                                 (1U<<6)
#define ST25R200_REG_SQT_sqt5                                 (1U<<5)
#define ST25R200_REG_SQT_sqt4                                 (1U<<4)
#define ST25R200_REG_SQT_sqt3                                 (1U<<3)
#define ST25R200_REG_SQT_sqt2                                 (1U<<2)
#define ST25R200_REG_SQT_sqt1                                 (1U<<1)
#define ST25R200_REG_SQT_sqt0                                 (1U<<0)

#define ST25R200_REG_NRT_GPT_CONF_rfu2                        (1U<<7)
#define ST25R200_REG_NRT_GPT_CONF_gptc2                       (1U<<6)
#define ST25R200_REG_NRT_GPT_CONF_gptc1                       (1U<<5)
#define ST25R200_REG_NRT_GPT_CONF_gptc0                       (1U<<4)
#define ST25R200_REG_NRT_GPT_CONF_gptc_no_trigger             (0U<<4)
#define ST25R200_REG_NRT_GPT_CONF_gptc_erx                    (1U<<4)
#define ST25R200_REG_NRT_GPT_CONF_gptc_srx                    (2U<<4)
#define ST25R200_REG_NRT_GPT_CONF_gptc_etx                    (3U<<5)
#define ST25R200_REG_NRT_GPT_CONF_gptc_mask                   (7U<<4)
#define ST25R200_REG_NRT_GPT_CONF_gptc_shift                  (4U)
#define ST25R200_REG_NRT_GPT_CONF_rfu1                        (1U<<3)  
#define ST25R200_REG_NRT_GPT_CONF_rfu0                        (1U<<2)
#define ST25R200_REG_NRT_GPT_CONF_nrt_emd                     (1U<<1)
#define ST25R200_REG_NRT_GPT_CONF_nrt_emd_on                  (1U<<1)
#define ST25R200_REG_NRT_GPT_CONF_nrt_emd_off                 (0U<<1)
#define ST25R200_REG_NRT_GPT_CONF_nrt_step                    (1U<<0)
#define ST25R200_REG_NRT_GPT_CONF_nrt_step_64fc               (0U<<0)
#define ST25R200_REG_NRT_GPT_CONF_nrt_step_4096fc             (1U<<0)

#define ST25R200_REG_NRT1_nrt15                               (1U<<7)
#define ST25R200_REG_NRT1_nrt14                               (1U<<6)
#define ST25R200_REG_NRT1_nrt13                               (1U<<5)
#define ST25R200_REG_NRT1_nrt12                               (1U<<4)
#define ST25R200_REG_NRT1_nrt11                               (1U<<3)
#define ST25R200_REG_NRT1_nrt10                               (1U<<2)
#define ST25R200_REG_NRT1_nrt9                                (1U<<1)
#define ST25R200_REG_NRT1_nrt8                                (1U<<0)

#define ST25R200_REG_NRT2_nrt7                                (1U<<7)
#define ST25R200_REG_NRT2_nrt6                                (1U<<6)
#define ST25R200_REG_NRT2_nrt5                                (1U<<5)
#define ST25R200_REG_NRT2_nrt4                                (1U<<4)
#define ST25R200_REG_NRT2_nrt3                                (1U<<3)
#define ST25R200_REG_NRT2_nrt2                                (1U<<2)
#define ST25R200_REG_NRT2_nrt1                                (1U<<1)
#define ST25R200_REG_NRT2_nrt0                                (1U<<0)

#define ST25R200_REG_GPT1_gpt15                               (1U<<7)
#define ST25R200_REG_GPT1_gpt14                               (1U<<6)
#define ST25R200_REG_GPT1_gpt13                               (1U<<5)
#define ST25R200_REG_GPT1_gpt12                               (1U<<4)
#define ST25R200_REG_GPT1_gpt11                               (1U<<3)
#define ST25R200_REG_GPT1_gpt10                               (1U<<2)
#define ST25R200_REG_GPT1_gpt9                                (1U<<1)
#define ST25R200_REG_GPT1_gpt8                                (1U<<0)

#define ST25R200_REG_GPT2_gpt7                                (1U<<7)
#define ST25R200_REG_GPT2_gpt6                                (1U<<6)
#define ST25R200_REG_GPT2_gpt5                                (1U<<5)
#define ST25R200_REG_GPT2_gpt4                                (1U<<4)
#define ST25R200_REG_GPT2_gpt3                                (1U<<3)
#define ST25R200_REG_GPT2_gpt2                                (1U<<2)
#define ST25R200_REG_GPT2_gpt1                                (1U<<1)
#define ST25R200_REG_GPT2_gpt0                                (1U<<0)

#define ST25R200_REG_DISPLAY3_rfu                             (1U<<7)
#define ST25R200_REG_DISPLAY3_rf_ind6                         (1U<<6)
#define ST25R200_REG_DISPLAY3_rf_ind5                         (1U<<5)
#define ST25R200_REG_DISPLAY3_rf_ind4                         (1U<<4)
#define ST25R200_REG_DISPLAY3_rf_ind3                         (1U<<3)
#define ST25R200_REG_DISPLAY3_rf_ind2                         (1U<<2)
#define ST25R200_REG_DISPLAY3_rf_ind1                         (1U<<1)
#define ST25R200_REG_DISPLAY3_rf_ind0                         (1U<<0)

#define ST25R200_REG_DISPLAY4_rfu1                            (1U<<7)
#define ST25R200_REG_DISPLAY4_q_tdi2                          (1U<<6)
#define ST25R200_REG_DISPLAY4_q_tdi1                          (1U<<5)
#define ST25R200_REG_DISPLAY4_q_tdi0                          (1U<<4)
#define ST25R200_REG_DISPLAY4_q_tdi_mask                      (7U<<4)
#define ST25R200_REG_DISPLAY4_q_tdi_shift                     (4U)
#define ST25R200_REG_DISPLAY4_rfu0                            (1U<<3)
#define ST25R200_REG_DISPLAY4_i_tdi2                          (1U<<2)
#define ST25R200_REG_DISPLAY4_i_tdi1                          (1U<<1)
#define ST25R200_REG_DISPLAY4_i_tdi0                          (1U<<0)
#define ST25R200_REG_DISPLAY4_i_tdi_mask                      (7U<<0)
#define ST25R200_REG_DISPLAY4_i_tdi_shift                     (0U)

#define ST25R200_REG_OVUNSHOOT_CONF_rfu3                      (1U<<7)
#define ST25R200_REG_OVUNSHOOT_CONF_rfu2                      (1U<<6)
#define ST25R200_REG_OVUNSHOOT_CONF_rfu1                      (1U<<5)
#define ST25R200_REG_OVUNSHOOT_CONF_rfu0                      (1U<<4)
#define ST25R200_REG_OVUNSHOOT_CONF_ov_tx_mode1               (1U<<3)
#define ST25R200_REG_OVUNSHOOT_CONF_ov_tx_mode0               (1U<<2)
#define ST25R200_REG_OVUNSHOOT_CONF_ov_tx_mode_mask           (3U<<3)
#define ST25R200_REG_OVUNSHOOT_CONF_ov_tx_mode_shift          (3U)
#define ST25R200_REG_OVUNSHOOT_CONF_uv_tx_mode1               (1U<<1)
#define ST25R200_REG_OVUNSHOOT_CONF_uv_tx_mode0               (1U<<0)
#define ST25R200_REG_OVUNSHOOT_CONF_uv_tx_mode_mask           (3U<<0)
#define ST25R200_REG_OVUNSHOOT_CONF_uv_tx_mode_shift          (0U)

#define ST25R200_REG_OVERSHOOT_CONF_ov_pattern7               (1U<<7)
#define ST25R200_REG_OVERSHOOT_CONF_ov_pattern6               (1U<<6)
#define ST25R200_REG_OVERSHOOT_CONF_ov_pattern5               (1U<<5)
#define ST25R200_REG_OVERSHOOT_CONF_ov_pattern4               (1U<<4)
#define ST25R200_REG_OVERSHOOT_CONF_ov_pattern3               (1U<<3)
#define ST25R200_REG_OVERSHOOT_CONF_ov_pattern2               (1U<<2)
#define ST25R200_REG_OVERSHOOT_CONF_ov_pattern1               (1U<<1)
#define ST25R200_REG_OVERSHOOT_CONF_ov_pattern0               (1U<<0)

#define ST25R200_REG_OVERSHOOT_CONF_uv_pattern7               (1U<<7)
#define ST25R200_REG_OVERSHOOT_CONF_uv_pattern6               (1U<<6)
#define ST25R200_REG_OVERSHOOT_CONF_uv_pattern5               (1U<<5)
#define ST25R200_REG_OVERSHOOT_CONF_uv_pattern4               (1U<<4)
#define ST25R200_REG_OVERSHOOT_CONF_uv_pattern3               (1U<<3)
#define ST25R200_REG_OVERSHOOT_CONF_uv_pattern2               (1U<<2)
#define ST25R200_REG_OVERSHOOT_CONF_uv_pattern1               (1U<<1)
#define ST25R200_REG_OVERSHOOT_CONF_uv_pattern0               (1U<<0)

#define ST25R200_REG_WAKEUP_CONF1_wut3                        (1U<<7)
#define ST25R200_REG_WAKEUP_CONF1_wut2                        (1U<<6)
#define ST25R200_REG_WAKEUP_CONF1_wut1                        (1U<<5)
#define ST25R200_REG_WAKEUP_CONF1_wut0                        (1U<<4)
#define ST25R200_REG_WAKEUP_CONF1_wut_mask                    (0x0FU<<4)
#define ST25R200_REG_WAKEUP_CONF1_wut_shift                   (4U)
#define ST25R200_REG_WAKEUP_CONF1_wuti                        (1U<<3)
#define ST25R200_REG_WAKEUP_CONF1_rfu2                        (1U<<2)
#define ST25R200_REG_WAKEUP_CONF1_rfu1                        (1U<<1)
#define ST25R200_REG_WAKEUP_CONF1_rfu0                        (1U<<0)

#define ST25R200_REG_WAKEUP_CONF2_skip_recal                  (1U<<7)
#define ST25R200_REG_WAKEUP_CONF2_skip_cal                    (1U<<6)
#define ST25R200_REG_WAKEUP_CONF2_skip_twcal                  (1U<<5)
#define ST25R200_REG_WAKEUP_CONF2_skip_twref                  (1U<<4)
#define ST25R200_REG_WAKEUP_CONF2_iq_aaref                    (1U<<3)
#define ST25R200_REG_WAKEUP_CONF2_td_mf                       (1U<<2)
#define ST25R200_REG_WAKEUP_CONF2_td_mt1                      (1U<<1)
#define ST25R200_REG_WAKEUP_CONF2_td_mt0                      (1U<<0)
#define ST25R200_REG_WAKEUP_CONF2_td_mt1                      (1U<<1)
#define ST25R200_REG_WAKEUP_CONF2_td_mt_mask                  (3U<<0)
#define ST25R200_REG_WAKEUP_CONF2_td_mt_shift                 (0U)

#define ST25R200_REG_WU_I_CONF_rfu1                           (1U<<7)
#define ST25R200_REG_WU_I_CONF_i_iirqm                        (1U<<6)
#define ST25R200_REG_WU_I_CONF_i_aaw1                         (1U<<5)
#define ST25R200_REG_WU_I_CONF_i_aaw0                         (1U<<4)
#define ST25R200_REG_WU_I_CONF_i_aaw_mask                     (3U<<4)
#define ST25R200_REG_WU_I_CONF_i_aaw_shift                    (4U)
#define ST25R200_REG_WU_I_CONF_rfu0                           (1U<<3)
#define ST25R200_REG_WU_I_CONF_i_tdi_en2                      (1U<<2)
#define ST25R200_REG_WU_I_CONF_i_tdi_en1                      (1U<<1)
#define ST25R200_REG_WU_I_CONF_i_tdi_en0                      (1U<<0)
#define ST25R200_REG_WU_I_CONF_i_tdi_en_shift                 (0U)
#define ST25R200_REG_WU_I_CONF_i_tdi_en_mask                  (0x07U<<0)

#define ST25R200_REG_WU_I_DELTA_rfu1                          (1U<<7)
#define ST25R200_REG_WU_I_DELTA_rfu0                          (1U<<6)
#define ST25R200_REG_WU_I_DELTA_i_diff5                       (1U<<5)
#define ST25R200_REG_WU_I_DELTA_i_diff4                       (1U<<4)
#define ST25R200_REG_WU_I_DELTA_i_diff3                       (1U<<3)
#define ST25R200_REG_WU_I_DELTA_i_diff2                       (1U<<2)
#define ST25R200_REG_WU_I_DELTA_i_diff1                       (1U<<1)
#define ST25R200_REG_WU_I_DELTA_i_diff0                       (1U<<0)
#define ST25R200_REG_WU_I_DELTA_i_diff_mask                   (0x3FU<<0)
#define ST25R200_REG_WU_I_DELTA_i_diff_shift                  (0U)

#define ST25R200_REG_WU_I_ADC_i_adc7                          (1U<<7)
#define ST25R200_REG_WU_I_ADC_i_adc6                          (1U<<6)
#define ST25R200_REG_WU_I_ADC_i_adc5                          (1U<<5)
#define ST25R200_REG_WU_I_ADC_i_adc4                          (1U<<4)
#define ST25R200_REG_WU_I_ADC_i_adc3                          (1U<<3)
#define ST25R200_REG_WU_I_ADC_i_adc2                          (1U<<2)
#define ST25R200_REG_WU_I_ADC_i_adc1                          (1U<<1)
#define ST25R200_REG_WU_I_ADC_i_adc0                          (1U<<0)

#define ST25R200_REG_WU_I_REF_i_ref7                          (1U<<7)
#define ST25R200_REG_WU_I_REF_i_ref6                          (1U<<6)
#define ST25R200_REG_WU_I_REF_i_ref5                          (1U<<5)
#define ST25R200_REG_WU_I_REF_i_ref4                          (1U<<4)
#define ST25R200_REG_WU_I_REF_i_ref3                          (1U<<3)
#define ST25R200_REG_WU_I_REF_i_ref2                          (1U<<2)
#define ST25R200_REG_WU_I_REF_i_ref1                          (1U<<1)
#define ST25R200_REG_WU_I_REF_i_ref0                          (1U<<0)

#define ST25R200_REG_WU_I_CAL_i_cal7                          (1U<<7)
#define ST25R200_REG_WU_I_CAL_i_cal6                          (1U<<6)
#define ST25R200_REG_WU_I_CAL_i_cal5                          (1U<<5)
#define ST25R200_REG_WU_I_CAL_i_cal4                          (1U<<4)
#define ST25R200_REG_WU_I_CAL_i_cal3                          (1U<<3)
#define ST25R200_REG_WU_I_CAL_i_cal2                          (1U<<2)
#define ST25R200_REG_WU_I_CAL_i_cal1                          (1U<<1)
#define ST25R200_REG_WU_I_CAL_i_cal0                          (1U<<0)

#define ST25R200_REG_WU_Q_CONF_rfu1                           (1U<<7)
#define ST25R200_REG_WU_Q_CONF_q_iirqm                        (1U<<6)
#define ST25R200_REG_WU_Q_CONF_q_aaw1                         (1U<<5)
#define ST25R200_REG_WU_Q_CONF_q_aaw0                         (1U<<4)
#define ST25R200_REG_WU_Q_CONF_q_aaw_mask                     (3U<<4)
#define ST25R200_REG_WU_Q_CONF_q_aaw_shift                    (4U)
#define ST25R200_REG_WU_Q_CONF_rfu0                           (1U<<3)
#define ST25R200_REG_WU_Q_CONF_q_tdi_en2                      (1U<<2)
#define ST25R200_REG_WU_Q_CONF_q_tdi_en1                      (1U<<1)
#define ST25R200_REG_WU_Q_CONF_q_tdi_en0                      (1U<<0)
#define ST25R200_REG_WU_Q_CONF_q_tdi_en_shift                 (0U)
#define ST25R200_REG_WU_Q_CONF_q_tdi_en_mask                  (0x07U<<0)

#define ST25R200_REG_WU_Q_DELTA_rfu1                          (1U<<7)
#define ST25R200_REG_WU_Q_DELTA_rfu0                          (1U<<6)
#define ST25R200_REG_WU_Q_DELTA_q_diff5                       (1U<<5)
#define ST25R200_REG_WU_Q_DELTA_q_diff4                       (1U<<4)
#define ST25R200_REG_WU_Q_DELTA_q_diff3                       (1U<<3)
#define ST25R200_REG_WU_Q_DELTA_q_diff2                       (1U<<2)
#define ST25R200_REG_WU_Q_DELTA_q_diff1                       (1U<<1)
#define ST25R200_REG_WU_Q_DELTA_q_diff0                       (1U<<0)
#define ST25R200_REG_WU_Q_DELTA_q_diff_mask                   (0x3FU<<0)
#define ST25R200_REG_WU_Q_DELTA_q_diff_shift                  (0U)

#define ST25R200_REG_WU_Q_ADC_q_adc7                          (1U<<7)
#define ST25R200_REG_WU_Q_ADC_q_adc6                          (1U<<6)
#define ST25R200_REG_WU_Q_ADC_q_adc5                          (1U<<5)
#define ST25R200_REG_WU_Q_ADC_q_adc4                          (1U<<4)
#define ST25R200_REG_WU_Q_ADC_q_adc3                          (1U<<3)
#define ST25R200_REG_WU_Q_ADC_q_adc2                          (1U<<2)
#define ST25R200_REG_WU_Q_ADC_q_adc1                          (1U<<1)
#define ST25R200_REG_WU_Q_ADC_q_adc0                          (1U<<0)

#define ST25R200_REG_WU_Q_REF_q_ref7                          (1U<<7)
#define ST25R200_REG_WU_Q_REF_q_ref6                          (1U<<6)
#define ST25R200_REG_WU_Q_REF_q_ref5                          (1U<<5)
#define ST25R200_REG_WU_Q_REF_q_ref4                          (1U<<4)
#define ST25R200_REG_WU_Q_REF_q_ref3                          (1U<<3)
#define ST25R200_REG_WU_Q_REF_q_ref2                          (1U<<2)
#define ST25R200_REG_WU_Q_REF_q_ref1                          (1U<<1)
#define ST25R200_REG_WU_Q_REF_q_ref0                          (1U<<0)

#define ST25R200_REG_WU_Q_CAL_q_cal7                          (1U<<7)
#define ST25R200_REG_WU_Q_CAL_q_cal6                          (1U<<6)
#define ST25R200_REG_WU_Q_CAL_q_cal5                          (1U<<5)
#define ST25R200_REG_WU_Q_CAL_q_cal4                          (1U<<4)
#define ST25R200_REG_WU_Q_CAL_q_cal3                          (1U<<3)
#define ST25R200_REG_WU_Q_CAL_q_cal2                          (1U<<2)
#define ST25R200_REG_WU_Q_CAL_q_cal1                          (1U<<1)
#define ST25R200_REG_WU_Q_CAL_q_cal0                          (1U<<0)

#define ST25R200_REG_TX_FRAME1_ntx12                          (1U<<7)
#define ST25R200_REG_TX_FRAME1_ntx11                          (1U<<6)
#define ST25R200_REG_TX_FRAME1_ntx10                          (1U<<5)
#define ST25R200_REG_TX_FRAME1_ntx9                           (1U<<4)
#define ST25R200_REG_TX_FRAME1_ntx8                           (1U<<3)
#define ST25R200_REG_TX_FRAME1_ntx7                           (1U<<2)
#define ST25R200_REG_TX_FRAME1_ntx6                           (1U<<1)
#define ST25R200_REG_TX_FRAME1_ntx5                           (1U<<0)
                                                               
#define ST25R200_REG_TX_FRAME2_ntx4                           (1U<<7)
#define ST25R200_REG_TX_FRAME2_ntx3                           (1U<<6)
#define ST25R200_REG_TX_FRAME2_ntx2                           (1U<<5)
#define ST25R200_REG_TX_FRAME2_ntx1                           (1U<<4)
#define ST25R200_REG_TX_FRAME2_ntx0                           (1U<<3)
#define ST25R200_REG_TX_FRAME2_ntx_mask                       (0x1FU<<3)
#define ST25R200_REG_TX_FRAME2_ntx_shift                      (3U)
#define ST25R200_REG_TX_FRAME2_nbtx2                          (1U<<2)
#define ST25R200_REG_TX_FRAME2_nbtx1                          (1U<<1)
#define ST25R200_REG_TX_FRAME2_nbtx0                          (1U<<0)
#define ST25R200_REG_TX_FRAME2_nbtx_mask                      (7U<<0)
#define ST25R200_REG_TX_FRAME2_nbtx_shift                     (0U)
                                                               
#define ST25R200_REG_FIFO_STATUS1_fifo_b7                     (1U<<7)
#define ST25R200_REG_FIFO_STATUS1_fifo_b6                     (1U<<6)
#define ST25R200_REG_FIFO_STATUS1_fifo_b5                     (1U<<5)
#define ST25R200_REG_FIFO_STATUS1_fifo_b4                     (1U<<4)
#define ST25R200_REG_FIFO_STATUS1_fifo_b3                     (1U<<3)
#define ST25R200_REG_FIFO_STATUS1_fifo_b2                     (1U<<2)
#define ST25R200_REG_FIFO_STATUS1_fifo_b1                     (1U<<1)
#define ST25R200_REG_FIFO_STATUS1_fifo_b0                     (1U<<0)
                                                               
#define ST25R200_REG_FIFO_STATUS2_rfu                         (1U<<7)
#define ST25R200_REG_FIFO_STATUS2_fifo_b8                     (1U<<6)
#define ST25R200_REG_FIFO_STATUS2_fifo_b_shift                (6U)
#define ST25R200_REG_FIFO_STATUS2_fifo_unf                    (1U<<5)
#define ST25R200_REG_FIFO_STATUS2_fifo_ovr                    (1U<<4)
#define ST25R200_REG_FIFO_STATUS2_fifo_lb2                    (1U<<3)
#define ST25R200_REG_FIFO_STATUS2_fifo_lb1                    (1U<<2)
#define ST25R200_REG_FIFO_STATUS2_fifo_lb0                    (1U<<1)
#define ST25R200_REG_FIFO_STATUS2_fifo_lb_mask                (7U<<1)
#define ST25R200_REG_FIFO_STATUS2_fifo_lb_shift               (1U)
#define ST25R200_REG_FIFO_STATUS2_np_lb                       (1U<<0)

#define ST25R200_REG_COLLISION_c_byte3                        (1U<<7)
#define ST25R200_REG_COLLISION_c_byte2                        (1U<<6)
#define ST25R200_REG_COLLISION_c_byte1                        (1U<<5)
#define ST25R200_REG_COLLISION_c_byte0                        (1U<<4)
#define ST25R200_REG_COLLISION_c_byte_mask                    (0xFU<<4)
#define ST25R200_REG_COLLISION_c_byte_shift                   (4U)
#define ST25R200_REG_COLLISION_c_bit2                         (1U<<3)
#define ST25R200_REG_COLLISION_c_bit1                         (1U<<2)
#define ST25R200_REG_COLLISION_c_bit0                         (1U<<1)
#define ST25R200_REG_COLLISION_c_bit_mask                     (0x7U<<1)
#define ST25R200_REG_COLLISION_c_bit_shift                    (1U)
#define ST25R200_REG_COLLISION_c_pb                           (1U<<0)

#define ST25R200_REG_IC_ID_ic_type4                           (1U<<7)
#define ST25R200_REG_IC_ID_ic_type3                           (1U<<6)
#define ST25R200_REG_IC_ID_ic_type2                           (1U<<5)
#define ST25R200_REG_IC_ID_ic_type1                           (1U<<4)
#define ST25R200_REG_IC_ID_ic_type0                           (1U<<3)
#define ST25R200_REG_IC_ID_ic_type_st25r200                   (21U<<3)
#define ST25R200_REG_IC_ID_ic_type_mask                       (0x1FU<<3)
#define ST25R200_REG_IC_ID_ic_type_shift                      (3U)
#define ST25R200_REG_IC_ID_ic_rev1                            (1U<<0)
#define ST25R200_REG_IC_ID_ic_rev0                            (0U<<0)
#define ST25R200_REG_IC_ID_ic_rev_mask                        (7U<<0)
#define ST25R200_REG_IC_ID_ic_rev_shift                       (0U)

/*! \endcond DOXYGEN_SUPPRESS */

/*
******************************************************************************
* GLOBAL FUNCTION PROTOTYPES
******************************************************************************
*/

/*! 
 *****************************************************************************
 *  \brief  Returns the content of a register within the ST25R200
 *
 *  This function is used to read out the content of ST25R200 registers
 *
 *  \param[in]  reg: Address of register to read
 *  \param[out] val: Returned value
 *
 *  \return RFAL_ERR_NONE  : Operation successful
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_SEND  : Transmission error or acknowledge not received
 *****************************************************************************
 */
ReturnCode st25r200ReadRegister( uint8_t reg, uint8_t* val );

/*! 
 *****************************************************************************
 *  \brief  Reads from multiple ST25R200 registers
 *
 *  This function is used to read from multiple registers using the
 *  auto-increment feature. That is, after each read the address pointer
 *  inside the ST25R200 gets incremented automatically
 *
 *  \param[in]  reg: Address of the frist register to read from
 *  \param[in]  values: pointer to a buffer where the result shall be written to
 *  \param[in]  length: Number of registers to be read out
 *
 *  \return RFAL_ERR_NONE  : Operation successful
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_SEND  : Transmission error or acknowledge not received
 *****************************************************************************
 */
ReturnCode st25r200ReadMultipleRegisters( uint8_t reg, uint8_t* values, uint16_t length );

/*! 
 *****************************************************************************
 *  \brief  Writes a given value to a register within the ST25R200
 *
 *  This function is used to write \a val to address \a reg within the ST25R200.
 *
 *  \param[in]  reg: Address of the register to write
 *  \param[in]  val: Value to be written
 *
 *  \return RFAL_ERR_NONE  : Operation successful
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_SEND  : Transmission error or acknowledge not received
 *****************************************************************************
 */
ReturnCode st25r200WriteRegister( uint8_t reg, uint8_t val );

/*! 
 *****************************************************************************
 *  \brief  Writes multiple values to ST25R200 registers
 *
 *  This function is used to write multiple values to the ST25R200 using the
 *  auto-increment feature. That is, after each write the address pointer
 *  inside the ST25R200 gets incremented automatically
 *
 *  \param[in]  reg   : Address of the frist register to write
 *  \param[in]  values: pointer to a buffer containing the values to be written
 *  \param[in]  length: Number of values to be written
 *
 *  \return RFAL_ERR_NONE  : Operation successful
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_SEND  : Transmission error or acknowledge not received
 *****************************************************************************
 */
ReturnCode st25r200WriteMultipleRegisters( uint8_t reg, const uint8_t* values, uint16_t length );

/*! 
 *****************************************************************************
 *  \brief  Writes values to ST25R200 FIFO
 *
 *  This function needs to be called in order to write to the ST25R200 FIFO.
 *
 *  \param[in]  values: pointer to a buffer containing the values to be written
 *                      to the FIFO
 *  \param[in]  length: Number of values to be written
 *
 *  \return RFAL_ERR_NONE  : Operation successful
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_SEND  : Transmission error or acknowledge not received
 *****************************************************************************
 */
ReturnCode st25r200WriteFifo( const uint8_t* values, uint16_t length );

/*! 
 *****************************************************************************
 *  \brief  Read values from ST25R200 FIFO
 *
 *  This function needs to be called in order to read from ST25R200 FIFO.
 *
 *  \param[out]  buf: pointer to a buffer where the FIFO content shall be
 *                       written to
 *  \param[in]  length: Number of bytes to read
 *  
 *  \note: This function doesn't check whether \a length is really the
 *  number of available bytes in FIFO
 *
 *  \return RFAL_ERR_NONE  : Operation successful
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_SEND  : Transmission error or acknowledge not received
 *****************************************************************************
 */
ReturnCode st25r200ReadFifo( uint8_t* buf, uint16_t length );

/*! 
 *****************************************************************************
 *  \brief  Execute a direct command
 *
 *  This function is used to trigger a direct command. These commands
 *  are implemented inside the chip and each command has unique code
 *
 *  \param[in]  cmd : code of the direct command to be executed
 *
 *  \return RFAL_ERR_NONE  : Operation successful
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_SEND  : Transmission error or acknowledge not received
 *****************************************************************************
 */
ReturnCode st25r200ExecuteCommand( uint8_t cmd );

/*! 
 *****************************************************************************
 *  \brief  Execute direct commands
 *
 *  This function is used to trigger execution of direct commands. These 
 *  commands are implemented inside the chip and each command has 
 *  unique code (see datasheet).
 *
 *  \warning Commands to be executed must support command chaining
 *
 *  \param[in] cmds   : code of the direct commands to be executed
 *  \param[in] length : number of direct command to be executed
 *
 *  \return RFAL_ERR_NONE  : Operation successful
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_SEND  : Transmission error or acknowledge not received
 *****************************************************************************
 */
ReturnCode st25r200ExecuteCommands( const uint8_t *cmds, uint8_t length );

/*! 
 *****************************************************************************
 *  \brief  Read a test register within the ST25R200
 *
 *  This function is used to read the content of test address \a reg within the ST25R200
 *
 *  \param[in]   reg: Address of the register to read
 *  \param[out]  val: Returned read value
 *
 *  \return RFAL_ERR_NONE  : Operation successful
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_SEND  : Transmission error or acknowledge not received
 *****************************************************************************
 */
ReturnCode st25r200ReadTestRegister( uint8_t reg, uint8_t* val );

/*! 
 *****************************************************************************
 *  \brief  Writes a given value to a test register within the ST25R200
 *
 *  This function is used to write \a val to test address \a reg within the ST25R200
 *
 *  \param[in]  reg: Address of the register to write
 *  \param[in]  val: Value to be written
 *
 *  \return RFAL_ERR_NONE  : Operation successful
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_SEND  : Transmission error or acknowledge not received
 *****************************************************************************
 */
ReturnCode st25r200WriteTestRegister( uint8_t reg, uint8_t val );

/*! 
 *****************************************************************************
 *  \brief  Writes a multiple values to test registers within the ST25R200
 *
 *  This function is used to write \a val to test address \a reg within the ST25R200
 *
 *  \param[in]  reg   : Address of the frist register to write
 *  \param[in]  values: Pointer to a buffer containing the values to be written
 *  \param[in]  length: Number of values to be written
 *
 *  \return RFAL_ERR_NONE  : Operation successful
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_SEND  : Transmission error or acknowledge not received
 *****************************************************************************
 */
ReturnCode st25r200WriteMultipleTestRegister( uint8_t reg, const uint8_t* values, uint8_t length );

/*! 
 *****************************************************************************
 *  \brief  Cleart bits on Register
 *
 *  This function clears the given bitmask on the register 
 *
 *  \param[in]  reg: Address of the register clear
 *  \param[in]  clr_mask: Bitmask of bit to be cleared
 *
 *  \return RFAL_ERR_NONE  : Operation successful
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_SEND  : Transmission error or acknowledge not received
 *****************************************************************************
 */
ReturnCode st25r200ClrRegisterBits( uint8_t reg, uint8_t clr_mask );

/*! 
 *****************************************************************************
 *  \brief  Set bits on Register
 *
 *  This function sets the given bitmask on the register 
 *
 *  \param[in]  reg: Address of the register clear
 *  \param[in]  set_mask: Bitmask of bit to be cleared
 *
 *  \return RFAL_ERR_NONE  : Operation successful
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_SEND  : Transmission error or acknowledge not received
 *****************************************************************************
 */
ReturnCode st25r200SetRegisterBits( uint8_t reg, uint8_t set_mask );

/*! 
 *****************************************************************************
 *  \brief  Changes the given bits on a ST25R200 register
 *
 *  This function is used if only a particular bits should be changed within
 *  an ST25R200 register.
 *
 *  \param[in]  reg: Address of the register to change.
 *  \param[in]  valueMask: bitmask of bits to be changed
 *  \param[in]  value: the bits to be written on the enabled valueMask bits
 *
 *  \return RFAL_ERR_NONE  : Operation successful
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_SEND  : Transmission error or acknowledge not received
 *****************************************************************************
 */
ReturnCode st25r200ChangeRegisterBits( uint8_t reg, uint8_t valueMask, uint8_t value );

/*! 
 *****************************************************************************
 *  \brief  Modifies a value within a ST25R200 register
 *
 *  This function is used if only a particular bits should be changed within
 *  an ST25R200 register.
 *
 *  \param[in]  reg: Address of the register to write.
 *  \param[in]  clr_mask: bitmask of bits to be cleared to 0.
 *  \param[in]  set_mask: bitmask of bits to be set to 1.
 *
 *  \return RFAL_ERR_NONE  : Operation successful
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_SEND  : Transmission error or acknowledge not received
 *****************************************************************************
 */
ReturnCode st25r200ModifyRegister( uint8_t reg, uint8_t clr_mask, uint8_t set_mask );

/*! 
 *****************************************************************************
 *  \brief  Changes the given bits on a ST25R200 Test register
 *
 *  This function is used if only a particular bits should be changed within
 *  an ST25R200 register.
 *
 *  \param[in]  reg: Address of the Test register to change.
 *  \param[in]  valueMask: bitmask of bits to be changed
 *  \param[in]  value: the bits to be written on the enabled valueMask bits
 *
 *  \return RFAL_ERR_NONE  : Operation successful
 *  \return RFAL_ERR_PARAM : Invalid parameter
 *  \return RFAL_ERR_SEND  : Transmission error or acknowledge not received
 *****************************************************************************
 */
ReturnCode st25r200ChangeTestRegisterBits( uint8_t reg, uint8_t valueMask, uint8_t value );

/*! 
 *****************************************************************************
 *  \brief  Checks if register contains a expected value
 *
 *  This function checks if the given reg contains a value that once masked
 *  equals the expected value
 *
 *  \param reg  : the register to check the value
 *  \param mask : the mask apply on register value
 *  \param val  : expected value to be compared to
 *    
 *  \return  true when reg contains the expected value | false otherwise
 */
bool st25r200CheckReg( uint8_t reg, uint8_t mask, uint8_t val );

/*! 
 *****************************************************************************
 *  \brief  Check if register ID is valid
 *
 *  Checks if the given register ID a valid ST25R200 register
 *
 *  \param[in]  reg: Address of register to check
 *  
 *  \return  true if is a valid register ID
 *  \return  false otherwise
 *
 *****************************************************************************
 */
bool st25r200IsRegValid( uint8_t reg );

/*! 
 *****************************************************************************
 *  \brief  ST25R200 LED Initialize
 *
 *  This function initializes the LEDs that represent ST25R200 activity 
 *
 *****************************************************************************
 */
void st25r200ledInit( void );

/*! 
 *****************************************************************************
 *  \brief  ST25R200 LED Event Interrupt
 *
 *  This function should be called upon a ST25R200 Interrupt, providing 
 *  the interrupt event with ST25R200 irq flags to update LEDs 
 *
 *  \param[in] irqs: ST25R200 irqs mask
 *
 *****************************************************************************
 */
void st25r200ledEvtIrq( uint32_t irqs );

/*! 
 *****************************************************************************
 *  \brief  ST25R200 LED Event Write Register
 *
 *  This function should be called on a ST25R200 Write Register operation
 *  providing the event with the register and value to update LEDs 
 *
 *  \param[in] reg: ST25R200 register to be written
 *  \param[in] val: value to be written on the register
 *
 *****************************************************************************
 */
void st25r200ledEvtWrReg( uint8_t reg, uint8_t val );

/*! 
 *****************************************************************************
 *  \brief  ST25R200 LED Event Write Multiple Register
 *
 *  This function should be called upon a ST25R200 Write Multiple Registers, 
 *  providing the event with the registers and values to update LEDs 
 *
 *  \param[in] reg : ST25R200 first register written
 *  \param[in] vals: pointer to the values written
 *  \param[in] len : number of registers written
 *
 *****************************************************************************
 */
void st25r200ledEvtWrMultiReg( uint8_t reg, const uint8_t* vals, uint8_t len );

/*! 
 *****************************************************************************
 *  \brief  ST25R200 LED Event Direct Command
 *
 *  This function should be called upon a ST25R200 direct command, providing 
 *  the event with the command executed
 *
 *  \param[in] cmd: ST25R200 cmd executed
 *
 *****************************************************************************
 */
void st25r200ledEvtCmd( uint8_t cmd );

/*! 
 *****************************************************************************
 *  \brief  ST25R200 LED Event Direct Commands
 *
 *  This function should be called upon the execution of ST25R200 direct 
 *  commands, providing the event with the commands executed
 *
 *  \param[in] cmds: ST25R200 cmds executed
 *  \param[in] len : number of commands executed
 *
 *****************************************************************************
 */
void st25r200ledEvtCmds( const uint8_t* cmds, uint8_t len );

#endif /* ST25R200_COM_H */


/**
  * @}
  *
  * @}
  *
  * @}
  * 
  * @}
  */
