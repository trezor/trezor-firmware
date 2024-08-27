#ifndef MODELS_MODEL_H_
#define MODELS_MODEL_H_

#if defined TREZOR_MODEL_1
#include "T1B1/versions.h"
#elif defined TREZOR_MODEL_T
#include "T2T1/versions.h"
#elif defined TREZOR_MODEL_R
#include "T2B1/versions.h"
#elif defined TREZOR_MODEL_T3T1
#include "T3T1/versions.h"
#elif defined TREZOR_MODEL_T3B1
#include "T3B1/versions.h"
#elif defined TREZOR_MODEL_DISC1
#include "D001/versions.h"
#elif defined TREZOR_MODEL_DISC2
#include "D002/versions.h"
#else
#error Unknown Trezor model
#endif

#endif
