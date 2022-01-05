import datetime as dt

class FileLogger:
    def __init__(self, path: str):
        self.path = path

    def log(self, msg: str):
        with open(self.path, 'a') as file:
            file.write(str(dt.datetime.now()) + '\t' + msg)