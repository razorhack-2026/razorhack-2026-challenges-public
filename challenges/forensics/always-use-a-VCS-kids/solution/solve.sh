#!/bin/bash
BASH_SOURCE_DIR=$(echo $BASH_SOURCE | awk -F'[/]' '{OFS="/"; NF--; print}')
GIT_TAR_FILEPATH="${BASH_SOURCE_DIR}/../dist/my_calculator.tar.gz"

tar -xzf $GIT_TAR_FILEPATH && cd my_calculator && (git fsck --lost-found | grep "^dangling commit" | sed "s/^dangling commit //g" | xargs git grep "flag")
