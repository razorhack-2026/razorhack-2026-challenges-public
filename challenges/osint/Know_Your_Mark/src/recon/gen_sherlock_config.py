#!/usr/bin/env python3
"""Generate a Sherlock site manifest for the deployed challenge services.

Use real competitor-reachable URLs, not Docker-internal names or localhost. The
required username_claimed field is left blank so the manifest does not disclose
the target handle; it is not needed for a normal Sherlock search.
"""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

OTHER_SITE_NAMES = (
    "BeaconBoard", "CrewExchange", "DeepSignal", "Dockside", "FleetArchive", "HorizonForum",
    "LunarList", "OrbitalNotes", "OutpostMarket", "RelayHub", "Starlight", "TransitSquare",
    "AsteroidBazaar", "CargoCommons", "CelestialBoards", "CometCorner", "CosmosJournal", "FlightLog",
    "GalaxyForum", "LaunchPad", "NebulaNotes", "NovaNetwork", "SectorMarket", "WaypointBoard",
)
DEFAULT_OTHER_PORTS = tuple(range(8100, 8124))


def site(name, base_url):
    url = urlsplit(base_url)
    if (url.scheme not in ("http", "https") or not url.netloc or url.username
            or url.password or url.query or url.fragment or "{" in base_url or "}" in base_url):
        raise ValueError(f"{name} URL must be an HTTP(S) base URL without credentials, query, or fragment")
    base = base_url.rstrip("/")
    return {"urlMain": base + "/", "url": base + "/u/{}",
            "errorType": "status_code", "username_claimed": ""}


def build_manifest(starfic_url, driftmarket_url, starfic_name="StarFic", driftmarket_name="DriftMarket",
                   other_host=None, other_ports=DEFAULT_OTHER_PORTS, other_names=OTHER_SITE_NAMES):
    names = [starfic_name.strip(), driftmarket_name.strip()]
    if not all(names) or names[0] == names[1]:
        raise ValueError("Site names must be nonempty and distinct")
    manifest = {names[0]: site(names[0], starfic_url), names[1]: site(names[1], driftmarket_url)}
    if other_host:
        host = urlsplit(other_host)
        if (host.scheme not in ("http", "https") or not host.hostname or host.port is not None
                or host.username or host.password or host.path not in ("", "/") or host.query or host.fragment):
            raise ValueError("Other-site host must be an HTTP(S) origin without a port or path")
        if len(other_ports) != 24 or any(not 1 <= port <= 65535 for port in other_ports):
            raise ValueError("Supply exactly 24 valid other-site ports")
        other_names = tuple(name.strip() for name in other_names)
        if len(other_names) != 24 or not all(other_names) or len(set(other_names)) != 24:
            raise ValueError("Supply exactly 24 nonempty, distinct other-site names")
        if len(set(other_ports)) != len(other_ports) or set(names) & set(other_names):
            raise ValueError("Site names and other-site ports must be distinct")
        for real_url in (starfic_url, driftmarket_url):
            real = urlsplit(real_url)
            real_port = real.port or (443 if real.scheme == "https" else 80)
            if real.scheme == host.scheme and real.hostname == host.hostname and real_port in other_ports:
                raise ValueError("An other-site port overlaps a real site's port")
        for name, port in zip(other_names, other_ports):
            manifest[name] = site(name, f"{host.scheme}://{host.netloc}:{port}")
    return dict(sorted(manifest.items()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--starfic-url", required=True, help="competitor-reachable StarFic base URL")
    parser.add_argument("--driftmarket-url", required=True, help="competitor-reachable DriftMarket base URL")
    parser.add_argument("--starfic-name", default="StarFic", help="display name in Sherlock")
    parser.add_argument("--driftmarket-name", default="DriftMarket", help="display name in Sherlock")
    parser.add_argument("--other-host", required=True, help="competitor-reachable HTTP(S) origin for other sites, without a port")
    parser.add_argument("--other-ports", default=",".join(map(str, DEFAULT_OTHER_PORTS)),
                        help="24 comma-separated published ports, in Compose order")
    parser.add_argument("--other-names", default=",".join(OTHER_SITE_NAMES),
                        help="24 comma-separated site display names, in Compose order")
    parser.add_argument("--out", required=True, type=Path, help="output JSON path")
    args = parser.parse_args()
    try:
        ports = tuple(int(port) for port in args.other_ports.split(","))
        manifest = build_manifest(args.starfic_url, args.driftmarket_url, args.starfic_name, args.driftmarket_name,
                                  args.other_host, ports, tuple(args.other_names.split(",")))
    except ValueError as exc:
        parser.error(str(exc))
    args.out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
