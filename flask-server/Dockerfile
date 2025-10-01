FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安裝 Java
RUN apt-get update && apt-get install -y default-jdk && rm -rf /var/lib/apt/lists/*

COPY . .

# 设置启动脚本权限
RUN chmod +x startup.sh

EXPOSE 5000
CMD ["./startup.sh"]
