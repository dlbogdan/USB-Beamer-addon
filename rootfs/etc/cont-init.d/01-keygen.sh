#!/bin/bash

# Generate SSH key pair if it doesn't exist
if [ ! -f /data/id_rsa ]; then
    echo "Generating SSH key pair..."
    ssh-keygen -t rsa -b 4096 -f /data/id_rsa -N ""
fi

# Extract public key and update config
PUBLIC_KEY=$(cat /data/id_rsa.pub)
bashio::config.set 'public_key' "$PUBLIC_KEY" 