#!/bin/bash

# Function to display usage
function usage() {
    echo "Usage: $0 {build|run|up}"
    exit 1
}

# Check if command line argument is provided
if [ $# -eq 0 ]; then
    usage
fi

# Load environment variables from .env file
export $(grep -v '^#' .env | xargs)

# Define variables for Docker image name and tag
imageName="benchmarkingapp" # Assuming 'chunkingindexingskill' is your Docker image name
imageTag="latest" # Replace 'latest' with your specific tag if needed
templateFile="deployment\\container-apps\\index-azure-ai-app.bicep" # Replace 'yourBicepFileName.bicep' with your Bicep file name

# Define the Azure Container Registry name
containerRegistryName="${ENVIRONMENT}containerregistryaigbb"

# Check the command line argument
case "$1" in

    build_and_push_container)
    echo "Using IMAGE NAME: ${IMAGENAME}"
    echo "Using IMAGE TAG: ${IMAGETAG}"
    echo "Using CONTAINER REGISTRY NAME: ${CONTAINER_REGISTRY_NAME}"
    az acr build --image ${IMAGENAME}:${IMAGETAG} \
        --registry ${CONTAINER_REGISTRY_NAME} \
        --file $PWD\\devops\\cicd\\benchmarking_app\\Dockerfile .
    ;;
    build_container)
        # Build the Docker image
        docker build -f app/Indexing/Dockerfile -t $imageName:$imageTag .
        ;;
    run_container)
        # Run the Docker container, mapping port 8000 to 8000 and setting environment variables
        docker run -p 8000:8000 \
            -e AZURE_OPENAI_KEY=$AZURE_OPENAI_KEY \
            -e AZURE_AOAI_CHAT_MODEL_NAME_DEPLOYMENT_ID=$AZURE_AOAI_CHAT_MODEL_NAME_DEPLOYMENT_ID \
            -e AZURE_OPENAI_API_VERSION=$AZURE_OPENAI_API_VERSION \
            -e AZURE_OPENAI_API_ENDPOINT=$AZURE_OPENAI_API_ENDPOINT \
            $imageName
        ;;
    push_container)
        #az acr build -t doc-uploader1.0 -r
        # Non-Interactive Azure Login using Service Principal
        echo "Logging in to Azure with service principal..."
        echo "az login --service-principal -u $CLIENT_ID -p $CLIENT_SECRET --tenant $TENANT_ID"
        az login --service-principal -u $CLIENT_ID -p $CLIENT_SECRET --tenant $TENANT_ID

        # Log in to Azure Container Registry
        echo "Logging in to Azure Container Registry..."
        echo "az acr login --name $containerRegistryName.azurecr.io"
        az acr login --name $containerRegistryName.azurecr.io

        # Tag the Docker image for Azure Container Registry
        echo "Tagging Docker image for Azure Container Registry..."
        echo "docker tag $imageName:$imageTag $containerRegistryName.azurecr.io/$imageName:$imageTag"
        docker tag $imageName:$imageTag $containerRegistryName.azurecr.io/$imageName:$imageTag

        # Push the Docker image to Azure Container Registry
        echo "Pushing Docker image to Azure Container Registry..."
        echo "docker push $containerRegistryName.azurecr.io/$imageName:$imageTag"
        docker push $containerRegistryName.azurecr.io/$imageName:$imageTag
        ;;
    up_job)
        # create the job
        az containerapp job create \
            --name "indexing-job" --resource-group "$AZURE_RESOURCE_GROUP"  --environment $AZURE_CONTAINER_ENVIRONMENT_NAME \
            --trigger-type "Schedule" \
            --cron-expression "*/10 * * * *" \
            --replica-timeout 1800 --replica-retry-limit 0 --replica-completion-count 1 --parallelism 1 \
            --image $containerRegistryName.azurecr.io/prepdocs:1.0 \
            --cpu "2" --memory "4Gi" \
            --env-vars "AZURE_OPENAI_KEY=$AZURE_OPENAI_KEY" \
            "AZURE_AOAI_CHAT_MODEL_NAME_DEPLOYMENT_ID=$AZURE_AOAI_CHAT_MODEL_NAME_DEPLOYMENT_ID" \
            "AZURE_OPENAI_API_VERSION=$AZURE_OPENAI_API_VERSION" \
            "AZURE_OPENAI_API_ENDPOINT=$AZURE_OPENAI_API_ENDPOINT" \
            --registry-server $containerRegistryName.azurecr.io \
            --registry-identity system \
            --mi-system-assigned

        # give the job permissions to resources
        az role assignment create --role "Storage Blob Data Contributor" --assignee `az containerapp job show -n indexing-job -g $AZURE_RESOURCE_GROUP -o tsv --query identity.principalId` --resource-group $AZURE_RESOURCE_GROUP
        az role assignment create --role "Cognitive Services OpenAI User" --assignee `az containerapp job show -n indexing-job -g $AZURE_RESOURCE_GROUP -o tsv --query identity.principalId` --resource-group $AZURE_RESOURCE_GROUP
        az role assignment create --role "Cognitive Services User" --assignee `az containerapp job show -n indexing-job -g $AZURE_RESOURCE_GROUP -o tsv --query identity.principalId` --resource-group $AZURE_RESOURCE_GROUP
        az role assignment create --role "Search Index Data Contributor" --assignee `az containerapp job show -n indexing-job -g $AZURE_RESOURCE_GROUP -o tsv --query identity.principalId` --resource-group $AZURE_RESOURCE_GROUP
        az role assignment create --role "Search Service Contributor" --assignee `az containerapp job show -n indexing-job -g $AZURE_RESOURCE_GROUP -o tsv --query identity.principalId` --resource-group $AZURE_RESOURCE_GROUP
        ;;
    up_app)
        # create the job
        az containerapp create -n doc-indexer -g $AZURE_RESOURCE_GROUP --environment $AZURE_CONTAINER_ENVIRONMENT_NAME \
        --image $CONTAINER_REGISTRY_NAME.azurecr.io/$IMAGENAME:$IMAGETAG \
        --cpu "1" --memory "2Gi" \
        --env-vars "AZURE_OPENAI_KEY=$AZURE_OPENAI_KEY" \
            "AZURE_AOAI_CHAT_MODEL_NAME_DEPLOYMENT_ID=$AZURE_AOAI_CHAT_MODEL_NAME_DEPLOYMENT_ID" \
            "AZURE_OPENAI_API_VERSION=$AZURE_OPENAI_API_VERSION" \
            "AZURE_OPENAI_API_ENDPOINT=$AZURE_OPENAI_API_ENDPOINT" \
        --registry-server $CONTAINER_REGISTRY_NAME.azurecr.io \
        --registry-identity system \
        --system-assigned \
        --min-replicas 1 --max-replicas 5 \
        --scale-rule-http-concurrency 4 \
        --ingress external \
        --target-port $PORT

        az role assignment create --role "Contributor" --assignee `az containerapp show -n doc-indexer -g $AZURE_RESOURCE_GROUP -o tsv --query identity.principalId` --resource-group $AZURE_RESOURCE_GROUP
        az role assignment create --role "Storage Blob Data Contributor" --assignee `az containerapp show -n doc-indexer -g $AZURE_RESOURCE_GROUP -o tsv --query identity.principalId` --resource-group $AZURE_RESOURCE_GROUP
       ;;
    *)
 esac
