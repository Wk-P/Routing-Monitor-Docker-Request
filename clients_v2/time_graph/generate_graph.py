from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import typing

class Data:
    def __init__(self, data: typing.List[float | int], label: str):
        self.data = data
        self.label = label


def main(data_sets_groups: typing.List[typing.List[Data]], titles: typing.List[str], fig_name=0, fig_dir_path=None, direction='row'):
    num_groups = len(data_sets_groups)  # 数据集组数量，即要并列显示的图的数量

    # 根据 direction 参数确定子图的行列排列方式
    if direction == 'row':
        fig, axs = plt.subplots(1, num_groups, figsize=(5 * num_groups, 5), squeeze=False)  # 水平排列
    elif direction == 'column':
        fig, axs = plt.subplots(num_groups, 1, figsize=(5, 5 * num_groups), squeeze=False)  # 垂直排列

    axs = axs.flatten()

    # 遍历每组数据并在对应的子图中绘制
    for idx, (data_sets, title) in enumerate(zip(data_sets_groups, titles)):
        ax = axs[idx]

        # 打印每个数据集的平均值
        for data_set in data_sets:
            print_avg(data_set.data, data_set.label)

        # 提取标签和数据
        labels = [data_set.label for data_set in data_sets]
        data_values = [data_set.data for data_set in data_sets]

        # 设置柱状图宽度和位置
        num_bars = len(data_values[0])  # 每个数据集中的数据点数量
        x = np.arange(num_bars)  # x 轴的刻度位置
        width = 0.8 / len(data_sets)  # 每个柱的宽度（根据数据集数量调整）

        # 绘制柱状图
        for i, (data, label) in enumerate(zip(data_values, labels)):
            bars = ax.bar(x + i * width, data, width, label=label)

            # 显示数值在每个柱顶端
            add_values(bars, ax)

        # 添加一些文本标签
        ax.set_xlabel('Data Sets')
        ax.set_ylabel('Values')
        ax.set_title(title)  # 为每个子图添加标题
        ax.set_xticks(x + width * (len(data_sets) - 1) / 2)  # 调整 x 轴刻度
        ax.set_xticklabels([f'{i+1}' for i in range(num_bars)])  # 适配数据点数量
        ax.legend()

        # 自动调整纵轴范围
        all_data = [value for data in data_values for value in data]  # 获取所有数据点
        max_value = max(all_data)
        min_value = min(all_data)
        ax.set_ylim(min_value - (max_value - min_value) * 0.1, max_value + (max_value - min_value) * 0.1)  # 纵轴范围稍微大于最大值，留出空间

    # 调整布局并显示所有子图
    plt.tight_layout()
    if fig_name != 0 or fig_dir_path:
        plt.savefig(Path(fig_dir_path) / f"fig{fig_name}.png")
    else:
        plt.show()

def print_avg(data: typing.List[float | int], name: str):
    print(f'{name:<20} {np.average(data):<50}')


def add_values(bars, ax, offset=0.2):
    for i, bar in enumerate(bars):
        yval = bar.get_height()
        # 格式化显示数字，只保留一位小数
        formatted_value = f"{yval:.1f}"  # 控制小数位数
        # 动态调整偏移量，i 为当前柱子的索引
        ax.text(bar.get_x() + bar.get_width() / 2, yval + offset + 0.1, formatted_value, ha='center', va='bottom', fontsize=8)


# 示例使用
if __name__ == "__main__":
    data1 = Data([3, 5, 1, 2], 'Data Set 1')
    data2 = Data([4, 7, 2, 3], 'Data Set 2')
    data3 = Data([5, 2, 8, 6], 'Data Set 3')  # 添加第三个数据集

    # 并列显示两张图，每张图有一个标题
    main([[data1, data2, data3], [data1]], ["Group 1: Comparison", "Group 2: Single Data Set"], direction='column')
