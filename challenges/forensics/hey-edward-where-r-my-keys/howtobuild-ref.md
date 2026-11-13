Temporary "Design Doc" for Grace

Setup

In a Kali VM, Run
```
# Install SSH Stuff (this might already be installed)
sudo apt upgrade && sudo apt install openssh-client

# Enable SSH (this might already be running)
sudo systemctl enable --now ssh

# Generate an SSH Key
mkdir .ssh # might already be created
cd .ssh

# Create ed25519 key pair. THE EMAIL IS IMPORTANT. NO PASSPHRASE.
ssh-keygen -t ed25519 -C "iwakuralain@wired.net"

# Add private key to ssh-agent
ssh-add ~/.ssh/<PRIVATE-KEY-FILE>

# Create a coredump of ssh-agent
ulimit -c unlimited
sudo gcore -a $SSH_AGENT_PID
```

Solution
something
