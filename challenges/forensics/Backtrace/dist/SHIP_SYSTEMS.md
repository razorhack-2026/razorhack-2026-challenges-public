# ISV Kestrel — Shipnet Asset Inventory

Internal network segment: `10.10.0.0/24` (flat, unsegmented — engineering,
crew workstations, and OT devices all share the same broadcast domain).

| IP Address  | Hostname      | Description                                                        |
|-------------|---------------|--------------------------------------------------------------------|
| 10.10.0.2   | `eng-console` | Engineering console. Telnet management interface; also acts as the Modbus/TCP master for OT devices on this segment. |
| 10.10.0.5   | `shipnet-fs`  | Internal file server. Accepts crew/engineering backups over FTP.     |
| 10.10.0.10  | `airlock-plc` | Airlock environmental & safety PLC. Modbus/TCP slave, unit ID 1.      |
| 10.10.0.15  | `voss-ws`     | Workstation assigned to R. Voss, Propulsion Engineer.                 |
| 10.10.0.47  | `mtx-47`      | Shared maintenance terminal, Cargo Bay 2. No assigned crew — logs in with whatever credentials are on hand for the shift. |

## `airlock-plc` register map (for context only)

| Type            | Address | Name                       | Notes                                   |
|-----------------|---------|----------------------------|-----------------------------------------|
| Coil            | 0       | `airlock_safety_interlock` | 1 = engaged (safe), 0 = disabled          |
| Coil            | 1       | `airlock_door_status`      | 0 = closed, 1 = open                      |
| Holding Register| 0       | `cabin_pressure_kpa`       | —                                          |
| Holding Register| 1       | `cabin_temp_c`             | —                                          |
| Holding Register| 2       | `occupancy_count`          | —                                          |

This map is for reference only — see `kestrel_shipnet.pcap` for the actual
capture.
