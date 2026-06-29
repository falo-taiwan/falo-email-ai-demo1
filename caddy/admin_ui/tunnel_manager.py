import os
import subprocess
import signal
from typing import Dict, Any

class TunnelProcessManager:
    def __init__(self, caddy_dir: str):
        self.caddy_dir = os.path.abspath(caddy_dir)
        self.project_dir = os.path.dirname(self.caddy_dir)
        self.bin_path = os.path.join(self.project_dir, "bin", "cloudflared")
        self.pid_file = os.path.join(self.caddy_dir, "cloudflared.pid")
        self.log_file = os.path.join(self.caddy_dir, "cloudflared.log")
        self.env_file = os.path.join(self.project_dir, ".env")

    def _get_tunnel_token(self) -> str:
        """從 .env 載入 CLOUDFLARE_TUNNEL_TOKEN"""
        if not os.path.exists(self.env_file):
            return ""
        try:
            with open(self.env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split('=', 1)
                        if len(parts) == 2 and parts[0].strip() == "CLOUDFLARE_TUNNEL_TOKEN":
                            return parts[1].strip().strip('"').strip("'")
        except Exception:
            pass
        return ""

    def get_status(self) -> Dict[str, Any]:
        """檢查本地 cloudflared 代理是否正在執行"""
        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, "r") as f:
                    pid = int(f.read().strip())
                # 檢查進程是否真的存在
                os.kill(pid, 0)
                return {"status": "running", "pid": pid}
            except (ValueError, ProcessLookupError, PermissionError):
                # PID 無效或無權限，清理失效的 PID 檔
                try:
                    os.remove(self.pid_file)
                except OSError:
                    pass
        return {"status": "stopped"}

    def start(self) -> Dict[str, Any]:
        """啟動 cloudflared 隧道代理"""
        status = self.get_status()
        if status["status"] == "running":
            return {"success": True, "message": "cloudflared 隧道代理已在執行中"}

        if not os.path.exists(self.bin_path):
            return {"success": False, "message": f"找不到 cloudflared 執行檔，路徑為: {self.bin_path}"}

        token = self._get_tunnel_token()
        if not token:
            return {"success": False, "message": "無法在 .env 中找到 CLOUDFLARE_TUNNEL_TOKEN"}

        try:
            # 刪除舊的 pid 檔案與 log 檔案
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
                
            cmd = [self.bin_path, "tunnel", "run", "--token", token]
            
            # 將 stdout/stderr 導向日誌檔，以背景進程啟動，不阻塞 Python
            log_f = open(self.log_file, "a", encoding="utf-8")
            process = subprocess.Popen(
                cmd,
                cwd=self.project_dir,
                stdout=log_f,
                stderr=log_f,
                start_new_session=True # 脫離父進程 Session，確保重啟 Python 時不影響 Tunnel
            )
            
            # 將 PID 寫入檔案
            with open(self.pid_file, "w") as f:
                f.write(str(process.pid))
                
            return {"success": True, "message": "cloudflared 隧道代理已成功啟動"}
        except Exception as e:
            return {"success": False, "message": f"啟動失敗: {str(e)}"}

    def stop(self) -> Dict[str, Any]:
        """關閉 cloudflared 隧道代理"""
        status = self.get_status()
        if status["status"] == "stopped":
            return {"success": True, "message": "cloudflared 隧道代理已處於停止狀態"}

        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, "r") as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGTERM)
                os.remove(self.pid_file)
                return {"success": True, "message": f"已發送 SIGTERM 停止 cloudflared (PID: {pid})"}
            except Exception as e:
                # 備用方案: pkill
                pass

        try:
            subprocess.run(["pkill", "-f", "cloudflared tunnel run"], check=True)
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
            return {"success": True, "message": "已使用 pkill 終止 cloudflared"}
        except subprocess.CalledProcessError:
            pass

        return {"success": False, "message": "無法關閉 cloudflared 服務，可能未啟動或權限不足"}
