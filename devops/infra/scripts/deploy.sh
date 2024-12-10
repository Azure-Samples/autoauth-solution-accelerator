#!/bin/bash

# Check if the user provided a password as an argument
if [ $# -lt 1 ]; then
    echo "Usage: $0 <Cosmos Admin Password>"
    exit 1
fi

cosmosAdminPassword="$1"

# Generate a unique 3-character alphanumeric identifier
unique_id=$(printf "%7d" $((RANDOM % 10000000)) | awk '{$1=$1};1')
region="eastus2"

# Function to measure the time taken for each step
measure_time() {
    start_time=$(date +%s)
    "$@"
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    echo "Time taken for $1: $duration seconds"
}

# Create the resource group for search services
prior_auth_rg="prior-auth-$unique_id"
echo "Creating resource group for prior auth services: $prior_auth_rg"
measure_time az group create --name "$prior_auth_rg" --location "$region"

# Deploy the main Bicep file
main_bicep_file="devops/infra/main.bicep"
echo "Deploying main Bicep file: $main_bicep_file"
measure_time az deployment group create \
    --debug \
    --resource-group "$prior_auth_rg" \
    --template-file "$main_bicep_file" \
    --parameters priorAuthName="priorAuth" \
                 tags={} \
                 location="$region" \
                 cosmosAdministratorPassword="$cosmosAdminPassword"