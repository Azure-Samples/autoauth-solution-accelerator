#!/bin/bash

set -x

CURRENT_USER_CLIENT_ID=$(az ad signed-in-user show --query id -o tsv)
azd env set PRINCIPAL_ID $CURRENT_USER_CLIENT_ID
