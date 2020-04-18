#ifndef __HIDAPI_H_

#include <stddef.h>
#include <sys/socket.h>
#include <netinet/in.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    int fd;
    struct sockaddr_in other;
    socklen_t slen;
} hid_device;

int hid_init(void);

int hid_exit(void);

hid_device *hid_open_path(const char *path);

void hid_close(hid_device *device);

int hid_write(hid_device *device, const unsigned char *data, size_t length);

int hid_read_timeout(hid_device *dev, unsigned char *data, size_t length, int milliseconds);

#ifdef __cplusplus
}
#endif

#endif
