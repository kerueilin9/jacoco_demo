import os
import subprocess
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__)

# 配置路径
EXEC_FILE = "/jacoco/jacoco.exec"
TCP_EXEC_FILE = "/jacoco/jacoco-tcp.exec"  # 新增TCP模式的exec文件
REPORT_DIR = "/jacoco/report"
CLASS_FILES = "/spring-petclinic-classes/java/main"  # 通过共享卷访问
JACOCO_CLI_JAR = "/app/jacococli.jar"

# 确保报告目录存在
os.makedirs(REPORT_DIR, exist_ok=True)


@app.route("/coverage/dump")
def dump_coverage():
    """检查覆盖率文件状态"""
    exec_files = [EXEC_FILE, TCP_EXEC_FILE]
    status = {}
    
    for exec_file in exec_files:
        if os.path.exists(exec_file):
            size = os.path.getsize(exec_file)
            status[os.path.basename(exec_file)] = {"exists": True, "size": size}
        else:
            status[os.path.basename(exec_file)] = {"exists": False, "size": 0}
    
    return jsonify({"status": "success", "files": status})


@app.route("/coverage/dump-tcp")
def dump_tcp_coverage():
    """通过TCP连接导出覆盖率数据"""
    try:
        # 使用JaCoCo CLI通过TCP连接导出数据
        subprocess.run([
            "java", "-jar", JACOCO_CLI_JAR, "dump",
            "--address", "spring-petclinic_1",  # 容器名称
            "--port", "6300",
            "--destfile", TCP_EXEC_FILE
        ], check=True)
        
        if os.path.exists(TCP_EXEC_FILE):
            size = os.path.getsize(TCP_EXEC_FILE)
            return jsonify({"status": "success", "file": "jacoco-tcp.exec", "size": size})
        else:
            return jsonify({"status": "error", "error": "Failed to create TCP dump file"}), 500
            
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "error": f"TCP dump failed: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/coverage/report")
def generate_report():
    """生成覆盖率报告"""
    # 选择可用的exec文件
    exec_file_to_use = None
    if os.path.exists(TCP_EXEC_FILE):
        exec_file_to_use = TCP_EXEC_FILE
        file_type = "TCP"
    elif os.path.exists(EXEC_FILE):
        exec_file_to_use = EXEC_FILE
        file_type = "File"
    else:
        return jsonify({"status": "error", "error": "No jacoco.exec file found"}), 404
    
    try:
        os.makedirs(REPORT_DIR, exist_ok=True)
        
        # 生成覆盖率报告
        subprocess.run([
            "java", "-jar", JACOCO_CLI_JAR, "report", exec_file_to_use,
            "--classfiles", CLASS_FILES,
            "--html", REPORT_DIR,
            "--name", f"Spring PetClinic Coverage Report ({file_type})"
        ], check=True)
        
        # 检查报告是否成功生成
        index_file = os.path.join(REPORT_DIR, "index.html")
        if os.path.exists(index_file):
            return jsonify({
                "status": "success", 
                "url": "/coverage/report-html/index.html",
                "exec_file": os.path.basename(exec_file_to_use),
                "file_type": file_type
            })
        else:
            return jsonify({"status": "error", "error": "Report generation failed - no index.html created"}), 500
            
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "error": f"Report generation failed: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/coverage/report-tcp")
def generate_tcp_report():
    """先导出TCP数据然后生成报告"""
    try:
        # 第一步：通过TCP导出数据
        tcp_result = subprocess.run([
            "java", "-jar", JACOCO_CLI_JAR, "dump",
            "--address", "spring-petclinic_1",  # 容器名称
            "--port", "6300",
            "--destfile", TCP_EXEC_FILE
        ], check=True)
        
        # 第二步：生成报告
        return generate_report()
        
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "error": f"TCP dump failed: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/coverage/check-classes")
def check_class_files():
    """检查class文件是否可用"""
    possible_paths = [
        "/spring-petclinic-classes/java/main",  # 共享卷路径
        "/spring-petclinic/build/classes/java/main",  # 直接路径
    ]
    
    available_paths = []
    for path in possible_paths:
        if os.path.exists(path):
            try:
                class_count = len([f for f in os.listdir(path) if f.endswith('.class')]) if os.path.isdir(path) else 0
                available_paths.append({
                    "path": path,
                    "exists": True,
                    "is_directory": os.path.isdir(path),
                    "class_files": class_count
                })
            except Exception as e:
                available_paths.append({
                    "path": path,
                    "exists": True,
                    "error": str(e)
                })
        else:
            available_paths.append({
                "path": path,
                "exists": False
            })
    
    return jsonify({
        "status": "success",
        "class_paths": available_paths,
        "current_config": CLASS_FILES
    })


@app.route("/coverage/auto-setup")
def auto_setup_class_files():
    """自动设置class文件路径"""
    global CLASS_FILES
    
    possible_paths = [
        "/spring-petclinic-classes/java/main",  # 共享卷路径
        "/spring-petclinic/build/classes/java/main",  # 直接路径
    ]
    
    for path in possible_paths:
        if os.path.exists(path) and os.path.isdir(path):
            # 检查是否包含class文件（递归检查子目录）
            try:
                has_class_files = False
                for root, dirs, files in os.walk(path):
                    if any(f.endswith('.class') for f in files):
                        has_class_files = True
                        break
                
                if has_class_files:
                    CLASS_FILES = path
                    return jsonify({
                        "status": "success",
                        "message": f"Class files path updated to: {path}",
                        "path": path
                    })
            except Exception as e:
                continue
    
    return jsonify({
        "status": "error",
        "message": "No valid class files path found",
        "checked_paths": possible_paths
    }), 404


@app.route("/")
def index():
    """API首页"""
    return jsonify({
        "service": "JaCoCo Coverage API",
        "endpoints": {
            "/coverage/dump": "Check coverage file status",
            "/coverage/dump-tcp": "Dump coverage data via TCP",
            "/coverage/report": "Generate coverage report from available exec file",
            "/coverage/report-tcp": "Dump TCP data and generate report",
            "/coverage/check-classes": "Check available class file paths",
            "/coverage/auto-setup": "Automatically setup class file path",
            "/coverage/report-html/index.html": "View generated HTML report",
            "/health": "Service health check"
        }
    })


@app.route("/health")
def health():
    """健康检查端点"""
    try:
        # 检查Java是否可用
        java_result = subprocess.run(["java", "-version"], capture_output=True, text=True)
        java_available = java_result.returncode == 0
        
        # 检查JaCoCo CLI是否存在
        jacoco_available = os.path.exists(JACOCO_CLI_JAR)
        
        # 检查目录权限
        jacoco_dir_writable = os.access("/jacoco", os.W_OK)
        
        return jsonify({
            "status": "healthy",
            "java_available": java_available,
            "jacoco_cli_available": jacoco_available,
            "jacoco_dir_writable": jacoco_dir_writable,
            "java_version": java_result.stderr if java_available else "N/A"
        })
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
