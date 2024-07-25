def main():
    l1 = [chr(n) for n in range(ord('a'), ord('z') + 1)]
    # print(l1)
    # ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y']
    
    # deep
    l2 = l1.copy()
    # remove
    l1.remove('z')
    print(l1)
    print(l2)
    




if __name__ == "__main__":
    main()