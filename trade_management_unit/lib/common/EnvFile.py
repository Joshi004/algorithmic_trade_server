import os
class EnvFile:
    def __init__(self, filename):
        self.filename = filename

    def read(self, key):
        with open(self.filename, 'r') as file:
            for line in file:
                k, v = line.strip().split('=', 1)
                if k.strip() == key:
                    return v.strip()
        return None

    def write(self, key, value):
        lines = []
        found = False
        with open(self.filename, 'r') as file:
            for line in file:
                k, v = line.strip().split('=', 1)
                if k.strip() == key:
                    lines.append(f'{key}={value}\n')
                    found = True
                else:
                    lines.append(line)
        if not found:
            lines.append(f'{key}={value}\n')
        with open(self.filename, 'w') as file:
            file.writelines(lines)
