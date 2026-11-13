# Training Wi-Fi Challenges

## Description:
The goal of these challenges is for competitors to go through the setup process for Wi-Fi hacking and get used to the commands involved while understanding *why* they are doing each step.  They are expected to do some research into the Aircrack-ng docs to find the commands needed for challenge 2 and 3 (the commands are listed at the bottom for reference).

## Challenge 1: Systems Check

To start peering into the invisible wireless networks around you, your device must have a compatible Wi-Fi card connected.  Any device that can use Wi-Fi has a Wi-Fi card (with an antenna), whether connected internally or externally through USB.  In Linux, they show up as network *interfaces* with the name `wlan`.  Your VM has some interfaces connected already.  One way to see them is to use the `ip a` command.

How many wireless interfaces are connected to the machine?
<br>`flag{3}`

## Challenge 2: Mailbox Shenanigans

By default, Wi-Fi interfaces are configured to only listen to broadcast packets or packets that have the device’s MAC address attached.  It’s like the Wi-Fi card is shuffling through an apartment mailbox and looking for letters addressed to itself or to everyone.  It will disregard anything specifically addressed to a different person (or device).  However, we can tell the interface to read everything it can and ignore who it is addressed to, allowing you to conduct wireless network reconnaissance.  There is a suite of Linux tools designed around Wi-Fi hacking called *Aircrack-ng* that can be used to place interfaces into *monitor* mode, among many other uses.  The machine already has the tools installed, and they will be used for all the wireless challenges.

Place the `wlan0` interface into monitor mode.  What is its name after doing this?
<br>`flag{wlan0mon}`

## Challenge 3: Yo, those are my packets, bro…

Finally, now that we have a Wi-Fi interface in monitor mode, we can start looking around and *capturing packets*.  Another command in the Aircrack-ng suite can do this.

How many wireless networks are there?
<br>`flag{8}`

<details>
<summary>Commands</summary>

* Challenge 2: `airmon-ng start wlan0`
* Challenge 3: `airodump-ng wlan0mon`
</details>
