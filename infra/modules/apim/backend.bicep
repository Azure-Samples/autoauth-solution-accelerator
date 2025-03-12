/**
 * Backend Module
 * This module creates API Management backends and, if multiple backends are provided, a backend pool.
 *
 * Parameters:
 * - backendInstances: Array of backend definitions.
 *   Each object can include:
 *     - name: unique backend name.
 *     - url: service endpoint.
 *     - description (optional): description for the backend.
 *     - weight (optional): backend weight for the pool (default 10).
 *     - priority (optional): backend priority for the pool (default 1).
 *     - failureCount (optional): number of failures to trigger the circuit breaker (default 1).
 *     - errorReasons (optional): list of error reasons (default: ['Server errors']).
 *     - failureInterval (optional): time interval to evaluate failures (default 'PT5M').
 *     - statusCodeRanges (optional): list of status code ranges (default: [{ min:429, max:429 }]).
 *     - breakerRuleName (optional): circuit breaker rule name (default 'defaultBreakerRule').
 *     - tripDuration (optional): duration the breaker remains open (default 'PT1M').
 *     - acceptRetryAfter (optional): whether Retry-After header is supported (default false).
 *
 * - backendPoolName: The name of the backend pool to be created (if more than one backend is provided).
 * - apimResource: The APIM resource object (from your main deployment) to which the backends belong.
 */

 @description('Array of backend instance definitions.')
 param backendInstances array

 @description('Name for the backend pool; used if more than one backend instance is provided.')
 param backendPoolName string = 'backend-pool'

 @description('The parent API Management resource name.')
 param apimName string

 resource apimResource 'Microsoft.ApiManagement/service@2023-09-01-preview' existing = {
   name: apimName
 }

 // Create individual backend resources for each provided instance
 resource backends 'Microsoft.ApiManagement/service/backends@2023-09-01-preview' = [for instance in backendInstances: {
   name: instance.name
   parent: apimResource
   properties: {
    description: 'Backend for ${instance.name}. Part of pool ${backendPoolName}.'
     url: instance.url
     protocol: 'http'
     tls: {
       validateCertificateChain: true
       validateCertificateName: true
     }
     circuitBreaker: {
       rules: [
         {
           failureCondition: {
             count: 1
             errorReasons: [
               'Server errors'
             ]
             interval: 'PT5M'
             statusCodeRanges: [
               {
                 min: 429
                 max: 429
               }
             ]
           }
           name: 'defaultBreakerRule'
           tripDuration: 'PT1M'
           acceptRetryAfter: true
         }
       ]
     }
   }
 }]

 // If more than one backend instance is provided, create a backend pool resource.
 resource backendPool 'Microsoft.ApiManagement/service/backends@2023-09-01-preview' = if (length(backendInstances) > 1) {
   name: backendPoolName
   parent: apimResource
   properties: {
     description: 'Generic Backend Pool'
     type: 'Pool'
     pool: {
       services: [for instance in backendInstances: {
           id: '/backends/${instance.name}'
           priority: instance.priority ?? 1
           weight: instance.weight ?? 10
       }]
     }
   }
   dependsOn: [
     backends
   ]
 }


 @description('Outputs the created backend pool resource. If only one backend is used, this will be null.')
 output backendPoolOutput object = backendPool
