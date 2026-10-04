"""Template manager for PSTricks / pdftricks / auto-pst-pdf documents."""

import re

# ---------------------------------------------------------------------------
# Default templates
# ---------------------------------------------------------------------------

# Recommended modern path: auto-pst-pdf + pdflatex -shell-escape
DEFAULT_PREAMBLE = r"""\documentclass[border=5pt]{standalone}
\usepackage[utf8]{inputenc}
\usepackage{amsmath,amssymb}
\usepackage{pstricks,pst-plot,pst-node,pst-tree,pstricks-add}
\usepackage{auto-pst-pdf}

\begin{document}
<PSTRICKS_CODE>
\end{document}
"""

DEFAULT_PREAMBLE_BODY = r"""\usepackage[utf8]{inputenc}
\usepackage{amsmath,amssymb}
\usepackage{pstricks,pst-plot,pst-node,pst-tree,pstricks-add}
\usepackage{auto-pst-pdf}
"""

# pdftricks style (user must wrap code in \begin{pdfpic}...\end{pdfpic})
PDFTRICKS_PREAMBLE = r"""\documentclass[border=5pt]{standalone}
\usepackage[utf8]{inputenc}
\usepackage{amsmath,amssymb}
\usepackage{pdftricks}
\begin{psinputs}
  \usepackage{pstricks,pst-plot,pst-node,pst-tree,pstricks-add}
\end{psinputs}

\begin{document}
\begin{pdfpic}
<PSTRICKS_CODE>
\end{pdfpic}
\end{document}
"""

# XeLaTeX / LuaLaTeX direct (no extra package needed for most diagrams)
XELATEX_PREAMBLE = r"""\documentclass[border=5pt]{standalone}
\usepackage{amsmath,amssymb}
\usepackage{pstricks,pst-plot,pst-node,pst-tree,pstricks-add}

\begin{document}
<PSTRICKS_CODE>
\end{document}
"""

# Classic DVI → PS → PDF pipeline
CLASSIC_PREAMBLE = r"""\documentclass[border=5pt]{standalone}
\usepackage[utf8]{inputenc}
\usepackage{amsmath,amssymb}
\usepackage{pstricks,pst-plot,pst-node,pst-tree,pstricks-add}

\begin{document}
<PSTRICKS_CODE>
\end{document}
"""

BASIC_PREAMBLE = r"""\documentclass[border=2pt]{standalone}
\usepackage{pstricks}

\begin{document}
<PSTRICKS_CODE>
\end{document}
"""


class TemplateManager:
    """Manages PSTricks LaTeX templates and document wrapping."""

    PLACEHOLDER = "<PSTRICKS_CODE>"

    def __init__(self, template_str=None, mode: str = "auto-pst-pdf"):
        self.mode = mode
        self.template = template_str or self._default_for_mode(mode)

    def _default_for_mode(self, mode: str) -> str:
        mapping = {
            "auto-pst-pdf": DEFAULT_PREAMBLE,
            "pdftricks": PDFTRICKS_PREAMBLE,
            "xelatex-direct": XELATEX_PREAMBLE,
            "classic": CLASSIC_PREAMBLE,
        }
        return mapping.get(mode, DEFAULT_PREAMBLE)

    def set_mode(self, mode: str) -> None:
        """Switch the default template according to the compilation mode.
        Only overrides the template if the user has not loaded a custom one
        that already contains the placeholder.
        """
        self.mode = mode
        # Keep current template if it looks custom; otherwise refresh
        if self.PLACEHOLDER not in self.template or "pstricks" not in self.template.lower():
            self.template = self._default_for_mode(mode)

    def load_preamble_file(self, path: str) -> None:
        """Loads a custom preamble from a `.pgs` file.

        Two authoring styles are supported:
        - Full template containing the placeholder <PSTRICKS_CODE>.
        - Preamble-only (packages only) → automatically wrapped.
        """
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        if self.PLACEHOLDER in content or "<TIKZ_CODE>" in content:
            # Accept legacy TikZ placeholder too
            self.template = content.replace("<TIKZ_CODE>", self.PLACEHOLDER)
        else:
            # Wrap preamble-only content
            if self.mode == "pdftricks":
                self.template = (
                    "\\documentclass[border=5pt]{standalone}\n"
                    "\\usepackage{pdftricks}\n"
                    "\\begin{psinputs}\n"
                    f"{content.rstrip()}\n"
                    "\\end{psinputs}\n\n"
                    "\\begin{document}\n"
                    "\\begin{pdfpic}\n"
                    f"{self.PLACEHOLDER}\n"
                    "\\end{pdfpic}\n"
                    "\\end{document}\n"
                )
            else:
                self.template = (
                    "\\documentclass[border=5pt]{standalone}\n"
                    f"{content.rstrip()}\n\n"
                    "\\begin{document}\n"
                    f"{self.PLACEHOLDER}\n"
                    "\\end{document}\n"
                )

    def wrap_code(self, code: str) -> str:
        """Insert user PSTricks code into the active template."""
        code = code.strip()
        if not code:
            code = "% empty"

        # If the user already wrote a full document, return it as-is
        if re.search(r"\\documentclass", code) and re.search(r"\\begin\{document\}", code):
            return code

        # If the user already has a pspicture / pspicture* environment,
        # just drop it into the template.
        return self.template.replace(self.PLACEHOLDER, code)

    def extract_user_code(self, full_source: str) -> str:
        """Best-effort extraction of the diagram body from a full document."""
        # Try to pull content between \begin{document} ... \end{document}
        m = re.search(
            r"\\begin\{document\}(.*)\\end\{document\}",
            full_source,
            re.DOTALL,
        )
        if m:
            body = m.group(1).strip()
            # Strip pdfpic wrapper if present
            m2 = re.search(r"\\begin\{pdfpic\}(.*)\\end\{pdfpic\}", body, re.DOTALL)
            if m2:
                return m2.group(1).strip()
            return body
        return full_source
