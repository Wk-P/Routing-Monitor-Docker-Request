import pandas as pd
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

def read_data(filename):
    df = pd.read_excel(filename)
    columns = df.columns.to_list()
    data_dict = {col: df[col].to_list() for col in columns}
    return data_dict

def parse_data():
    filename = Path.cwd() / 'RS5' / 'clientv_single_worker_node-L1-RB150-DTTueSep31817402024.xlsx'
    data = read_data(filename)

    # x axis 1
    jobs_on_worker_node = np.array(data['jobs_on_worker_node']).tolist()

    # x axis 2
    worker_wait_time = np.array(data['worker_wait_time']).tolist()

    return jobs_on_worker_node, worker_wait_time

if __name__ == "__main__":
    # Parse data
    jobs_on_worker_node, worker_wait_time = parse_data()

    # Plot the data
    plt.figure(figsize=(10, 7))

    # Plot both datasets in the same subplot
    plt.scatter(jobs_on_worker_node, worker_wait_time, color='red', marker='o', label='Received Jobs vs Delay Time')
    plt.scatter(worker_wait_time, jobs_on_worker_node, color='green', marker='x', label='Processing Jobs vs Delay Time')

    # Add title and labels
    plt.title('Jobs vs Delay Time')
    plt.xlabel('Jobs / Delay Time')
    plt.ylabel('Delay Time / Jobs')

    # Add legend
    plt.legend()

    # Show the plot
    plt.show()
