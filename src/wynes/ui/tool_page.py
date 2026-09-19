"""Generic page for a single diagnostic tool.

Builds the input form from the tool's :class:`InputField` metadata,
validates input, executes the tool on a worker thread (UI stays
responsive) and renders the result through :class:`ResultView`.

Planned tools reuse the same page but show an explanatory placeholder
instead of an input form — no dead buttons, no fake functionality.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from wynes.core.process import guard_exceptions
from wynes.core.tool_base import Tool, ToolResult, ToolStatus
from wynes.core.tool_manager import ToolEntry
from wynes.ui.outputs import ResultView
from wynes.ui.widgets import card, header_label, horizontal_rule, muted_label


class _WorkerSignals(QObject):
    finished = Signal(object)  # ToolResult


class _ToolWorker(QRunnable):
    """Runs one tool off the GUI thread, guarded against all failures."""

    def __init__(self, tool: Tool, inputs: dict) -> None:
        super().__init__()
        self.signals = _WorkerSignals()
        self._tool = tool
        self._inputs = inputs

    def run(self) -> None:
        self.signals.finished.emit(guard_exceptions(self._tool.run, **self._inputs))


class ToolPage(QWidget):
    def __init__(self, entry: ToolEntry, parent=None) -> None:
        super().__init__(parent)
        self._entry = entry
        self._tool = entry.tool
        self._widgets: dict = {}
        self._active = False

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(10)

        root.addWidget(header_label(self._tool.name))
        if self._tool.description:
            root.addWidget(muted_label(self._tool.description))
        meta = self._meta_line()
        if meta:
            root.addWidget(meta)
        root.addWidget(horizontal_rule())

        if entry.planned:
            self._build_planned(root)
        else:
            self._build_form(root)
            root.addWidget(horizontal_rule())
            results_header = QLabel("Result")
            results_header.setProperty("role", "h2")
            root.addWidget(results_header)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            self.results = ResultView()
            scroll.setWidget(self.results)
            root.addWidget(scroll, 1)

    # ------------------------------------------------------------- layout
    def _meta_line(self):
        parts = [part for part in (self._tool.category, self._tool.version) if part]
        if not parts:
            return None
        return muted_label("  ·  ".join(parts), wrap=False)

    def _build_planned(self, root: QVBoxLayout) -> None:
        box = card()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)
        title = QLabel("This tool is planned for an upcoming milestone.")
        title.setProperty("role", "h2")
        layout.addWidget(title)
        note = getattr(self._tool, "planned_note", "") or self._tool.description
        layout.addWidget(muted_label(note))
        status = muted_label(f"Status: {self._entry.detail}")
        layout.addWidget(status)
        root.addWidget(box)
        root.addStretch(1)

    def _build_form(self, root: QVBoxLayout) -> None:
        box = card()
        grid = QGridLayout(box)
        grid.setContentsMargins(18, 16, 18, 16)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        for row, field in enumerate(self._tool.input_fields):
            label = QLabel(field.label)
            label.setProperty("role", "muted")
            grid.addWidget(label, row, 0)
            if field.kind == "checkbox":
                widget = QCheckBox()
                widget.setChecked(bool(field.default))
            else:
                widget = QLineEdit()
                widget.setPlaceholderText(field.placeholder)
                widget.setClearButtonEnabled(True)
                widget.returnPressed.connect(self._on_run)
            self._widgets[field.key] = widget
            grid.addWidget(widget, row, 1)
        grid.setColumnStretch(1, 1)

        button_row = QHBoxLayout()
        self.run_button = QPushButton("Run")
        self.run_button.setProperty("primary", True)
        self.run_button.setFixedWidth(120)
        self.run_button.clicked.connect(self._on_run)
        button_row.addWidget(self.run_button)
        button_row.addStretch(1)
        grid.addLayout(button_row, len(self._tool.input_fields), 1)

        root.addWidget(box)

    # ------------------------------------------------------------ execution
    def _collect_inputs(self) -> dict:
        values = {}
        for key, widget in self._widgets.items():
            if isinstance(widget, QCheckBox):
                values[key] = widget.isChecked()
            else:
                values[key] = widget.text().strip()
        return values

    def _on_run(self) -> None:
        if self._active:
            return  # one execution at a time; no overlapping worker spam

        inputs = self._collect_inputs()
        errors = self._tool.validate(**inputs)
        if errors:
            first = errors[0]
            self.results.show_result(
                ToolResult(
                    status=ToolStatus.ERROR,
                    summary="Invalid input",
                    error=first.message,
                )
            )
            widget = self._widgets.get(first.field or "")
            if widget is not None and hasattr(widget, "setFocus"):
                widget.setFocus()
            return

        self._active = True
        self.run_button.setEnabled(False)
        self.run_button.setText("Running…")
        self.results.show_idle("Running — please wait…")

        worker = _ToolWorker(self._tool, inputs)
        worker.signals.finished.connect(self._on_finished)
        QThreadPool.globalInstance().start(worker)

    def _on_finished(self, result: ToolResult) -> None:
        self._active = False
        self.run_button.setEnabled(True)
        self.run_button.setText("Run")
        self.results.show_result(result)
