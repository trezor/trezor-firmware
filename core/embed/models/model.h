#ifndef MODELS_MODEL_H_
#define MODELS_MODEL_H_

#include "layout_common.h"

#if defined TREZOR_MODEL_1
#include "T1B1/model_T1B1.h"
#elif defined TREZOR_MODEL_T
#include "T2T1/model_T2T1.h"
#elif defined TREZOR_MODEL_R
#include "T2B1/model_T2B1.h"
#elif defined TREZOR_MODEL_T3T1
#include "T3T1/model_T3T1.h"
#elif defined TREZOR_MODEL_T3B1
#include "T3B1/model_T3B1.h"
#elif defined TREZOR_MODEL_DISC1
#include "D001/model_D001.h"
#elif defined TREZOR_MODEL_DISC2
#include "D002/model_D002.h"
#else
#error Unknown Trezor model
#endif

#endif
