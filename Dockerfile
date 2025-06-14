ARG BUILD_FROM=ghcr.io/hassio-addons/base:latest
FROM ${BUILD_FROM}

ARG BUILD_ARCH=amd64
RUN apk add --no-cache \
    kmod \
    linux-tools-usbip \
    hwdata-usb \
    device-mapper-libs \
    grep \
    openssh-client \
    python3 \
    py3-zeroconf \
    py3-aiohttp \
    usbip-utils \
    usbutils

# Copy root filesystem
COPY rootfs /

RUN chmod +x /etc/cont-init.d/01-keygen.sh \
    && chmod +x /etc/cont-init.d/02-load-modules.sh \
    && chmod +x /etc/services.d/beamer-client/run

# Build arguments
ARG BUILD_ARCH
ARG BUILD_DATE
ARG BUILD_DESCRIPTION
ARG BUILD_NAME
ARG BUILD_REF
ARG BUILD_REPOSITORY
ARG BUILD_VERSION

# Labels
LABEL \
    io.hass.name="${BUILD_NAME}" \
    io.hass.description="${BUILD_DESCRIPTION}" \
    io.hass.arch="${BUILD_ARCH}" \
    io.hass.type="addon" \
    io.hass.version=${BUILD_VERSION} \
    maintainer="Bogdan Dumitru <bogdan.dumitru@me.com>" \
    org.opencontainers.image.title="${BUILD_NAME}" \
    org.opencontainers.image.description="${BUILD_DESCRIPTION}" \
    org.opencontainers.image.vendor="Home Assistant Community Add-ons" \
    org.opencontainers.image.authors="Bogdan Dumitru <bogdan.dumitru@me.com>" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.url="https://addons.community" \
    org.opencontainers.image.source="https://github.com/${BUILD_REPOSITORY}" \
    org.opencontainers.image.documentation="https://github.com/${BUILD_REPOSITORY}/blob/main/README.md" \
    org.opencontainers.image.created=${BUILD_DATE} \
    org.opencontainers.image.revision=${BUILD_REF} \
    org.opencontainers.image.version=${BUILD_VERSION}
