import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

parent_path = Path.cwd().parent

excel_suffix = ".xlsx"
file_name = "test(150#Tue-Jul-23-19-05-12-2024)"
read_dataset_file_path = parent_path / "excels" / f"{file_name}{excel_suffix}"


pic_suffix = ".png"
pic_file_name = "table3"
pic_save_path = parent_path / "table_pic" / f"{pic_file_name}{pic_suffix}"

def draw(x, y, pf):
    plt.plot(x, y, '.', linewidth=2.0)
    plt.xlabel("wait time")
    plt.ylabel("jobs number")
    plt.savefig(pf)
    print("table picture saved!")
    plt.show()


def readData(filepath):
    df = pd.read_excel(filepath)

    columns = df.columns.to_list()

    data_dict = {col: df[col].to_list() for col in columns}

    x, y = data_dict.get("wait_time_in_worker_node"), data_dict.get("waiting_cnt")

    return x, y


if __name__ == "__main__":
    x, y = readData(read_dataset_file_path)
    draw(x, y, pic_save_path)
