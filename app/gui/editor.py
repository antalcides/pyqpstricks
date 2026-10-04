import os
from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QTextCursor, QTextFormat, QKeySequence, QShortcut
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from app.gui.syntax import PSTricksHighlighter


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.lineNumberAreaPaintEvent(event)


class PSTricksCodeEditor(QPlainTextEdit):
    """Custom code editor with line numbers, syntax highlighting, and shortcuts."""
    
    text_changed_debounced = Signal()

    def __init__(self, parent=None, is_dark: bool = True):
        super().__init__(parent)
        self.is_dark = is_dark
        self.line_number_area = LineNumberArea(self)

        # Monospace font (can be changed via set_editor_font)
        family = "Consolas" if os.name == "nt" else "Monospace"
        font = QFont(family, 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        # Tab stop = 4 spaces
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(' ') * 4)

        # Syntax highlighter
        self.highlighter = PSTricksHighlighter(self.document(), is_dark=self.is_dark)

        # Signals
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.update_line_number_area_width(0)
        self.highlight_current_line()

        # Comment shortcut: Ctrl+/
        self.shortcut_comment = QShortcut(QKeySequence("Ctrl+/"), self)
        self.shortcut_comment.activated.connect(self.toggle_comment)

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        self.highlighter.set_theme(is_dark)
        self.highlight_current_line()
        self.line_number_area.update()

    def line_number_area_width(self):
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = 15 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.line_number_area)
        bg_color = QColor("#1E1E1E") if self.is_dark else QColor("#F3F3F3")
        fg_color = QColor("#858585") if self.is_dark else QColor("#717171")
        
        painter.fillRect(event.rect(), bg_color)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(fg_color)
                painter.drawText(0, top, self.line_number_area.width() - 5, self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor("#2A2D2E") if self.is_dark else QColor("#E8E8E8")
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

        self.setExtraSelections(extra_selections)

    def toggle_comment(self):
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        doc = self.document()
        start_block = doc.findBlock(start)
        end_block = doc.findBlock(end)

        cursor.beginEditBlock()
        block = start_block
        while block.isValid():
            text = block.text()
            b_cursor = QTextCursor(block)
            if text.lstrip().startswith("%"):
                # Remove first %
                idx = text.find("%")
                b_cursor.setPosition(block.position() + idx)
                b_cursor.deleteChar()
            else:
                # Add % at beginning of text
                b_cursor.setPosition(block.position())
                b_cursor.insertText("% ")
            
            if block == end_block:
                break
            block = block.next()

        cursor.endEditBlock()


    def set_editor_font(self, family: str, size: int):
        """Apply a custom font family and point size to the editor."""
        font = QFont(family or ("Consolas" if os.name == "nt" else "Monospace"), max(6, int(size)))
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.update_line_number_area_width(0)
        self.line_number_area.update()

    def goto_line(self, line_number: int):
        doc = self.document()
        block = doc.findBlockByNumber(max(0, line_number - 1))
        if block.isValid():
            cursor = QTextCursor(block)
            self.setTextCursor(cursor)
            self.centerCursor()
            self.setFocus()
