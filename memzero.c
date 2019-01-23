#include <string.h>
#include <strings.h>

// taken from https://github.com/jedisct1/libsodium/blob/1647f0d53ae0e370378a9195477e3df0a792408f/src/libsodium/sodium/utils.c#L102-L130

void memzero(void *const pnt, const size_t len)
{
#ifdef _WIN32
    SecureZeroMemory(pnt, len);
#elif defined(HAVE_MEMSET_S)
    memset_s(pnt, (rsize_t) len, 0, (rsize_t) len);
#elif defined(HAVE_EXPLICIT_BZERO)
    explicit_bzero(pnt, len);
#elif defined(HAVE_EXPLICIT_MEMSET)
    explicit_memset(pnt, 0, len);
#else
    volatile unsigned char *volatile pnt_ =
        (volatile unsigned char *volatile) pnt;
    size_t i = (size_t) 0U;

    while (i < len) {
        pnt_[i++] = 0U;
    }
#endif
}
