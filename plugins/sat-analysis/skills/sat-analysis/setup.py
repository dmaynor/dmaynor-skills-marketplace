"""Package the canonical rendering templates without a second editable copy."""

from pathlib import Path
import shutil

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildWithTemplates(build_py):
    """Copy canonical skill templates into the built wheel's package resources."""

    def run(self) -> None:
        super().run()
        source = Path(__file__).resolve().parent / "assets" / "templates"
        target = Path(self.build_lib) / "sat_engine" / "resources" / "templates"
        target.mkdir(parents=True, exist_ok=True)
        for name in ("decision_card.md", "analytic_trace.md", "analytic_trace_light.md", "tasking_view.md"):
            shutil.copy2(source / name, target / name)


setup(cmdclass={"build_py": BuildWithTemplates})
