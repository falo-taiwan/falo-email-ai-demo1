#!/usr/bin/env python3
import urllib.request
import urllib.error
import json

key = "cfk_FfKvCz8vn9QRDvxm3Py1Udpz3KFDUzdus7vmubP3f70b02bf"

# 測試的 Email 列表
emails = [
    "force.chinese@gmail.com",
    "force@formosa-ai.com",
    "admin@formosa-ai.com",
    "dev@formosa-ai.com",
    "falo@formosa-ai.com"
]

for email in emails:
    print(f"📡 測試 Email: {email}...")
    url = "https://api.cloudflare.com/client/v4/user"
    req = urllib.request.Request(url)
    req.add_header("X-Auth-Email", email)
    req.add_header("X-Auth-Key", key)
    req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req) as response:
            body = json.loads(response.read().decode('utf-8'))
            if response.getcode() == 200 and body.get("success"):
                print(f"✅ 成功！正確的 Email 為: {email}")
                print(f"使用者 ID: {body['result']['id']}")
                exit(0)
    except urllib.error.HTTPError as e:
        try:
            error_body = json.loads(e.read().decode('utf-8'))
            print(f"❌ 失敗: HTTP {e.code} - {error_body.get('errors')[0].get('message')}")
        except:
            print(f"❌ 失敗: HTTP {e.code}")
    except Exception as e:
        print(f"❌ 異常: {e}")
