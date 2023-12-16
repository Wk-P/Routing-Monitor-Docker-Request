import matplotlib.pyplot as plt
import statsmodels.api as sm

# 读取log文件内容
log_file_path = "logs/hs-log.log"

with open(log_file_path, 'r', encoding='utf-8') as file:
    log_content = file.read()

# 分割每行的数据
lines = log_content.split('\n')

# 提取信息
time_series = []
workers_data = {}

for line in lines:
    parts = line.split(':')
    if len(parts) == 3:
        time_point, worker, percentage = parts
        percentage = round(float(percentage.rstrip('%')), 1)

        if time_point not in workers_data:
            workers_data[time_point] = {}

        workers_data[time_point][worker] = percentage

# 将字典中的数据拆分为 time_series 和 percentages
time_series = list(workers_data.keys())


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


percentages = {worker: [workers_data[time_point].get(worker, 0) for time_point in time_series] for worker in workers_names}

# 绘制平滑曲线图
plt.figure(figsize=(10, 6))

for worker in workers_names:
    x = range(1, len(time_series) + 1)
    y = percentages[worker]

    # 使用LOWESS进行平滑
    lowess = sm.nonparametric.lowess(y, x, frac=0.2)
    
    plt.plot(lowess[:, 0], lowess[:, 1], label=f'{worker}')

plt.title('Worker Percentage Over Time')
plt.xlabel('Time Index')
plt.ylabel('Percentage')
plt.legend()
plt.grid(True)
plt.show()
