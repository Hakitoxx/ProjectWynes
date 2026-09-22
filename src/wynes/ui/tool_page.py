"""Generic page for a single diagnostic tool.

Builds the input form from the tool's :class:`InputField` metadata
(text, checkbox, choice, number, file), validates input, executes the
tool on a worker thread (UI stays responsive) and renders the result
through :class:`ResultView`. Every tool page therefore shares one
consistent layout: header -> notice (optional) -> input card -> status
row -> results.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from wynes.core.i18n import tr
from wynes.core.process import guard_exceptions
from wynes.core.tool_base import Availability, ToolResult, ToolStatus
from wynes.core.tool_manager import ToolEntry, ToolManager
from wynes.ui.outputs import ResultView
from wynes.ui.widgets import card, header_label, horizontal_rule, muted_label, status_dot


class _WorkerSignals(QObject):
    finished = Signal(object)  # ToolResult


class _ToolWorker(QRunnable):
    """Runs one tool off the GUI thread, guarded against all failures."""

    def __init__(self, tool, inputs: dict) -> None:
        super().__init__()
        self.signals = _WorkerSignals()
        self._tool = tool
        self._inputs = inputs

    def run(self) -> None:
        result = guard_exceptions(self._tool.run, **self._inputs)
        try:
            self.signals.finished.emit(result)
        except RuntimeError:
            # The page (and its signal source) was deleted while the tool was
            # still running — e.g. a language rebuild. The result is obsolete
            # and intentionally dropped.
            pass


class ToolPage(QWidget):
    def __init__(self, entry: ToolEntry, manager: ToolManager, parent=None) -> None:
        super().__init__(parent)
        self._entry = entry
        self._manager = manager
        self._tool = entry.tool
        self._widgets: dict = {}
        self._active = False

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(10)

        root.addWidget(header_label(self._tool.name))
        root.addWidget(muted_label(self._tool.description))
        root.addWidget(muted_label(f"{tr(self._tool.category_key)} · v{self._tool.version}"))
        root.addWidget(horizontal_rule())

        if self._tool.notice_key:
            root.addWidget(self._notice_card(tr(self._tool.notice_key)))

        if entry.availability is Availability.MISSING:
            root.addWidget(self._missing_card(entry.detail))
        else:
            self._build_form(root)
            root.addWidget(horizontal_rule())
            results_header = QLabel(tr("result.title"))
            results_header.setProperty("role", "h2")
            root.addWidget(results_header)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            self.results = ResultView()
            scroll.setWidget(self.results)
            root.addWidget(scroll, 1)

            if self._tool.auto_run:
                QTimer.singleShot(60, self._on_run)

    # ------------------------------------------------------------- layout
    def _notice_card(self, text: str) -> QWidget:
        box = card()
        box.setProperty("notice", True)
        layout = QHBoxLayout(box)
        layout.setContentsMargins(14, 10, 14, 10)
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addWidget(label)
        return box

    def _missing_card(self, detail: str) -> QWidget:
        box = card()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)
        title = QLabel(tr("tool.missing.title"))
        title.setProperty("role", "h2")
        layout.addWidget(title)
        layout.addWidget(muted_label(detail))
        hint = muted_label(tr("tool.missing.hint"))
        layout.addWidget(hint)
        return box

    def _build_form(self, root: QVBoxLayout) -> None:
        box = card()
        grid = QGridLayout(box)
        grid.setContentsMargins(18, 16, 18, 16)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        row = 0
        for field in self._tool.input_fields:
            label = QLabel(tr(field.label_key))
            label.setProperty("role", "muted")
            grid.addWidget(label, row, 0, Qt.AlignmentFlag.AlignTop)
            grid.addWidget(self._build_input(field), row, 1)
            row += 1
        grid.setColumnStretch(1, 1)

        button_row = QHBoxLayout()
        self.run_button = QPushButton(tr("action.run"))
        self.run_button.setProperty("primary", True)
        self.run_button.setFixedWidth(140)
        self.run_button.clicked.connect(self._on_run)
        button_row.addWidget(self.run_button)

        button_row.addSpacing(14)
        self._status_dot = status_dot("planned")
        button_row.addWidget(self._status_dot)
        self._status_label = QLabel(tr("state.ready"))
        self._status_label.setProperty("role", "muted")
        button_row.addWidget(self._status_label)
        button_row.addStretch(1)

        grid.addLayout(button_row, row, 1)
        root.addWidget(box)

    def _build_input(self, field) -> QWidget:
        if field.kind == "checkbox":
            widget = QCheckBox()
            widget.setChecked(bool(field.default))
        elif field.kind == "choice":
            widget = QComboBox()
            for value, label_key in field.options:
                widget.addItem(tr(label_key), userData=value)
            index = widget.findData(field.default)
            if index >= 0:
                widget.setCurrentIndex(index)
        elif field.kind == "number":
            widget = QSpinBox()
            widget.setRange(int(field.minimum), int(field.maximum))
            try:
                widget.setValue(int(field.default))
            except (TypeError, ValueError):
                pass
        elif field.kind == "file":
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)
            path_edit = QLineEdit()
            path_edit.setObjectName("edit")
            browse = QPushButton(tr("action.browse"))
            browse.clicked.connect(lambda _checked=False, edit=path_edit: self._browse(edit))
            layout.addWidget(path_edit, 1)
            layout.addWidget(browse)
            self._widgets[field.key] = path_edit
            return container
        else:
            widget = QLineEdit()
            if field.placeholder_key:
                widget.setPlaceholderText(tr(field.placeholder_key))
            widget.setClearButtonEnabled(True)
            widget.returnPressed.connect(self._on_run)
        self._widgets[field.key] = widget
        return widget

    def _browse(self, edit: QLineEdit) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(self, tr("action.browse"))
        if path:
            edit.setText(path)

    def _set_status(self, kind: str, text_key: str) -> None:
        self._status_dot.setProperty("dot", kind)
        # re-polish so the QSS change applies
        self._status_dot.style().unpolish(self._status_dot)
        self._status_dot.style().polish(self._status_dot)
        self._status_label.setText(tr(text_key))

    # ------------------------------------------------------------ execution
    def _collect_inputs(self) -> dict:
        values = {}
        for key, widget in self._widgets.items():
            if isinstance(widget, QCheckBox):
                values[key] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                values[key] = widget.currentData()
            elif isinstance(widget, QSpinBox):
                values[key] = widget.value()
            else:
                values[key] = widget.text().strip()
        return values

    def _on_run(self) -> None:
        if self._active:
            return  # one execution at a time; no overlapping worker spam

        unavailable = self._manager.ensure_ready(self._tool)
        if unavailable:
            self.results.show_result(ToolResult(
                status=ToolStatus.ERROR,
                summary=tr("tool.missing.title"),
                error=unavailable,
            ))
            return

        inputs = self._collect_inputs()
        errors = self._tool.validate(**inputs)
        if errors:
            first = errors[0]
            self.results.show_result(ToolResult(
                status=ToolStatus.ERROR,
                summary=tr("validation.invalid_title"),
                error=first.message,
            ))
            widget = self._widgets.get(first.field or "")
            if isinstance(widget, (QLineEdit, QSpinBox, QComboBox)):
                widget.setFocus()
            return

        self._active = True
        self.run_button.setEnabled(False)
        self.run_button.setText(tr("action.running"))
        self._set_status("warn", "state.running")
        self.results.show_idle()

        worker = _ToolWorker(self._tool, inputs)
        worker.signals.finished.connect(self._on_finished)
        self._worker = worker  # keep the Python object alive while it runs
        QThreadPool.globalInstance().start(worker)

    def _on_finished(self, result: ToolResult) -> None:
        self._active = False
        self.run_button.setEnabled(True)
        self.run_button.setText(tr("action.run"))
        if result.status is ToolStatus.SUCCESS:
            self._set_status("ok", "state.success")
        elif result.status is ToolStatus.TIMEOUT:
            self._set_status("warn", "state.timeout")
        else:
            self._set_status("error", "state.error")
        self.results.show_result(result)
