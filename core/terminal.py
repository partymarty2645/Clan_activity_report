from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markup import escape
import datetime

console = Console()

def get_timestamp():
    return datetime.datetime.now().strftime("%H:%M:%S")

def log_section(title: str, subtitle: Optional[str] = None):
    """Prints a major section header."""
    text = Text(title, style="bold magenta")
    if subtitle is not None:
        text.append(f"\n{subtitle}", style="italic cyan")
    console.print(Panel(text, border_style="bright_magenta", expand=False))

def log_step(step_num: int, total_steps: int, name: str):
    """Prints a step header."""
    console.print(f"\n[bold black on bright_cyan] STEP {step_num}/{total_steps} [/bold black on bright_cyan] [bold bright_cyan]{name}[/bold bright_cyan]")

def log_info(message: str):
    """Prints an info message."""
    console.print(f"[dim]{get_timestamp()}[/dim] [bold cyan]ℹ[/bold cyan] [bright_white]{message}[/bright_white]")

def log_success(message: str):
    """Prints a success message."""
    console.print(f"[dim]{get_timestamp()}[/dim] [bold green]✔[/bold green] [bold spring_green3]{message}[/bold spring_green3]")

def log_warning(message: str):
    """Prints a warning message."""
    console.print(f"[dim]{get_timestamp()}[/dim] [bold yellow]⚡[/bold yellow] [bold gold1]{message}[/bold gold1]")

def log_error(message: str):
    """Prints an error message."""
    console.print(f"[dim]{get_timestamp()}[/dim] [bold white on red] ✖ [/bold white on red] [bright_red]{message}[/bright_red]")

def log_plain(message: str):
    """Prints a plain message."""
    console.print(message)
