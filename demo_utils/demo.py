import multiprocessing

if __name__ == "__main__":
    manager = multiprocessing.Manager()
    _d = manager.dict({
        "a": manager.dict({
            "a1": 20,
        }), 
        "b": manager.dict({
            "b1": 40,
        }),
    })

    _dd = dict()

    for key in _d.keys():
        _dd[key] = dict()
        for k in _d[key].keys():
            _dd[key] = None

    print(_dd)
