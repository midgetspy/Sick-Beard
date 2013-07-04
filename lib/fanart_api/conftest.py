def pytest_collect_file(path, parent):
    if path.ext == ".py":
        return parent.Module(path, parent)