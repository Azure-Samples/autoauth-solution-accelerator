#!/bin/bash

# =============================================================================
# Deployment Script for Prior Authorization Resources
#
# Usage:
#   ./deploy.sh <Cosmos Admin Password> <ACR Password> <AAD Client Secret>
#
# Description:
#   This script deploys Azure resources defined in the main Bicep file.
#   It accepts two secure passwords as arguments:
#     1. Cosmos Admin Password
#     2. Azure Container Registry (ACR) Password
#
# Security Note:
#   Passing sensitive information via command-line arguments can expose them
#   through process listings. Consider using environment variables or Azure Key Vault
#   for enhanced security.
# =============================================================================

# Exit immediately if a command exits with a non-zero status
set -e

# -----------------------------------------------------------------------------
# Function: print_usage
# Description: Displays the correct script usage.
# -----------------------------------------------------------------------------
print_usage() {
    echo "Usage: $0 <Cosmos Admin Password> <ACR Password> <AAD Client Secret>"
}

# -----------------------------------------------------------------------------
# Argument Validation
# -----------------------------------------------------------------------------
if [ $# -lt 3 ]; then
    echo "Error: Insufficient arguments provided."
    print_usage
    exit 1
fi

# Assign arguments to variables
cosmosAdminPassword="$1"
acrPassword="$2"
clientSecret="$3"

# -----------------------------------------------------------------------------
# Generate a Unique 7-Digit Identifier
# Description:
#   Generates a 7-digit unique identifier based on the resource group's ID.
# -----------------------------------------------------------------------------
unique_id=$(printf "%7d" $((RANDOM % 10000000)) | awk '{$1=$1};1')
region="westeurope"

# -----------------------------------------------------------------------------
# Function: measure_time
# Description:
#   Measures and prints the time taken by a given command.
# Usage:
#   measure_time <command>
# Example:
#   measure_time az group create --name "myRg" --location "eastus"
# -----------------------------------------------------------------------------
measure_time() {
    local cmd_description="$1"
    shift
    echo "Starting: $cmd_description"
    start_time=$(date +%s)
    
    # Execute the command
    "$@"
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    echo "Completed: $cmd_description in $duration seconds"
}

# -----------------------------------------------------------------------------
# Create the Resource Group for Prior Authorization Services
# -----------------------------------------------------------------------------
prior_auth_rg="prior-auth-$unique_id"
echo "Creating resource group: $prior_auth_rg in region: $region"
measure_time "Creating resource group $prior_auth_rg" \
    az group create --name "$prior_auth_rg" --location "$region"

# -----------------------------------------------------------------------------
# Deploy the Main Bicep File
# -----------------------------------------------------------------------------
main_bicep_file="devops/infra/main.bicep"
echo "Deploying main Bicep file: $main_bicep_file"

measure_time "Deploying main Bicep template" \
    az deployment group create \
        --debug \
        --resource-group "$prior_auth_rg" \
        --template-file "$main_bicep_file" \
        --parameters \
            priorAuthName="priorAuth" \
            tags={} \
            location="$region" \
            cosmosAdministratorPassword="$cosmosAdminPassword" \
            acrContainerImage="msftpriorauth.azurecr.io/priorauth-frontend:v2" \
            acrUsername="msftpriorauth" \
            acrPassword="$acrPassword" \
            aadClientId="2d30fb06-5f39-4d52-96c3-01ea8331e6f6" \
            aadClientSecret="$clientSecret" \
            aadTenantId="7621c2b4-468f-45a0-a5ae-270c4fad8d75" \
            authProvider="none"

echo "Deployment completed successfully."