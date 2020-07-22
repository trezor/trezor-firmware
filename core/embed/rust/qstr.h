enum Qstr {
#define QDEF(id, str) id,
#include QSTR_GENERATED_PATH
#undef QDEF
};
