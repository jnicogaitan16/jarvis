# Claude Code Remoto desde iPhone

Guia rapida para trabajar con Claude Code desde tu iPhone usando Tailscale + Termius + SSH.

---

## Arquitectura

```
iPhone (cualquier red: datos, WiFi, etc.)
  |
  |  Termius app
  |
  v
Tailscale VPN (encriptado punto a punto)
  |
  v
Mac mini (100.111.174.40)
  |
  |  SSH
  |
  v
security unlock-keychain  -->  claude / claude --resume
  |
  +--> Repos (JARVIS, IAAgent, KameCol)
  +--> DBs (MySQL prod/QA, PostgreSQL KameCol)
  +--> Git (commits, PRs, branches)
```

---

## Setup inicial (una sola vez, ya completado)

| Paso | Mac mini | iPhone |
|------|----------|--------|
| SSH | Ajustes > General > Compartir > Inicio de sesion remoto | — |
| Tailscale | `brew install --cask tailscale` + login Google | App Store + login misma cuenta |
| Termius | — | App Store + crear host con IP `100.111.174.40` |
| Verificar | `tailscale ip` muestra `100.111.174.40` | Tailscale dice "Connected" |

---

## Flujo diario (cada vez que quieras trabajar)

### Desde iPhone

```
1. Abrir Tailscale        --> verificar "Connected"
2. Abrir Termius          --> tocar host 100.111.174.40
3. Contraseña del Mac     --> (si la pide)
4. security unlock-keychain   --> contraseña del Mac
5. claude                     --> nueva sesion
   claude --resume            --> retomar ultima sesion
6. Trabajar normalmente       --> traza completa en tiempo real
```

### Desde Mac (mantener listo)

- Tailscale activo en barra de menu (icono verde)
- SSH habilitado (es persistente, no se apaga)
- Mac encendido y con internet
- **Sleep desactivado** (ver seccion abajo)

### Evitar que el Mac duerma (importante)

Si el Mac entra en suspension/hibernacion, SSH y Tailscale dejan de funcionar.

| Estado del Mac | SSH funciona? |
|----------------|---------------|
| Encendido + pantalla bloqueada | Si |
| Pantalla apagada (displaysleep) | Si |
| Suspension (sleep) | No |
| Hibernacion | No |

Configurar una sola vez:

```bash
# Desactivar sleep cuando esta conectado a corriente
sudo pmset -c sleep 0 displaysleep 0 disksleep 0

# Activar Wake on LAN como respaldo
sudo pmset -c womp 1

# Verificar
pmset -g
```

---

## Cambiar de proyecto

Antes de ejecutar `claude`, navega al directorio:

```bash
cd ~/Developer/Personal/jarvis    # JARVIS
cd ~/Developer/Personal/IaAgent   # IAAgent
cd ~/Developer/Personal/kamecol   # KameCol
```

---

## Comandos esenciales

| Accion | Comando |
|--------|---------|
| Nueva sesion | `claude` |
| Retomar ultima | `claude --resume` |
| Pregunta rapida | `claude -p "tu pregunta"` |
| Desbloquear keychain | `security unlock-keychain` |
| Ver IP Tailscale | `tailscale ip` |

---

## Solucion de problemas

| Problema | Causa | Solucion |
|----------|-------|----------|
| "Connection refused" | SSH apagado en Mac | Ajustes > Compartir > Inicio sesion remoto |
| "Not logged in" | Keychain bloqueado | `security unlock-keychain` + contraseña del Mac |
| No conecta fuera de casa | Tailscale desconectado | Abrir Tailscale en ambos dispositivos |
| Timeout al conectar | Mac apagado o sin internet | Verificar Mac encendido con WiFi |
| IP cambio | Raro | `tailscale ip` en Mac, actualizar Termius |

---

## Abrir sesion remota (paso a paso)

```
iPhone:
  1. Abrir Tailscale      --> esperar "Connected"
  2. Abrir Termius         --> tocar host "Mac mini"
  3. Ya estas en terminal  --> escribir:

  $ security unlock-keychain
  Password: (tu contraseña del Mac)

  $ cd ~/Developer/Personal/IaAgent    (o el proyecto que quieras)
  $ claude
```

## Cerrar sesion de manera segura (paso a paso)

```
Dentro de Claude Code:
  1. Escribe:  /exit          --> cierra Claude Code
     (o presiona Ctrl+C dos veces si no responde)

En la terminal SSH:
  2. Escribe:  exit           --> cierra la sesion SSH

En Termius (iPhone):
  3. Desliza para cerrar la app (o simplemente sal)

Tailscale:
  4. NO lo cierres           --> dejalo activo, no consume bateria
```

### Que pasa si cierro mal?

| Situacion | Consecuencia | Que hacer |
|-----------|-------------|-----------|
| Cierro Termius sin /exit | Claude Code sigue corriendo en Mac | Proximo login: `claude --resume` recupera la sesion |
| Se corta el internet | Igual que arriba | Reconectar y `claude --resume` |
| Cierro Tailscale en iPhone | No puedes conectar hasta reabrirlo | Abrir Tailscale de nuevo |
| Apago el Mac | Todo muere | Encender Mac, esperar Tailscale, reconectar |

### Tip: usar tmux para sesiones persistentes

Si quieres que Claude Code sobreviva desconexiones:

```bash
# En vez de "claude" directamente, usa:
tmux new -s trabajo        # crea sesion persistente
claude                     # dentro de tmux

# Si te desconectas, al volver:
tmux attach -t trabajo     # recuperas todo tal cual
```

---

## Nota sobre autenticacion

La cuenta de Claude Code es **empresarial (Claude Max)**. NO hacer `claude /login` ni re-autenticarse
sin autorizacion — el token esta vinculado a la cuenta de la empresa.

Si aparece "Not logged in", la solucion es **siempre** desbloquear el keychain:

```bash
security unlock-keychain ~/Library/Keychains/login.keychain-db
```

Esto desbloquea el token que ya esta guardado. No necesitas credenciales de la cuenta empresarial,
solo la contraseña de tu usuario del Mac.

---

## IPs de referencia

- **Mac mini (Tailscale):** `100.111.174.40`
- **iPhone (Tailscale):** `100.126.94.77`
- **Mac mini (local):** `192.168.40.6`
