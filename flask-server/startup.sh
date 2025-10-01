#!/bin/bash

# 等待Spring Boot容器启动
echo "Waiting for Spring Boot container to be ready..."
sleep 30

# 检查Spring Boot容器是否存在class文件
if [ -d "/spring-petclinic-classes" ]; then
    echo "Class files are available via shared volume"
else
    echo "Shared volume not available, trying to copy from Spring container..."
    # 如果共享卷不可用，这里可以添加其他逻辑
fi

# 启动Flask应用
echo "Starting Flask application..."
python app.py