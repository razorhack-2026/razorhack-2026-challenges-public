#!/usr/bin/env bash

if (( $# != 1 )); then
    echo "Usage: $0 <path_to_folder_with_bkcrack_executable>"
    exit 1
fi

curl -L -X GET "https://mast.stsci.edu/search/hst/api/v0.1/retrieve_product?product_name=U2SA2902T%2Fu2sa2902t_flt.fits" --output "observation.fits" --fail --create-dirs
mapfile -t lines <<< $( $1/bkcrack -C ../dist/errorLogs.zip -c observation.fits -p observation.fits)
read -r key1 key2 key3 <<< "${lines[-1]}"
echo "Recovered keys: $key1 $key2 $key3"
$1/bkcrack -C ../dist/errorLogs.zip -k $key1 $key2 $key3 -D decryptedErrorLogs.zip