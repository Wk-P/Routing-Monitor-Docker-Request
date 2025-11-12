import matplotlib.pyplot as plt
import typing
import numpy as np
from pathlib import Path
import json

def draw(**kw):
    title: str = kw.get('title', "Untitle")
    x_labels: typing.List[str] = kw.get('x_labels', [])
    data = kw.get('data', [])
    save_path: str | Path = kw.get('save_path')

    save_path.mkdir(parents=True, exist_ok=True)
    fig_name: str = kw.get('file_name', "result.png")

    xLabel = kw.get('xLabel', 'Labels')
    yLabel = kw.get("yLabel", 'Values')

    if save_path == None:
        return
    else:
        if isinstance(save_path, str):
            save_path = Path(save_path)
        save_path = save_path / fig_name
        
    print(f"Save picture as path: {save_path}")

    if not data or not x_labels:
        print("Data or x_labels is missing")
        return

    num_groups = len(data)          # n groups
    num_bars = len(x_labels)        # x axis points
    bar_width = 0.8 / num_groups    # width
    x = np.arange(num_bars)     # x axis position


    def auto_figsize(data_length, base_width=8, base_height=6, step=10, scale=1.5):
        width = base_width + (data_length // step) * scale
        height = base_height + (data_length // step) * scale * 0.5
        return (width, height)

    figsize = auto_figsize(len(data))
    plt.figure(figsize=figsize)

    for i, group in enumerate(data):
        label = group['label']
        values = group['values']
        if len(values) != num_bars:
            print(f"Warning: group {label} data length mismatch x_labels")
            continue
        plt.bar(x + i * bar_width, values, width=bar_width, label=label)

    
    plt.xlabel(xLabel)
    plt.ylabel(yLabel)
    plt.title(title)
    plt.xticks(x + bar_width * (num_groups - 1) / 2, x_labels)
    plt.legend()
    plt.tight_layout()
    plt.savefig(save_path)

def draw_plot(filepath: Path, filename: str, data: dict, title: str):
    if not filepath.exists():
        filepath.mkdir(parents=True, exist_ok=True)

    file_path = filepath / filename

    plt.figure(figsize=(16, 9))
    
    for y_key, y in data.items():
        plt.plot(range(len(y)), y, marker="", label=y_key)

    plt.title(title)
    plt.xlabel("Index")
    plt.ylabel("Seconds")
    plt.xticks(rotation=45)  # 日期标签旋转
    plt.grid(True)


    # 添加图例
    plt.legend()

    # 调整布局并显示图表
    plt.tight_layout()
    plt.savefig(str(file_path))
    plt.close()


def draw_bar(filepath: Path, filename: str, data: dict, title: str):
    if not filepath.exists():
        filepath.mkdir(parents=True, exist_ok=True)

    file_path = filepath / filename

    plt.figure(figsize=(16, 9))
    
    for y_key, y in data.items():
        plt.bar(y_key, y, label=y_key)

    plt.title(title)
    plt.xlabel("total response time")
    plt.ylabel("algorithm name")
    plt.grid(True)


    # 添加图例
    plt.legend()

    # 调整布局并显示图表
    plt.tight_layout()
    plt.savefig(str(file_path))
    plt.close()


# multi y-value
def draw_bar2(filepath: Path, filename: str, data: list[dict], title: str):
    if not filepath.exists():
        filepath.mkdir(parents=True, exist_ok=True)

    file_path = filepath / filename

    plt.figure(figsize=(16, 9))
    
    # 提取 X 轴名称（算法名称）
    x_labels = sorted(set(key for item in data for key in item.keys()))


    # 计算 X 轴索引
    x_indexes = np.arange(len(x_labels))
    width = 0.8 / max(1, len(data) + 1) # 柱状图的宽度

    # 绘制柱状图
    for i, item in enumerate(data):
        y_values = [item.get(x, 0) for x in x_labels]  # 提取所有 y_key 对应的值
        label_text = ""
        if i == 0:
            label_text = "Total response time of all requests"
        elif i == 1:
            label_text = "Sum of single request response time"
        elif i == 2:
            label_text = "Differenc"
        else:
            label_text = "Unknown data"
        plt.bar(x_indexes + (i - len(data) / 2) * width, y_values, width=width, label=label_text)

    # difference bar
    if len(data) == 2:
        diff_values = [abs(data[1].get(x, 0) - data[0].get(x, 0)) for x in x_labels]
        plt.bar(x_indexes + (len(data) / 2) * width, diff_values, width=width, label="Difference", color='red')

    # 设置 X 轴刻度
    plt.xticks(ticks=x_indexes + width / 4, labels=x_labels)

    plt.title(title)
    plt.xlabel("Worker Node ID")
    plt.ylabel("Total Response Time")
    plt.grid(True)

    # 添加图例
    plt.legend()

    # 调整布局并显示图表
    plt.tight_layout()
    plt.savefig(str(file_path))
    plt.close()


def custom_serializer(obj):
        if isinstance(obj, Path):
            return str(obj)
        raise TypeError(f"Type {type(obj)} not serializable.")


def write_json_file(filepath: Path, filename: str, data: dict, mode: str):
    if not filepath.exists():
        filepath.mkdir(parents=True, exist_ok=True)
    
    #  自动加 编号
    count = sum(1 for file in filepath.iterdir() if file.is_file() and file.suffix == '.json')
    if count > 0:
        filename = f"{filename}_{count}.json"
    else:
        filename = f"{filename}.json"   

    full_path = filepath / filename
    with open(full_path, mode) as json_file:
        json.dump(data, json_file, indent=4, default=custom_serializer)

    return full_path


# ====================
# test
# ====================
def test_draw():
    draw(
        title='Performance Metrics Comparison',
        x_labels=['500541', '199995', '200215', '500309', '199871'],
        data=[
            {'label': 'Real Process Time', 'values': [12.88, 3.37, 3.38, 12.84, 3.37]},
            {'label': 'Contention Time', 'values': [2.56, 0.67, 0.68, 2.55, 0.67]},
            {'label': 'CPU Usage', 'values': [0.80, 0.79, 0.79, 0.80, 0.79]},
        ],
        save_path=Path(__file__).absolute().parent
    )

if __name__ == "__main__":
    test_draw()