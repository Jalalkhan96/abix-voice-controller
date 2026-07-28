from __future__ import annotations

import subprocess
import shlex
from dataclasses import dataclass


@dataclass
class CommandResult:
    stdout: str
    stderr: str
    exit_code: int
    success: bool

    def summary(self) -> str:
        if self.success:
            output = self.stdout.strip()
            return output if output else "Command completed successfully"
        error = self.stderr.strip()
        return f"Command failed (exit code {self.exit_code}): {error}" if error else f"Command failed (exit code {self.exit_code})"


class CLIExecutor:
    def __init__(self, timeout: int = 30) -> None:
        self._timeout = timeout

    def execute(self, command: str) -> CommandResult:
        try:
            args = shlex.split(command)
        except ValueError:
            args = command.split()

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            return CommandResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                success=result.returncode == 0,
            )
        except subprocess.TimeoutExpired:
            return CommandResult(
                stdout="",
                stderr=f"Command timed out after {self._timeout} seconds",
                exit_code=-1,
                success=False,
            )
        except FileNotFoundError:
            return CommandResult(
                stdout="",
                stderr=f"Command not found: {args[0]}",
                exit_code=-1,
                success=False,
            )
        except Exception as e:
            return CommandResult(
                stdout="",
                stderr=str(e),
                exit_code=-1,
                success=False,
            )
