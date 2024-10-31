import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import numpy as np

class BarChartCanvas:
    def __init__(self, **kwargs):
        x_list = kwargs.get("x_list", [])        
        y_lists = kwargs.get("y_lists", [])
        titles = kwargs.get("titles", [])
        xlabels = kwargs.get("xlabels", [])
        ylabels = kwargs.get("ylabels", [])
        legends = kwargs.get("legends", [])
        figsize = kwargs.get('figsize')
        self.params: list[dict] = []

        if len(x_list) != len(y_lists) or len(x_list) != len(titles) or len(x_list) != len(xlabels) or len(x_list) != len(ylabels):
            raise Exception("Length of x list and y list is not same")
            

        for i in range(len(x_list)):
            self.params.append({
                "x": x_list[i],
                "y_lists": y_lists[i],
                "title": titles[i],
                "xlabel": xlabels[i],
                "ylabel": ylabels[i],
            })


        # Figure 对象
        self.ax: list[Axes]
        self.fig, self.ax = plt.subplots(ncols=len(self.params), figsize=(16 * len(self.params), 9))

        if len(self.params) == 1:
            self.ax = [self.ax]

        # ax上绘制条形图
        if len(self.params) > 0:
            for i, param in enumerate(self.params):
                x = np.arange(len(param['x']))
                bar_width = 0.3
                num_bars = len(param.get('y_lists'))

                for j, y in enumerate(param['y_lists']):
                    self.ax[i].bar(x + j * bar_width, y, bar_width)

                # 旋转标签
                # 间隔
                gap = int(len(param['x']) / 20)

                if gap == 0:
                    gap = 1

                tick_positions = np.arange(0, len(param['x']), gap)  # 每隔5个显示一个标签
                tick_labels = param['x'][::gap]  # 每隔5个取一个标签

                self.ax[i].set_xticks(tick_positions + bar_width * (num_bars - 1) / 2)
                self.ax[i].set_xticklabels(tick_labels, rotation=45, ha='right')

                self.ax[i].set_title(param['title'])
                self.ax[i].set_xlabel(param['xlabel'])
                self.ax[i].set_ylabel(param['ylabel'])

                # 添加图例
                self.ax[i].legend(legends)

    def show(self):
        plt.tight_layout()
        plt.show()


    def save(self, path):
        self.fig.savefig(path)


class LinearChartCanvas:
    def __init__(self, **kwargs):
        x_list = kwargs.get("x_list", [])        
        y_lists = kwargs.get("y_lists", [])
        titles = kwargs.get("titles", [])
        xlabels = kwargs.get("xlabels", [])
        ylabels = kwargs.get("ylabels", [])
        legends = kwargs.get("legends", [])
        figsize = kwargs.get('figsize', (16, 9))
        smooth = kwargs.get("smooth", False)  # 是否平滑
        window_size = kwargs.get("window_size", 10)  # 平滑窗口大小
        self.params: list[dict] = []

        if len(x_list) != len(y_lists) or len(x_list) != len(titles) or len(x_list) != len(xlabels) or len(x_list) != len(ylabels):
            raise Exception("Length of x list and y list is not same")
            

        for i in range(len(x_list)):
            self.params.append({
                "x": x_list[i],
                "y_lists": y_lists[i],
                "title": titles[i],
                "xlabel": xlabels[i],
                "ylabel": ylabels[i],
            })


        # Figure 对象
        self.ax: list[Axes]
        self.fig, self.ax = plt.subplots(ncols=len(self.params), figsize=(16 * len(self.params), 9))

        if len(self.params) == 1:
            self.ax = [self.ax]

        # 移动平滑均匀函数
        def moving_average(data, window_size):
            return np.convolve(data, np.ones(window_size) / window_size, mode='valid')


        # 绘制折线图
        if len(self.params) > 0:
            for i, param in enumerate(self.params):
                for j, y in enumerate(param['y_lists']):
                    if smooth:  # 如果选择平滑曲线
                        y_smooth = moving_average(y, window_size)
                        x_smooth = param['x'][:len(y_smooth)]
                        self.ax[i].plot(x_smooth, y_smooth, label=legends[j] if legends else f'Line {j+1} (smoothed)')
                    else:
                        self.ax[i].plot(param['x'], y, label=legends[j] if legends else f'Line {j+1}')
                
                # 设置标签、标题和图例
                self.ax[i].set_title(param['title'])
                self.ax[i].set_xlabel(param['xlabel'])
                self.ax[i].set_ylabel(param['ylabel'])
                self.ax[i].legend()

    def show(self):
        plt.tight_layout()
        plt.show()


    def save(self, path):
        self.fig.savefig(path)


def linearcharttest():
    # 假设有一些数据
    x_list = [np.arange(0, 1000)]
    y_lists = [np.random.normal(loc=0, scale=1, size=1000).cumsum()]
    titles = ["Response Time Comparison"]
    xlabels = ["Tasks Index"]
    ylabels = ["Response Time"]
    legends = ["Sample Line"]

    # 创建图表并设置平滑参数
    chart = LinearChartCanvas(
        x_list=x_list, 
        y_lists=[y_lists], 
        titles=titles, 
        xlabels=xlabels, 
        ylabels=ylabels, 
        legends=legends, 
        smooth=True, 
        window_size=20  # 平滑窗口大小
    )

    # 显示图表
    chart.show()


def barcharttest():
    data= {
        "x_list": [
            ['A', 'B', 'C', 'D'], 
            ['A', 'B', 'C', 'D'], 
            ['A', 'B', 'C', 'D'], 
        ],
        "y_lists": [
            [
                # 一张图
                [40, 20, 10, 30], 
                [10, 20, 30, 10],
            ],
            [
                # 一张图
                [40, 20, 10, 30], 
                [10, 20, 30, 10],
            ],
            [
                # 一张图
                [40, 20, 10, 30], 
                [10, 20, 30, 10],
            ],
        ],
        "titles": [
            "Chart1", "Chart2", "Chart3"
        ],
        "xlabels": [
            "Category1",
            "Category2",
            "Category3",
        ],
        "ylabels": [
            "Value1", 
            "Value2", 
            "Value3", 
        ],
        "legends": [
            "A",
            "B",
        ],
        "smooth": True,
        "window_size": 10
    }

    canvas = BarChartCanvas(**data)
    canvas.show()


if __name__ == "__main__":
    linearcharttest()
