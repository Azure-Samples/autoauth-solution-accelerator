#!/bin/bash

# Define the resource group name pattern: prior-auth- followed by exactly 4 or 5 digits
PATTERN="^prior-auth-[0-9]{4,5}$"

# Function to delete a Cosmos DB account
delete_cosmosdb_account() {
    local rg=$1
    local account=$2

    echo "Processing Cosmos DB account: $account in resource group: $rg"

    # List and remove any locks on the Cosmos DB account
    locks=$(az lock list --resource-group "$rg" --resource-name "$account" --resource-type "Microsoft.DocumentDB/databaseAccounts" --query "[].{name:name}" -o tsv)
    if [[ -n "$locks" ]]; then
        echo "Found locks on Cosmos DB account: $account. Removing locks..."
        for lock in $locks; do
            echo "Deleting lock: $lock"
            az lock delete --resource-group "$rg" --resource-name "$account" --resource-type "Microsoft.DocumentDB/databaseAccounts" --name "$lock"
            if [[ $? -eq 0 ]]; then
                echo "Successfully deleted lock: $lock"
            else
                echo "Failed to delete lock: $lock" >&2
            fi
        done
    else
        echo "No locks found on Cosmos DB account: $account."
    fi

    # Attempt to delete the Cosmos DB account using az cosmosdb delete
    echo "Attempting to delete Cosmos DB account: $account"
    az cosmosdb delete --name "$account" --resource-group "$rg" --yes --no-wait
    if [[ $? -eq 0 ]]; then
        echo "Deletion initiated for Cosmos DB account: $account"
    else
        echo "Failed to initiate deletion for Cosmos DB account: $account. Attempting force delete..."
        # Retrieve the resource ID
        resourceId=$(az cosmosdb show --name "$account" --resource-group "$rg" --query id --output tsv)
        if [[ -n "$resourceId" ]]; then
            # Force delete the resource
            az resource delete --ids "$resourceId" --yes --no-wait
            if [[ $? -eq 0 ]]; then
                echo "Force deletion initiated for Cosmos DB account: $account"
            else
                echo "Failed to force delete Cosmos DB account: $account" >&2
            fi
        else
            echo "Unable to retrieve resource ID for Cosmos DB account: $account" >&2
        fi
    fi
}

# Get the list of resource groups that start with "prior-auth-"
resourceGroups=$(az group list --query "[?starts_with(name, 'prior-auth-')].name" -o tsv)

# Loop through each resource group
for rg in $resourceGroups; do
    # Check if the resource group name matches the pattern prior-auth- followed by 4 or 5 digits
    if [[ $rg =~ $PATTERN ]]; then
        echo "Processing resource group: $rg"

        # List all Cosmos DB for MongoDB accounts in the resource group
        cosmosAccounts=$(az cosmosdb list --resource-group "$rg" --query "[?kind=='MongoDB'].name" -o tsv)

        if [[ -n "$cosmosAccounts" ]]; then
            echo "Found Cosmos DB for MongoDB accounts in resource group: $rg"
            for account in $cosmosAccounts; do
                delete_cosmosdb_account "$rg" "$account"
            done
        else
            echo "No Cosmos DB for MongoDB accounts found in resource group: $rg"
        fi

        # After deleting Cosmos DB accounts, attempt to delete the resource group
        echo "Deleting resource group: $rg"
        az group delete --name "$rg" --yes --no-wait
        if [[ $? -eq 0 ]]; then
            echo "Deletion initiated for resource group: $rg"
        else
            echo "Failed to initiate deletion for resource group: $rg" >&2
        fi
    else
        echo "Skipping resource group (does not match 4 or 5-digit pattern): $rg"
    fi
done

echo "All matching resource groups have been processed for deletion."