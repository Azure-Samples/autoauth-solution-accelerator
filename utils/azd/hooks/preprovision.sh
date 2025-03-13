#!/bin/bash

CURRENT_USER_CLIENT_ID=$(az ad signed-in-user show --query id -o tsv)
GIT_HASH=$(git rev-parse --short HEAD)
azd env set PRINCIPAL_ID $CURRENT_USER_CLIENT_ID
azd env set GIT_HASH $GIT_HASH

echo "======================================="
echo " Current User Client ID: $CURRENT_USER_CLIENT_ID"
echo " Git Commit Hash:        $GIT_HASH"
echo "======================================="


if [[ -z "$(azd env get-value ENABLE_EASY_AUTH 2>/dev/null)" || -z "$(azd env get-value DISABLE_INGRESS 2>/dev/null)" ]]; then
    while true; do
        read -p "Would you like to enable Easy Auth for your Container App? (y/n): " enable_easy_auth
        if [[ "$enable_easy_auth" =~ ^[Yy]$ ]]; then
            azd env set ENABLE_EASY_AUTH true
            azd env set DISABLE_INGRESS false
            break
        elif [[ "$enable_easy_auth" =~ ^[Nn]$ ]]; then
            echo "===================================================================="
            echo "⚠️  WARNING: You are deploying a publicly exposed frontend application"
            echo "without authentication. This poses significant security risks!"
            echo "===================================================================="
            while true; do
                read -p "Would you like to disable ingress by default to mitigate this risk? (y/n): " disable_ingress
                if [[ "$disable_ingress" =~ ^[Yy]$ ]]; then
                    azd env set ENABLE_EASY_AUTH false
                    azd env set DISABLE_INGRESS true
                    break
                elif [[ "$disable_ingress" =~ ^[Nn]$ ]]; then
                    break
                else
                    echo "Please enter 'y' or 'n'."
                fi
            done
            break
        else
            echo "Please enter 'y' or 'n'."
        fi
    done
elif [[ "$(azd env get-value ENABLE_EASY_AUTH)" == "true" ]]; then
    azd env set DISABLE_INGRESS false
else
    current_easy_auth=$(azd env get-value ENABLE_EASY_AUTH)
    current_disable_ingress=$(azd env get-value DISABLE_INGRESS)
    echo "======================================="
    echo "Environment variables already set:"
    echo " ENABLE_EASY_AUTH: $current_easy_auth"
    echo " DISABLE_INGRESS:  $current_disable_ingress"
    echo "To change these settings, run:"
    echo "  azd env set ENABLE_EASY_AUTH <true|false>"
    echo "  azd env set DISABLE_INGRESS <true|false>"
    echo "======================================="
fi
