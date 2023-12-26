import matplotlib.pyplot as plt
import numpy as np

# 读取log文件内容
log_file_path = "logs/hs-log.log"

with open(log_file_path, 'r', encoding='utf-8') as file:
    log_content = file.read()

# 分割每行的数据
lines = log_content.split('\n')

# 提取信息
time_series = []
workers_data = {}
workers_names = set()

for line in lines:
    parts = line.split(':')
    if len(parts) == 3:
        time_point, worker, percentage = parts
        percentage = round(float(percentage.rstrip('%')), 1)

        if time_point not in workers_data:
            workers_data[time_point] = {}

        workers_data[time_point][worker] = percentage
        workers_names.add(worker)

# 将字典中的数据拆分为 time_series 和 percentages
time_series = list(workers_data.keys())

print(workers_data)

# 绘制简单的折线图
plt.figure(figsize=(10, 6))

for worker in workers_names:
    x = range(1, len(time_series) + 1)
    y = [workers_data[time_point].get(worker, 0) for time_point in time_series]

    plt.plot(x, y, label=f'{worker}', marker='')

plt.title('Worker Percentage Over Time')
plt.xlabel('Time Index')
plt.ylabel('Percentage')
plt.legend()
plt.grid(True)
plt.show()
