"""GherkinAgent — generador de escenarios BDD/Gherkin profesionales."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from jarvis.agents.base import AgentRequest, AgentResult, AgentSpec, BaseAgent


@dataclass
class GherkinScenario:
    """Un escenario Gherkin individual."""

    name: str
    given: list[str] = field(default_factory=list)
    when: list[str] = field(default_factory=list)
    then: list[str] = field(default_factory=list)
    examples: list[dict[str, str]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = []
        if self.tags:
            lines.append("  " + " ".join(f"@{t}" for t in self.tags))
        lines.append(f"  Scenario: {self.name}")
        for step in self.given:
            lines.append(f"    Given {step}")
        for step in self.when:
            lines.append(f"    When {step}")
        for step in self.then:
            lines.append(f"    Then {step}")
        if self.examples:
            lines.append("    Examples:")
            keys = list(self.examples[0].keys())
            lines.append("      | " + " | ".join(keys) + " |")
            for ex in self.examples:
                lines.append("      | " + " | ".join(ex.get(k, "") for k in keys) + " |")
        return "\n".join(lines)


@dataclass
class GherkinFeature:
    """Feature completa con escenarios."""

    name: str
    description: str = ""
    scenarios: list[GherkinScenario] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = []
        if self.tags:
            lines.append(" ".join(f"@{t}" for t in self.tags))
        lines.append(f"Feature: {self.name}")
        if self.description:
            for desc_line in self.description.strip().splitlines():
                lines.append(f"  {desc_line.strip()}")
        lines.append("")
        for scenario in self.scenarios:
            lines.append(scenario.render())
            lines.append("")
        return "\n".join(lines)


class GherkinAgent(BaseAgent):
    """Agente generador de escenarios BDD/Gherkin."""

    def spec(self) -> AgentSpec:
        return AgentSpec(
            id="qa.gherkin",
            name="Gherkin Generator",
            description="Genera escenarios BDD/Gherkin a partir de requisitos o historias de usuario",
            skills=["gherkin", "bdd", "scenario"],
            supported_projects=[],
        )

    def execute(self, request: AgentRequest) -> AgentResult:
        start = time.monotonic()
        try:
            question = request.payload.get("question", request.intent)
            action = request.payload.get("action", self._detect_action(question))

            if action == "help":
                return self._show_help(start)

            feature = self._generate_feature(question)
            rendered = feature.render()

            return AgentResult(
                success=True,
                content=f"```gherkin\n{rendered}\n```",
                data={
                    "feature": feature.name,
                    "scenarios_count": len(feature.scenarios),
                    "tags": feature.tags,
                },
                duration_ms=int((time.monotonic() - start) * 1000),
            )

        except Exception as e:
            return AgentResult(
                success=False,
                error=str(e),
                duration_ms=int((time.monotonic() - start) * 1000),
            )

    def _detect_action(self, text: str) -> str:
        if re.search(r"(ayuda|help|cómo)", text, re.I):
            return "help"
        return "generate"

    def _generate_feature(self, text: str) -> GherkinFeature:
        """Generar feature Gherkin a partir de texto libre."""
        feature_name = self._extract_feature_name(text)
        tags = self._extract_tags(text)
        scenarios = []

        # Escenario happy path
        scenarios.append(self._generate_happy_path(text, feature_name))

        # Escenarios de validación
        validations = self._detect_validations(text)
        for val in validations:
            scenarios.append(self._generate_validation_scenario(val, feature_name))

        # Escenario de error / edge case
        scenarios.append(self._generate_error_scenario(text, feature_name))

        # Escenario de seguridad si aplica
        if self._needs_security_scenario(text):
            scenarios.append(self._generate_security_scenario(text, feature_name))

        return GherkinFeature(
            name=feature_name,
            description=f"Como usuario, quiero {feature_name.lower()}\n  para obtener el resultado esperado",
            scenarios=scenarios,
            tags=tags,
        )

    def _extract_feature_name(self, text: str) -> str:
        """Extraer nombre de la feature del texto."""
        # Buscar patrones comunes
        patterns = [
            r"(?:feature|funcionalidad|historia)[:.]?\s*(.+?)(?:\.|$)",
            r"(?:generar?|crear?|escenarios?\s+(?:para|de))\s+(.+?)(?:\.|$)",
            r"(?:probar|testing?\s+(?:de|para|el|la))\s+(.+?)(?:\.|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                name = match.group(1).strip()
                if len(name) > 5:
                    return name.capitalize()

        # Fallback: usar primeras palabras significativas
        words = [w for w in text.split() if len(w) > 3][:6]
        return " ".join(words).capitalize() if words else "Feature bajo prueba"

    def _extract_tags(self, text: str) -> list[str]:
        tags = []
        text_lower = text.lower()
        if any(w in text_lower for w in ("login", "auth", "sesión", "contraseña", "password")):
            tags.append("auth")
        if any(w in text_lower for w in ("api", "endpoint", "rest", "request")):
            tags.append("api")
        if any(w in text_lower for w in ("ui", "pantalla", "formulario", "botón", "interfaz")):
            tags.append("ui")
        if any(w in text_lower for w in ("pago", "payment", "checkout", "carrito", "cart")):
            tags.append("payment")
        if any(w in text_lower for w in ("admin", "backoffice", "dashboard")):
            tags.append("admin")
        tags.append("automated")
        return tags

    def _generate_happy_path(self, text: str, feature_name: str) -> GherkinScenario:
        context = self._detect_context(text)
        action = self._detect_main_action(text)
        return GherkinScenario(
            name=f"{feature_name} - flujo exitoso",
            given=[
                f"el usuario está en {context}",
                "el usuario tiene los permisos necesarios",
            ],
            when=[
                f"el usuario {action}",
                "el sistema procesa la solicitud",
            ],
            then=[
                "el sistema responde con código 200",
                "el resultado es el esperado",
                "el sistema registra la acción en el log",
            ],
            tags=["happy_path", "smoke"],
        )

    def _detect_validations(self, text: str) -> list[str]:
        validations = []
        text_lower = text.lower()
        if any(w in text_lower for w in ("campo", "formulario", "input", "required", "obligatorio")):
            validations.append("campos_obligatorios")
        if any(w in text_lower for w in ("formato", "email", "teléfono", "rut", "fecha")):
            validations.append("formato_datos")
        if any(w in text_lower for w in ("límite", "máximo", "mínimo", "rango", "longitud")):
            validations.append("limites")
        if not validations:
            validations.append("datos_invalidos")
        return validations

    def _generate_validation_scenario(self, validation: str, feature_name: str) -> GherkinScenario:
        scenarios_map = {
            "campos_obligatorios": GherkinScenario(
                name=f"{feature_name} - campos obligatorios vacíos",
                given=["el usuario está en el formulario", "existen campos obligatorios"],
                when=["el usuario deja campos obligatorios vacíos", "el usuario intenta enviar el formulario"],
                then=["el sistema muestra mensajes de error por cada campo vacío", "el formulario no se envía"],
                tags=["validation", "negative"],
            ),
            "formato_datos": GherkinScenario(
                name=f"{feature_name} - formato de datos inválido",
                given=["el usuario está en el formulario"],
                when=["el usuario ingresa datos con formato inválido", "el usuario intenta enviar"],
                then=["el sistema muestra error de formato", "el campo inválido se marca en rojo"],
                tags=["validation", "negative"],
            ),
            "limites": GherkinScenario(
                name=f"{feature_name} - valores fuera de rango",
                given=["el usuario está en el formulario"],
                when=["el usuario ingresa valores fuera del rango permitido"],
                then=["el sistema muestra mensaje indicando el rango válido", "no se acepta el valor"],
                tags=["validation", "boundary"],
            ),
            "datos_invalidos": GherkinScenario(
                name=f"{feature_name} - datos inválidos",
                given=["el usuario está en el contexto correspondiente"],
                when=["el usuario proporciona datos inválidos", "el usuario confirma la acción"],
                then=["el sistema valida los datos", "el sistema muestra los errores encontrados"],
                tags=["validation", "negative"],
            ),
        }
        return scenarios_map.get(validation, scenarios_map["datos_invalidos"])

    def _generate_error_scenario(self, text: str, feature_name: str) -> GherkinScenario:
        return GherkinScenario(
            name=f"{feature_name} - manejo de error del servidor",
            given=["el usuario está autenticado", "el servicio backend está degradado o caído"],
            when=["el usuario realiza la acción principal"],
            then=[
                "el sistema muestra un mensaje de error amigable",
                "el sistema no pierde los datos ingresados por el usuario",
                "el error se registra en los logs del sistema",
            ],
            tags=["error_handling", "negative"],
        )

    def _needs_security_scenario(self, text: str) -> bool:
        text_lower = text.lower()
        return any(w in text_lower for w in (
            "login", "auth", "password", "contraseña", "sesión", "token",
            "permiso", "rol", "admin", "pago", "payment", "tarjeta",
        ))

    def _generate_security_scenario(self, text: str, feature_name: str) -> GherkinScenario:
        return GherkinScenario(
            name=f"{feature_name} - acceso no autorizado",
            given=["un usuario sin los permisos requeridos"],
            when=["el usuario intenta acceder a la funcionalidad"],
            then=[
                "el sistema deniega el acceso",
                "el sistema muestra mensaje de acceso denegado",
                "el intento se registra en el log de seguridad",
            ],
            tags=["security", "authorization"],
        )

    def _detect_context(self, text: str) -> str:
        text_lower = text.lower()
        if "login" in text_lower or "auth" in text_lower:
            return "la página de login"
        if "api" in text_lower or "endpoint" in text_lower:
            return "el endpoint API correspondiente"
        if any(w in text_lower for w in ("carrito", "cart", "checkout")):
            return "el carrito de compras"
        if any(w in text_lower for w in ("dashboard", "panel")):
            return "el dashboard"
        return "la funcionalidad correspondiente"

    def _detect_main_action(self, text: str) -> str:
        text_lower = text.lower()
        if any(w in text_lower for w in ("login", "inicia sesión")):
            return "ingresa sus credenciales válidas y presiona login"
        if any(w in text_lower for w in ("registro", "registra", "signup")):
            return "completa el formulario de registro con datos válidos"
        if any(w in text_lower for w in ("compra", "checkout", "pago")):
            return "completa el proceso de compra"
        if any(w in text_lower for w in ("busca", "search", "filtro")):
            return "realiza la búsqueda con criterios válidos"
        if any(w in text_lower for w in ("edita", "modifica", "actualiza")):
            return "modifica los datos y guarda los cambios"
        if any(w in text_lower for w in ("elimina", "borra", "delete")):
            return "confirma la eliminación del recurso"
        return "realiza la acción principal del flujo"

    def _show_help(self, start: float) -> AgentResult:
        content = (
            "**Gherkin Generator — Generador BDD**\n\n"
            "Genera escenarios Gherkin completos a partir de una descripción.\n\n"
            "Ejemplos:\n"
            "- `gherkin para login de usuarios con email y contraseña`\n"
            "- `escenarios para el checkout del carrito de compras`\n"
            "- `bdd para el endpoint API de creación de órdenes`\n"
            "- `genera gherkin para el formulario de registro`\n\n"
            "Cada feature incluye:\n"
            "- Happy path (flujo exitoso)\n"
            "- Validaciones (campos, formatos, límites)\n"
            "- Manejo de errores\n"
            "- Seguridad (si aplica)\n"
        )
        return AgentResult(
            success=True,
            content=content,
            duration_ms=int((time.monotonic() - start) * 1000),
        )
