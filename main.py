import asyncio
import logging
import sys
import subprocess
import os
from logging.handlers import RotatingFileHandler
from core.terminal import log_section, log_step, log_info, log_success, log_warning, log_error, console

# Setup File Logging Only (Console handled by Rich)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        RotatingFileHandler("app.log", maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
    ]
)
logger = logging.getLogger("Orchestrator")

# Import and validate configuration at startup
try:
    from core.observability import setup_observability
    setup_observability(logger)
    
    from core.config import Config
    Config.fail_fast()
    
    # We delay logging config details to file only to keep terminal clean
    Config.log_config()
except Exception as e:
    log_error(f"Configuration Critical Failure: {e}")
    sys.exit(1)

def run_module(module_name: str, description: str) -> bool:
    """Runs a module via `python -m <module>` and streams output."""
    log_info(f"Starting: [bold]{description}[/bold]...")
    process = None
    try:
        cmd = [sys.executable, "-u", "-m", module_name]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                # Dynamic Coloring for Subprocess Output
                line = output.strip()
                style = "bright_black" # Default gray-ish
                
                lower_line = line.lower()
                if "error" in lower_line or "failed" in lower_line:
                    style = "bold red"
                elif "warning" in lower_line:
                    style = "yellow"
                elif "success" in lower_line or "completed" in lower_line or "saved" in lower_line or "synced" in lower_line:
                    style = "green"
                elif "waiting" in lower_line or "remaining" in lower_line:
                    style = "orange1"
                elif "downloading" in lower_line or "fetching" in lower_line:
                    style = "cyan"
                elif "found" in lower_line: # e.g. "Found X members"
                    style = "bright_blue"
                elif ">>" in lower_line: # Script headers
                    style = "bold white"

                console.print(f"    [{style}]{line}[/{style}]")

        rc = process.poll()
        if rc != 0:
            err = process.stderr.read()
            log_error(f"{description} failed (Exit Code {rc})")
            if err:
                console.print(f"[red]{err.strip()}[/red]")
            return False

        log_success(f"{description} completed.")
        return True
    except KeyboardInterrupt:
        log_warning(f"Interrupted {description}...")
        if process: process.kill()
        raise
    except Exception as e:
        log_error(f"Failed to execute {description}: {e}")
        return False

async def main():
    log_section("CLAN ACTIVITY REPORT PIPELINE", "Automated Data Harvest & Analytics Engine")
    
    # Step 1: Harvest
    log_step(1, 5, "DATA HARVEST")
    # Using descriptive name for the task
    if not run_module('scripts.harvest_sqlite', "Harvesting Data from Wise Old Man & Discord"):
        log_error("Harvest stage failed. Stopping pipeline to prevent partial data report.")
        return sys.exit(1)

    # Step 2: AI Enrichment
    log_step(2, 5, "AI ENRICHMENT")
    if not run_module('scripts.mcp_enrich', "Enriching Data with AI (Gemini)"):
        log_error("AI Enrichment failed. Stopping pipeline.")
        return sys.exit(1)

    # Step 3: Report
    log_step(3, 5, "REPORT GENERATION")
    if not run_module('scripts.report_sqlite', "Generating Excel Report (SQLite source)"):
        log_error("Excel Report generation failed.")
    
    # Step 3: Analytics & Export
    log_step(3, 4, "DASHBOARD EXPORT")
    if not run_module('scripts.export_sqlite', "Exporting JSON Data for Web Dashboard"):
        log_error("Dashboard data export failed.")

    # Step 3b: Deploy Docs
    if not run_module('scripts.publish_docs', "Deploying Dashboard to /docs"):
        log_error("Docs deployment failed.")

    # Step 4: CSV Export
    log_step(4, 4, "LEGACY EXPORT")
    run_module('scripts.export_csv', "Generating CSV Dump")

    # Final Summary
    console.print()
    log_success("[bold]Pipeline Execution Successful.[/bold] All systems go.")
    console.print()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        log_warning("Pipeline stopped by user action.")
