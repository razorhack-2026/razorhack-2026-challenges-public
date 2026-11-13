# hey edward where r my keys

**Category:** Forensics  
**Difficulty:** Insane  
**Author:** Grace  

## Description

Your coworker Lain somehow lost their SSH keys to an important server in the ship. All you've got is
a coredump of OpenSSH's
[`ssh-agent`](https://github.com/openssh/openssh-portable/blob/master/ssh-agent.c) and, for whatever
reason, the public key the server uses `id_ed25519.pub`.

Log back in to the server to get your flag (SSH in as `iwakuralain` at the address in the connection info).

## Files Provided

- `core.961.tar.gz`
- `id_ed25519.pub`
