# WiFi Challenge 1 - MAC lookup

**Category:** WiFi  
**Difficulty:** Easy  
**Author:** Lt. Rico Kopernicus

## Description

There's an unsecured wireless control system network on the Icarus.  We know that RTX (Raytheon) supplied networking devices for the ship, see if you can find one on this network and get the MAC address.

## Flag

The MAC address of the RTX device connected to `Icarus_Extnl_Sys_E`.  
`flag{44:51:DB:CD:F6:6F}`

## Solution

1. Put a wireless interface into monitor mode using `airmon-ng start <interface_name>`
2. Run `airodump-ng <new_interface_name>` to see networks and devices
3. Find devices (called stations in `airodump-ng`) connected to `Icarus_Extnl_Sys_E`
4. Use a MAC lookup website (https://maclookup.app/) to find the one that is from Raytheon (now called RTX).

## Known Issues / Notes

Since there are only four devices on `Icarus_Extnl_Sys_E`, players can just brute force enter MAC addresses as the flag until they find the right one. Only solution I can think of is to create more devices so it's not as easy, but that could only go so far.

## Techniques / Tags

`wireless`, `wifi`, `forensics` 
