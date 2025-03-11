#!/bin/bash

set -x

CURRENT_USER_CLIENT_ID=$(az ad signed-in-user show --query id -o tsv)
GIT_HASH=$(git rev-parse --short HEAD)
azd env set PRINCIPAL_ID $CURRENT_USER_CLIENT_ID
azd env set GIT_HASH $GIT_HASH
