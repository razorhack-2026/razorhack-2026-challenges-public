# hey edward where r my keys

**Category:** Forensics  
**Difficulty:** Insane  
**Author:** Grace  

## Description

Your coworker Lain somehow lost their SSH keys to an important server in the ship. All you've got is
a coredump of OpenSSH's
[`ssh-agent`](https://github.com/openssh/openssh-portable/blob/master/ssh-agent.c) and, for whatever
reason, the public key the server uses `id_ed25519.pub`.

Log back in to the server to get your flag (`ssh iwakuralain@<ip-address-here>`).

## Tools Used

- `gdb` / `lldb`

## Files Provided

- `core.961.tar.gz`
- `id_ed25519.pub`

## Flag

`flag{oh_my_keys_r_right_here}`

## Solution

### Preface
This solution is largely based on ["OpenSSH ssh-agent Shielded Private Key Extraction (x86_64
Linux)"](https://hnsecurity.it/blog/openssh-ssh-agent-shielded-private-key-extraction-x86_64-linux/")
by Piergiovanni Cipolloni with some tweaks to keep it up to date.

### Memory Extraction
The challenge asks us to log back in to the SSH server with the hint "Your coworker Lain somehow
lost their SSH keys," along with a link to OpenSSH's `ssh-agent` and a coredump of `ssh-agent`. This
let's us know that we need to somehow find SSH keys from the coredump.

If we go to the link provided, we'll see a `struct identity`.
```C
typedef struct identity {
	TAILQ_ENTRY(identity) next;
	struct sshkey *key;
	char *comment;
	char *provider;
	time_t death;
	u_int confirm;
	char *sk_provider;
	struct dest_constraint *dest_constraints;
	size_t ndest_constraints;
} Identity;
```

We probably want the `struct sshkey *key`. In the public key that was given, `id_ed25519.pub`, we
know that there is a comment 'iwakuralain@wired.net'. That is probably stored in the `char
*comment`, so we can use that to locate the struct in memory.

We can use GDB to find the string `iwakuralain@wired.net` in the coredump's memory. We first need
to list the addresses the program allocated by running `maintenance info sections` in GDB:
```
(gdb) maintenance info sections
...
[12]     0x00000000->0x00001f10 at 0x00296b0c: .gdb-tdesc/961 HAS_CONTENTS
[13]     0x00000000->0x00001f10 at 0x00296b0c: .gdb-tdesc HAS_CONTENTS
[14]     0x558db571b000->0x558db5722000 at 0x000007b0: load1 ALLOC LOAD READONLY HAS_CONTENTS
[15]     0x558db5763000->0x558db5765000 at 0x000077b0: load2 ALLOC LOAD READONLY HAS_CONTENTS
[16]     0x558db5765000->0x558db5766000 at 0x000097b0: load3 ALLOC LOAD HAS_CONTENTS
[17]     0x558db5766000->0x558db5767000 at 0x0000a7b0: load4 ALLOC LOAD HAS_CONTENTS
[18]     0x558ddf4ee000->0x558ddf572000 at 0x0000b7b0: load5 ALLOC LOAD HAS_CONTENTS
[19]     0x7ff8c17e2000->0x7ff8c17e9000 at 0x0008f7b0: load6 ALLOC LOAD READONLY HAS_CONTENTS
[20]     0x7ff8c1800000->0x7ff8c1805000 at 0x000967b0: load7 ALLOC LOAD READONLY HAS_CONTENTS
[21]     0x7ff8c1805000->0x7ff8c1806000 at 0x0009b7b0: load8 ALLOC LOAD HAS_CONTENTS
...
```

We run `find <start-address>, <end-address>, "iwakuralain@wired.net"` for each pair of addresses to
find where `iwakuralain@wired.net` lives in memory. Eventually, we find a match in the address
`0x558ddf5548f0`:
```
(gdb) find 0x558ddf4ee000, 0x558ddf572000, "iwakuralain@wired.net"
0x558ddf5548f0
warning: Unable to access 8571 bytes of target memory at 0x558ddf56fe86, halting search.
1 pattern found.
```

