#!/bin/bash
set -e

# Constants and configuration
SCRIPT_NAME=$(basename "$0")
SPINNER_CHARS='|/-\'
SPINNER_DELAY=0.1

# Initialize logging
log() {
    local level="$1"
    local message="$2"
    echo "[$SCRIPT_NAME] [$level] $message"
}

log_info() { log "INFO" "$1"; }
log_error() { log "ERROR" "$1" >&2; }
log_warn() { log "WARN" "$1"; }

# Check required dependencies
check_dependencies() {
    log_info "Checking required dependencies..."
    local missing=0
    for cmd in az jq pytest; do
        if ! command -v "$cmd" &>/dev/null; then
            log_error "Required command not found: $cmd"
            missing=1
        fi
    done

    if [[ $missing -eq 1 ]]; then
        log_error "Please install missing dependencies"
        return 1
    fi
    return 0
}

# Load environment variables
load_environment() {
    log_info "Loading environment variables..."
    job_name=$(azd env get-value CONTAINER_JOB_NAME)
    rg_name=$(azd env get-value AZURE_RESOURCE_GROUP)
    frontend_image=$(azd env get-value SERVICE_FRONTEND_IMAGE_NAME)
    acr_endpoint=$(azd env get-value AZURE_CONTAINER_REGISTRY_ENDPOINT)
    storage_account=$(azd env get-value AZURE_STORAGE_ACCOUNT_NAME)

    # Validate required variables
    if [[ -z "$job_name" || -z "$rg_name" ]]; then
        log_error "Required environment variables not set"
        return 1
    fi
    return 0
}

# Find project root by searching for .git directory
find_project_root() {
    local current_dir="$PWD"
    while [[ "$current_dir" != "/" ]]; do
        if [[ -d "$current_dir/.git" ]]; then
            echo "$current_dir"
            return 0
        fi
        current_dir="$(dirname "$current_dir")"
    done
    log_error ".git directory not found in any parent directory"
    return 1
}

check_container_job() {
    log_info "Checking if Container App Job exists and has successful executions..."

    # Check if job exists
    if az containerapp job show -g "$rg_name" --name "$job_name" &>/dev/null; then
        successful_count=$(az containerapp job execution list -g "$rg_name" --name "$job_name" \
            --query "length([?properties.status=='Succeeded'])" -o tsv)
        if [ "$successful_count" -gt 0 ]; then
            log_info "Container App Job already has $successful_count successful execution(s). Skipping..."
            return 0
        fi
        log_info "Container App Job exists but has no successful executions. Continuing..."
        return 1
    else
        log_info "Container App Job does not exist or could not be accessed. Continuing with deployment..."
        return 1
    fi
}

update_and_run_job() {
    if [ -z "$frontend_image" ]; then
        log_error "SERVICE_FRONTEND_IMAGE_NAME is null. Ensure your azd deployment succeeded. Exiting..."
        return 1
    fi

    log_info "Logging into Azure Container Registry..."
    az acr login --name "$acr_endpoint"

    log_info "Updating container app job image..."
    az containerapp job update -g "$rg_name" --name "$job_name" --image "$frontend_image"

    log_info "Starting job $job_name..."
    az containerapp job start -g "$rg_name" --name "$job_name"

    log_info "Waiting for job to complete..."
    status="Running"
    while [[ "$status" == "Running" || "$status" == "Pending" ]]; do
        sleep 10
        execution=$(az containerapp job execution list -g "$rg_name" --name "$job_name" --query "[0]" -o json)
        status=$(echo "$execution" | jq -r .properties.status)
        log_info "Status: $status"
    done

    if [[ "$status" == "Succeeded" ]]; then
        log_info "Job completed successfully."
        return 0
    else
        log_error "Job failed with status: $status"
        return 1
    fi
}

# Display a spinner for long-running processes
show_spinner() {
    local pid=$1
    while kill -0 "$pid" 2>/dev/null; do
        for (( i=0; i<${#SPINNER_CHARS}; i++ )); do
            printf "\r[%s] %s" "$SCRIPT_NAME" "${SPINNER_CHARS:$i:1}"
            sleep "$SPINNER_DELAY"
        done
    done
    printf "\r%s\n" "$(printf ' %.0s' {1..50})"  # Clear the line
}

# Toggle storage account shared key access
set_storage_shared_key_access() {
    local enable=$1  # true/false

    if [ -z "$storage_account" ]; then
        log_warn "Storage account name not found in environment variables. Skipping key access update."
        return 0
    fi

    log_info "$([ "$enable" = true ] && echo "Enabling" || echo "Disabling") key-based access for storage account: $storage_account"
    if az storage account update --name "$storage_account" --resource-group "$rg_name" --allow-shared-key-access "$enable" &>/dev/null; then
        log_info "Successfully $([ "$enable" = true ] && echo "enabled" || echo "disabled") key-based access."
        return 0
    else
        log_error "Failed to $([ "$enable" = true ] && echo "enable" || echo "disable") key-based access."
        return 1
    fi
}

run_evaluations() {
    # Ask user if they want to run evaluations (if not already set)
    if [ -z "${RUN_EVALS:-}" ]; then
        log_info "RUN_EVALS env flag currently not set. Model evaluations will be skipped."
        return 0
    else
        log_info "RUN_EVALS flag is already set to: $RUN_EVALS"
        if [[ "$RUN_EVALS" =~ ^[Ff][Aa][Ll][Ss][Ee]$ ]]; then
            log_info "RUN_EVALS is set to false. Skipping evaluations."
            return 0
        fi
    fi

    # Change to project root directory
    local project_root
    project_root=$(find_project_root) || return 1
    log_info "Changing directory to project root: $project_root"
    cd "$project_root" || { log_error "Failed to change directory to project root"; return 1; }

    if [ ! -d "tests" ]; then
        log_error "Tests directory not found! Current directory: $(pwd)"
        return 1
    fi

    # Enable key-based auth for storage account
    set_storage_shared_key_access true

    local test_result=0

    # Install dependencies
    log_info "Checking and installing dependencies..."
    if [ -f "requirements.txt" ]; then
        if ! pip install -r requirements.txt --quiet; then
            log_error "Failed to install required packages."
            test_result=1
        else
            log_info "Dependencies installed."
        fi
    else
        log_warn "No requirements.txt found. Skipping dependency installation."
    fi

    # Run tests with spinner status
    if [ $test_result -eq 0 ]; then
        log_info "Starting pytest..."
        pytest -s --color=yes tests &
        pytest_pid=$!

        show_spinner $pytest_pid &
        spinner_pid=$!

        wait $pytest_pid || test_result=1
        kill $spinner_pid 2>/dev/null
        wait $spinner_pid 2>/dev/null  # Wait for spinner to terminate

        [ $test_result -eq 0 ] && log_info "Tests completed successfully." || log_error "Tests failed."
    fi

    # Disable shared key access
    set_storage_shared_key_access false

    return $test_result
}

# Setup cleanup trap
cleanup() {
    # Make sure spinner process is killed
    if [[ -n "${spinner_pid:-}" ]]; then
        kill $spinner_pid 2>/dev/null
        wait $spinner_pid 2>/dev/null
    fi

    # Make sure storage account key access is disabled
    if [[ -n "$storage_account" ]]; then
        set_storage_shared_key_access false
    fi

    log_info "Script finished"
}
trap cleanup EXIT

# Main execution flow
main() {
    check_dependencies || exit 1
    load_environment || exit 1

    if ! check_container_job; then
        update_and_run_job || exit 1
    fi

    run_evaluations
    return $?
}

main
