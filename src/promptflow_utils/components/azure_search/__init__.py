import requests

def search_bing(query, api_key, top_k):
    # Bing Search API URL
    url = "https://api.bing.microsoft.com/v7.0/search"

    # Parameters for the search
    params = {
        "q": query,     # Search query
        "count": top_k  # Number of results to return
    }

    # Headers including the API key
    headers = {
        "Ocp-Apim-Subscription-Key": api_key
    }

    # Send the request
    response = requests.get(url, headers=headers, params=params)

    # Check if the request was successful
    if response.status_code == 200:
        return response.json()
    else:
        return f"Error: {response.status_code}"

