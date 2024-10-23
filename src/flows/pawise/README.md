# Copilot Rag Project Structure 📂

This repository contains the source code and related files for the Copilot Rag project, which is designed to be run using the PromptFlow orchestration tool.

## Directory Structure 🌳

- `src/`: This is the main directory where all the source code files reside. It contains all the components and tools needed to run the project in Prompt Flow.

- `chunking_and_indexing/`: This directory contains code for chunking and indexing files from the web and PDFs into Azure AI search.

- `evaluation/`: This directory contains evaluation methods to test Prompt Flow. It allows batch sequence and individual evaluations through various metrics.

## Running the Project 🏃‍♂️

### 1. Create Conda Environment from the Repository

> Instructions for Windows users: 

1. **Create the Conda Environment**:
   - In your terminal or command line, navigate to the repository directory.
   - Execute the following command to create the Conda environment using the `environment.yml` file:
     ```bash
     conda env create -f environment.yml
     ```
   - This command creates a Conda environment as defined in `environment.yml`.

2. **Activating the Environment**:
   - After creation, activate the new Conda environment by using:
     ```bash
     conda activate sharepoint-indexing
     ```

> Instructions for Linux users (or Windows users with WSL or other linux setup): 

1. **Use `make` to Create the Conda Environment**:
   - In your terminal or command line, navigate to the repository directory and look at the Makefile.
   - Execute the `make` command specified below to create the Conda environment using the `environment.yml` file:
     ```bash
     make create_conda_env
     ```

2. **Activating the Environment**:
   - After creation, activate the new Conda environment by using:
     ```bash
     conda activate sharepoint-indexing
     ```
### 2. Install the Prompt Flow Extension for VS Code 

You can download the Prompt Flow extension for Visual Studio Code from the following link:

[https://marketplace.visualstudio.com/items?itemName=prompt-flow.prompt-flow](https://marketplace.visualstudio.com/items?itemName=prompt-flow.prompt-flow)

### 3. Execute and Evaluate 

Navigate to the `copilot/chat` directory and open the `flow.dag.yaml` file. This file outlines the orchestration in YAML format. It points to tasks and provides a clear understanding of the layers and directions of the Directed Acyclic Graph (DAG).





