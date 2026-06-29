import os
import subprocess
import urllib.request
import urllib.error
import json
import signal
from typing import Dict, Any, List

class CaddyManager:
    def __init__(self, caddy_dir: str):
        self.caddy_dir = os.path.abspath(caddy_dir)
        self.bin_path = os.path.join(self.caddy_dir, "bin", "caddy")
        self.caddyfile_path = os.path.join(self.caddy_dir, "Caddyfile")
        self.pid_file = os.path.join(self.caddy_dir, "caddy.pid")
        self.rules_file = os.path.join(self.caddy_dir, "rules.json")
        self.admin_api = "http://localhost:2019"

    def get_status(self) -> Dict[str, Any]:
        """檢查 Caddy 是否正在執行"""
        # 1. 嘗試連線 Caddy Admin API
        try:
            req = urllib.request.Request(f"{self.admin_api}/config/", method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return {"status": "running", "api_responsive": True}
        except Exception:
            pass

        # 2. 檢查 PID 檔案
        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, "r") as f:
                    pid = int(f.read().strip())
                # 檢查進程是否真的存在
                os.kill(pid, 0)
                return {"status": "running", "api_responsive": False, "pid": pid}
            except (ValueError, ProcessLookupError, PermissionError):
                # PID 無效或無權限，刪除失效的 PID 檔
                try:
                    os.remove(self.pid_file)
                except OSError:
                    pass

        return {"status": "stopped", "api_responsive": False}

    def start(self) -> Dict[str, Any]:
        """啟動 Caddy"""
        status = self.get_status()
        if status["status"] == "running":
            return {"success": True, "message": "Caddy 已經在執行中"}

        if not os.path.exists(self.bin_path):
            return {"success": False, "message": "找不到 Caddy 執行檔，請先執行 setup-caddy.sh"}

        try:
            # 使用 caddy start 命令在背景執行，不阻塞 python 進程
            cmd = [self.bin_path, "start", "--config", self.caddyfile_path]
            # 這裡不使用 PIPE 避免 daemon process 繼承 pipe 導致 Python hang 住
            process = subprocess.run(
                cmd,
                cwd=self.caddy_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            if process.returncode == 0:
                return {"success": True, "message": "Caddy 啟動成功"}
            else:
                return {"success": False, "message": "Caddy 啟動失敗"}
                
        except Exception as e:
            return {"success": False, "message": f"啟動異常: {str(e)}"}

    def start_with_pidfile(self) -> Dict[str, Any]:
        """帶有 pidfile 參數的啟動"""
        status = self.get_status()
        if status["status"] == "running":
            return {"success": True, "message": "Caddy 已經在執行中"}

        if not os.path.exists(self.bin_path):
            return {"success": False, "message": "找不到 Caddy 執行檔，請先執行 setup-caddy.sh"}

        try:
            # 刪除舊的 pid 檔案
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
                
            cmd = [self.bin_path, "start", "--config", self.caddyfile_path, "--pidfile", self.pid_file]
            # 這裡不使用 PIPE 避免 daemon process 繼承 pipe 導致 Python hang 住
            process = subprocess.run(
                cmd,
                cwd=self.caddy_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            if process.returncode == 0:
                return {"success": True, "message": "Caddy 啟動成功"}
            else:
                return {"success": False, "message": "Caddy 啟動失敗"}
        except Exception as e:
            return {"success": False, "message": f"啟動異常: {str(e)}"}

    def stop(self) -> Dict[str, Any]:
        """關閉 Caddy"""
        status = self.get_status()
        if status["status"] == "stopped":
            return {"success": True, "message": "Caddy 已經處於停止狀態"}

        # 1. 嘗試使用 Admin API 關閉
        if status["api_responsive"]:
            try:
                req = urllib.request.Request(f"{self.admin_api}/stop", method="POST")
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    if resp.status == 200:
                        # 刪除 pid file
                        if os.path.exists(self.pid_file):
                            os.remove(self.pid_file)
                        return {"success": True, "message": "已成功透過 API 停止 Caddy"}
            except Exception:
                pass

        # 2. 嘗試透過 PID 殺死進程
        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, "r") as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGTERM)
                os.remove(self.pid_file)
                return {"success": True, "message": f"已發送 SIGTERM 停止 Caddy (PID: {pid})"}
            except Exception as e:
                return {"success": False, "message": f"無法透過 PID 關閉 Caddy: {str(e)}"}

        # 3. 備用方案: 使用 pkill
        try:
            subprocess.run(["pkill", "-f", f"{self.bin_path}"], check=True)
            return {"success": True, "message": "已使用 pkill 終止 Caddy"}
        except subprocess.CalledProcessError:
            pass

        return {"success": False, "message": "無法關閉 Caddy，可能未啟動或權限不足"}

    def load_rules(self) -> List[Dict[str, Any]]:
        """載入轉址規則"""
        if not os.path.exists(self.rules_file):
            return []
        try:
            with open(self.rules_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def save_rules_and_reload(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """儲存規則，生成 Caddyfile，並重載 Caddy"""
        # 1. 儲存至 rules.json
        try:
            with open(self.rules_file, "w", encoding="utf-8") as f:
                json.dump(rules, f, indent=4, ensure_ascii=False)
        except Exception as e:
            return {"success": False, "message": f"儲存 rules.json 失敗: {str(e)}"}

        # 2. 重新產生 Caddyfile
        try:
            caddyfile_content = self.generate_caddyfile_content(rules)
            with open(self.caddyfile_path, "w", encoding="utf-8") as f:
                f.write(caddyfile_content)
        except Exception as e:
            return {"success": False, "message": f"寫入 Caddyfile 失敗: {str(e)}"}

        # 3. 如果 Caddy 正在運行，執行 reload
        status = self.get_status()
        if status["status"] == "running":
            try:
                cmd = [self.bin_path, "reload", "--config", self.caddyfile_path]
                process = subprocess.run(
                    cmd,
                    cwd=self.caddy_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if process.returncode == 0:
                    return {"success": True, "message": "規則儲存成功，且 Caddy 已完成熱重載 (Hot-Reload)"}
                else:
                    return {"success": False, "message": f"規則已儲存，但 Caddy 重載失敗: {process.stderr}"}
            except Exception as e:
                return {"success": False, "message": f"規則已儲存，但重載時發生異常: {str(e)}"}
        
        return {"success": True, "message": "規則已儲存 (Caddy 當前未啟動，啟動後將自動套用)"}

    def generate_caddyfile_content(self, rules: List[Dict[str, Any]]) -> str:
        """生成 Caddyfile 內容"""
        template = """{
    # Caddy 管理 API，用於監控與動態載入
    admin localhost:2019

    # 輸出日誌到檔案 (JSON 格式以供管理端點解析)
    log {
        output file caddy.log
        format json
    }
}

# go.formosa-ai.com 的 Caddy 轉址服務 (預設監聽 8080 埠口)
http://go.formosa-ai.com:8080, http://localhost:8080 {
    
    # 記錄存取日誌到 caddy.log 且為 JSON 格式
    log {
        output file caddy.log
        format json
    }
    
    # 健康檢查端點
    respond /caddy-health "OK" 200

    # 預設首頁或未匹配時的回應 (顯示為轉址入口系統)
    # respond "FALO Go Redirection Gateway is active." 200

    # [DYNAMIC_RULES_START]
"""
        for r in rules:
            if not r.get("active", True):
                continue
            path = r["path"]
            if not path.startswith("/"):
                path = "/" + path
                
            target = r["target"]
            rtype = r["type"] # "redirect" | "proxy"
            desc = r.get("description", "")
            
            template += f"\n    # {desc}\n"
            if rtype == "redirect":
                template += f"    redir {path} {target} 302\n"
            elif rtype == "proxy":
                # For proxy, strip path before proxying, matching both with/without trailing slash
                clean_path = path if path.endswith("/") else path + "/"
                template += f"    handle_path {clean_path}* {{\n"
                template += f"        reverse_proxy {target}\n"
                template += f"    }}\n"
            elif rtype == "static":
                # 靜態實體資料夾對接：支援自動展開家目錄波浪號 ~
                resolved_target = os.path.expanduser(target)
                clean_path = path if path.endswith("/") else path + "/"
                # 防呆：自動將無尾斜線網址 308 重導向至有尾斜線網址，以載入 index.html
                if path != "/":
                    base_path = path.rstrip("/")
                    template += f"    redir {base_path} {base_path}/ 308\n"
                template += f"    handle_path {clean_path}* {{\n"
                template += f"        root * {resolved_target}\n"
                template += f"        file_server\n"
                template += f"    }}\n"
                
        template += """    # [DYNAMIC_RULES_END]
}
"""
        return template
