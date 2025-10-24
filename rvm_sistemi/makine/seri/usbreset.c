/* usbreset -- USB cihaz resetleme utility
 *
 * Kullanim: usbreset /dev/bus/usb/BBB/DDD
 *
 * BBB = Bus numarası
 * DDD = Device numarası
 *
 * Örnek: usbreset /dev/bus/usb/003/012
 */

#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <string.h>
#include <sys/ioctl.h>
#include <linux/usbdevice_fs.h>

int main(int argc, char **argv) {
    const char *filename;
    int fd;
    int rc;

    if (argc != 2) {
        fprintf(stderr, "Kullanim: usbreset /dev/bus/usb/BBB/DDD\n");
        fprintf(stderr, "  BBB = Bus numarasi\n");
        fprintf(stderr, "  DDD = Device numarasi\n");
        fprintf(stderr, "\nOrnek: usbreset /dev/bus/usb/003/012\n");
        return 1;
    }

    filename = argv[1];

    fd = open(filename, O_WRONLY);
    if (fd < 0) {
        fprintf(stderr, "Hata: '%s' acilamadi: %s\n", filename, strerror(errno));
        return 1;
    }

    printf("USB cihaz resetleniyor: %s\n", filename);

    rc = ioctl(fd, USBDEVFS_RESET, 0);
    if (rc < 0) {
        fprintf(stderr, "Hata: USB reset basarisiz: %s\n", strerror(errno));
        close(fd);
        return 1;
    }

    printf("✓ USB cihaz basariyla resetlendi\n");

    close(fd);
    return 0;
}
