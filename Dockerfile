FROM python:3.9-slim
# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 设置构建时的代理环境变量
ARG HTTP_PROXY
ARG HTTPS_PROXY

WORKDIR /app

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt 

# 复制程序文件
COPY . .

# 设置运行时的代理环境变量
ENV HTTP_PROXY=${HTTP_PROXY:-""}
ENV HTTPS_PROXY=${HTTPS_PROXY:-""}

# 运行程序
CMD ["python3", "-u", "main.py"] 