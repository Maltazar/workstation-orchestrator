from models.base.command import Command
from logger.logger import logger
from helpers.helper import get_host_os, is_same_linux_dist
from helpers.subprocess_helper import run_subprocess


def run_commands(group_name: str, commands: list[Command]):
    logger.info(f"Running command group: {group_name}")
    host_os = get_host_os()

    for command in commands:
        logger.debug(f"Active OS: {command.get_active_os()}")
        validate_shell = False

        validate_shell_cmd = command.validate_shell_type(host_os)

        if command.os_dist:
            validate_dist = is_same_linux_dist(command.os_dist)
            if validate_dist and validate_shell_cmd:
                validate_shell = True
        elif validate_shell_cmd:
            validate_shell = True

        if validate_shell:
            for cmd_run in command.execute:
                run_shell = False
                fail_on_error = cmd_run.fail_on_error
                if cmd_run.valid_exit_codes:
                    valid_exit_codes = cmd_run.valid_exit_codes
                    valid_exit_codes += [0]
                else:
                    valid_exit_codes = [0]

                set_shell_type = None
                if isinstance(cmd_run.run, str) and "\n" in cmd_run.run:
                    logger.debug("Is multiline command block")
                    run_shell = True
                    set_shell_type = command.shell
                cmd = cmd_run.create_command(command.shell.get_shell_command())
                result = run_subprocess(
                    cmd,
                    shell=run_shell,
                    raise_on_error=fail_on_error,
                    shell_type=set_shell_type,  # Pass the shell type for multiline commands
                )
                if result.returncode not in valid_exit_codes:
                    logger.error(f"Command failed: {cmd}")
                    logger.error(result.stderr)
                    continue
                logger.output(result.stdout)
                logger.success(f"{group_name} - executed successfully")
                # Save output if requested
                cmd_run.save_output(result.stdout)
