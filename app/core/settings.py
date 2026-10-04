import os
from PySide6.QtCore import QSettings, QStandardPaths


class AppSettings:
    """Persistent application settings for PyQPSTricks Studio."""

    def __init__(self):
        self.settings = QSettings("PyQPSTricks", "PyQPSTricksStudio")

    # ------------------------------------------------------------------
    # TeX engine
    # ------------------------------------------------------------------
    @property
    def compiler(self) -> str:
        return self.settings.value("compiler", "pdflatex")

    @compiler.setter
    def compiler(self, val: str):
        self.settings.setValue("compiler", val or "pdflatex")

    @property
    def tex_bin_path(self) -> str:
        return self.settings.value("tex_bin_path", "")

    @tex_bin_path.setter
    def tex_bin_path(self, val: str):
        self.settings.setValue("tex_bin_path", val or "")

    @property
    def shell_escape(self) -> bool:
        return self.settings.value("shell_escape", True, type=bool)

    @shell_escape.setter
    def shell_escape(self, val: bool):
        self.settings.setValue("shell_escape", bool(val))

    @property
    def compilation_mode(self) -> str:
        """One of: auto-pst-pdf | pdftricks | xelatex-direct | classic"""
        return self.settings.value("compilation_mode", "auto-pst-pdf")

    @compilation_mode.setter
    def compilation_mode(self, val: str):
        self.settings.setValue("compilation_mode", val or "auto-pst-pdf")

    @property
    def passes(self) -> int:
        return self.settings.value("passes", 1, type=int)

    @passes.setter
    def passes(self, val: int):
        self.settings.setValue("passes", max(1, int(val)))

    # ------------------------------------------------------------------
    # Preamble
    # ------------------------------------------------------------------
    @staticmethod
    def default_preamble_path() -> str:
        config_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppConfigLocation
        ) or os.path.expanduser("~")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "preamble.pgs")

    @property
    def preamble_path(self) -> str:
        return self.settings.value("preamble_path", self.default_preamble_path())

    @preamble_path.setter
    def preamble_path(self, val: str):
        self.settings.setValue("preamble_path", val or self.default_preamble_path())

    @property
    def use_custom_preamble(self) -> bool:
        return self.settings.value("use_custom_preamble", True, type=bool)

    @use_custom_preamble.setter
    def use_custom_preamble(self, val: bool):
        self.settings.setValue("use_custom_preamble", bool(val))

    @property
    def external_editor(self) -> str:
        """Command or path of the external editor used for the preamble file."""
        return self.settings.value("external_editor", "")

    @external_editor.setter
    def external_editor(self, val: str):
        self.settings.setValue("external_editor", val or "")

    # ------------------------------------------------------------------
    # Editor font
    # ------------------------------------------------------------------
    @property
    def editor_font_family(self) -> str:
        default = "Consolas" if os.name == "nt" else "Monospace"
        return self.settings.value("editor_font_family", default)

    @editor_font_family.setter
    def editor_font_family(self, val: str):
        self.settings.setValue("editor_font_family", val or "Monospace")

    @property
    def editor_font_size(self) -> int:
        return self.settings.value("editor_font_size", 11, type=int)

    @editor_font_size.setter
    def editor_font_size(self, val: int):
        self.settings.setValue("editor_font_size", max(6, min(48, int(val))))

    # ------------------------------------------------------------------
    # Preview / UI
    # ------------------------------------------------------------------
    @property
    def live_preview(self) -> bool:
        return self.settings.value("live_preview", True, type=bool)

    @live_preview.setter
    def live_preview(self, val: bool):
        self.settings.setValue("live_preview", val)

    @property
    def preview_delay_ms(self) -> int:
        return self.settings.value("preview_delay_ms", 800, type=int)

    @preview_delay_ms.setter
    def preview_delay_ms(self, val: int):
        self.settings.setValue("preview_delay_ms", val)

    @property
    def theme(self) -> str:
        return self.settings.value("theme", "dark")

    @theme.setter
    def theme(self, val: str):
        self.settings.setValue("theme", val)

    @property
    def transparent_bg(self) -> bool:
        return self.settings.value("transparent_bg", False, type=bool)

    @transparent_bg.setter
    def transparent_bg(self, val: bool):
        self.settings.setValue("transparent_bg", val)

    @property
    def dpi(self) -> int:
        return self.settings.value("dpi", 300, type=int)

    @dpi.setter
    def dpi(self, val: int):
        self.settings.setValue("dpi", val)

    @property
    def new_file_mode(self) -> str:
        """One of: empty | sample"""
        return self.settings.value("new_file_mode", "empty")

    @new_file_mode.setter
    def new_file_mode(self, val: str):
        self.settings.setValue("new_file_mode", val or "empty")

