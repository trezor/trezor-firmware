#ifndef TF15411A_H_
#define TF15411A_H_

// GC9307 IC controller

void tf15411a_init_seq(void);
void tf15411a_rotate(int degrees, buffer_offset_t* offset);

#endif
