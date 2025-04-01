#pragma once

// TS orientations
#define TS_ORIENTATION_PORTRAIT 0U
#define TS_ORIENTATION_LANDSCAPE 1U
#define TS_ORIENTATION_PORTRAIT_ROT180 2U
#define TS_ORIENTATION_LANDSCAPE_ROT180 3U

typedef struct {
  // Screen width
  uint32_t Width;
  // Screen width
  uint32_t Height;
  // Touch screen orientation
  uint32_t Orientation;
  // Expressed in pixel and means the x or y difference vs
  // old position to consider the new values valid
  uint32_t Accuracy;

} TS_Init_t;

typedef struct {
  uint32_t TouchDetected;
  uint32_t TouchX;
  uint32_t TouchY;
} TS_State_t;

extern uint8_t sitronix_touching;

int32_t BSP_TS_Init(uint32_t Instance, TS_Init_t *TS_Init);

int32_t BSP_TS_DeInit(uint32_t Instance);

int32_t BSP_TS_GetState(uint32_t Instance, TS_State_t *TS_State);
