#!/bin/bash
set -euo pipefail

# Deploy the frontend container image to an existing Azure Container Registry.
# This script uses `az acr build` for a cloud-based build (no local Docker needed).
#
# Usage:
#   ./app/frontend/deploy_to_acr.sh --registry <acr-name> [--image <name>] [--tag <tag>]
#
# Examples:
#   ./app/frontend/deploy_to_acr.sh --registry myregistry
#   ./app/frontend/deploy_to_acr.sh --registry myregistry --image autoauth-frontend --tag v1.2.0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

IMAGE_NAME="autoauth-frontend"
IMAGE_TAG="latest"
REGISTRY_NAME=""

usage() {
    echo "Usage: $0 --registry <acr-name> [--image <name>] [--tag <tag>]"
    echo ""
    echo "Options:"
    echo "  --registry, -r   Name of the Azure Container Registry (required)"
    echo "  --image, -i      Image name (default: autoauth-frontend)"
    echo "  --tag, -t        Image tag (default: latest)"
    echo "  --help, -h       Show this help message"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --registry|-r)  REGISTRY_NAME="$2"; shift 2 ;;
        --image|-i)     IMAGE_NAME="$2"; shift 2 ;;
        --tag|-t)       IMAGE_TAG="$2"; shift 2 ;;
        --help|-h)      usage ;;
        *)              echo "Unknown option: $1"; usage ;;
    esac
done

if [[ -z "$REGISTRY_NAME" ]]; then
    echo "Error: --registry is required."
    usage
fi

# Verify az CLI is available and logged in
if ! command -v az &>/dev/null; then
    echo "Error: Azure CLI (az) is not installed."
    exit 1
fi

if ! az account show &>/dev/null; then
    echo "Error: Not logged in to Azure. Run 'az login' first."
    exit 1
fi

echo "=== Frontend Container Build & Push ==="
echo "  Registry:  ${REGISTRY_NAME}"
echo "  Image:     ${IMAGE_NAME}:${IMAGE_TAG}"
echo "  Dockerfile: app/frontend/Dockerfile"
echo "  Context:   ${REPO_ROOT}"
echo ""

az acr build \
    --registry "$REGISTRY_NAME" \
    --image "${IMAGE_NAME}:${IMAGE_TAG}" \
    --file "$REPO_ROOT/app/frontend/Dockerfile" \
    "$REPO_ROOT"

echo ""
echo "Done. Image pushed to ${REGISTRY_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}"
