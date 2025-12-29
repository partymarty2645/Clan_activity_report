
import subprocess
import json
import time

def call_mcp_tool(image_name, tool_name, arguments, args=[]):
    print(f"\n>>> DEMO: Calling '{tool_name}' on {image_name}...")
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

        # JSON-RPC Handshake + Tool Call
        requests = [
            {"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "demo-client", "version": "1.0"}}, "id": 0},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": tool_name, "arguments": arguments}, "id": 1}
        ]

        # Send requests
        input_str = "\n".join(json.dumps(r) for r in requests) + "\n"
        
        try:
            stdout, stderr = process.communicate(input=input_str, timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            print("!!! TIMEOUT !!!")

        # Parse output for tools/call response
        found_response = False
        for line in stdout.splitlines():
            try:
                data = json.loads(line)
                if data.get("id") == 1:
                    found_response = True
                    if "result" in data:
                        content = data["result"].get("content", [])
                        for item in content:
                            if item["type"] == "text":
                                print("--- RESULT ---")
                                print(item["text"])
                                print("--------------")
                    elif "error" in data:
                        print(f"!!! TOOL ERROR: {data['error']['message']}")
            except json.JSONDecodeError:
                pass # Ignore non-JSON lines

        if not found_response:
             print("!!! NO RESPONSE TO TOOL CALL FOUND !!!")
             if stderr: print(f"STDERR: {stderr}")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    # 1. SQLite: Count data rows
    call_mcp_tool(
        "mcp/sqlite", 
        "read_query", 
        {"query": "SELECT count(*) as member_count FROM members"},
        args=["-v", "d:/Clan_activity_report/clan_data.db:/app/clan_data.db", "--db-path", "/app/clan_data.db"]
    )

    # 2. Fetch: Get a snippet
    call_mcp_tool(
        "mcp/fetch",
        "fetch",
        {"url": "https://example.com"}
    )
    
    # 3. Refactoring: Analyze main.py
    # Note: We need to mount the project dir to let it see the file
    call_mcp_tool(
        "mcp/mcp-python-refactoring", 
        "analyze_python_file", 
        {"file_path": "/projects/main.py"},
        args=["-v", "d:/Clan_activity_report:/projects"]
    )
