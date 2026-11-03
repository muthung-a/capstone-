# -*- coding: utf-8 -*-
"""엑셀/CSV 의 '구조'만 요약합니다 (셀 값은 출력하지 않음). 구조요약.bat 에 파일을 끌어다 놓으면 실행됩니다."""
import os
import sys

from core import structure


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else input("엑셀/CSV 파일 경로 (파일을 이 창에 끌어다 놓고 Enter): ")
    path = path.strip().strip('"')
    if not os.path.isfile(path):
        print("파일을 찾을 수 없습니다:", path)
        return 1
    with open(path, "rb") as f:
        data = f.read()
    text = "\n".join(structure.summarize(os.path.basename(path), data))
    print(text)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "구조요약_결과.txt")
    with open(out, "w", encoding="utf-8-sig") as f:
        f.write(text + "\n")
    print("\n위 내용은 다음 파일에도 저장했습니다:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
