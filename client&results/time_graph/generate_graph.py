import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

def read_data_from_file(file):
    with open(file, 'r', encoding='utf-8') as f:
        data = f.readlines()
        return [float(line.strip()) for line in data]

def print_avg(l, name):
    print(f'{name:<20} {np.average(l):<50}')


base_dir = Path.cwd().parent / 'time_records'

x1 = read_data_from_file(file=base_dir / 'records2' / 'record(RR).txt')
x2 = read_data_from_file(file=base_dir / 'records2' / 'record(PR).txt')
labels = [_ for _ in range(len(x1))]

print_avg(x1, 'round robin')
print_avg(x2, 'xgboost')

# 设置柱状图宽度和位置
x = np.arange(len(labels))  # x 轴的刻度位置
width = 0.35  # 每个柱的宽度

# 创建柱状图
fig, ax = plt.subplots()
bar1 = ax.bar(x - width/2, x1, width, label='Round Roubin')
bar2 = ax.bar(x + width/2, x2, width, label='Xgboost')

# 添加一些文本标签
ax.set_xlabel('Category')
ax.set_ylabel('Values')
ax.set_title('Bar chart comparison between x1 and x2')
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.legend()

# 显示数值在每个柱顶端
def add_values(bars):
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval, round(yval, 2), ha='center', va='bottom')

# add_values(bar1)
# add_values(bar2)

# 展示图形
plt.tight_layout()
plt.show()
