import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import numpy as np

class Cavans:
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
                tick_positions = np.arange(0, len(param['x']), 5)  # 每隔5个显示一个标签
                tick_labels = param['x'][::5]  # 每隔5个取一个标签

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


if __name__ == "__main__":
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
        ]
    }

    cavans = Cavans(**data)
    cavans.show()
