"""Main window for PyQPSTricks Studio."""

import json
import os
import shutil

import qdarktheme
from PySide6.QtCore import QTimer, Qt, QUrl
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.core.compiler import AsyncCompilerManager
from app.core.settings import AppSettings
from app.core.template import TemplateManager, DEFAULT_PREAMBLE, DEFAULT_PREAMBLE_BODY
from app.gui.editor import PSTricksCodeEditor
from app.gui.log_viewer import LaTeXLogViewer
from app.gui.preferences_dialog import PreferencesDialog
from app.gui.preview import PSTricksPreviewWidget
from app.gui.snippets_dock import SnippetsDockWidget

TAB_CODE = 0
TAB_PREAMBLE = 1

DEFAULT_SAMPLE_PSTRICKS = r"""\begin{pspicture}(-2.5,-2.5)(2.5,2.5)
  \psgrid[subgriddiv=0,gridcolor=lightgray,gridlabels=0pt]
  \pscircle[linewidth=1.5pt,linecolor=blue](0,0){2}
  \pscircle*[linecolor=cyan!40](0,0){1.2}
  \psline[linewidth=1.2pt,linecolor=red,arrowsize=4pt]{->}(-2,0)(2,0)
  \psline[linewidth=1.2pt,linecolor=red,arrowsize=4pt]{->}(0,-2)(0,2)
  \rput(0,0){\textbf{PSTricks}}
  \rput(1.6,1.6){$A$}
  \rput(-1.6,1.6){$B$}
\end{pspicture}
"""


