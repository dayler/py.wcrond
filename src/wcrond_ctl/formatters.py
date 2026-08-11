import datetime

def format_datetime(iso_str: str) -> str:
    if not iso_str or iso_str == "Never":
        return iso_str
    try:
        dt = datetime.datetime.fromisoformat(iso_str)
        local_dt = dt.astimezone()
        return local_dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return iso_str

def format_duration(seconds):
    if seconds is None:
        return "-"
    seconds = float(seconds)
    if seconds < 60:
        return f"{seconds:.1f}s"
    m = int(seconds // 60)
    s = int(seconds % 60)
    if m < 60:
        return f"{m}m {s}s"
    h = m // 60
    m = m % 60
    return f"{h}h {m}m"

# ANSI colors
class Colors:
    SUCCESS = "\033[92m"
    FAILED = "\033[91m"
    RUNNING = "\033[94m"
    TIMEOUT = "\033[93m"
    RESET = "\033[0m"

def colorize(text, status):
    if status.upper() == "SUCCESS":
        return f"{Colors.SUCCESS}{text}{Colors.RESET}"
    elif status.upper() == "FAILED":
        return f"{Colors.FAILED}{text}{Colors.RESET}"
    elif status.upper() == "RUNNING":
        return f"{Colors.RUNNING}{text}{Colors.RESET}"
    elif status.upper() == "TIMEOUT":
        return f"{Colors.TIMEOUT}{text}{Colors.RESET}"
    return text

def print_table(headers, rows):
    if not rows:
        print("No data.")
        return

    # Calculate column widths
    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, col in enumerate(row):
            # clean ANSI escapes for length calculation
            clean_col = str(col).replace(Colors.SUCCESS, "").replace(Colors.FAILED, "")\
                .replace(Colors.RUNNING, "").replace(Colors.TIMEOUT, "").replace(Colors.RESET, "")
            col_widths[i] = max(col_widths[i], len(clean_col))

    def print_sep(left, mid, right):
        parts = ["─" * (w + 2) for w in col_widths]
        print(left + mid.join(parts) + right)

    # Top border
    print_sep("┌", "┬", "┐")
    
    # Headers
    header_str = "│"
    for i, h in enumerate(headers):
        header_str += f" {str(h).ljust(col_widths[i])} │"
    print(header_str)
    
    # Header separator
    print_sep("├", "┼", "┤")
    
    # Rows
    for row in rows:
        row_str = "│"
        for i, col in enumerate(row):
            clean_col = str(col).replace(Colors.SUCCESS, "").replace(Colors.FAILED, "")\
                .replace(Colors.RUNNING, "").replace(Colors.TIMEOUT, "").replace(Colors.RESET, "")
            padding = " " * (col_widths[i] - len(clean_col))
            row_str += f" {str(col)}{padding} │"
        print(row_str)
        
    # Bottom border
    print_sep("└", "┴", "┘")
