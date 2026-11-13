# Ignition 8.3 gateway with the Containment project, its tags and the four Modbus devices
# already loaded from the files in this folder (the ones containment.gwbk was built from), so it
# boots ready with no restore and no mounts: one Fargate task per team.
# Build context: src/ignition   (docker compose build, or tools/challenge_images.py)
#
# The sim and hmi-proxy share this container's network namespace, so the devices point at
# 127.0.0.1:502-505 and the gateway listens on 8089 (hmi-proxy has 8088, the port players use).
# Ignition can't be told to listen on loopback only, so its admin password is random for each
# copy (rh-entrypoint.sh) instead of the lab login the backup carries.
FROM inductiveautomation/ignition:8.3.9

# Unlicensed = the 2-hour trial; rh-entrypoint.sh resets it when it expires.
ENV ACCEPT_IGNITION_EULA=Y \
    IGNITION_EDITION=standard \
    GATEWAY_ADMIN_USERNAME=admin \
    GATEWAY_HTTP_PORT=8089 \
    TZ=America/Chicago

# A fresh gateway faults if data/config/resources/core/ already exists, so the config goes in
# the external collection, which core inherits from.
COPY --chown=2003:0 projects/ /usr/local/bin/ignition/data/projects/
COPY --chown=2003:0 config/resources/core/ /usr/local/bin/ignition/data/config/resources/external/
COPY rh-entrypoint.sh /usr/local/bin/rh-entrypoint.sh
USER root
RUN sed -i 's/\r$//' /usr/local/bin/rh-entrypoint.sh && chmod 755 /usr/local/bin/rh-entrypoint.sh
USER 2003:2003

EXPOSE 8089
ENTRYPOINT ["rh-entrypoint.sh"]