class MainWindow(QMainWindow):
    """Main application window for PyQPSTricks Studio."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQPSTricks Studio — PSTricks / pdftricks Live Editor")
        self.resize(1280, 800)

        for icon_path in [
            "pyqpstricks.ico",
            "pyqpstricks.png",
            os.path.join("app", "resources", "pyqpstricks.png"),
        ]:
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
                break

        self.settings = AppSettings()
        self.template_manager = TemplateManager(mode=self.settings.compilation_mode)
        self.compiler_manager = AsyncCompilerManager(self)
        self.current_file_path = None
        self._preamble_path = self._resolve_preamble_path()

        self.live_timer = QTimer(self)
        self.live_timer.setSingleShot(True)
        self.live_timer.timeout.connect(self.compile_current_code)

        self._init_ui()
        self._init_menus()
        self._connect_signals()
        self._apply_theme()
        self._reload_preamble()

        # Initial sample + first compile
        if not self.editor.toPlainText().strip():
            if self.settings.new_file_mode == "sample":
                self.editor.setPlainText(DEFAULT_SAMPLE_PSTRICKS)
            else:
                self.editor.setPlainText("")
        QTimer.singleShot(400, self.compile_current_code)

    # ------------------------------------------------------------------
    # Paths / preamble helpers
    # ------------------------------------------------------------------
    def _resolve_preamble_path(self) -> str:
        # Prefer user-configured path when custom preamble is enabled
        if self.settings.use_custom_preamble and self.settings.preamble_path:
            return self.settings.preamble_path
        local = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "preamble.pgs",
        )
        if os.path.exists(local):
            return local
        return self.settings.preamble_path

    def _reload_preamble(self):
        path = self._preamble_path
        try:
            if self.settings.use_custom_preamble and path:
                if os.path.exists(path):
                    self.template_manager.load_preamble_file(path)
                else:
                    # Seed a default preamble file for the user
                    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(DEFAULT_PREAMBLE_BODY)
                    self.template_manager.load_preamble_file(path)
            else:
                # Built-in default template for the current compilation mode
                self.template_manager.set_mode(self.settings.compilation_mode)
        except Exception:
            self.template_manager.template = DEFAULT_PREAMBLE
        self._load_preamble_into_editor()

    def _load_preamble_into_editor(self):
        try:
            if os.path.exists(self._preamble_path):
                with open(self._preamble_path, "r", encoding="utf-8") as f:
                    self.preamble_editor.setPlainText(f.read())
        except Exception:
            pass

    def _save_preamble_from_editor(self):
        try:
            with open(self._preamble_path, "w", encoding="utf-8") as f:
                f.write(self.preamble_editor.toPlainText())
            self.template_manager.load_preamble_file(self._preamble_path)
            self.status_bar.showMessage(f"Preámbulo guardado: {self._preamble_path}", 4000)
            self.compile_current_code()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo guardar el preámbulo:\n{e}")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _init_ui(self):
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.left_splitter = QSplitter(Qt.Orientation.Vertical, self)

        self.editor_tabs = QTabWidget(self)
        self.editor_tabs.setDocumentMode(True)

        self.editor = PSTricksCodeEditor(self, is_dark=(self.settings.theme == "dark"))
        self.editor.set_editor_font(self.settings.editor_font_family, self.settings.editor_font_size)
        self.editor_tabs.addTab(self.editor, "📝 Código")

        self.preamble_editor = PSTricksCodeEditor(
            self, is_dark=(self.settings.theme == "dark")
        )
        self.preamble_editor.set_editor_font(self.settings.editor_font_family, self.settings.editor_font_size)
        self.preamble_editor.setPlaceholderText(
            "% Preámbulo LaTeX / PSTricks personalizado.\n"
            "% Puedes usar el marcador <PSTRICKS_CODE> o solo listar paquetes.\n"
            "% Guarda con el botón 📜 Preámbulo de la barra de herramientas."
        )
        self.editor_tabs.addTab(self.preamble_editor, "📜 Preámbulo")

        self.log_viewer = LaTeXLogViewer(self, is_dark=(self.settings.theme == "dark"))

        self.left_splitter.addWidget(self.editor_tabs)
        self.left_splitter.addWidget(self.log_viewer)
        self.left_splitter.setSizes([550, 180])

        self.preview = PSTricksPreviewWidget(
            self, is_dark=(self.settings.theme == "dark")
        )
        self.preview.dpi = self.settings.dpi
        self.preview.transparent_grid = self.settings.transparent_bg

        self.main_splitter.addWidget(self.left_splitter)
        self.main_splitter.addWidget(self.preview)
        self.main_splitter.setSizes([600, 680])
        self.setCentralWidget(self.main_splitter)

        # Snippets dock
        self.snippets_dock = SnippetsDockWidget(self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.snippets_dock)

        # Toolbar
        self.toolbar = QToolBar("Main Toolbar", self)
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        self.act_compile = QAction("▶ Compile (F5)", self)
        self.act_compile.setShortcut(QKeySequence("F5"))
        self.act_compile.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.act_compile.setToolTip("Compilar código PSTricks (F5 o Ctrl+Enter)")
        self.act_compile.triggered.connect(self.compile_current_code)
        self.addAction(self.act_compile)
        self.toolbar.addAction(self.act_compile)

        # Ctrl+Enter shortcuts
        self.sc_ctrl_enter1 = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.sc_ctrl_enter1.activated.connect(self.compile_current_code)
        self.sc_ctrl_enter2 = QShortcut(QKeySequence("Ctrl+Enter"), self)
        self.sc_ctrl_enter2.activated.connect(self.compile_current_code)

        self.toolbar.addSeparator()

        # Compiler combo
        self.cmb_compiler = QComboBox(self)
        self.cmb_compiler.addItems(["pdflatex", "lualatex", "xelatex", "tectonic", "latex"])
        idx = self.cmb_compiler.findText(self.settings.compiler)
        if idx >= 0:
            self.cmb_compiler.setCurrentIndex(idx)
        self.cmb_compiler.currentTextChanged.connect(self._on_compiler_changed)
        self.toolbar.addWidget(QLabel(" Motor: "))
        self.toolbar.addWidget(self.cmb_compiler)

        # Compilation mode combo
        self.cmb_mode = QComboBox(self)
        self.cmb_mode.addItem("auto-pst-pdf", "auto-pst-pdf")
        self.cmb_mode.addItem("pdftricks", "pdftricks")
        self.cmb_mode.addItem("Xe/Lua directo", "xelatex-direct")
        self.cmb_mode.addItem("Clásico (dvips)", "classic")
        idx = self.cmb_mode.findData(self.settings.compilation_mode)
        if idx >= 0:
            self.cmb_mode.setCurrentIndex(idx)
        self.cmb_mode.currentIndexChanged.connect(self._on_mode_changed)
        self.toolbar.addWidget(QLabel("  Modo: "))
        self.toolbar.addWidget(self.cmb_mode)

        self.toolbar.addSeparator()

        self.act_shell_escape = QAction("⚡ --shell-escape", self)
        self.act_shell_escape.setCheckable(True)
        self.act_shell_escape.setChecked(self.settings.shell_escape)
        self.act_shell_escape.setToolTip(
            "Necesario para auto-pst-pdf y pdftricks (pdflatex)"
        )
        self.act_shell_escape.triggered.connect(self._on_shell_escape_toggled)
        self.toolbar.addAction(self.act_shell_escape)

        self.act_preamble = QAction("📜 Preámbulo", self)
        self.act_preamble.setToolTip("Ir a la pestaña de preámbulo / guardar preámbulo")
        self.act_preamble.triggered.connect(self._on_preamble_button)
        self.toolbar.addAction(self.act_preamble)

        self.act_prefs = QAction("⚙️ Preferencias", self)
        self.act_prefs.triggered.connect(self.open_preferences)
        self.toolbar.addAction(self.act_prefs)

        self.toolbar.addSeparator()

        self.act_theme = QAction("🌗 Theme", self)
        self.act_theme.triggered.connect(self.toggle_theme)
        self.toolbar.addAction(self.act_theme)

        self.act_grid = QAction("🏁 Grid BG", self)
        self.act_grid.setCheckable(True)
        self.act_grid.setChecked(self.settings.transparent_bg)
        self.act_grid.triggered.connect(self._on_grid_toggled)
        self.toolbar.addAction(self.act_grid)

        self.toolbar.addSeparator()

        self.act_export_png = QAction("📷 Export PNG", self)
        self.act_export_png.triggered.connect(lambda: self.export_image("png"))
        self.toolbar.addAction(self.act_export_png)

        self.act_export_pdf = QAction("📄 Save PDF", self)
        self.act_export_pdf.triggered.connect(lambda: self.export_image("pdf"))
        self.toolbar.addAction(self.act_export_pdf)

        self.act_export_svg = QAction("🖼 Export SVG", self)
        self.act_export_svg.triggered.connect(lambda: self.export_image("svg"))
        self.toolbar.addAction(self.act_export_svg)

        # Status bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.lbl_compiler_status = QLabel("Listo", self)
        self.status_bar.addPermanentWidget(self.lbl_compiler_status)

        self._load_preamble_into_editor()

    def _init_menus(self):
        menubar = self.menuBar()

        menu_file = menubar.addMenu("&Archivo")
        act_new = QAction("&Nuevo", self)
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_new.setToolTip("Nuevo archivo (según la preferencia configurada)")
        act_new.triggered.connect(lambda: self.new_file())
        menu_file.addAction(act_new)

        act_new_empty = QAction("Nuevo (&vacío)", self)
        act_new_empty.setShortcut(QKeySequence("Ctrl+Shift+N"))
        act_new_empty.triggered.connect(lambda: self.new_file(empty=True))
        menu_file.addAction(act_new_empty)

        act_new_sample = QAction("Nuevo (con &ejemplo)", self)
        act_new_sample.triggered.connect(lambda: self.new_file(empty=False))
        menu_file.addAction(act_new_sample)

        act_open = QAction("&Abrir…", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self.open_file)
        menu_file.addAction(act_open)

        act_save = QAction("&Guardar", self)
        act_save.setShortcut(QKeySequence.StandardKey.Save)
        act_save.triggered.connect(self.save_file)
        menu_file.addAction(act_save)

        act_save_as = QAction("Guardar &como…", self)
        act_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        act_save_as.triggered.connect(self.save_file_as)
        menu_file.addAction(act_save_as)
        menu_file.addSeparator()

        act_export_png = QAction("Exportar PNG…", self)
        act_export_png.triggered.connect(lambda: self.export_image("png"))
        menu_file.addAction(act_export_png)

        act_export_pdf = QAction("Exportar PDF…", self)
        act_export_pdf.triggered.connect(lambda: self.export_image("pdf"))
        menu_file.addAction(act_export_pdf)

        act_export_svg = QAction("Exportar SVG…", self)
        act_export_svg.triggered.connect(lambda: self.export_image("svg"))
        menu_file.addAction(act_export_svg)
        menu_file.addSeparator()

        act_quit = QAction("&Salir", self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)
        menu_file.addAction(act_quit)

        menu_edit = menubar.addMenu("&Edición")
        act_prefs = QAction("&Preferencias…", self)
        act_prefs.triggered.connect(self.open_preferences)
        menu_edit.addAction(act_prefs)

        menu_view = menubar.addMenu("&Vista")
        menu_view.addAction(self.act_theme)
        menu_view.addAction(self.act_grid)
        menu_view.addAction(self.snippets_dock.toggleViewAction())

        menu_help = menubar.addMenu("A&yuda")
        act_about = QAction("&Acerca de…", self)
        act_about.triggered.connect(self.show_about)
        menu_help.addAction(act_about)

        act_docs = QAction("Documentación PSTricks…", self)
        act_docs.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://tug.org/PSTricks/main.cgi/")
            )
        )
        menu_help.addAction(act_docs)

    def _connect_signals(self):
        self.editor.textChanged.connect(self._on_code_changed)
        self.compiler_manager.started.connect(self._on_compile_started)
        self.compiler_manager.finished.connect(self._on_compile_finished)
        self.compiler_manager.log_output.connect(self.log_viewer.append_log)
        self.compiler_manager.errors_found.connect(self._on_errors_found)
        self.log_viewer.line_selected.connect(self.editor.goto_line)
        self.snippets_dock.snippet_selected.connect(self._insert_snippet)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _on_code_changed(self):
        if self.settings.live_preview:
            self.live_timer.start(self.settings.preview_delay_ms)

    def _on_compiler_changed(self, text: str):
        self.settings.compiler = text

    def _on_mode_changed(self, _index: int):
        mode = self.cmb_mode.currentData()
        self.settings.compilation_mode = mode
        self.template_manager.set_mode(mode)
        # Suggest matching engine
        if mode == "classic":
            self.cmb_compiler.setCurrentText("latex")
        elif mode == "xelatex-direct":
            if self.cmb_compiler.currentText() not in ("xelatex", "lualatex"):
                self.cmb_compiler.setCurrentText("xelatex")
        elif mode in ("auto-pst-pdf", "pdftricks"):
            if self.cmb_compiler.currentText() not in ("pdflatex", "lualatex"):
                self.cmb_compiler.setCurrentText("pdflatex")
            self.act_shell_escape.setChecked(True)
            self.settings.shell_escape = True
        self.compile_current_code()

    def _on_shell_escape_toggled(self, checked: bool):
        self.settings.shell_escape = checked

    def _on_preamble_button(self):
        if self.editor_tabs.currentIndex() == TAB_PREAMBLE:
            self._save_preamble_from_editor()
        else:
            self.editor_tabs.setCurrentIndex(TAB_PREAMBLE)

    def _on_grid_toggled(self, checked: bool):
        self.settings.transparent_bg = checked
        self.preview.transparent_grid = checked
        if self.preview.current_pdf_path:
            self.preview.load_pdf(self.preview.current_pdf_path)

    def _on_compile_started(self):
        self.lbl_compiler_status.setText("Compilando…")
        self.act_compile.setEnabled(False)

    def _on_compile_finished(self, pdf_path: str, success: bool):
        self.act_compile.setEnabled(True)
        if success and pdf_path and os.path.exists(pdf_path):
            self.preview.load_pdf(pdf_path)
            self.lbl_compiler_status.setText("✓ OK")
            self.status_bar.showMessage("Compilación correcta", 3000)
        else:
            self.lbl_compiler_status.setText("✗ Error")
            self.status_bar.showMessage("Error de compilación — revisa el log", 5000)

    def _on_errors_found(self, errors):
        self.log_viewer.set_errors(errors)

    def _insert_snippet(self, code: str):
        self.editor.insertPlainText(code)
        self.editor.setFocus()

    # ------------------------------------------------------------------
    # Compilation
    # ------------------------------------------------------------------
    def compile_current_code(self):
        user_code = self.editor.toPlainText()
        full_source = self.template_manager.wrap_code(user_code)
        mode = self.settings.compilation_mode
        compiler = self.settings.compiler
        # In classic mode force "latex" as the first stage (the worker handles the rest)
        if mode == "classic":
            compiler = "latex"

        self.log_viewer.clear()
        self.compiler_manager.compile(
            code=full_source,
            compiler_cmd=compiler,
            extra_flags="",
            tex_bin_path=self.settings.tex_bin_path,
            passes=self.settings.passes,
            shell_escape=self.settings.shell_escape,
            mode=mode,
        )

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------
    def new_file(self, empty: bool = None):
        if empty is True:
            content = ""
        elif empty is False:
            content = DEFAULT_SAMPLE_PSTRICKS
        else:
            content = "" if self.settings.new_file_mode == "empty" else DEFAULT_SAMPLE_PSTRICKS
        self.editor.setPlainText(content)
        self.current_file_path = None
        self.setWindowTitle("PyQPSTricks Studio — [Nuevo]")
        self.compile_current_code()

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir archivo PSTricks / TeX",
            "",
            "TeX / PSTricks (*.tex *.pstricks *.pst);;Archivos PSTricks (*.pst);;Archivos TeX (*.tex);;Todos los archivos (*.*)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            # If it is a full document, extract the body for the editor
            body = self.template_manager.extract_user_code(content)
            self.editor.setPlainText(body)
            self.current_file_path = path
            self.setWindowTitle(f"PyQPSTricks Studio — {os.path.basename(path)}")
            self.compile_current_code()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo abrir:\n{e}")

    def save_file(self):
        if self.current_file_path:
            self._write_file(self.current_file_path)
        else:
            self.save_file_as()

    def save_file_as(self):
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Guardar archivo",
            "",
            "Archivos PSTricks (*.pst);;Archivos TeX (*.tex);;Todos los archivos (*.*)",
        )
        if path:
            ext = os.path.splitext(path)[1]
            if not ext:
                if "*.pst" in selected_filter:
                    path += ".pst"
                else:
                    path += ".tex"
            self._write_file(path)
            self.current_file_path = path
            self.setWindowTitle(f"PyQPSTricks Studio — {os.path.basename(path)}")

    def _write_file(self, path: str):
        try:
            # Save the full wrapped document so it is self-contained
            full = self.template_manager.wrap_code(self.editor.toPlainText())
            with open(path, "w", encoding="utf-8") as f:
                f.write(full)
            self.status_bar.showMessage(f"Guardado: {path}", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo guardar:\n{e}")

    def export_image(self, fmt: str = "png"):
        if not self.preview.current_pdf_path or not os.path.exists(
            self.preview.current_pdf_path
        ):
            QMessageBox.information(
                self, "Exportar", "No hay un PDF compilado para exportar."
            )
            return
        fmt = (fmt or "png").lower()
        if fmt == "pdf":
            path, _ = QFileDialog.getSaveFileName(
                self, "Guardar PDF", "", "PDF (*.pdf)"
            )
            if path:
                if not path.lower().endswith(".pdf"):
                    path += ".pdf"
                shutil.copy2(self.preview.current_pdf_path, path)
                self.status_bar.showMessage(f"PDF guardado: {path}", 4000)
        elif fmt == "svg":
            path, _ = QFileDialog.getSaveFileName(
                self, "Exportar SVG", "", "SVG (*.svg)"
            )
            if path:
                if not path.lower().endswith(".svg"):
                    path += ".svg"
                ok = self.preview.export_svg(path)
                if ok:
                    self.status_bar.showMessage(f"SVG exportado: {path}", 4000)
                else:
                    QMessageBox.warning(
                        self,
                        "Error",
                        "No se pudo exportar el SVG.\n"
                        "Comprueba que PyMuPDF esté actualizado (pip install -U PyMuPDF).",
                    )
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, "Exportar PNG", "", "PNG (*.png)"
            )
            if path:
                if not path.lower().endswith(".png"):
                    path += ".png"
                ok = self.preview.export_png(path)
                if ok:
                    self.status_bar.showMessage(f"PNG exportado: {path}", 4000)
                else:
                    QMessageBox.warning(self, "Error", "No se pudo exportar el PNG.")


    def toggle_theme(self):
        new_theme = "light" if self.settings.theme == "dark" else "dark"
        self.settings.theme = new_theme
        self._apply_theme()

    def _apply_theme(self):
        is_dark = self.settings.theme == "dark"
        try:
            qdarktheme.setup_theme(self.settings.theme)
        except Exception:
            pass
        self.editor.set_theme(is_dark)
        self.preamble_editor.set_theme(is_dark)
        if hasattr(self.log_viewer, "set_theme"):
            self.log_viewer.set_theme(is_dark)
        if hasattr(self.preview, "set_theme"):
            self.preview.set_theme(is_dark)

    def open_preferences(self):
        dlg = PreferencesDialog(self.settings, self)
        if dlg.exec():
            dlg.apply()
            # Sync UI widgets
            idx = self.cmb_compiler.findText(self.settings.compiler)
            if idx >= 0:
                self.cmb_compiler.setCurrentIndex(idx)
            idx = self.cmb_mode.findData(self.settings.compilation_mode)
            if idx >= 0:
                self.cmb_mode.setCurrentIndex(idx)
            self.act_shell_escape.setChecked(self.settings.shell_escape)
            self.act_grid.setChecked(self.settings.transparent_bg)
            self.preview.dpi = self.settings.dpi
            self.preview.transparent_grid = self.settings.transparent_bg
            self.template_manager.set_mode(self.settings.compilation_mode)
            # Font
            self.editor.set_editor_font(
                self.settings.editor_font_family, self.settings.editor_font_size
            )
            self.preamble_editor.set_editor_font(
                self.settings.editor_font_family, self.settings.editor_font_size
            )
            # Preamble path may have changed
            self._preamble_path = self._resolve_preamble_path()
            self._reload_preamble()
            self._apply_theme()
            self.compile_current_code()

    def show_about(self):
        QMessageBox.about(
            self,
            "Acerca de PyQPSTricks Studio",
            "<h3>PyQPSTricks Studio 1.0</h3>"
            "<p>Editor y previsualizador en vivo para <b>PSTricks</b> y "
            "<b>pdftricks / auto-pst-pdf</b>.</p>"
            "<p>Fork de PyQTikz Studio, adaptado a gráficos PostScript.</p>"
            "<p>Soporta:</p>"
            "<ul>"
            "<li>auto-pst-pdf + pdflatex (-shell-escape)</li>"
            "<li>pdftricks</li>"
            "<li>XeLaTeX / LuaLaTeX nativo</li>"
            "<li>Pipeline clásico latex → dvips → ps2pdf</li>"
            "</ul>"
            "<p>Basado en PySide6 + PyMuPDF.</p>",
        )
