# WiFi Challenge 2 - Hidden SSID & PSK Cracking

**Category:** WiFi  
**Difficulty:** Medium  
**Author:** Lt. Rico Kopernicus

## Description

Something hidden is running on the Icarus.  It's password-protected, so it must be important. Find a way to get the password.

## Flag

The password to the network `Icarus_Bridge`.  
`flag{suhninnwittyeesoe}`

## Solution

1. Run `airodump-ng -w <output_filename> <interface>` to find the WPA2 encrypted AP (the `-w` option will let you specify the name of the output file).  Make sure the interface is in monitor mode from previous challenge.
2. Find the BSSID of the device (called station in `airodump-ng`) connected to `Icarus_Bridge`
3. Open another terminal and connect to the challenge VM
4. In this new terminal, run `aireplay-ng -0 5 -a <AP_BSSID> -c <Device_BSSID> <different_interface>` while the other terminal is running airodump.  Make sure to use a different interface that's not in monitor mode.
    - You may need to set the channel to the AP's one (found in `airodump-ng`), use `iwconfig <interface> channel <channel#>`
5. Once you see `WPA handshake` appear in the top-right of the `airodump-ng` terminal, you can stop it.
6. Run `aircrack-ng -w <wordlist> <cap_file>` on each `.cap` file created until you find the right AP.
7. Let it run until it cracks the password.

## Known Issues / Notes

The password used in this challenge was pulled from the `rockyou.txt` wordlist, which is provided on the challenge VM.  A challenge solve is not guaranteed if the player uses a different wordlist.

## Techniques / Tags

`wireless`, `wifi`, `password`, `cracking`, `brute_force`
