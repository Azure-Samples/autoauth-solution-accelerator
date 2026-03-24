#!/bin/bash
set -euo pipefail

# Constants and configuration
SCRIPT_NAME=$(basename "$0")

# Initialize logging
log() {
    local level="$1"
    local message="$2"
    echo "[$SCRIPT_NAME] [$level] $message"
}

log_info() { log "INFO" "$1"; }
log_warn() { log "WARN" "$1"; }
log_error() { log "ERROR" "$1" >&2; }

should_fail_postdeploy() {
    local strict_mode="${POSTDEPLOY_STRICT:-false}"
    strict_mode=$(printf '%s' "$strict_mode" | tr '[:upper:]' '[:lower:]')
    [[ "$strict_mode" == "1" || "$strict_mode" == "true" || "$strict_mode" == "yes" ]]
}

handle_postdeploy_failure() {
    local message="$1"

    if should_fail_postdeploy; then
        log_error "$message"
        return 1
    fi

    log_warn "$message"
    log_warn "Continuing because POSTDEPLOY_STRICT is not enabled. Re-run utils/azd/hooks/postdeploy.sh later if you want to bootstrap the indexer after deployment."
    return 0
}

# Load environment variables
load_environment() {
    log_info "Loading environment variables..."
    indexer_hostname=$(azd env get-value INDEXER_FUNCTION_APP_HOSTNAME 2>/dev/null | tail -1 | tr -d '\r' || true)
    indexer_app_name=$(azd env get-value INDEXER_FUNCTION_APP_NAME 2>/dev/null | tail -1 | tr -d '\r' || true)
    frontend_container_name=$(azd env get-value FRONTEND_CONTAINER_NAME 2>/dev/null | tail -1 | tr -d '\r' || true)
    rg_name=$(azd env get-value AZURE_RESOURCE_GROUP 2>/dev/null | tail -1 | tr -d '\r' || true)

    if [[ -z "$indexer_hostname" ]]; then
        log_error "INDEXER_FUNCTION_APP_HOSTNAME is not set. Ensure the indexer function app was deployed."
        return 1
    fi
    if [[ -z "$indexer_app_name" || -z "$rg_name" ]]; then
        log_error "INDEXER_FUNCTION_APP_NAME or AZURE_RESOURCE_GROUP is not set."
        return 1
    fi
    if [[ -z "$frontend_container_name" ]]; then
        log_error "FRONTEND_CONTAINER_NAME is not set. Ensure the frontend container app was deployed."
        return 1
    fi
    return 0
}

sync_frontend_function_access() {
    local func_key="$1"
    local secret_name="indexer-function-key"

    log_info "Syncing Function App access into frontend container app '$frontend_container_name'..."

    az containerapp secret set \
        --name "$frontend_container_name" \
        --resource-group "$rg_name" \
        --secrets "${secret_name}=${func_key}" >/dev/null

    az containerapp update \
        --name "$frontend_container_name" \
        --resource-group "$rg_name" \
        --set-env-vars \
            "INDEXER_FUNCTION_KEY=secretref:${secret_name}" \
            "INDEXER_FUNCTION_BASE_URL=https://${indexer_hostname}" \
            "INDEXER_FUNCTION_APP_HOSTNAME=${indexer_hostname}" >/dev/null

    log_info "Frontend container app updated with indexer function access."
}

# Fetch the default function host key (with retries — keys may not be
# available immediately after the app starts responding).
get_function_key_via_arm() {
    az rest \
        --method post \
        --url "https://management.azure.com/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${rg_name}/providers/Microsoft.Web/sites/${indexer_app_name}/host/default/listkeys?api-version=2024-04-01" \
        --query 'functionKeys.default' \
        -o tsv 2>/dev/null | tail -1 | tr -d '\r' || true
}

get_function_key() {
    local max_attempts=12
    local delay=15
    local key=""

    for (( attempt=1; attempt<=max_attempts; attempt++ )); do
        key=$(az functionapp keys list \
            --name "$indexer_app_name" \
            --resource-group "$rg_name" \
            --query "functionKeys.default" -o tsv 2>/dev/null | tail -1 | tr -d '\r' || true)

        if [[ -z "$key" ]]; then
            key=$(az functionapp keys list \
                --name "$indexer_app_name" \
                --resource-group "$rg_name" \
                --query "masterKey" -o tsv 2>/dev/null | tail -1 | tr -d '\r' || true)
        fi

        if [[ -z "$key" ]]; then
            key=$(get_function_key_via_arm)
        fi

        if [[ -n "$key" ]]; then
            echo "$key"
            return 0
        fi

        # Print to stderr so it doesn't pollute the captured stdout
        echo "Key not ready yet (attempt $attempt/$max_attempts), retrying in ${delay}s..." >&2
        sleep "$delay"
    done

    echo ""
}

# Wait for the function app to become reachable on the protected health endpoint
wait_for_function_app() {
    local func_key="$1"
    local max_attempts=12
    local delay=15
    local url="https://${indexer_hostname}/api/health?code=${func_key}"
    log_info "Waiting for function app health endpoint to become available (up to $((max_attempts * delay))s)..."

    for (( attempt=1; attempt<=max_attempts; attempt++ )); do
        local status
        status=$(curl -s -o /dev/null -w "%{http_code}" \
            "$url" \
            --max-time 10 2>/dev/null || true)

        if [[ "$status" == "200" || "$status" == "401" || "$status" == "403" ]]; then
            log_info "Function app endpoint is responding (HTTP $status)."
            return 0
        fi
        log_info "Attempt $attempt/$max_attempts — not ready yet, retrying in ${delay}s..."
        sleep "$delay"
    done

    log_error "Function app did not become available in time."
    return 1
}

