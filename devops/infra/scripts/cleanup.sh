#!/bin/bash

# Get the list of resource groups that start with "prior-auth-"
resourceGroups=$(az group list --query "[?starts_with(name, 'prior-auth-')].name" -o tsv)

# Loop through each resource group
for rg in $resourceGroups; do
    # Check if the resource group name matches the pattern prior-auth- followed by exactly four digits
    if [[ $rg =~ ^prior-auth-[0-9]{4}$ ]]; then
        echo "Deleting resource group: $rg"
        az group delete --name $rg --yes --no-wait
    else
        echo "Skipping resource group (does not match four-digit pattern): $rg"
    fi
done

echo "All matching resource groups have been scheduled for deletion."