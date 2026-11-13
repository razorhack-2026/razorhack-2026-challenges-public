# Connection Guide

Most of RASA's machines aren't on your desk. Drill controllers, survey computers, and station servers can be on the other side of the station, or on a rock a few million kilometers away. To work on them, you'll connect remotely using **SSH**.

## What Is SSH?

**SSH** (Secure Shell) is a way to log into another computer over a network and run commands on it as if you were sitting in front of it. Everything sent over an SSH connection, including your password, is encrypted, so nobody listening in on the network can read it.

When you connect, you'll get a **terminal**: a text window where you type commands and the remote machine responds. No mouse, no icons, just text.

To connect, you need three things:

| What | Example | Where to get it |
|---|---|---|
| A **username** | `cadet` | Your supervisor or a Gamemaster |
| An **address** (hostname or IP) | `10.0.0.25` or `drill-07.example` | Same |
| A **password** or **key** | | Same (and keep it secret) |

Sometimes you'll also need a **port** number. SSH uses port `22` by default, but some machines listen on a different one.

## The Basic Command

On almost every system, connecting looks like this:

```
ssh username@address
```

If the machine uses a non-standard port, add `-p`:

```
ssh -p 2222 username@address
```

## Connecting From Your Computer

### Linux

SSH is almost always installed already.

1. Open a terminal (often **Ctrl + Alt + T**).
2. Type `ssh username@address` and press **Enter**.

If it says `command not found`, install the OpenSSH client with your package manager (for example, `sudo apt install openssh-client` on Ubuntu/Debian).

### macOS

SSH is built in.

1. Open **Terminal** (press **Cmd + Space**, type "Terminal", press **Enter**).
2. Type `ssh username@address` and press **Enter**.

### Windows

Modern Windows 10 and 11 include an SSH client.

1. Open **PowerShell** or **Command Prompt** (press the **Windows key**, type "PowerShell", press **Enter**).
2. Type `ssh username@address` and press **Enter**.

If that doesn't work, or you prefer a graphical tool, **PuTTY** is a popular free alternative:

1. Open PuTTY.
2. Enter the address in **Host Name (or IP address)**.
3. Make sure **Port** is correct (usually `22`) and **Connection type** is **SSH**.
4. Click **Open**, then enter your username and password when asked.

## What Happens When You Connect

### The first-time warning

The first time you connect to a machine, you'll see something like:

```
The authenticity of host '10.0.0.25 (10.0.0.25)' can't be established.
ED25519 key fingerprint is SHA256:abc123...
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

This is normal. Your computer has never seen this machine before and is asking you to confirm it's the right one. Type `yes` and press **Enter**. Your computer remembers the machine from now on.

If you see this warning for a machine you've connected to *before*, or a big scary message saying the host key has **changed**, stop and tell someone. That can mean something is pretending to be the machine you're trying to reach.

### Entering your password

```
cadet@10.0.0.25's password:
```

Type your password and press **Enter**. **Nothing will appear while you type**, not even dots or asterisks. That's on purpose. Just type it and press Enter.

### You're in

When it works, you'll see a prompt from the remote machine, something like:

```
cadet@drill-07:~$
```

Anything you type now runs on *that* machine, not yours.

## A Few Commands to Get Started

| Command | What it does |
|---|---|
| `whoami` | Shows which user you're logged in as |
| `hostname` | Shows which machine you're on |
| `pwd` | Shows which folder you're in |
| `ls` | Lists files in the current folder |
| `ls -la` | Lists *all* files, including hidden ones |
| `cd foldername` | Moves into a folder |
| `cat filename` | Prints the contents of a file |
| `exit` | Disconnects and returns you to your own computer |

## SSH Keys (Optional)

Instead of typing a password every time, you can use an **SSH key pair**: a private key that stays on your computer and a public key that goes on the remote machine.

```
ssh-keygen -t ed25519
```

This creates the keys (by default in a `.ssh` folder in your home directory). The file ending in `.pub` is the public one and is safe to share. The other one is **private**. Never share it, the same way you'd never share your badge.

## Copying Files

Need to move a file to or from a remote machine? `scp` works like `ssh`:

```
scp myfile.txt username@address:/home/username/
scp username@address:/home/username/report.txt .
```

The first copies a file *to* the remote machine. The second copies a file *from* it into your current folder.

## Troubleshooting

| Message | What it usually means |
|---|---|
| `Connection refused` | Wrong port, or SSH isn't running on that machine |
| `Connection timed out` | Wrong address, or you're not on the right network |
| `Permission denied` | Wrong username or password |
| `Could not resolve hostname` | Typo in the address |

Still stuck? Read the error message carefully (see **How To Read**), then ask a crewmate or a Gamemaster.
