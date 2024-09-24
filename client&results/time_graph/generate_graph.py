import matplotlib.pyplot as plt
import numpy as np
import typing

class Data:
    def __init__(self, data: typing.List[float | int], label: str):
        self.data = data
        self.label = label


def main(*data_sets: Data):
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

    # 创建柱状图
    fig, ax = plt.subplots()

    # 绘制柱状图
    for i, (data, label) in enumerate(zip(data_values, labels)):
        bars = ax.bar(x + i * width, data, width, label=label)

        # 显示数值在每个柱顶端
        add_values(bars)

    # 添加一些文本标签
    ax.set_xlabel('Data Sets')
    ax.set_ylabel('Values')
    ax.set_title('Bar chart comparison between data sets')
    ax.set_xticks(x + width * (len(data_sets) - 1) / 2)  # 调整 x 轴刻度
    ax.set_xticklabels([f'{i+1}' for i in range(num_bars)])  # 适配数据点数量
    ax.legend()

    # 调整布局并显示图形
    plt.tight_layout()
    plt.show()


def print_avg(data: typing.List[float | int], name: str):
    print(f'{name:<20} {np.average(data):<50}')


def add_values(bars):
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, yval, round(yval, 2), ha='center', va='bottom')


# 示例使用
if __name__ == "__main__":
    data1 = Data([3, 5, 1, 2], 'Data Set 1')
    data2 = Data([4, 7, 2, 3], 'Data Set 2')
    data3 = Data([5, 2, 8, 6], 'Data Set 3')  # 添加第三个数据集
    main(data1, data2, data3)  # 调用 main 函数，支持多个数据集
