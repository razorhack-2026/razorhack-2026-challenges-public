# GM-only sniffer image used to generate dist/substation_test_window.pcap.
# Never part of the live challenge deployment.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends tcpdump \
    && rm -rf /var/lib/apt/lists/*

CMD ["sh", "-c", "timeout ${CAPTURE_SECONDS:-115} tcpdump -i eth0 -w /out/substation_test_window.pcap; echo done"]
