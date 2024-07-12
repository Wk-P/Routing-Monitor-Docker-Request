import requests

def main():
    # Prometheus server URL
    prometheus_url = "http://192.168.0.100:9090/api/v1/query"

    # Prometheus query
    query = 'sum(100 * (1 - irate(node_cpu_seconds_total{mode="idle"}[5s]))) by (instance)'

    # Connect to Prometheus

    # Query Prometheus
    result = requests.get(prometheus_url, params={'query': query})

    print(result.json())


if __name__ == "__main__":
    main()
