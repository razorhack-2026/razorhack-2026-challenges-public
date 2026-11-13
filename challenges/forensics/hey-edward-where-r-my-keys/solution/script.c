/* ssh-keygen.c's original includes */
#include "includes.h"

#include <sys/types.h>
#include <sys/socket.h>
#include <sys/stat.h>

#ifdef WITH_OPENSSL
#include "openbsd-compat/openssl-compat.h"
#include <openssl/bn.h>
#include <openssl/evp.h>
#include <openssl/pem.h>
#endif

#include <stdint.h>
#include <errno.h>
#include <fcntl.h>
#include <netdb.h>
#include <paths.h>
#include <pwd.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <limits.h>
#include <locale.h>
#include <time.h>

#include "xmalloc.h"
#include "sshkey.h"
#include "authfile.h"
#include "sshbuf.h"
#include "pathnames.h"
#include "log.h"
#include "misc.h"
#include "match.h"
#include "hostfile.h"
#include "dns.h"
#include "ssh.h"
#include "ssh2.h"
#include "ssherr.h"
#include "atomicio.h"
#include "krl.h"
#include "digest.h"
#include "utf8.h"
#include "authfd.h"
#include "sshsig.h"
#include "ssh-sk.h"
#include "sk-api.h" /* XXX for SSH_SK_USER_PRESENCE_REQD; remove */
#include "cipher.h"

int main(int argc, char **argv) {
    struct sshkey *k = sshkey_new(KEY_ED25519);
    k->shielded_len = 0x80;
    k->shielded_private = calloc(1, k->shielded_len);
    k->shield_prekey_len = 0x4000;
    k->shield_prekey = calloc(1, k->shield_prekey_len);

    FILE *shielded_private_file = fopen("shielded_private.bin", "rb");
    FILE *shield_prekey_file = fopen("shield_prekey.bin", "rb");

    fread(k->shielded_private, k->shielded_len, 1, shielded_private_file);
    fread(k->shield_prekey, k->shield_prekey_len, 1, shield_prekey_file);

    int res;
    if((res = sshkey_unshield_private(k)) != 0) {
        printf("messed up at unshielding");
        return res;
    }

    if((res = sshkey_save_private(k, "./id_ed25519", "", "iwakuralain@wired.net", 0, "\x00", 0)) != 0) {
        printf("messed up at saving");
        return res;
    }

    return 0;
}
