from datetime import datetime
import inspect

DEBUG = True  # Set to False to disable debug output

def set_debug_mode(enabled: bool):
    global DEBUG
    DEBUG = enabled or False

def debug(title, *msg):
    if not DEBUG:
        return

    # Get current caller frame info
    caller_frame = inspect.currentframe().f_back
    lineno = caller_frame.f_lineno
    filename = caller_frame.f_globals.get("__file__", "<stdin>")
    func_name = caller_frame.f_code.co_name

    # Print debug banner
    print("\n" + "~" * 100)
    print(f"[DEBUG @ {filename}:{lineno} in {func_name}()]")
    print(f"🕒 {datetime.now().strftime('%H:%M:%S')} | {title}")
    print()
    try:
        for comment in msg:
            print("   ➤", comment)
    except KeyError as error:
        print(f"Debug Error: {error}")

    print("\n" + "~" * 100)