import math
import random
from pathlib import Path


def main():

    random_int_max = 500000
    random_int_min = 10

    requests_batch = 1000

    args = [math.floor(random.uniform(random_int_min * 10, random_int_max * 10) / 10) for _ in range(requests_batch)]

    with open(str(Path.cwd() / 'args.txt'), 'w') as file:
        for item in args:
            file.write(f"{item}\n")



if __name__ == "__main__":
    main()
    print("Generate success")