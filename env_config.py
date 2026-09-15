"""Read only explicitly requested dotenv keys without evaluating their contents."""

import re
import shlex


def read_values(path, names):
    if not path.exists():
        return {}
    values = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeError:
        raise ValueError("配置文件必须使用 UTF-8 编码") from None
    for number, line in enumerate(lines, 1):
        match = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$", line)
        if not match or match.group(1) not in names:
            continue
        try:
            parts = shlex.split(match.group(2), comments=True, posix=True)
            if len(parts) > 1:
                raise ValueError()
        except ValueError:
            raise ValueError("配置第 {} 行格式无效（值含空格时请加引号）".format(number)) from None
        values[match.group(1)] = parts[0] if parts else ""
    return values
