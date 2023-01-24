enum Qstr {
#define QDEF(id, hash, len, str) id,
#include "genhdr/qstrdefs.generated.h"
#undef QDEF
};
