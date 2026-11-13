# Ignition 8.3 gateway with both Perspective HMIs, both Modbus devices and every
# tag already loaded, so it boots ready (no Designer, no Script Console).
# Build context: src/   (docker compose build, or tools/challenge_images.py)
#
# The PLCs share this container's network namespace (one Fargate task), so the
# devices point at 127.0.0.1:502 (ECLSS) and 127.0.0.1:5020 (training).

# Trimmed to what the rig uses, because Fargate pulls the whole image and boots
# every module on each start. The HMIs are core Perspective components with no
# scripts, and the tags all come from the two Modbus devices, so the gateway
# keeps three modules: Perspective, OPC-UA and the Modbus driver (which needs
# OPC-UA). Also gone: the Designer/Vision launcher and Perspective Workstation
# installers it offers for download, the JRE archives it hands to launchers
# (the gateway runs on the unpacked lib/runtime/jre-nix), and JxBrowser
# (Chromium for Vision and Workstation clients). Nobody logs in to a team's
# copy, so none of that is used.
FROM inductiveautomation/ignition:8.3.9 AS trimmed
USER root
WORKDIR /usr/local/bin/ignition
RUN find user-lib/modules -name '*.modl' \
        ! -name 'Perspective-module.modl' \
        ! -name 'OPC-UA-module.modl' \
        ! -name 'Modbus Driver v2-module.modl' \
        -delete \
    && test "$(find user-lib/modules -name '*.modl' | wc -l)" -eq 3 \
    && rm -f lib/core/launch/*.dmg lib/core/launch/*.exe lib/core/launch/*.tar.gz \
        lib/runtime/jre-mac.tar.gz lib/runtime/jre-win.zip lib/runtime/jre-nix.tar.gz \
    && rm -rf lib/opt/jxbrowser \
    && test -x lib/runtime/jre/bin/java

# Deleting files in a later layer would leave them in the image Fargate pulls,
# so the trimmed filesystem is copied onto an empty image instead, and the
# stock image's settings are restored below. That list is complete for 8.3.9:
# its config is the ENV, WORKDIR, USER, EXPOSE, HEALTHCHECK and ENTRYPOINT
# below (ENTRYPOINT replaced by ours), with no CMD, VOLUME, STOPSIGNAL or SHELL.
# When bumping the tag, compare `docker inspect --format '{{json .Config}}'` of
# the new stock image and of this one, and copy over anything that changed.
FROM scratch
COPY --from=trimmed / /
LABEL org.opencontainers.image.base.name="docker.io/inductiveautomation/ignition:8.3.9"
ENV PATH=/usr/local/bin/ignition/lib/runtime/jre/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US \
    LC_ALL=en_US.UTF-8 \
    PASS_THROUGH=both \
    IGNITION_INSTALL_LOCATION=/usr/local/bin/ignition \
    HOME=/home/ignition
WORKDIR /usr/local/bin/ignition

# Unlicensed = the 2-hour trial; rh-entrypoint.sh resets it when it expires.
# IGN_GATEWAY_NAME is training IG1's flag: keep it equal to gateway_name in
# training/training_flags.json.
ENV ACCEPT_IGNITION_EULA=Y \
    IGNITION_EDITION=standard \
    GATEWAY_ADMIN_USERNAME=admin \
    TZ=America/Chicago \
    IGN_GATEWAY_NAME=ozark-horizon-gw \
    IGN_MAX_MEMORY_MB=1536

COPY --chown=2003:0 ignition/projects/ /usr/local/bin/ignition/data/projects/
COPY --chown=2003:0 ignition/config/ /usr/local/bin/ignition/data/config/resources/external/
COPY images/ignition/rh-entrypoint.sh /usr/local/bin/rh-entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/rh-entrypoint.sh && chmod 755 /usr/local/bin/rh-entrypoint.sh
USER 2003:2003

EXPOSE 8088
HEALTHCHECK --interval=10s --timeout=3s --start-period=60s --retries=10 CMD health-check.sh -t 3
ENTRYPOINT ["rh-entrypoint.sh"]
