#!/usr/bin/env bashio

bashio::log.info "Checking for SSH key pair..."

# Generate SSH key pair if it doesn't exist
if ! bashio::fs.file_exists "/data/id_rsa"; then
    bashio::log.info "No key pair found, generating a new one..."
    ssh-keygen -t rsa -b 4096 -f /data/id_rsa -N ""
fi

# Read the public key
PUBLIC_KEY=$(cat /data/id_rsa.pub)

bashio::log.info "-----------------------------------------------------------"
bashio::log.info "COPY THE PUBLIC KEY BELOW TO THE SERVER'S WEB UI"
bashio::log.info "-----------------------------------------------------------"
echo "$PUBLIC_KEY"
bashio::log.info "-----------------------------------------------------------" 