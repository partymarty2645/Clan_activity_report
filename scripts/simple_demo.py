
import subprocess
import json
import time
import sys

def run_demo(label, image, tool, args_dict, docker_args=[]):
    print(f"\n[{label}] Running {tool}...")
    
    cmd = ["docker", "run", "-i", "--rm"] + docker_args + [image]
    
    # JSON-RPC Sequence
    msgs = [
        {"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "demo", "version": "1.0"}}, "id": 0},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": tool, "arguments": args_dict}, "id": 1}
    ]
    
    input_str = "\n".join(json.dumps(m) for m in msgs) + "\n"

    try:
        # Run process
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        stdout, stderr = p.communicate(input=input_str, timeout=20)
        
        # Parse result
        for line in stdout.splitlines():
            try:
                data = json.loads(line)
                if data.get("id") == 1:
                    if "result" in data:
                        # Pretty print the result content
                        content = data["result"].get("content", [])
                        print(f"[{label}] SUCCESS:")
                        for c in content:
                            if c["type"] == "text":
                                print(c["text"][:500] + "..." if len(c["text"]) > 500 else c["text"])
                    elif "error" in data:
                        print(f"[{label}] ERROR: {data['error']['message']}")
            except:
                pass
                
        if stderr:
             # filter out loading bars
             errs = [e for e in stderr.splitlines() if "Loading" not in e and "Pulling" not in e]
             if errs: print(f"[{label}] STDERR: {errs[:3]}")
             
    except Exception as e:
        print(f"[{label}] FAIL: {e}")

if __name__ == "__main__":
    # 1. SQLite
    run_demo("SQLITE", "mcp/sqlite", "read_query", 
             {"query": "SELECT count(*) as member_count FROM members"},
             ["-v", "d:/Clan_activity_report/clan_data.db:/app/clan_data.db", "--db-path", "/app/clan_data.db"])
            
    # 2. Fetch
    run_demo("FETCH", "mcp/fetch", "fetch", 
             {"url": "https://example.com"})

    # 3. Refactoring
    run_demo("REFACTOR", "mcp/mcp-python-refactoring", "analyze_python_file", 
             {"file_path": "/projects/main.py"},
             ["-v", "d:/Clan_activity_report:/projects"])
