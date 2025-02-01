# Documentation for the Bicep modules in this directory



## Table of Contents
- [fetch-container-image](#fetch-container-image)
  - [Parameters](#parameters)
  - [Outputs](#outputs)
  - [Snippets](#snippets)

# fetch-container-image

## Parameters

Parameter name | Required | Description
-------------- | -------- | -----------
exists         | Yes      |
name           | Yes      |

### exists

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)



### name

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)



## Outputs

Name | Type | Description
---- | ---- | -----------
containers | array |

## Snippets

### Parameter file

```json
{
    "$schema": "https://schema.management.azure.com/schemas/2015-01-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "metadata": {
        "template": "infra/modules/compute/fetch-container-image.json"
    },
    "parameters": {
        "exists": {
            "value": null
        },
        "name": {
            "value": ""
        }
    }
}
```
