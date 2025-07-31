import shlex
import subprocess
from logger.logger import logger
import os
import shutil
import tempfile


# Cache for sudo availability to avoid repeated system checks
_sudo_available = None


def reset_sudo_cache():
    """
    Reset the sudo availability cache to force a fresh check.
    This is useful when system changes might affect sudo availability,
    such as after package installation or environment changes.
    """
    global _sudo_available
    _sudo_available = None


def is_sudo_available():
    """
    Check if sudo is available in the system.
    Result is cached to avoid repeated system checks during program execution.
    Use reset_sudo_cache() if you need to force a fresh check.

    Returns:
        bool: True if sudo is available, False otherwise
    """
    global _sudo_available
    if _sudo_available is None:
        _sudo_available = bool(shutil.which("sudo"))
    return _sudo_available


def parse_command(cmd):
    """
    Parse a command into words, handling quotes, escapes, and line continuations.
    Also splits on command chains (&&, ||, |).

    Args:
        cmd: Command to parse (string or list)

    Returns:
        tuple: (list of command parts, list of separators)
        Each command part is a list of words, and separators are the original chain operators
    """
    if isinstance(cmd, list):
        return [cmd], []

    # For multiline commands, treat the entire block as a single command
    if isinstance(cmd, str) and "\n" in cmd:
        # Preserve the exact multiline format
        return [[cmd]], []

    # Handle line continuations and normalize whitespace
    if isinstance(cmd, str):
        # Replace line continuations with spaces
        cmd = cmd.replace("\\\n", " ")
        # Normalize whitespace
        cmd = " ".join(cmd.split())

    # Split on command chains first
    parts = []
    separators = []
    current_part = []
    current_word = []
    in_quotes = False
    quote_char = None

    for char in cmd:
        if char in ["'", '"'] and (not in_quotes or quote_char == char):
            in_quotes = not in_quotes
            quote_char = char if in_quotes else None
            current_word.append(char)
        elif char.isspace() and not in_quotes:
            if current_word:
                word = "".join(current_word)
                if word in ["&&", "||", "|"]:
                    if current_part:
                        parts.append(current_part)
                        separators.append(word)
                    current_part = []
                else:
                    current_part.append(word)
                current_word = []
        else:
            current_word.append(char)

    # Handle last word
    if current_word:
        word = "".join(current_word)
        if word in ["&&", "||", "|"]:
            if current_part:
                parts.append(current_part)
                separators.append(word)
        else:
            current_part.append(word)
            if current_part:
                parts.append(current_part)

    return parts or [[]], separators


def is_installing_sudo(cmd):
    """
    Check if the command is trying to install sudo itself.

    Args:
        cmd: Command to check (string or list)

    Returns:
        bool: True if the command is installing sudo
    """
    # Parse command into parts (handles chains like &&, ||, |)
    command_parts, _ = parse_command(cmd)

    # Check each part of the command chain
    return any(_is_single_command_installing_sudo(part) for part in command_parts)


def _is_single_command_installing_sudo(words):
    """
    Check if a single command (no chains) is installing sudo.

    Args:
        words: List of command words

    Returns:
        bool: True if the command is installing sudo
    """
    if not words:
        return False

    # Skip sudo and its flags
    start_idx = 0
    if words[0].lower() == "sudo":
        start_idx = 1
        while start_idx < len(words) and words[start_idx].startswith("-"):
            start_idx += 1

    if start_idx >= len(words) - 1:  # Need at least command and action
        return False

    # Check package manager and action
    pkg_manager = words[start_idx].lower()
    action = words[start_idx + 1]

    # Handle different package manager syntaxes
    if pkg_manager == "pacman" and action == "-S":
        packages_start = start_idx + 2
    elif (
        pkg_manager in ["apt", "apt-get", "yum", "dnf", "zypper"]
        and action.lower() == "install"
    ):
        packages_start = start_idx + 2
    else:
        return False

    # Check if sudo is in the package list
    # Look for 'sudo' or packages starting with 'sudo='
    packages = []
    for word in words[packages_start:]:
        if not word.startswith("-"):  # Skip flags
            # Handle package versions (e.g., sudo=1.8.31-1ubuntu1.2)
            pkg_name = word.split("=")[0].lower()
            packages.append(pkg_name)

    return "sudo" in packages


def strip_sudo(cmd):
    """
    Remove sudo from a command if present, unless it's installing sudo itself.

    Args:
        cmd: Command to strip sudo from (string or list)

    Returns:
        The command without sudo (same type as input)
    """
    # Don't strip sudo if we're trying to install it
    if is_installing_sudo(cmd):
        return cmd

    # Parse the command into parts
    command_parts, separators = parse_command(cmd)

    # Process each part
    stripped_parts = []
    for words in command_parts:
        # Skip sudo and its flags
        start_idx = 0
        if words and words[0].lower() == "sudo":
            start_idx = 1
            while start_idx < len(words) and words[start_idx].startswith("-"):
                start_idx += 1
        stripped_parts.append(words[start_idx:])

    # Return in the same format as input
    if isinstance(cmd, list):
        return stripped_parts[0] if stripped_parts else []
    else:
        # Join parts with their original separators
        result = []
        for i, part in enumerate(stripped_parts):
            if i > 0 and i - 1 < len(separators):
                result.append(separators[i - 1])
            result.extend(part)
        return " ".join(result)


