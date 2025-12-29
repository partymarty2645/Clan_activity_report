
import subprocess
import json
import time
import sys

def probe_server(image_name, args=[]):
    print(f"\n--- Probing {image_name} ---")
    cmd = ["docker", "run", "-i", "--rm"] + args + [image_name]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8' # Ensure UTF-8
        )

        # JSON-RPC Handshake
        requests = [
            {"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "probe", "version": "1.0"}}, "id": 0},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        ]

        # Send requests
        input_str = "\n".join(json.dumps(r) for r in requests) + "\n"
        
        # We communicate carefully. Some servers might block if we don't read stdout/stderr.
        # Ideally we'd use threads, but let's try a simple communicate with timeout.
        try:
            stdout, stderr = process.communicate(input=input_str, timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            print("TIMEOUT")

        print("STDERR:", stderr)
        
        # Parse output for tools/list response
        for line in stdout.splitlines():
            try:
                data = json.loads(line)
                if data.get("id") == 1 and "result" in data:
                    tools = data["result"].get("tools", [])
                    print(f"FOUND {len(tools)} TOOLS:")
                    for t in tools:
                        print(f"- {t['name']}: {t.get('description', 'No description')[:100]}...")
            except json.JSONDecodeError:
                pass # Ignore non-JSON lines

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    # Probe specific known servers
    probe_server("mcp/fetch")
    probe_server("mcp/mcp-python-refactoring")
    probe_server("mcp/gemini-api-docs-mcp")
    probe_server("mcp/sqlite", args=["-v", "d:/Clan_activity_report/clan_data.db:/app/clan_data.db", "--db-path", "/app/clan_data.db"])
