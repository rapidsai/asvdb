#!/bin/bash

set -e
UPLOAD_FILE=`conda build ./conda --output`
UPLOAD_FILES=$(echo ${UPLOAD_FILE}|sed -e 's/\-py[0-9][0-9]/\-py36/')
UPLOAD_FILES="${UPLOAD_FILES} $(echo ${UPLOAD_FILE}|sed -e 's/\-py[0-9][0-9]/\-py37/')"
UPLOAD_FILES="${UPLOAD_FILES} $(echo ${UPLOAD_FILE}|sed -e 's/\-py[0-9][0-9]/\-py38/')"

conda build --variants="{python: [3.6, 3.7, 3.8]}" ./conda
if [ "$1" = "--publish" ]; then
    anaconda upload ${UPLOAD_FILES}
fi