def command_needs_sudo(cmd):
    """
    Check if a command needs sudo.

    Args:
        cmd: Command to check (string or list)

    Returns:
        bool: True if sudo is needed, False otherwise
    """
    if not is_sudo_available():
        return False

    # Parse command into parts and check each part
    parts, _ = parse_command(cmd)

    # If any part already has sudo, the whole command doesn't need sudo
    if any(words and words[0].lower() == "sudo" for words in parts):
        return False

    # Check each part
    for words in parts:
        if not words:
            continue

        # Get the base command
        base_cmd = words[0].lower()

        # Windows admin commands
        if os.name == "nt":
            admin_commands = [
                "net",
                "sc",
                "reg",
                "bcdedit",
                "diskpart",
                "chkdsk",
                "format",
            ]
            if base_cmd in admin_commands:
                # For net commands, check if it's an admin operation
                if base_cmd == "net":
                    admin_operations = ["user", "localgroup", "accounts", "share"]
                    return len(words) > 1 and words[1].lower() in admin_operations
                return True
            continue  # Windows doesn't use sudo
        else:
            # On Unix-like systems, check if it's a Windows admin command being tested
            if base_cmd == "net" and len(words) > 1 and words[1].lower() == "user":
                return True

        # Commands that typically need sudo on Unix-like systems
        sudo_commands = [
            "apt",
            "apt-get",
            "dnf",
            "yum",
            "pacman",
            "rpm",
            "dpkg",
            "systemctl",
            "service",
            "mount",
            "umount",
            "fdisk",
            "mkfs",
            "cryptsetup",
            "lvextend",
            "resize2fs",
        ]

        # Check if it's a known sudo command
        if base_cmd in sudo_commands:
            return True

        # Check file permissions if it's a path
        cmd_path = (
            words[0]
            if os.path.isabs(words[0]) and os.path.exists(words[0])
            else shutil.which(words[0])
        )

        if cmd_path and not os.access(cmd_path, os.X_OK):
            return True

    return False


def run_subprocess(
    cmd,
    interactive=False,
    input=None,
    shell=False,
    raise_on_error=False,
    shell_type=None,
    **kwargs,
):
    """
    Run a subprocess with proper sudo handling based on platform.

    Args:
        cmd: Command to run (string or list)
        interactive: Whether to run in interactive mode with live output (default: False)
        input: Input to pass to the process (default: None)
        shell: Whether to run command in shell (default: False)
        raise_on_error: Whether to raise an exception on non-zero exit code (default: False)
        shell_type: The shell type to use for multiline scripts (ShellType enum)
        **kwargs: Additional arguments to pass to subprocess.run

    Returns:
        subprocess.CompletedProcess: Result of the subprocess
    """
    # Parse the command
    parts, separators = parse_command(cmd)
    if not parts:
        raise ValueError("Empty command")

    # Process each part based on platform
    processed_parts = []
    for part in parts:
        if not part:
            continue

        # On Windows, strip sudo
        if os.name == "nt":
            if part[0].lower() == "sudo":
                start_idx = 1
                while start_idx < len(part) and part[start_idx].startswith("-"):
                    start_idx += 1
                processed_parts.append(part[start_idx:])
            else:
                processed_parts.append(part)
        # On Unix-like systems, add sudo if needed
        else:
            if part[0].lower() != "sudo" and command_needs_sudo(part):
                processed_parts.append(["sudo"] + part)
            else:
                processed_parts.append(part)

    # Reconstruct the command
    final_cmd = []
    for i, part in enumerate(processed_parts):
        if i > 0 and i - 1 < len(separators):
            final_cmd.append(separators[i - 1])
        final_cmd.extend(part)

    # Convert to string if input was string
    if isinstance(cmd, str):
        final_cmd = " ".join(final_cmd)

    # Set up IO handling
    io_kwargs = {}
    if interactive:
        io_kwargs.update({"stdout": None, "stderr": None, "stdin": subprocess.PIPE})
    else:
        io_kwargs.update(
            {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "stdin": None}
        )

    # Add input if provided
    if input:
        if isinstance(input, str):
            io_kwargs["input"] = input
            if not input.endswith("\n"):
                io_kwargs["input"] += "\n"
        else:
            io_kwargs["input"] = input
        # When input is provided, we need stdin to be PIPE
        io_kwargs["stdin"] = subprocess.PIPE
        # Remove stdin from the final kwargs if it's in expected_kwargs
        if "stdin" not in kwargs.get("expected_kwargs", {}):
            del io_kwargs["stdin"]

    # Merge with user kwargs
    kwargs.update(io_kwargs)

    # Run the subprocess
    logger.debug(f"Running command: {final_cmd}")

    if isinstance(final_cmd, str) and not shell:
        final_cmd = shlex.split(final_cmd)

    try:
        if shell_type:
            # Don't wrap the command in a list, just prepend the shebang
            script_content = f"\n{final_cmd}"
            # script_content = f"#!{shell_type.value}\n{final_cmd}"
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".sh", delete=False
            ) as script:
                script.write(script_content)
                script.flush()
                script_path = script.name
                os.chmod(script_path, 0o755)
                # Use the shell_type's command to execute the script
                final_cmd = f"{shell_type.get_shell_command()} {script_path}"
                logger.info(f"Running command: {final_cmd}")
                shell = True

        if interactive:
            process = subprocess.run(
                final_cmd,
                shell=shell,
                check=raise_on_error,
                text=True,
                **kwargs,
            )
            return process
        else:
            return subprocess.run(
                final_cmd,
                shell=shell,
                check=raise_on_error,
                text=True,
                input=input,
                **kwargs,
            )

    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"Command failed with error: {e}")
        raise

    finally:
        if shell_type and "script_path" in locals():
            os.unlink(script_path)
