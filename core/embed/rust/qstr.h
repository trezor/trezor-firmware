enum Qstr {
#define QDEF(id, str) id,
#include "genhdr/qstrdefs.generated.h"
#undef QDEF
};
