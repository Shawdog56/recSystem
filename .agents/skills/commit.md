# Skill: Estándar de Commits

## Formato

```
tipo(ámbito): descripción en español
```

## Tipos

| Tipo | Cuándo usarlo |
|---|---|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de error |
| `refactor` | Cambio de código sin agregar funcionalidad ni corregir error |
| `docs` | Documentación |
| `test` | Tests |
| `chore` | Tareas de mantenimiento (docker, config, gitignore, dependencias) |
| `style` | Formato, estilos CSS, templates |
| `db` | Migraciones, cambios en esquema de BD |

## Ámbito

El módulo o carpeta afectada:

| Ámbito | Cuándo usarlo |
|---|---|
| `auth` | login, registro, verificación, sesión |
| `vacante` | CRUD de vacantes, postulación |
| `perfil` | Perfil de aspirante, CV, habilidades |
| `auth2fa` | Tokens, email service |
| `templates` | HTML, CSS, JS frontend |
| `models` | Modelos y migraciones |
| `tests` | Solo cambios en tests |
| `infra` | Docker, config, dependencias |

## Reglas

1. **Siempre en español con acentos y ñ** — ej. `feat(auth): añadida verificación por código`
2. **Verbo en participio o pasado** — `añadido`, `corregido`, `actualizado`, `eliminado`
3. **Sin punto al final** — el título del commit no lleva punto
4. **Mensaje descriptivo** — que explique QUÉ cambia, no cómo
5. **Un solo cambio por commit** — no mezcles features distintas

## Ejemplos

```
feat(auth): añadida pre-verificación por email en registro
fix(vacante): corregido error al postularse sin perfil
refactor(models): unificados campos de Vacante en JSONB
docs(db): agregado diagrama relacional Mermaid
test(auth): corregidos teléfonos duplicados en tests
chore(infra): eliminado init.sql, migraciones como única fuente
style(templates): actualizado login con mensajes de error
db(models): añadida tabla perfil_habilidad
```

## Uso con Git

```bash
git add -A
git commit -m "feat(módulo): descripción del cambio"
```
