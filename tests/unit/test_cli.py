"""Tests para CLI de JARVIS."""

from typer.testing import CliRunner

from jarvis.cli import app

runner = CliRunner()


class TestCLI:
    def test_version(self):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_ask(self):
        result = runner.invoke(app, ["ask", "hola"])
        assert result.exit_code == 0
        # Con o sin LLM, JARVIS aparece en el output
        assert "JARVIS" in result.output

    def test_ask_with_project(self):
        result = runner.invoke(app, ["ask", "test", "--project", "integratepie"])
        assert result.exit_code == 0
        assert "IntegratePIE" in result.output or "JARVIS" in result.output

    def test_status(self):
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_events(self):
        # Primero crear un evento
        runner.invoke(app, ["ask", "for events test"])
        result = runner.invoke(app, ["events"])
        assert result.exit_code == 0

    def test_no_args_shows_help(self):
        result = runner.invoke(app, [])
        # Typer returns exit code 0 or 2 for no_args_is_help depending on version
        assert result.exit_code in (0, 2)
        assert "JARVIS" in result.output or "Usage" in result.output
