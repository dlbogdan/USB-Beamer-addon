#!/command/with-contenv bashio

bashio::log.info "Preparing system for USB/IP..."

# In some container environments, /sys is mounted read-only.
# usbip needs to write to /sys to create the virtual device, so we remount it.
bashio::log.info "Remounting /sys in container."
if ! mount -o remount -t sysfs sysfs /sys; then
    bashio::log.fatal "Failed to remount /sys as read-write!"
    bashio::log.warning "This is a critical step for USB/IP to function."
    exit 1
fi

# Load kernel modules that are required for USB/IP to function.
# This is crucial for the vhci_hcd (Virtual Host Controller Interface)
# which allows the system to create virtual USB host controllers that remote
# devices can be attached to.
bashio::log.info "Loading required kernel module for USB/IP..."

if ! modprobe vhci-hcd; then
    bashio::log.fatal "Failed to load 'vhci-hcd' kernel module!"
    bashio::log.warning "This addon requires the 'vhci-hcd' kernel module to be available on the host system."
    bashio::log.warning "Please ensure your Home Assistant OS or supervised installation has this module."
    exit 1
fi

bashio::log.info "Kernel module 'vhci-hcd' loaded successfully." 