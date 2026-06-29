#!/usr/bin/env python3
import urllib.request
import json
import random

def api_request(url, method="GET", headers=None, data=None):
    if headers is None:
        headers = {}
    headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    req = urllib.request.Request(url, method=method)
    for k, v in headers.items():
        req.add_header(k, v)
        
    body = None
    if data is not None:
        req.add_header("Content-Type", "application/json")
        body = json.dumps(data).encode('utf-8')
        
    try:
        with urllib.request.urlopen(req, data=body) as response:
            return json.loads(response.read().decode('utf-8')), response.status
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode('utf-8', errors='ignore')
        return json.loads(err_msg) if err_msg.startswith('{') else err_msg, e.code

def main():
    base_url = "https://falo-email-portal.force-chinese.workers.dev"
    run_id = random.randint(1000, 9999)
    admin_email = f"admin_client_{run_id}@formosa-ai.com"
    agent_email = f"agent_client_{run_id}@formosa-ai.com"
    username_agent = f"agent_{run_id}"
    
    print("📡 Step 1: Login as force...")
    login_res, status = api_request(f"{base_url}/api/login", "POST", data={"username": "force", "password": "0922764763"})
    if status != 200:
        print("❌ Login failed")
        return
    token_force = login_res["token"]
    headers_force = {"Authorization": f"Bearer {token_force}"}
    
    print(f"\n📡 Step 2: Creating contact under force ({admin_email})...")
    c_admin = {"name": "Admin Client", "email": admin_email, "remark": "Admin exclusive contact"}
    res, status = api_request(f"{base_url}/api/contacts", "POST", headers=headers_force, data=c_admin)
    print(f"Status: {status}, Response: {res}")
    
    print(f"\n📡 Step 3: Creating a new user '{username_agent}'...")
    res, status = api_request(f"{base_url}/api/users", "POST", headers=headers_force, data={"username": username_agent, "password": "agent_password123"})
    print(f"Status: {status}, Response: {res}")
    
    print("\n📡 Step 4: Login as the new agent user...")
    login_res2, status = api_request(f"{base_url}/api/login", "POST", data={"username": username_agent, "password": "agent_password123"})
    token_agent = login_res2["token"]
    headers_agent = {"Authorization": f"Bearer {token_agent}"}
    
    print(f"\n📡 Step 5: Listing contacts for {username_agent} (should be empty)...")
    res_list_agent, status = api_request(f"{base_url}/api/contacts", "GET", headers=headers_agent)
    contacts_initial = res_list_agent.get('contacts', [])
    print(f"Status: {status}, Contacts: {contacts_initial}")
    assert len(contacts_initial) == 0, f"Error: {username_agent}'s contacts list should be empty!"
    print("✅ Verified: contacts list is initially empty!")
    
    print(f"\n📡 Step 6: Creating contact under {username_agent} ({agent_email})...")
    c_agent = {"name": "Agent Client", "email": agent_email, "remark": "Agent exclusive contact"}
    res, status = api_request(f"{base_url}/api/contacts", "POST", headers=headers_agent, data=c_agent)
    print(f"Status: {status}, Response: {res}")
    
    print("\n📡 Step 7: Verifying contacts list immediately (strong consistency test)...")
    res_list_agent2, status = api_request(f"{base_url}/api/contacts", "GET", headers=headers_agent)
    contacts_agent = res_list_agent2.get('contacts', [])
    print(f"   Contacts found: {contacts_agent}")
    assert len(contacts_agent) == 1 and contacts_agent[0]['email'] == agent_email, "Error: Contact failed to appear in list!"
    print("✅ Verified: Contact appeared instantly without delay!")
    
    print("\n📡 Step 8: Verifying force's contacts only has the admin contact...")
    res_list_force, status = api_request(f"{base_url}/api/contacts", "GET", headers=headers_force)
    contacts_force = res_list_force.get('contacts', [])
    print(f"Force contacts: {contacts_force}")
    emails_force = [c['email'] for c in contacts_force]
    assert admin_email in emails_force, "Error: admin contact not found in force's list!"
    assert agent_email not in emails_force, "Error: agent contact leaked into force's list!"
    print("✅ Verified: force's contacts list is isolated and unaffected!")
    
    print("\n📡 Step 9: Cleaning up...")
    api_request(f"{base_url}/api/contacts?email={admin_email}", "DELETE", headers=headers_force)
    api_request(f"{base_url}/api/contacts?email={agent_email}", "DELETE", headers=headers_agent)
    api_request(f"{base_url}/api/users?username={username_agent}", "DELETE", headers=headers_force)
    print("✅ Cleanup completed!")
    
    print("\n🎉 ALL MULTI-USER ISOLATION TESTS COMPLETED SUCCESSFULLY! Personal contact lists are 100% operational, strongly consistent, and isolated on the backend database!")

if __name__ == "__main__":
    main()
