"""Validate the project MCP policy; --live probes public docs without credentials."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
URL = "https://mcp.context7.com/mcp"
TOOLS = {"resolve-library-id", "query-docs"}


def check_config(path):
    config = tomllib.loads(Path(path).read_text())
    server = config["mcp_servers"]["context7"]
    if server.get("url") != URL or server.get("enabled") is not True:
        raise ValueError("Expected enabled official Context7 HTTP endpoint")
    if server.get("required") is not False or set(server.get("enabled_tools", [])) != TOOLS:
        raise ValueError("Expected optional startup and exactly two documentation tools")
    if server.get("default_tools_approval_mode") != "writes":
        raise ValueError("Expected approval for tools not marked read-only")
    if any(key in server for key in ("command", "args", "env", "http_headers", "env_http_headers",
                                    "http_headers_helper", "bearer_token_env_var", "oauth")):
        raise ValueError("This checker supports only the credential-free remote profile")
    for key in ("startup_timeout_sec", "tool_timeout_sec"):
        if not 0 < server.get(key, 0) <= 60:
            raise ValueError(f"Invalid bounded timeout: {key}")
    return server


class PublicDocsProbe:
    """Small HTTP/SSE diagnostic, not a replacement for the Codex MCP client."""

    def __init__(self):
        self.headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        self.identifier = 0

    def request(self, method, params=None, notification=False):
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        if not notification:
            self.identifier += 1
            payload["id"] = self.identifier
        with tempfile.TemporaryDirectory() as directory:
            header_path, body_path = Path(directory) / "headers", Path(directory) / "body"
            # Use the system TLS trust store; never use --insecure or print headers.
            command = ["curl", "--silent", "--show-error", "--fail-with-body", "--proto", "=https",
                       "--connect-timeout", "10", "--max-time", "45", "--max-filesize", "1048576",
                       "--dump-header", str(header_path), "--output", str(body_path), URL]
            for key, value in self.headers.items():
                command.extend(["--header", f"{key}: {value}"])
            command.extend(["--data-binary", "@-"])
            result = subprocess.run(command, input=json.dumps(payload).encode(), capture_output=True, timeout=50)
            if result.returncode:
                raise ValueError(f"MCP HTTPS probe failed (curl exit {result.returncode}); check network, TLS or quota")
            for line in header_path.read_text().splitlines():
                if line.lower().startswith("mcp-session-id:"):
                    self.headers["Mcp-Session-Id"] = line.split(":", 1)[1].strip()
            raw = body_path.read_text()
        if notification:
            return {}
        if raw.lstrip().startswith("{"):
            response = json.loads(raw)
        else:
            events = []
            for block in raw.replace("\r\n", "\n").split("\n\n"):
                data = "\n".join(line[5:].lstrip() for line in block.splitlines() if line.startswith("data:"))
                if data:
                    events.append(json.loads(data))
            response = next((event for event in events if event.get("id") == self.identifier), {})
        if response.get("id") != self.identifier or "error" in response or "result" not in response:
            raise ValueError(f"Invalid/error MCP response for {method}")
        return response["result"]

    def tool(self, name, arguments):
        if name not in TOOLS:
            raise ValueError("Documentation tool not allowed")
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise ValueError(f"Documentation query failed: {name}; check service limits")
        text = "\n".join(item["text"] for item in result.get("content", []) if item.get("type") == "text")
        if not text.strip():
            raise ValueError(f"Empty documentation response: {name}")
        return text

    def check(self):
        init = self.request("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                            "clientInfo": {"name": "uav-research-mcp-check", "version": "1.0"}})
        self.headers["MCP-Protocol-Version"] = init["protocolVersion"]
        self.request("notifications/initialized", notification=True)
        tools = {tool["name"]: tool for tool in self.request("tools/list", {})["tools"]}
        if not TOOLS.issubset(tools) or any(tools[name].get("annotations", {}).get("readOnlyHint") is not True
                                          for name in TOOLS):
            raise ValueError("Expected two advertised read-only documentation tools")
        resolved = self.tool("resolve-library-id", {"libraryName": "ultralytics",
                             "query": "Official YOLO Python training documentation: epochs, imgsz and batch"})
        library = "/ultralytics/ultralytics"
        if library not in resolved:
            raise ValueError("Official Ultralytics repository ID not found; review index changes")
        docs = self.tool("query-docs", {"libraryId": library,
                         "query": "Python YOLO model.train parameters epochs imgsz batch; cite official documentation"})
        urls = re.findall(r"https://[^\s)\]>]+", docs)
        primary = sorted({url.rstrip(".,") for url in urls
                          if url.startswith(("https://docs.ultralytics.com/", "https://github.com/ultralytics/"))})
        if not primary:
            raise ValueError("No primary Ultralytics source URL returned")
        return {"server": init["serverInfo"], "protocol_version": init["protocolVersion"],
                "verified_tools": sorted(TOOLS), "library_id": library, "primary_sources": primary[:5],
                "credential_used": False, "scope": "connection and public docs; not installed-version API verification"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/mcp/codex.example.toml")
    parser.add_argument("--live", action="store_true", help="Send public library queries; requires internet and curl")
    args = parser.parse_args()
    try:
        check_config(args.config)
        print("PASS: optional official HTTP server, bounded timeouts, documentation tool allowlist, no credentials")
        if args.live:
            print(json.dumps(PublicDocsProbe().check(), indent=2, ensure_ascii=False))
            print("PASS: initialize, tools/list, library resolution and primary-source documentation retrieval")
        else:
            print("Offline policy check only; live MCP connection was not tested by this invocation.")
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, f"FAIL: {exc}\n")


if __name__ == "__main__":
    main()
