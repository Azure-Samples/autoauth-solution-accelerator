# tests

usage:

```bash
export AZURE_OPENAI_ENDPOINT="https://evaluationfoun3932674679.openai.azure.com" && \
export AZURE_OPENAI_KEY="<scrubbed>" && \
export AZURE_OPENAI_DEPLOYMENT="gpt-4o-standard" && \
export AZURE_AI_FOUNDRY_CONNECTION_STRING="eastus2.api.azureml.ms;28d2df62-e322-4b25-b581-c43b94bd2607;rg-priorauth-eastus2-hls-autoauth;evaluations" && \
export AZURE_OPENAI_CHAT_DEPLOYMENT_ID="gpt-4o" && \
export PYTHONPATH="/Users/marcjimz/Documents/Development/gbb-ai-hls-factory-prior-auth:$PYTHONPATH" && \
pytest
```