FROM python:3.9-slim
# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 设置构建时的代理环境变量
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG TWITTER_API_BASE_URL

WORKDIR /app

# 安装Python依赖 - 开发环境下不复制文件，使用挂载卷
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt 

# 安装开发工具
RUN pip install --no-cache-dir watchdog

# 设置运行时的代理环境变量
ENV HTTP_PROXY=${HTTP_PROXY:-""}
ENV HTTPS_PROXY=${HTTPS_PROXY:-""}
ENV TWITTER_API_BASE_URL=${TWITTER_API_BASE_URL:-""}

# 开发环境使用 watchdog 监控文件变化并自动重启
CMD ["python", "-m", "watchdog.watchmedo", "auto-restart", "--directory=.", "--pattern=*.py", "--recursive", "--", "python", "-u", "main.py"]