"""Asynchronous LaTeX / PSTricks compiler with support for
auto-pst-pdf, pdftricks, XeLaTeX, LuaLaTeX and the classic
latex → dvips → ps2pdf pipeline.
"""

import os
import re
import shutil
import tempfile
import subprocess
from dataclasses import dataclass
from typing import List, Optional

from PySide6.QtCore import QObject, QThread, Signal


@dataclass
class LaTeXError:
    line_number: int
    message: str
    context: str = ""


class LaTeXCompilerWorker(QObject):
    """Worker that runs the compilation pipeline in a background thread."""

    started = Signal()
    finished = Signal(str, bool)  # pdf_path, success
    log_output = Signal(str)
    errors_found = Signal(list)  # List[LaTeXError]

    def __init__(
        self,
        code: str,
        compiler_cmd: str = "pdflatex",
        extra_flags: str = "",
        tex_bin_path: str = "",
        passes: int = 1,
        shell_escape: bool = True,
        mode: str = "auto-pst-pdf",
    ):
        super().__init__()
        self.code = code
        self.compiler_cmd = compiler_cmd
        self.extra_flags = extra_flags
        self.tex_bin_path = tex_bin_path or ""
        self.passes = max(1, int(passes))
        self.shell_escape = shell_escape
        self.mode = mode

    # ------------------------------------------------------------------
    # Environment helpers
    # ------------------------------------------------------------------
    def _resolve_env_and_executable(self, cmd_name: str):
        env = os.environ.copy()
        extra_paths = []

        if self.tex_bin_path and os.path.exists(self.tex_bin_path):
            extra_paths.append(self.tex_bin_path)
            for sub in [
                "windows",
                "win32",
                "x86_64-windows",
                "x86_64-linux",
                "x86_64-darwin",
                "bin",
            ]:
                sub_path = os.path.join(self.tex_bin_path, sub)
                if os.path.exists(sub_path):
                    extra_paths.append(sub_path)

        fallback_dirs = [
            r"C:\texlive\2026\bin\windows",
            r"C:\texlive\2025\bin\windows",
            r"C:\texlive\2024\bin\windows",
            r"C:\Program Files\MiKTeX\miktex\bin\x64",
            "/usr/local/texlive/2026/bin/x86_64-linux",
            "/usr/local/texlive/2025/bin/x86_64-linux",
            "/usr/bin",
        ]
        for fb in fallback_dirs:
            if os.path.exists(fb) and fb not in extra_paths:
                extra_paths.append(fb)

        if extra_paths:
            env["PATH"] = os.pathsep.join(extra_paths) + os.pathsep + env.get("PATH", "")

        exe_path = shutil.which(cmd_name, path=env.get("PATH"))
        return env, exe_path

    def _build_latex_cmd(self, exe_path: str, temp_dir: str, tex_path: str) -> list:
        flags = [f for f in self.extra_flags.split() if f]

        if self.compiler_cmd == "tectonic":
            return [exe_path, "--outdir", temp_dir, tex_path]

        cmd = [
            exe_path,
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={temp_dir}",
        ]

        # shell-escape is required by auto-pst-pdf and pdftricks
        if self.shell_escape or self.mode in ("auto-pst-pdf", "pdftricks"):
            # Prefer modern flag; fall back for older MiKTeX
            cmd.append("-shell-escape")

        cmd += flags + [tex_path]
        return cmd

    # ------------------------------------------------------------------
    # Classic pipeline: latex → dvips → ps2pdf
    # ------------------------------------------------------------------
    def _run_classic_pipeline(self, env, temp_dir: str, tex_path: str) -> bool:
        base = os.path.join(temp_dir, "document")
        dvi_path = base + ".dvi"
        ps_path = base + ".ps"
        pdf_path = base + ".pdf"

        # 1. latex
        latex_exe = shutil.which("latex", path=env.get("PATH"))
        if not latex_exe:
            self.log_output.emit("Error: 'latex' executable not found (needed for classic mode).\n")
            return False

        cmd_latex = [
            latex_exe,
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={temp_dir}",
            tex_path,
        ]
        self.log_output.emit(f"Running: {' '.join(cmd_latex)}\n")
        if not self._run_process(cmd_latex, env, temp_dir):
            return False
        if not os.path.exists(dvi_path):
            self.log_output.emit("Error: DVI file was not produced.\n")
            return False

        # 2. dvips
        dvips_exe = shutil.which("dvips", path=env.get("PATH"))
        if not dvips_exe:
            self.log_output.emit("Error: 'dvips' executable not found.\n")
            return False

        cmd_dvips = [dvips_exe, "-o", ps_path, dvi_path]
        self.log_output.emit(f"Running: {' '.join(cmd_dvips)}\n")
        if not self._run_process(cmd_dvips, env, temp_dir):
            return False
        if not os.path.exists(ps_path):
            self.log_output.emit("Error: PostScript file was not produced.\n")
            return False

        # 3. ps2pdf
        ps2pdf_exe = (
            shutil.which("ps2pdf", path=env.get("PATH"))
            or shutil.which("ps2pdf14", path=env.get("PATH"))
            or shutil.which("gswin64c", path=env.get("PATH"))
            or shutil.which("gs", path=env.get("PATH"))
        )
        if not ps2pdf_exe:
            self.log_output.emit("Error: 'ps2pdf' / Ghostscript not found.\n")
            return False

        if "gs" in os.path.basename(ps2pdf_exe).lower() and "ps2pdf" not in os.path.basename(ps2pdf_exe).lower():
            # Raw Ghostscript
            cmd_ps2pdf = [
                ps2pdf_exe,
                "-dBATCH",
                "-dNOPAUSE",
                "-sDEVICE=pdfwrite",
                f"-sOutputFile={pdf_path}",
                ps_path,
            ]
        else:
            cmd_ps2pdf = [ps2pdf_exe, ps_path, pdf_path]

        self.log_output.emit(f"Running: {' '.join(cmd_ps2pdf)}\n")
        if not self._run_process(cmd_ps2pdf, env, temp_dir):
            return False

        return os.path.exists(pdf_path)

    def _run_process(self, cmd: list, env: dict, cwd: str, timeout: int = 45) -> bool:
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=cwd,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if process.stdout:
                for line in process.stdout:
                    self.log_output.emit(line)
            process.wait(timeout=timeout)
            return process.returncode == 0
        except subprocess.TimeoutExpired:
            process.kill()
            self.log_output.emit(f"\nTimeout ({timeout}s) for command: {' '.join(cmd)}\n")
            return False
        except Exception as e:
            self.log_output.emit(f"\nProcess error: {e}\n")
            return False

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def run(self):
        self.started.emit()
        temp_dir = tempfile.mkdtemp(prefix="pyqpstricks_")
        tex_path = os.path.join(temp_dir, "document.tex")
        pdf_path = os.path.join(temp_dir, "document.pdf")
        log_path = os.path.join(temp_dir, "document.log")

        try:
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(self.code)
        except Exception as e:
            self.log_output.emit(f"Error writing temporary TeX file: {e}")
            self.finished.emit("", False)
            return

        env, _ = self._resolve_env_and_executable(self.compiler_cmd)

        # ---------- Classic pipeline ----------
        if self.mode == "classic":
            success = self._run_classic_pipeline(env, temp_dir, tex_path)
            errors = self.parse_log(
                log_path if os.path.exists(log_path) else None, ""
            )
            self.errors_found.emit(errors)
            self.finished.emit(pdf_path if success else "", success)
            return

        # ---------- Single-engine modes (pdflatex / xelatex / lualatex / tectonic) ----------
        env, exe_path = self._resolve_env_and_executable(self.compiler_cmd)
        if not exe_path:
            hint = (
                f"Configured TeX bin directory: '{self.tex_bin_path}'\n"
                if self.tex_bin_path
                else "No custom TeX bin directory is configured (Preferences).\n"
            )
            err_msg = (
                f"Error: Compiler '{self.compiler_cmd}' not found in PATH.\n"
                f"{hint}"
                "Install TeX Live, MiKTeX or Tectonic, or set the correct bin directory.\n"
                "For PSTricks with pdflatex you also need the auto-pst-pdf (or pdftricks) package\n"
                "and must enable -shell-escape.\n"
            )
            self.log_output.emit(err_msg)
            self.errors_found.emit(
                [LaTeXError(line_number=1, message=f"Compiler '{self.compiler_cmd}' not found.")]
            )
            self.finished.emit("", False)
            return

        cmd = self._build_latex_cmd(exe_path, temp_dir, tex_path)
        success = False
        all_stdout: List[str] = []

        for pass_num in range(1, self.passes + 1):
            if self.passes > 1:
                self.log_output.emit(
                    f"\n=== Pass {pass_num}/{self.passes} ({self.compiler_cmd}) ===\n"
                )
            self.log_output.emit(f"Running: {' '.join(cmd)}\n")

            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=temp_dir,
                    env=env,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                stdout_lines = []
                if process.stdout:
                    for line in process.stdout:
                        stdout_lines.append(line)
                        self.log_output.emit(line)

                process.wait(timeout=60)  # auto-pst-pdf can be slower
                all_stdout.extend(stdout_lines)
                success = (process.returncode == 0) and os.path.exists(pdf_path)

                if not success:
                    break

            except subprocess.TimeoutExpired:
                process.kill()
                self.log_output.emit("\nCompilation timed out (limit: 60s).\n")
                self.errors_found.emit(
                    [LaTeXError(line_number=1, message="Compilation timeout")]
                )
                self.finished.emit("", False)
                return
            except Exception as e:
                self.log_output.emit(f"\nCompilation error: {e}\n")
                self.errors_found.emit(
                    [LaTeXError(line_number=1, message=str(e))]
                )
                self.finished.emit("", False)
                return

        errors = self.parse_log(
            log_path if os.path.exists(log_path) else None, "".join(all_stdout)
        )
        self.errors_found.emit(errors)
        self.finished.emit(pdf_path if success else "", success)

    # ------------------------------------------------------------------
    # Log parser (same heuristics as the original)
    # ------------------------------------------------------------------
    def parse_log(self, log_path: Optional[str], stdout_text: str) -> List[LaTeXError]:
        content = ""
        if log_path and os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                content = stdout_text
        else:
            content = stdout_text

        errors: List[LaTeXError] = []
        # Classic LaTeX error pattern
        for match in re.finditer(
            r"! (.*?)\n(?:.*?\n)*?l\.(\d+)\s+(.*)", content, re.MULTILINE
        ):
            msg = match.group(1).strip()
            line_no = int(match.group(2))
            context = match.group(3).strip()
            errors.append(LaTeXError(line_number=line_no, message=msg, context=context))

        if not errors:
            for match in re.finditer(r"l\.(\d+)\s+(.*)", content):
                errors.append(
                    LaTeXError(line_number=int(match.group(1)), message=match.group(2))
                )

        return errors


class AsyncCompilerManager(QObject):
    """Manages background compiler worker threads."""

    started = Signal()
    finished = Signal(str, bool)
    log_output = Signal(str)
    errors_found = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_jobs = []

    def compile(
        self,
        code: str,
        compiler_cmd: str = "pdflatex",
        extra_flags: str = "",
        tex_bin_path: str = "",
        passes: int = 1,
        shell_escape: bool = True,
        mode: str = "auto-pst-pdf",
    ):
        thread = QThread(self)
        worker = LaTeXCompilerWorker(
            code,
            compiler_cmd,
            extra_flags,
            tex_bin_path,
            passes,
            shell_escape,
            mode,
        )
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.started.connect(self.started)
        worker.log_output.connect(self.log_output)
        worker.errors_found.connect(self.errors_found)
        worker.finished.connect(self.finished)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        job = (thread, worker)
        self._active_jobs.append(job)
        thread.finished.connect(
            lambda: self._active_jobs.remove(job) if job in self._active_jobs else None
        )
        thread.start()