Now, we want to find places in memory that reference that address since we're trying to find `char
*comment`. We can run the find command for each pair of addresses again, but this time we search for
`0x558ddf5548f0`. Eventually, we find a match in the address `0x558ddf50f538`:
```
(gdb) find 0x558ddf4ee000, 0x558ddf572000, 0x558ddf5548f0
0x558ddf50f538
warning: Unable to access 4161 bytes of target memory at 0x558ddf570fc0, halting search.
1 pattern found
```

So there is a `char *comment` in the address `0x558ddf50f538`. This must mean there is a `struct
sshkey *key` in the address `0x558ddf50f538 - 0x8 = 0x558ddf50f530` since `char *comment` has a size
of 8 bytes.  We can read the address `0x558ddf50f530` to know that `struct sshkey *key` lives in
`0x558ddf5108e0`:
```
(gdb) x/xg 0x558ddf50f530
0x558ddf50f530: 0x0000558ddf5108e0
```

If we look at the definition of `struct sshkey` from [sshkey.h](https://salsa.debian.org/ssh-team/openssh/-/blob/master/sshkey.h), we see
```C
/* XXX opacify? */
struct sshkey {
	int	 type;
	int	 flags;
	/* KEY_ECDSA and KEY_ECDSA_SK */
	int	 ecdsa_nid;	/* NID of curve */
	/* libcrypto-backed keys */
	EVP_PKEY *pkey;
	/* KEY_ED25519 and KEY_ED25519_SK */
	u_char	*ed25519_sk;
	u_char	*ed25519_pk;
	/* KEY_MLDSA44_ED25519 */
	u_char	*mldsa_ed25519_sk;
	u_char	*mldsa_ed25519_pk;
	/* KEY_ECDSA_SK and KEY_ED25519_SK */
	char	*sk_application;
	uint8_t	sk_flags;
	struct sshbuf *sk_key_handle;
	struct sshbuf *sk_reserved;
	/* Certificates */
	struct sshkey_cert *cert;
	/* Private key shielding */
	u_char	*shielded_private;
	size_t	shielded_len;
	u_char	*shield_prekey;
	size_t	shield_prekey_len;
};
```

It seems like we want `ed25519_pk`, but we actually get a null pointer if we try read it. This is
because the key has been ["shielded"](https://xorhash.gitlab.io/xhblog/0010.html), i.e. encrypted in
memory. What we want actually lives in `u_char *shielded_private` and `u_char *shield_prekey`.

We want to read the fields to get the value of the pointers. The offset of the fields are `0x50` and
`0x60` respectively:
```
(gdb) x/xg 0x558ddf5108e0 + 0x50
0x558ddf510930: 0x0000558ddf555840

(gdb) x/xg 0x558ddf5108e0 + 0x60
0x558ddf510940: 0x00007ff8c2135000
```

We also want their lengths, so we know how much to read from the pointers we just found. The offsets
of `size_t shielded_len` and `size_t shield_prekey_len` are `0x58` and `0x68` respectively:
```
(gdb) x/xg 0x558ddf5108e0 + 0x58
0x558ddf510938: 0x0000000000000080

(gdb) x/xg 0x558ddf5108e0 + 0x68
0x558ddf510948: 0x0000000000004000
```

So now, we want to dump the contents that live in `u_char *shielded_private` and `u_char
*shield_prekey`:
```
(gdb) dump binary memory shielded_private.bin 0x558ddf555840 0x558ddf555840+0x80
(gdb) dump binary memory shield_prekey.bin 0x7ff8c2135000 0x7ff8c2135000+0x4000
```

### Unshielding

The two binaries we extracted from the coredump isn't very useful since it is still encrypted.
However, we can decrypt it using the function `sshkey_unshield_private` from OpenSSH's `sshkey.c`.
Then, we can save the key by using `sshkey_save_private` from `authfile.c`. We can write a simple C
"script" (see `script.c` for full):
```C
...
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
```

We can then overwrite `ssh-keygen.c` with the previous script. This is because `ssh-keygen.c`
includes all the necessary headers to use the functions we need. Additionally, it's so that we can
use the build system OpenSSH includes to compile our program into an executable. We can just follow
the steps on [how to build a release
version](https://github.com/openssh/openssh-portable#building-a-release) of `openssh`
```
# Download and decompress the latest version of openssh.
curl https://cdn.openbsd.org/pub/OpenBSD/OpenSSH/portable/openssh-10.4p1.tar.gz | tar -xzf -

# Replace ssh-keygen.c with out script.
cat script.c > openssh-10.4p1/ssh-keygen.c

# Follow the steps on building openssh.
cd openssh
./configure

# We only really want ssh-keygen.
make ssh-keygen

# Solve!
mv ssh-keygen ../
cd ../
./ssh-keygen && ssh -i id_ed25519 iwakuralain@<ip-address-here>
```

### Resources
- https://hnsecurity.it/blog/openssh-ssh-agent-shielded-private-key-extraction-x86_64-linux/
- https://vnhacker.substack.com/p/sapheads-hackjam-2009-challenge-6-or
- https://xorhash.gitlab.io/xhblog/0010.html

## Solve Script

Run `extract_linux.sh` then `unshield_linux.sh`.
- Use the `macos` versions if you're on MacOS. Just
- Use WSL if you're on Windows sorry.
- `unshield_linux.sh` or `unshield_macos.sh` will download a release version of [openssh](https://github.com/openssh/openssh-portable#building-a-release)
- If you're on MacOS you might have to `brew install openssl` if it's not installed already.

## Techniques / Tags

`sql-injection`, `blind-injection`, `time-based`

## Setup / Deployment Notes

Run `docker compose up` in the parent folder.
- Run `docker inspect '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' edward` to find the
  IP Address of the container so you can SSH into it.

## Known Issues / Notes

N/A
