#!/usr/bin/env python3
import http.server
import socketserver

PORT = 8080

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        html = """
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>FALO Edge Platform - Test Page</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    background: radial-gradient(circle at center, #0f172a 0%, #020617 100%);
                    color: #f8fafc;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    overflow: hidden;
                }
                .card {
                    background: rgba(255, 255, 255, 0.03);
                    backdrop-filter: blur(16px);
                    -webkit-backdrop-filter: blur(16px);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 24px;
                    padding: 48px;
                    text-align: center;
                    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                    max-width: 600px;
                    width: 90%;
                    animation: fadeIn 1s ease-out;
                }
                h1 {
                    color: #38bdf8;
                    margin-top: 0;
                    margin-bottom: 24px;
                    font-size: 2.2rem;
                    background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }
                p {
                    color: #94a3b8;
                    font-size: 1.1rem;
                    line-height: 1.6;
                    margin-bottom: 32px;
                }
                .badge {
                    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                    color: white;
                    padding: 8px 18px;
                    border-radius: 9999px;
                    font-size: 0.95rem;
                    font-weight: 600;
                    display: inline-block;
                    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2);
                    animation: pulse 2s infinite;
                }
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                @keyframes pulse {
                    0% { transform: scale(1); }
                    50% { transform: scale(1.05); }
                    100% { transform: scale(1); }
                }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Hello Cloudflare Tunnel on macOS!</h1>
                <p>🚀 FALO Edge Platform (Cloud Foundation) 已成功將流量安全地導向您的本機服務 <code>localhost:8080</code>！</p>
                <div class="badge">已成功建立 Tunnel 加密連線</div>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode("utf-8"))

socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
    print(f"📡 FALO Hello Server running on http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Stopping server...")
