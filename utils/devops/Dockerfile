FROM ghcr.io/actions/actions-runner:2.304.0
# for latest release, see https://github.com/actions/runner/releases

USER root

# install curl and jq
RUN apt-get update && apt-get install -y curl jq && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Azure CLI
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

# Install Azure Developer CLI (azd)
RUN mkdir -p /tmp/azd && \
    curl -fsSL https://aka.ms/install-azd.sh > /tmp/azd/install-azd.sh && \
    chmod +x /tmp/azd/install-azd.sh && \
    /tmp/azd/install-azd.sh && \
    rm -rf /tmp/azd

COPY github-actions-runner/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

USER runner

ENTRYPOINT ["./entrypoint.sh"]