# Upload seed policy PDFs from utils/data/cases/policies/ to blob storage
# via the function app's upload_policies endpoint.
upload_seed_policies() {
    local func_key="$1"
    local policy_dir="utils/data/cases/policies"
    local url="https://${indexer_hostname}/api/upload_policies?code=${func_key}"

    if [[ ! -d "$policy_dir" ]]; then
        log_info "Seed policy directory '$policy_dir' not found — skipping upload."
        return 0
    fi

    local pdf_files=()
    while IFS= read -r -d '' f; do
        pdf_files+=("$f")
    done < <(find "$policy_dir" -maxdepth 1 -name '*.pdf' -print0 2>/dev/null)

    if [[ ${#pdf_files[@]} -eq 0 ]]; then
        log_info "No PDF files found in $policy_dir — skipping upload."
        return 0
    fi

    log_info "Uploading ${#pdf_files[@]} seed PDF(s) to $url ..."

    local failed=0
    for pdf in "${pdf_files[@]}"; do
        local filename
        filename=$(basename "$pdf")
        log_info "  Uploading $filename ..."

        local http_code
        http_code=$(curl -s -o /dev/null -w "%{http_code}" \
            -X POST "$url" \
            -H "Content-Type: application/octet-stream" \
            -H "X-Filename: $filename" \
            -H "x-functions-key: ${func_key}" \
            --data-binary "@$pdf" \
            --connect-timeout 30 \
            --max-time 120 2>/dev/null || true)

        if [[ -n "$http_code" && "$http_code" -ge 200 && "$http_code" -lt 300 ]]; then
            log_info "  $filename uploaded (HTTP $http_code)."
        else
            log_error "  $filename upload failed (HTTP $http_code)."
            failed=$((failed + 1))
        fi
    done

    if [[ $failed -gt 0 ]]; then
        log_error "$failed file(s) failed to upload."
        return 1
    fi

    log_info "All seed PDFs uploaded successfully."
    return 0
}

# Invoke the indexer function app's reindex_all endpoint
invoke_reindex_all() {
    log_info "Fetching function host key for $indexer_app_name..."
    local func_key
    func_key=$(get_function_key)

    if [[ -z "$func_key" ]]; then
        handle_postdeploy_failure "Could not retrieve function key. Check your permissions on the function app, or re-run postdeploy once the function host is ready."
        return $?
    fi

    sync_frontend_function_access "$func_key" || {
        handle_postdeploy_failure "Failed to sync Function App access into the frontend container app."
        return $?
    }

    wait_for_function_app "$func_key" || {
        handle_postdeploy_failure "Function app did not become available in time."
        return $?
    }

    # Upload seed PDFs before triggering reindex
    upload_seed_policies "$func_key" || {
        log_error "Seed policy upload failed — continuing with reindex anyway."
    }

    local url="https://${indexer_hostname}/api/reindex_all?code=${func_key}"
    log_info "Invoking reindex_all at: $url"
    local masked_key="${func_key:0:8}..."
    log_info "curl command: curl -X POST \"$url\" -H \"Content-Type: application/json\" -H \"x-functions-key: ${masked_key}\" -d '{\"prefix\":\"policies_ocr/\"}' --connect-timeout 30 --max-time 600"

    local max_retries=3
    local retry_delay=20

    for (( retry=1; retry<=max_retries; retry++ )); do
        local http_code
        local tmp_body
        local tmp_err
        tmp_body=$(mktemp)
        tmp_err=$(mktemp)

        http_code=$(curl -s -o "$tmp_body" -w "%{http_code}" \
            -X POST "$url" \
            -H "Content-Type: application/json" \
            -H "x-functions-key: ${func_key}" \
            -d '{"prefix":"policies_ocr/"}' \
            --connect-timeout 30 \
            --max-time 600 2>"$tmp_err" || true)

        local response_body
        response_body=$(cat "$tmp_body")
        local curl_err
        curl_err=$(cat "$tmp_err")
        rm -f "$tmp_body" "$tmp_err"

        log_info "HTTP status: $http_code"
        if [[ -n "$response_body" ]]; then
            log_info "Response: $response_body"
        fi
        if [[ -n "$curl_err" ]]; then
            log_info "curl stderr: $curl_err"
        fi

        if [[ -n "$http_code" && "$http_code" != "000" && "$http_code" -ge 200 && "$http_code" -lt 300 ]]; then
            log_info "reindex_all completed successfully."
            return 0
        fi

        if [[ $retry -lt $max_retries ]]; then
            log_info "Attempt $retry/$max_retries failed, retrying in ${retry_delay}s..."
            sleep "$retry_delay"
        fi
    done

    handle_postdeploy_failure "reindex_all failed after $max_retries attempts."
    return $?
}

# Main execution flow
main() {
    load_environment || exit 1
    invoke_reindex_all || exit 1
    log_info "Post-deploy finished."
}

main
