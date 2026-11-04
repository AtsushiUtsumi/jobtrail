"""フロントの型生成に使う OpenAPI を標準出力へ書き出す。DB には接続しない。"""

import json
import sys

from jobtrail.main import app

if __name__ == "__main__":
    text = json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n"
    sys.stdout.buffer.write(text.encode("utf-8"))
