from __future__ import annotations

from dataclasses import dataclass, field

from playcue.models import GameConfig


@dataclass(frozen=True)
class ConfigValidationIssue:
    """A single validation problem found when loading a config file.

    ``level`` is ``"error"`` when the file could not be loaded at all, or
    ``"warning"`` when the file loaded but contains a value that may cause
    problems at runtime (e.g. a missing game exe or a malformed link URL).

    ``file`` holds the bare filename only — never an absolute path — so that
    this object is safe to display to the user or include in logs.
    """

    level: str   # "warning" | "error"
    file: str    # filename only, never an absolute path
    field: str   # field name, or "" for file-level issues
    message: str


@dataclass
class ConfigLoadResult:
    """Result of loading all config files from a directory.

    ``configs`` contains every :class:`~playcue.models.GameConfig` that was
    loaded successfully.  ``issues`` records every problem encountered,
    including both hard errors (files that could not be loaded) and soft
    warnings (files that loaded but contain suspicious values).

    A file that produced an error is *not* included in ``configs``.
    A file that produced only warnings *is* included in ``configs``.
    """

    configs: list[GameConfig] = field(default_factory=list)
    issues: list[ConfigValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Return True if any issue has level ``"error"``."""
        return any(i.level == "error" for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        """Return True if any issue has level ``"warning"``."""
        return any(i.level == "warning" for i in self.issues)
