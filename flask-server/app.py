import os
import subprocess
from flask import Flask, jsonify, send_from_directory

REPORT_DIR = "/jacoco/report"
os.makedirs(REPORT_DIR, exist_ok=True)

app = Flask(__name__)

EXEC_FILE = "/jacoco/jacoco.exec"
REPORT_DIR = "/jacoco/report"
CLASS_FILES = "/spring-petclinic/build/classes/java/main"  # 可視情況調整
SOURCE_FILES = "/spring-petclinic/src/main/java"
JACOCO_CLI_JAR = "/app/jacococli.jar"


@app.route("/coverage/dump")
def dump_coverage():
    if not os.path.exists(EXEC_FILE):
        return jsonify({"error": "jacoco.exec not found"}), 404
    size = os.path.getsize(EXEC_FILE)
    return jsonify({"status": "success", "jacoco_exec_size": size})


@app.route("/coverage/report")
def generate_report():
    try:
        os.makedirs(REPORT_DIR, exist_ok=True)
        # 使用简化的命令，只指定类文件路径
        subprocess.run([
            "java", "-jar", JACOCO_CLI_JAR, "report", EXEC_FILE,
            "--classfiles", "/spring-petclinic-classes",
            "--html", REPORT_DIR,
            "--name", "Spring PetClinic Coverage Report"
        ], check=True)
        return jsonify({"status": "success", "url": "/coverage/report-html/index.html"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/coverage/report-html/<path:filename>")
def serve_report(filename):
    return send_from_directory(REPORT_DIR, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
