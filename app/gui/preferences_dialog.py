"""Preferences dialog for PyQPSTricks Studio."""

import os
import shutil
import subprocess

from PySide6.QtCore import QProcess, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFontComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from app.core.template import DEFAULT_PREAMBLE_BODY


class PreferencesDialog(QDialog):
    """Configure TeX engine, compilation mode, preamble path, editor font, etc."""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Preferences — PyQPSTricks Studio")
        self.setMinimumWidth(620)

        root = QVBoxLayout(self)

        # --- Compilation mode -------------------------------------------------
        grp_mode = QGroupBox("Modo de compilación PSTricks")
        form_mode = QFormLayout(grp_mode)

        self.cmb_mode = QComboBox(self)
        self.cmb_mode.addItem("auto-pst-pdf (pdflatex + shell-escape)", "auto-pst-pdf")
        self.cmb_mode.addItem("pdftricks (pdflatex + shell-escape)", "pdftricks")
        self.cmb_mode.addItem("XeLaTeX / LuaLaTeX directo", "xelatex-direct")
        self.cmb_mode.addItem("Clásico (latex → dvips → ps2pdf)", "classic")
        idx = self.cmb_mode.findData(self.settings.compilation_mode)
        if idx >= 0:
            self.cmb_mode.setCurrentIndex(idx)
        form_mode.addRow("Modo:", self.cmb_mode)

        hint_mode = QLabel(
            "<b>auto-pst-pdf</b>: recomendado con pdflatex. Requiere <code>-shell-escape</code>.<br>"
            "<b>pdftricks</b>: el código debe ir dentro de <code>\\begin{pdfpic}...\\end{pdfpic}</code>.<br>"
            "<b>XeLaTeX/LuaLaTeX</b>: PSTricks funciona de forma nativa (elige xelatex o lualatex abajo).<br>"
            "<b>Clásico</b>: pipeline latex → dvips → ps2pdf (más lento pero muy compatible)."
        )
        hint_mode.setWordWrap(True)
        form_mode.addRow(hint_mode)
        root.addWidget(grp_mode)

        # --- TeX engine -------------------------------------------------------
        grp_engine = QGroupBox("Motor TeX")
        form = QFormLayout(grp_engine)

        self.cmb_compiler = QComboBox(self)
        self.cmb_compiler.addItems(["pdflatex", "lualatex", "xelatex", "tectonic", "latex"])
        idx = self.cmb_compiler.findText(self.settings.compiler)
        if idx >= 0:
            self.cmb_compiler.setCurrentIndex(idx)
        form.addRow("Motor:", self.cmb_compiler)

        path_row = QHBoxLayout()
        self.txt_tex_path = QLineEdit(self.settings.tex_bin_path, self)
        self.txt_tex_path.setPlaceholderText(
            r"Opcional. Ej: C:\texlive\2026\bin\windows  o  /usr/bin"
        )
        btn_browse = QPushButton("Examinar…", self)
        btn_browse.clicked.connect(self._browse_tex_path)
        path_row.addWidget(self.txt_tex_path)
        path_row.addWidget(btn_browse)
        form.addRow("Ruta del motor (bin):", path_row)

        self.chk_shell = QCheckBox("Activar -shell-escape (necesario para auto-pst-pdf y pdftricks)")
        self.chk_shell.setChecked(self.settings.shell_escape)
        form.addRow(self.chk_shell)

        self.spn_passes = QSpinBox(self)
        self.spn_passes.setRange(1, 5)
        self.spn_passes.setValue(self.settings.passes)
        form.addRow("Pasadas de compilación:", self.spn_passes)

        hint = QLabel(
            "Deja la ruta vacía para usar el PATH del sistema. "
            "Si TeX Live / MiKTeX no está en el PATH, indica aquí la carpeta que contiene "
            "pdflatex / xelatex / latex / dvips / ps2pdf."
        )
        hint.setWordWrap(True)
        form.addRow(hint)
        root.addWidget(grp_engine)

        # --- Preámbulo personalizado (como en la captura de PyQTikz) ----------
        grp_preamble = QGroupBox("Preámbulo personalizado (preamble.pgs)")
        form_pre = QFormLayout(grp_preamble)

        self.chk_custom_preamble = QCheckBox("Usar preámbulo personalizado")
        self.chk_custom_preamble.setChecked(self.settings.use_custom_preamble)
        form_pre.addRow(self.chk_custom_preamble)

        pre_row = QHBoxLayout()
        self.txt_preamble_path = QLineEdit(self.settings.preamble_path, self)
        self.txt_preamble_path.setPlaceholderText("Ruta al archivo .pgs / .tex del preámbulo")
        btn_browse_pre = QPushButton("Examinar…", self)
        btn_browse_pre.clicked.connect(self._browse_preamble_path)
        btn_edit_pre = QPushButton("Editar…", self)
        btn_edit_pre.setToolTip("Abrir el archivo del preámbulo en el editor externo")
        btn_edit_pre.clicked.connect(self._edit_preamble_external)
        pre_row.addWidget(self.txt_preamble_path)
        pre_row.addWidget(btn_browse_pre)
        pre_row.addWidget(btn_edit_pre)
        form_pre.addRow("Archivo preamble.pgs:", pre_row)

        editor_row = QHBoxLayout()
        self.txt_external_editor = QLineEdit(self.settings.external_editor, self)
        self.txt_external_editor.setPlaceholderText(
            r"Opcional. Ej: code, notepad++, gedit, C:\Program Files\…\notepad++.exe"
        )
        btn_browse_ed = QPushButton("Examinar…", self)
        btn_browse_ed.clicked.connect(self._browse_external_editor)
        editor_row.addWidget(self.txt_external_editor)
        editor_row.addWidget(btn_browse_ed)
        form_pre.addRow("Editor externo:", editor_row)

        hint_pre = QLabel(
            "El archivo puede contener solo los <code>\\usepackage</code> / comandos "
            "que quieras (se envolverá automáticamente en <code>\\documentclass{standalone}</code> "
            "y <code>\\begin{document}</code>), o un documento completo con el marcador "
            "<code>&lt;PSTRICKS_CODE&gt;</code>."
        )
        hint_pre.setWordWrap(True)
        form_pre.addRow(hint_pre)
        root.addWidget(grp_preamble)

        # --- Editor font ------------------------------------------------------
        grp_font = QGroupBox("Fuente del editor")
        form_font = QFormLayout(grp_font)

        self.cmb_font = QFontComboBox(self)
        self.cmb_font.setCurrentFont(QFont(self.settings.editor_font_family))
        form_font.addRow("Familia:", self.cmb_font)

        self.spn_font_size = QSpinBox(self)
        self.spn_font_size.setRange(6, 48)
        self.spn_font_size.setValue(self.settings.editor_font_size)
        self.spn_font_size.setSuffix(" pt")
        form_font.addRow("Tamaño:", self.spn_font_size)
        root.addWidget(grp_font)

        # --- Nuevo archivo ----------------------------------------------------
        grp_new_file = QGroupBox("Nuevo archivo")
        form_new_file = QFormLayout(grp_new_file)
        self.cmb_new_file_mode = QComboBox(self)
        self.cmb_new_file_mode.addItem("Documento en blanco (vacío)", "empty")
        self.cmb_new_file_mode.addItem("Ejemplo PSTricks por defecto", "sample")
        idx = self.cmb_new_file_mode.findData(self.settings.new_file_mode)
        if idx >= 0:
            self.cmb_new_file_mode.setCurrentIndex(idx)
        form_new_file.addRow("Contenido por defecto:", self.cmb_new_file_mode)
        root.addWidget(grp_new_file)


        # --- Preview ----------------------------------------------------------
        grp_prev = QGroupBox("Vista previa")
        form_prev = QFormLayout(grp_prev)

        self.chk_live = QCheckBox("Live preview (recompilar al escribir)")
        self.chk_live.setChecked(self.settings.live_preview)
        form_prev.addRow(self.chk_live)

        self.spn_delay = QSpinBox(self)
        self.spn_delay.setRange(200, 5000)
        self.spn_delay.setSingleStep(100)
        self.spn_delay.setSuffix(" ms")
        self.spn_delay.setValue(self.settings.preview_delay_ms)
        form_prev.addRow("Retraso live preview:", self.spn_delay)

        self.spn_dpi = QSpinBox(self)
        self.spn_dpi.setRange(72, 600)
        self.spn_dpi.setValue(self.settings.dpi)
        form_prev.addRow("DPI de renderizado:", self.spn_dpi)

        self.chk_transparent = QCheckBox("Fondo de cuadrícula transparente")
        self.chk_transparent.setChecked(self.settings.transparent_bg)
        form_prev.addRow(self.chk_transparent)
        root.addWidget(grp_prev)

        # --- Theme ------------------------------------------------------------
        grp_theme = QGroupBox("Apariencia")
        form_theme = QFormLayout(grp_theme)
        self.cmb_theme = QComboBox(self)
        self.cmb_theme.addItems(["dark", "light"])
        idx = self.cmb_theme.findText(self.settings.theme)
        if idx >= 0:
            self.cmb_theme.setCurrentIndex(idx)
        form_theme.addRow("Tema:", self.cmb_theme)
        root.addWidget(grp_theme)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _browse_tex_path(self):
        path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta bin de TeX")
        if path:
            self.txt_tex_path.setText(path)

    def _browse_preamble_path(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Elegir archivo de preámbulo",
            self.txt_preamble_path.text() or self.settings.default_preamble_path(),
            "Preámbulo (*.pgs *.tex);;Todos (*.*)",
        )
        if path:
            self.txt_preamble_path.setText(path)

    def _browse_external_editor(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar editor externo",
            "",
            "Ejecutables (*.exe);;Todos (*.*)" if os.name == "nt" else "Todos (*.*)",
        )
        if path:
            self.txt_external_editor.setText(path)

    def _edit_preamble_external(self):
        """Open the preamble file with the configured external editor (or OS default)."""
        path = self.txt_preamble_path.text().strip()
        if not path:
            QMessageBox.information(self, "Preámbulo", "Indica primero la ruta del archivo.")
            return

        # Create file if it does not exist yet
        if not os.path.exists(path):
            try:
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(DEFAULT_PREAMBLE_BODY)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo crear el archivo:\n{e}")
                return

        editor = self.txt_external_editor.text().strip()
        if editor:
            try:
                # Support both a bare command name and a full path with optional args
                if os.path.isfile(editor) or shutil.which(editor):
                    QProcess.startDetached(editor, [path])
                else:
                    # Maybe "code -w" style
                    parts = editor.split()
                    QProcess.startDetached(parts[0], parts[1:] + [path])
                return
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Editor externo",
                    f"No se pudo lanzar el editor «{editor}»:\n{e}\n"
                    "Se abrirá con la aplicación predeterminada del sistema.",
                )

        # Fallback: OS default association
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(path)))

    def apply(self):
        """Write values back into the settings object."""
        self.settings.compilation_mode = self.cmb_mode.currentData()
        self.settings.compiler = self.cmb_compiler.currentText()
        self.settings.tex_bin_path = self.txt_tex_path.text().strip()
        self.settings.shell_escape = self.chk_shell.isChecked()
        self.settings.passes = self.spn_passes.value()
        self.settings.use_custom_preamble = self.chk_custom_preamble.isChecked()
        self.settings.preamble_path = self.txt_preamble_path.text().strip()
        self.settings.external_editor = self.txt_external_editor.text().strip()
        self.settings.editor_font_family = self.cmb_font.currentFont().family()
        self.settings.editor_font_size = self.spn_font_size.value()
        self.settings.live_preview = self.chk_live.isChecked()
        self.settings.preview_delay_ms = self.spn_delay.value()
        self.settings.dpi = self.spn_dpi.value()
        self.settings.transparent_bg = self.chk_transparent.isChecked()
        self.settings.theme = self.cmb_theme.currentText()
        self.settings.new_file_mode = self.cmb_new_file_mode.currentData()
