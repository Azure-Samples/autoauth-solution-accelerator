#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# invoke_indexer.sh — Helper to invoke the local Policy Indexer Function App
#
# Usage:
#   ./invoke_indexer.sh reindex          # Full pipeline: setup + run indexer
#   ./invoke_indexer.sh setup            # Create/update AI Search resources only
#   ./invoke_indexer.sh run              # Trigger the indexer
#   ./invoke_indexer.sh status           # Check indexer status
#   ./invoke_indexer.sh health           # Health check
#   ./invoke_indexer.sh upload <file>    # Upload a PDF to blob storage
# ---------------------------------------------------------------------------
set -euo pipefail

BASE_URL="${FUNC_BASE_URL:-http://localhost:7071}"

# Get the current signed-in identity from Azure CLI
echo "== Current Azure Identity =="
ACCOUNT_INFO=$(az account show --output json 2>/dev/null) || {
    echo "ERROR: Not signed in to Azure CLI. Run 'az login' first."
    exit 1
}

USER_NAME=$(echo "$ACCOUNT_INFO" | jq -r '.user.name')
USER_TYPE=$(echo "$ACCOUNT_INFO" | jq -r '.user.type')
SUBSCRIPTION=$(echo "$ACCOUNT_INFO" | jq -r '.name')
TENANT_ID=$(echo "$ACCOUNT_INFO" | jq -r '.tenantId')

# Get the Entra ID Object ID for the signed-in user
if [[ "$USER_TYPE" == "user" ]]; then
    OBJECT_ID=$(az ad signed-in-user show --query id -o tsv 2>/dev/null) || OBJECT_ID="(could not resolve)"
else
    OBJECT_ID="(service principal — use 'az ad sp show')"
fi

echo "  User:         $USER_NAME"
echo "  Type:         $USER_TYPE"
echo "  Object ID:    $OBJECT_ID"
echo "  Tenant:       $TENANT_ID"
echo "  Subscription: $SUBSCRIPTION"
echo ""

# ---------------------------------------------------------------------------
ACTION="${1:-reindex}"
shift 2>/dev/null || true

case "$ACTION" in
    reindex)
        echo ">> POST $BASE_URL/api/reindex"
        echo "   (setup all AI Search resources + trigger indexer)"
        echo ""
        curl -s -X POST "$BASE_URL/api/reindex" | jq .
        ;;
    setup)
        echo ">> POST $BASE_URL/api/setup_index"
        echo "   (create/update data source, index, skillset, indexer)"
        echo ""
        curl -s -X POST "$BASE_URL/api/setup_index" | jq .
        ;;
    run)
        echo ">> POST $BASE_URL/api/run_indexer"
        echo "   (trigger the indexer)"
        echo ""
        curl -s -X POST "$BASE_URL/api/run_indexer" | jq .
        ;;
    status)
        echo ">> GET $BASE_URL/api/indexer_status"
        echo ""
        curl -s "$BASE_URL/api/indexer_status" | jq .
        ;;
    health)
        echo ">> GET $BASE_URL/api/health"
        echo ""
        curl -s "$BASE_URL/api/health" | jq .
        ;;
    upload)
        FILE="${1:-}"
        if [[ -z "$FILE" || ! -f "$FILE" ]]; then
            echo "ERROR: Provide a valid PDF file path. Usage: $0 upload <file.pdf>"
            exit 1
        fi
        FILENAME=$(basename "$FILE")
        echo ">> POST $BASE_URL/api/upload_policies"
        echo "   Uploading: $FILE"
        echo ""
        curl -s -X POST "$BASE_URL/api/upload_policies" \
            -H "Content-Type: application/octet-stream" \
            -H "X-Filename: $FILENAME" \
            --data-binary "@$FILE" | jq .
        ;;
    *)
        echo "Unknown action: $ACTION"
        echo "Usage: $0 {reindex|setup|run|status|health|upload <file>}"
        exit 1
        ;;
esac
