#!/bin/bash
set -e

# Constants and configuration
SCRIPT_NAME=$(basename "$0")

# Initialize logging
log() {
    local level="$1"
    local message="$2"
    echo "[$SCRIPT_NAME] [$level] $message"
}

log_info() { log "INFO" "$1"; }
log_error() { log "ERROR" "$1" >&2; }

# Load environment variables
load_environment() {
    log_info "Loading environment variables..."
    indexer_hostname=$(azd env get-value INDEXER_FUNCTION_APP_HOSTNAME 2>/dev/null | tail -1 || true)
    indexer_app_name=$(azd env get-value INDEXER_FUNCTION_APP_NAME 2>/dev/null | tail -1 || true)
    rg_name=$(azd env get-value AZURE_RESOURCE_GROUP 2>/dev/null | tail -1 || true)

    if [[ -z "$indexer_hostname" ]]; then
        log_error "INDEXER_FUNCTION_APP_HOSTNAME is not set. Ensure the indexer function app was deployed."
        return 1
    fi
    if [[ -z "$indexer_app_name" || -z "$rg_name" ]]; then
        log_error "INDEXER_FUNCTION_APP_NAME or AZURE_RESOURCE_GROUP is not set."
        return 1
    fi
    return 0
}

# Fetch the default function host key (with retries — keys may not be
# available immediately after the app starts responding).
get_function_key() {
    local max_attempts=6
    local delay=10
    local key=""

    for (( attempt=1; attempt<=max_attempts; attempt++ )); do
        key=$(az functionapp keys list \
            --name "$indexer_app_name" \
            --resource-group "$rg_name" \
            --query "functionKeys.default" -o tsv 2>/dev/null | tail -1 || true)

        if [[ -z "$key" ]]; then
            key=$(az functionapp keys list \
                --name "$indexer_app_name" \
                --resource-group "$rg_name" \
                --query "masterKey" -o tsv 2>/dev/null | tail -1 || true)
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

# Wait for the function app to become reachable
wait_for_function_app() {
    local max_attempts=12
    local delay=15
    log_info "Waiting for function app to become available (up to $((max_attempts * delay))s)..."

    for (( attempt=1; attempt<=max_attempts; attempt++ )); do
        local status
        status=$(curl -s -o /dev/null -w "%{http_code}" \
            "https://${indexer_hostname}/" \
            --max-time 10 2>/dev/null || true)

        if [[ -n "$status" && "$status" != "000" ]]; then
            log_info "Function app is responding (HTTP $status)."
            return 0
        fi
        log_info "Attempt $attempt/$max_attempts — not ready yet, retrying in ${delay}s..."
        sleep "$delay"
    done

    log_error "Function app did not become available in time."
    return 1
}

# Invoke the indexer function app's reindex_all endpoint
invoke_reindex_all() {
    log_info "Fetching function host key for $indexer_app_name..."
    local func_key
    func_key=$(get_function_key)

    if [[ -z "$func_key" ]]; then
        log_error "Could not retrieve function key. Check your permissions on the function app."
        return 1
    fi

    local url="https://${indexer_hostname}/api/reindex_all"
    log_info "Invoking reindex_all at: $url"
    local masked_key="${func_key:0:8}..."
    log_info "curl command: curl -X POST \"$url\" -H \"Content-Type: application/json\" -H \"x-functions-key: ${masked_key}\" -d '{}' --connect-timeout 30 --max-time 600"

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
            -d '{}' \
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

    log_error "reindex_all failed after $max_retries attempts."
    return 1
}

# Main execution flow
main() {
    load_environment || exit 1
    wait_for_function_app || exit 1
    invoke_reindex_all || exit 1
    log_info "Post-deploy finished."
}

main
