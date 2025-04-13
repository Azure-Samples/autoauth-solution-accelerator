

// Define a type for model configuration
@export()
@description('Configuration for a specific AI model deployment')
type ModelConfig = {
  @description('SKU name for the model')
  sku: string

  @description('Capacity for the model deployment')
  @minValue(1)
  capacity: int

  @description('Name of the AI model')
  name: string

  @description('Version of the AI model')
  version: string
}

// Define a type for backend configuration
@export()
@description('Configuration for an AI backend deployment')
type BackendConfigItem = {
  @description('Name of the backend configuration')
  name: string

  @description('Priority of the backend (lower values indicate higher priority)')
  @minValue(1)
  priority: int?

  @description('Azure region where the backend will be deployed')
  location: string

  @description('Chat model configuration')
  chat: ModelConfig?

  @description('Reasoning model configuration')
  reasoning: ModelConfig?

  @description('Embedding model configuration')
  embedding: ModelConfig?
}
