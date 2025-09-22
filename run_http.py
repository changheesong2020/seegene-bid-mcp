#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Seegene Bid MCP Server HTTP 전용 실행 스크립트
SSL 없이 HTTP로만 실행
"""

import os
import sys

# 환경변수로 SSL 비활성화 강제 설정
os.environ['SSL_ENABLED'] = 'False'
os.environ['PORT'] = '8080'
os.environ['HOST'] = '127.0.0.1'

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 기본 run.py 실행
if __name__ == "__main__":
    from run import main
    sys.exit(main())