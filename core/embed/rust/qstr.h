enum Qstr {

// Copied from `vendor/micropython/py/qstr.h`:

#define QDEF0(id, hash, len, str) id,
#define QDEF1(id, hash, len, str)
#include "genhdr/qstrdefs.generated.h"
#undef QDEF0
#undef QDEF1
  MP_QSTRnumber_of_static,
  // unused but shifts the enum counter back one
  MP_QSTRstart_of_main = MP_QSTRnumber_of_static - 1,

#define QDEF0(id, hash, len, str)
#define QDEF1(id, hash, len, str) id,
#include "genhdr/qstrdefs.generated.h"
#undef QDEF0
#undef QDEF1
  // no underscore so it can't clash with any of the above
  MP_QSTRnumber_of,
};
