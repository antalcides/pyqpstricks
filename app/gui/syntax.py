"""Syntax highlighter for PSTricks / LaTeX code."""

from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtCore import QRegularExpression


class PSTricksHighlighter(QSyntaxHighlighter):
    """Highlights PSTricks commands, options, coordinates, comments, etc."""

    def __init__(self, document, is_dark: bool = True):
        super().__init__(document)
        self.is_dark = is_dark
        self._setup_formats()
        self._build_rules()

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        self._setup_formats()
        self._build_rules()
        self.rehighlight()

    def _setup_formats(self):
        if self.is_dark:
            c_keyword = QColor("#569CD6")
            c_command = QColor("#DCDCAA")
            c_option = QColor("#9CDCFE")
            c_coord = QColor("#CE9178")
            c_math = QColor("#B5CEA8")
            c_comment = QColor("#6A9955")
            c_node_name = QColor("#C586C0")
            c_number = QColor("#B5CEA8")
            c_env = QColor("#C586C0")
        else:
            c_keyword = QColor("#0000FF")
            c_command = QColor("#795E26")
            c_option = QColor("#001080")
            c_coord = QColor("#A31515")
            c_math = QColor("#098658")
            c_comment = QColor("#008000")
            c_node_name = QColor("#AF00DB")
            c_number = QColor("#098658")
            c_env = QColor("#AF00DB")

        self.fmt_keyword = QTextCharFormat()
        self.fmt_keyword.setForeground(c_keyword)
        self.fmt_keyword.setFontWeight(QFont.Bold)

        self.fmt_command = QTextCharFormat()
        self.fmt_command.setForeground(c_command)
        self.fmt_command.setFontWeight(QFont.Bold)

        self.fmt_option = QTextCharFormat()
        self.fmt_option.setForeground(c_option)

        self.fmt_coord = QTextCharFormat()
        self.fmt_coord.setForeground(c_coord)
        self.fmt_coord.setFontWeight(QFont.Medium)

        self.fmt_math = QTextCharFormat()
        self.fmt_math.setForeground(c_math)

        self.fmt_comment = QTextCharFormat()
        self.fmt_comment.setForeground(c_comment)
        self.fmt_comment.setFontItalic(True)

        self.fmt_node_name = QTextCharFormat()
        self.fmt_node_name.setForeground(c_node_name)

        self.fmt_number = QTextCharFormat()
        self.fmt_number.setForeground(c_number)

        self.fmt_env = QTextCharFormat()
        self.fmt_env.setForeground(c_env)
        self.fmt_env.setFontWeight(QFont.Bold)

    def _build_rules(self):
        self.rules = []

        # Core PSTricks drawing commands
        pstricks_cmds = [
            r"\\psline", r"\\pscurve", r"\\psecurve", r"\\psccurve",
            r"\\pscircle", r"\\psellipse", r"\\psframe", r"\\psdiamond",
            r"\\pstriangle", r"\\pspolygon", r"\\pswedge", r"\\psarc",
            r"\\psellipticarc", r"\\psbezier", r"\\psdot", r"\\psdots",
            r"\\psgrid", r"\\psaxes", r"\\psplot", r"\\parametricplot",
            r"\\psclip", r"\\endpsclip", r"\\pscustom", r"\\psset",
            r"\\rput", r"\\uput", r"\\cput", r"\\rput*", r"\\uput*",
            r"\\psnode", r"\\pnode", r"\\Rnode", r"\\rnode", r"\\ncline",
            r"\\ncarc", r"\\nccurve", r"\\ncbar", r"\\ncdiag", r"\\ncdiagg",
            r"\\ncbarr", r"\\ncangles", r"\\pcbar", r"\\pcline",
            r"\\naput", r"\\nbput", r"\\ncput", r"\\nlput",
            r"\\pstree", r"\\psTree", r"\\TC", r"\\TF", r"\\Tcircle",
            r"\\Toval", r"\\Tr", r"\\Tdia", r"\\Ttri",
            r"\\multido", r"\\multips", r"\\psforeach",
            r"\\SpecialCoor", r"\\degrees", r"\\radians",
            r"\\newpsobject", r"\\newpsstyle", r"\\psframebox",
            r"\\pscirclebox", r"\\psdblframebox", r"\\psshadowbox",
            r"\\psdiabox", r"\\pstribox", r"\\psovalbox",
        ]
        cmd_pattern = r"(" + "|".join(pstricks_cmds) + r")\b"
        self.rules.append((QRegularExpression(cmd_pattern), self.fmt_keyword))

        # Environments
        env_pattern = r"\\(begin|end)\{(pspicture\*?|pdfpic|psinputs|psclip|pscustom)\}"
        self.rules.append((QRegularExpression(env_pattern), self.fmt_env))

        # General LaTeX / package commands
        self.rules.append((QRegularExpression(r"\\[a-zA-Z@]+"), self.fmt_command))

        # Options in brackets
        self.rules.append((QRegularExpression(r"\[[^\]]*\]"), self.fmt_option))

        # Coordinates / nodes in parentheses
        self.rules.append((QRegularExpression(r"\([^)]+\)"), self.fmt_coord))

        # Math mode
        self.rules.append((QRegularExpression(r"\$[^$]*\$"), self.fmt_math))

        # Numbers
        self.rules.append((QRegularExpression(r"\b\d+(\.\d+)?\b"), self.fmt_number))

        # Comments
        self.rules.append((QRegularExpression(r"%.*"), self.fmt_comment))

    def highlightBlock(self, text: str):
        for pattern, fmt in self.rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
