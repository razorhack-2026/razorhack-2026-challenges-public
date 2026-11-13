#!/usr/bin/env python3
"""Run the supplied recovery program on the local test box."""
import argparse

import paramiko


def recover(host: str, port: int, user: str, password: str, recovery_key: str):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, port=port, username=user, password=password, timeout=15)
    command = f"cd ~ && ./voidcrypt_recover --key '{recovery_key}' locked_dashboard.bin"
    _, stdout, _ = client.exec_command(command)
    output = stdout.read().decode(errors="replace")
    status = stdout.channel.recv_exit_status()
    client.close()
    return status, output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=2222)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--recovery-key", required=True)
    args = parser.parse_args()
    status, output = recover(args.host, args.port, args.user, args.password, args.recovery_key)
    print(output, end="")
    raise SystemExit(status)


if __name__ == "__main__":
    main()
