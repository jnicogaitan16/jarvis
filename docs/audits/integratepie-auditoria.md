# AUDITORÍA ESTRATÉGICA Y TÉCNICA — INTEGRATEPIE

## Informe de Diagnóstico Integral

---

## 1. RESUMEN EJECUTIVO

IntegratePIE es una plataforma empresarial de gestión del Programa de Integración Escolar (PIE) para establecimientos educacionales chilenos. Desarrollada sobre **Laravel 8.83 con PHP 8.4**, recientemente migrada desde Laravel 5. La plataforma administra **67 tipos de formularios** especializados en evaluación, diagnóstico e intervención de estudiantes con Necesidades Educativas Especiales (NEE), cubriendo desde el ingreso del estudiante hasta su egreso del programa.

**Dimensiones clave del sistema:**

| Métrica | Valor |
|---------|-------|
| Líneas de código (app/) | ~174.000 |
| Controladores | 78 |
| Servicios de negocio | 46 |
| Middleware personalizado | 20 |
| Migraciones de BD | 368 |
| Vistas Blade | 513 |
| Archivos de configuración | 43 |
| Tests unitarios (PHPUnit) | 43 archivos / 643 métodos |
| Tests E2E (Nightwatch) | 12 archivos / ~39 escenarios |
| Formularios/informes | 67 tipos |
| Categorías NEE | 33 diagnósticos |
| Tipos de PAI | 10 especialidades |

La plataforma opera sobre infraestructura **Azure** (App Service, Blob Storage, MySQL) con CI/CD mediante **Azure DevOps**, monitoreo con **Sentry**, analíticas con **Mixpanel**, y comunicación con usuarios vía **Intercom/WhatsApp**. El sistema es multi-tenant por RBD (Rol Base de Datos del establecimiento), manejando aislamiento a nivel de aplicación.

---

## 2. STACK TECNOLÓGICO

### Backend
- **PHP**: 8.4.* (migrado desde PHP 7.x)
- **Laravel**: 8.83.* (migrado desde Laravel 5)
- **Base de datos**: MySQL (utf8mb4, conexiones persistentes para Azure)
- **Cola**: Sincrónica (infraestructura para database/Redis/SQS disponible pero no activa)
- **Cache**: Configurable (array en testing)
- **Sesión**: File-based, 480 min lifetime

### Frontend
- **Vue.js** 3.x (componentes reactivos)
- **Laravel Mix** 6 (compilación de assets)
- **Bootstrap** 3 + jQuery 3.x
- **Librerías UI**: Select2, DataTables, FullCalendar 5.x, Highcharts, SweetAlert2, Toastr
- **Analítica cliente**: Mixpanel Browser, Intercom SDK

### Infraestructura
- **Hosting**: Azure App Service (slot-based deployment)
- **Almacenamiento**: Azure Blob Storage (primario), Google Drive (documentos), S3 (fallback)
- **CI/CD**: Azure DevOps (6 pipelines)
- **Monitoreo**: Sentry (error tracking con obfuscación de datos)
- **Broadcasting**: Pusher (WebSocket)
- **Email**: SMTP con fallback Mailgun

### Paquetes internos (Inteduc)
- `inteduc/fudei-masivo` v0.87.1 — Procesamiento masivo FUDEI
- `inteduc/informes` v0.79.2 — Generación de informes
- `inteduc/leyautismo` v0.40.11 — Implementación Ley de Autismo (PAEC)
- `phpoffice/phpword` (fork Inteduc) — Generación Word

### Testing
- **PHPUnit** ^8.5.8|^9.3.3 + Mockery ^1.3.1
- **Nightwatch** 3.1.2 (E2E actual, en migración)
- **Playwright** (estructura preparada, sin tests activos aún)

---

## 3. ARQUITECTURA

### 3.1 Patrones identificados

| Patrón | Implementación | Evidencia |
|--------|---------------|-----------|
| **MVC** | Estructura principal | Controllers → Views (513 Blade) → Models |
| **Service Layer** | 46 servicios encapsulando lógica de negocio | `app/Services/Fur/`, `app/Services/Pai/`, `app/Services/Sugerencias/` |
| **Adapter** | Abstracción de fuentes de datos FUR | `BaseFurAdapter`, `DefaultFurAdapter`, `FurProfesionalesAdapter` |
| **Strategy** | Algoritmos intercambiables para sugerencias | `SugerenciasStrategy`, `SugerenciasFactory` |
| **Observer/Event Manager** | Coordinación de flujos complejos | `PaiEventManager`, `PaciEventManager`, `InformeEventManager` |
| **Repository** | Acceso a datos especializado | `EstadoAvanceKineToRepository` |
| **Facade** | Acceso simplificado a servicios | `EventTracker` facade |

### 3.2 Estructura de directorios

```
app/ (210 archivos PHP)
├── Http/
│   ├── Controllers/          (78)  — Controladores MVC
│   │   ├── Api/V1/          (16)  — API RESTful v1
│   │   ├── Auth/            (5)   — Autenticación
│   │   ├── Informes/        (30+) — Informes y formularios
│   │   └── Coordinacion/    (2)   — Coordinación PIE
│   ├── Middleware/           (20)  — Middleware personalizado
│   ├── Helpers/              (26)  — Helpers de lógica
│   └── Requests/             (1)   — Form Requests
├── Models/                   (3)   — Modelos Eloquent
├── Services/                 (46)  — Lógica de negocio
│   ├── Fur/                 (20)  — Servicios FUR
│   ├── Pai/                 (7)   — Servicios PAI
│   └── Sugerencias/         (4)   — Motor de sugerencias
├── Events/                   (6)   — Event Managers
├── Providers/                (10)  — Service Providers
├── Console/                  (3)   — Comandos Artisan
├── Exceptions/               (3)   — Excepciones personalizadas
├── Contracts/                (1)   — Interfaces (FurDataAdapter)
├── Facades/                  (1)   — EventTracker
└── Traits/                   (1)   — HandlesPermissions
```

### 3.3 Mapa conceptual de arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENTE (Browser)                     │
│  Vue.js 3 │ Bootstrap 3 │ jQuery │ Mixpanel │ Intercom  │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP/WebSocket
┌─────────────────────▼───────────────────────────────────┐
│              MIDDLEWARE STACK (20 capas)                 │
│  AuthAuxiliar → SessionAuxiliar → PerPer → CORS → ...  │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│              CONTROLLERS (78 archivos)                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │
│  │ Informes │ │  API v1  │ │   Auth   │ │Coordinación│ │
│  │  (30+)   │ │  (16)    │ │   (5)    │ │    (2+)    │ │
│  └────┬─────┘ └────┬─────┘ └──────────┘ └────────────┘ │
└───────┼─────────────┼───────────────────────────────────┘
        │             │
┌───────▼─────────────▼───────────────────────────────────┐
│              SERVICES (46 archivos)                      │
│  ┌───────────┐ ┌──────────┐ ┌───────────┐ ┌──────────┐ │
│  │ FUR (20)  │ │ PAI (7)  │ │Sugerencias│ │ General  │ │
│  │ +Adapters │ │+Clasific.│ │ +Strategy │ │ +Config  │ │
│  └─────┬─────┘ └────┬─────┘ └───────────┘ └──────────┘ │
└────────┼────────────┼───────────────────────────────────┘
         │            │
┌────────▼────────────▼───────────────────────────────────┐
│  MODELOS (4) + HELPERS (26) + EVENT MANAGERS (6)        │
│  PieFormFudei │ Persona │ EquipoPie │ User              │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                   BASE DE DATOS                         │
│        MySQL (utf8mb4) — 368 migraciones                │
│  Multi-tenant por RBD (filtrado a nivel aplicación)     │
└─────────────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              SERVICIOS EXTERNOS                         │
│  Azure Blob │ Google Drive │ Sentry │ Pusher │ Mixpanel│
│  Intercom │ WhatsApp │ SMTP/Mailgun │ Inteduc API      │
└─────────────────────────────────────────────────────────┘
```

---

## 4. MAPA FUNCIONAL

### 4.1 Módulos principales

#### FUDEI (Formulario Único de Evaluación Integral)
- **Propósito**: Formulario diagnóstico inicial que determina las NEE del estudiante y su clasificación
- **Controladores**: `FurController`, `FudeiApiProgressController`
- **Servicios**: `FurAdapterManager`, adapters (Base, Default, Profesionales)
- **Modelo**: `PieFormFudei`
- **Rutas**: `/pie/form/fudei`, `/pie/form/fudei/reabrir`
- **Regla clave**: Es el formulario base que desencadena la creación de FUR y planes de apoyo
- **Paquete externo**: `inteduc/fudei-masivo` para procesamiento masivo

#### FUR (Formulario Único de Registro/Revaluación)
- **Propósito**: Registro legal/administrativo requerido por MINEDUC para cada estudiante PIE
- **Controladores**: `FurController`, `FurApiController`
- **Servicios**: 20 servicios especializados — `FurEstadoAvance[Psicopedagogico|Psicologico|Fono|KineTo]Service`, `FurDiagnosticoGarcTeaService`, `FurTrackingService`, `FurRegistroPieLogService`, `FurAiService`
- **Rutas**: 15+ rutas para diferentes tipos de FUR (Transitorio, DIS, TEA, DMultiple, DMotora, DAuditiva, DVisual, NEPP)
- **API**: `/api/v1/fur-transitorio/{fur_id}/{anio}/{rbd}/{run}`, `/api/v1/fur-permanente/...`
- **Configuración**: `config/fur.php` (186 KB) — el archivo de configuración más grande del sistema
- **Reglas clave**:
  - 8 tipos de FUR según categoría diagnóstica
  - FUR 2026 con rollout por fases (25%, 50%, 85% por RBD)
  - Regla GArc→TEA: estudiantes con diagnóstico GArc (ID 33) reciben FUR TEA en lugar de DMultiple
  - Importación desde múltiples fuentes (profesionales, estado avance, familia, estrategias)

#### PAI (Plan de Apoyo Individual)
- **Propósito**: Plan de intervención pedagógica/terapéutica individualizado por especialidad
- **Controladores**: `PaiController` (201 KB — el controlador más grande), `AutoSavePaiApiController`, `PaiApiController`
- **Servicios**: 7 servicios de clasificación (Psicológico, Psicopedagógico, Funcional, KineTo, Fono)
- **Eventos**: `PaiEventManager`, `PaiNewUserEventManager`
- **10 tipos de PAI**: Psicológico, Fonoaudiológico, Psicopedagógico, T. Ocupacional, Equinoterapia, Kinesiología, Empleabilidad, Trabajo Social, Pedagógico Curricular (antiguo/nuevo)
- **Criterios de logro**: L (Logrado), L/A (Logrado con Ayuda), N/L (No Logrado), N/T (No Trabajado)
- **Funcionalidad autosave** vía API REST

#### PACI / PACI 2.0 (Plan de Adecuación Curricular Individual)
- **Propósito**: Adaptaciones curriculares para estudiantes que requieren modificaciones al currículo estándar
- **Controladores**: `InformeAvanzadoController`, `AutoSavePaciApiController`
- **Eventos**: `PaciEventManager`
- **Versiones**: PACI 1.0 (legacy, deprecado post-2024) y PACI 2.0 (actual)
- **Sub-módulos**: PACI2 Planning, PACI2 Estado de Avance
- **Rutas**: 16+ rutas incluyendo CRUD de grupos e ítems, carga de OAs y progresiones

#### Libro de Registro
- **Propósito**: Bitácora de actividades e intervenciones diarias del equipo PIE
- **Controladores**: `LibroRegistroController` (58 KB), `LibroRegistroApiController`
- **Helpers**: `LibroRegistroHelper`, `WordLRHelper`
- **Secciones**: Equipo de Aula, Planificación del Proceso, Registro de Implementación, Registro de Actividades, Actas de Reuniones
- **API**: CRUD completo + calendario de reuniones + filtros + acceso guest

#### PAEC (Plan de Apoyo Especializado Complementario)
- **Propósito**: Soporte especializado para TEA (Ley de Autismo)
- **Paquete**: `inteduc/leyautismo` v0.40.11
- **Middleware dedicado**: `EnsurePaecAuthenticated`, `CheckPaecAccess`
- **Ruta**: `/pie/form/paec`

#### Certificados
- **Certificado Diagnóstico** (Form 54) — Certificado oficial de diagnóstico
- **Certificado Pertenencia PIE** (Form 66) — Constancia de membresía
- **Certificado Egreso PIE** (Form 67) — Certificado de egreso

#### Proceso Evaluativo
- **Propósito**: Seguimiento estructurado del proceso de evaluación según normativa MINEDUC
- **Tabla**: `pie_proceso_evaluativo`
- **Componentes**: Antecedentes generales, antecedentes específicos, pasos evaluativos

### 4.2 Informes especializados (27 controladores)

| Área | Informes |
|------|----------|
| **Evaluación diagnóstica** | Anamnesis, Conners (docente/apoderado), Evaluación Pedagógica, Pauta Observación Directa |
| **Psicología** | Informe Psicológico, Psicoeducativo, WISC-III, WISC-V, WAIS-IV |
| **Fonoaudiología** | Informe Fonoaudiológico, IDTEL |
| **Psicopedagogía** | EVALÚA, EVALEC/LecMat, Precálculo, Funciones Básicas |
| **Especialidades** | Terapia Ocupacional, ICAP, IDEA, TADI, PEFE |
| **Familia/Legal** | Informe Familia, Ficha Salud, Ficha Interconsulta, Poder Simple, Ficha MinEduc |
| **Pedagógico** | Informe Pedagógico, Prueba Pedagógica Informal, Psicopedagógica Informal |

### 4.3 Módulos administrativos

- **Coordinación**: Dashboard, configuración FUDEI, sincronización, proyección de subvenciones
- **Colegio**: Gráficos, listados de alumnos, gestión de profesionales, planificación, asignación equipo PIE
- **Administración**: Documentos de gobierno
- **Configuración**: Configuración de informes, diagnósticos, calendario de informes
- **Notificaciones**: Sistema de notificaciones con comentarios de informe
- **Capacitaciones**: Gestión de capacitaciones del equipo
- **Padres**: Acceso para apoderados

### 4.4 Flujo de dependencias entre módulos

```
FUDEI (Evaluación Diagnóstica)
  └──► FUR (Registro Legal)
         ├──► PAI (10 especialidades)
         │     ├──► Estado de Avance por especialidad
         │     └──► Libro de Registro (Bitácora diaria)
         ├──► PACI 2.0 (Adecuaciones curriculares)
         │     ├──► PACI2 Planificación
         │     └──► PACI2 Estado de Avance
         ├──► PAEC (Ley Autismo, si aplica)
         └──► 27 Informes Especializados
              ├──► Psicológicos (WISC, WAIS, etc.)
              ├──► Fonoaudiológicos (IDTEL, etc.)
              ├──► Psicopedagógicos (EVALÚA, etc.)
              └──► Familia/Salud/Legal

Certificados (generados en cualquier punto):
  ├── Diagnóstico
  ├── Pertenencia
  └── Egreso

Proceso Evaluativo (transversal):
  └── Antecedentes Generales + Específicos
```

---

## 5. REGLAS DE NEGOCIO RELEVANTES

### 5.1 Sistema de diagnóstico NEE (33 categorías)

**Transitorias** (requieren revaluación periódica):
- TDA/TDAH (IDs 1-3) — Déficit atencional con/sin hiperactividad
- TEL (IDs 4-6) — Trastorno Específico del Lenguaje (expresivo/mixto)
- DEA (IDs 7-10) — Dificultades Específicas de Aprendizaje (cálculo/lectura/escritura)
- FIL (ID 11) — Funcionamiento Intelectual Limítrofe
- ODF (ID 31) — Otros diagnósticos fonoaudiológicos

**Permanentes** (soporte de larga duración):
- DA (IDs 12-15) — Discapacidad Auditiva (leve/moderada/severa/sordera)
- DI (IDs 16-19) — Discapacidad Intelectual (leve/moderada/severa)
- DIS (ID 20) — Disfasia Severa/TCCL
- DV (IDs 21-23) — Discapacidad Visual (baja visión/ceguera)
- DMultiple (ID 24), DMotora (ID 25)
- TEA (IDs 26-28) — Autismo (clásico/Asperger/GDD)
- RGD (ID 29), Síndrome Down (ID 30), GArc (ID 33)

### 5.2 Máquina de estados de informes

```
NO_EMPEZADO (0) → EN_PROCESO (2) → TERMINADO (3) → APROBADO (8)
                                  → SUBIDO_MINEDUC (4)
                                  → ADJUNTADO (5)
                                  → ERROR_SINCRONIZAR (7)
      ↕                                    ↕
NO_APLICA (1)                      REABRIR (9) → EN_PROCESO (2)
```

**Regla**: Los estados 2, 3, 4, 5, 7, 8, 9 permiten descarga Word de Estado de Avance.

### 5.3 Regla GArc → TEA (FUR 2026)
- Estudiantes con diagnóstico GArc (pie_nee_id = 33) reciben FUR TEA (tipo 2) en lugar de FUR Múltiple (tipo 3)
- **Condiciones**: Año >= 2026, sin FUR Múltiple iniciado, colegio con códigos de educación especial (211-215)
- **Evidencia**: `FurDiagnosticoGarcTeaService.php`

### 5.4 Rollout FUR 2026 por fases
- Activación: `PieHelper::furHdusHabilitadas()` — requiere año >= 2026 AND RBD en lista de rollout
- Fases: Piloto (RBDs específicos) → 25% → 50% → 85% (por módulo aritmético de RBD)
- **Evidencia**: `config/fur.php`, migraciones de rollout

### 5.5 Períodos académicos
- Semestral: Periodo 1, Periodo 2
- Trimestral: Periodo 1, Periodo 2, Periodo 3
- Anual: Periodo 4
- **Regla**: No se pueden mezclar períodos en importación de Estado de Avance

### 5.6 Sistema de permisos (PerPer)
- Permisos almacenados como JSON en tabla `perfil`
- Usuarios tienen roles por RBD (colegio)
- Superadmin: acceso total a todos los colegios
- **Roles institucionales** (pueden firmar documentos oficiales): Coordinador PIE (2), Coordinador Académico (53), UTP (41), Director (54)
- **Permisos verificados**: `canAccessFormularioUnico`, `canAccessSincronizacionFudei`, `canAccessProyeccionSubvenciones`, `canAccessCalendarioDocumentos`, `canAccessColegioProfesionales`

### 5.7 Exclusiones por tipo de plan
- **PIE (1)**: Excluye Pauta Observación Psicológica
- **Privado (4)**: Excluye FUR, FUDEI, Poder Simple Apoderado
- **Especial (2) y Lenguaje (3)**: Sin exclusiones

### 5.8 Tracking analítico (Mixpanel)
- Niveles: 0 (Off) → 1 (Core) → 2 (Producto) → 3 (Análisis) → 4 (Debug)
- Eventos HDU: Importación profesionales (HDU1), Fecha diagnóstico (HDU2), Importaciones multi-fuente (HDU3-HDU10)
- HMAC para verificación de identidad

---

## 6. ARQUITECTURA DE DATOS

### 6.1 Base de datos
- **Motor**: MySQL con charset utf8mb4
- **Migraciones**: 368 archivos
- **Conexiones persistentes**: Habilitadas (optimización Azure para reutilización de puertos SNAT)
- **Strict mode**: Deshabilitado
- **Timeout**: 5 segundos

### 6.2 Tablas principales (inferidas de migraciones y código)

| Grupo | Tablas |
|-------|--------|
| **Personas** | `persona` (PK: persona_rut), `perfil`, `perfil_user` |
| **FUDEI** | `pie_form_fudei`, `config_pie`, `tabla_pie` |
| **FUR** | `pie_form_fur_transitorio`, `pie_form_fur_permanente`, `diagnostico_fur_*` |
| **PAI** | `pie_form_pai`, `pie_pai_estado_avance` |
| **PACI** | `pie_form_paci`, `pie_form_paci2`, `pie_form_paci2_ea` |
| **Libro Registro** | `pie_libro_registro_*` |
| **Proceso** | `pie_proceso_evaluativo`, `pie_antc_generales`, `pie_antc_especificos` |
| **Informes** | `pie_informes`, `pie_informes_valor` |
| **Config** | `pie_calendario_informes`, `pie_proyeccion_subvenciones` |
| **Equipo** | `equipo_pie`, `profesionales_establecimiento` |
| **Auditoría** | `registro_pie` (log de cambios) |

### 6.3 Multi-tenancy
- **Identificador**: RBD (Rol Base de Datos del establecimiento)
- **Mecanismo**: Filtrado a nivel de aplicación (WHERE `*_rbd = $rbd`)
- **Sesión**: RBD almacenado en `Session::put('rbd_cursos_pie', $rbd)`
- **No hay** aislamiento a nivel de schema ni row-level security nativa

### 6.4 Almacenamiento de archivos
- **Primario**: Azure Blob Storage (con tier extra)
- **Documentos**: Google Drive
- **Local**: `/storage/app/public/almacenamientos/`
- **Legacy**: FTP (fallback)
- **Extensiones permitidas**: png, jpg, jpeg, doc, docx, xls, xlsx, ppt, pptx, pdf

---

## 7. ESTADO DE AUTOMATIZACIÓN QA

### 7.1 PHPUnit (Backend)
- **Archivos**: 43 test files con **643 métodos de prueba**
- **Cobertura**: Helpers (15+), Services FUR (8), Services PAI (6), Config (1), Controllers (1), Catálogos (6+)
- **Patrones**: Data providers para tests paramétricos, mocking de config, edge cases (null, caracteres especiales, formatos)
- **Fortaleza**: Buena cobertura de lógica de rollout FUR, clasificaciones PAI, y helpers de permisos
- **Debilidad**: Sin tests de integración con BD real, un solo FormRequest testeado

### 7.2 Nightwatch.js (E2E — Framework actual)
- **Archivos**: 12 tests con ~39 escenarios (expandibles con data-driven)
- **Módulos cubiertos**: Login (3), Libro de Registro (5), Curso (1), Alumno (1), School (1), PAI solo-lectura (1)
- **Infraestructura**:
  - 12 Page Objects para abstracción de UI
  - 60 archivos JSON de datos de prueba (CDP)
  - 16 tipos de usuarios de prueba
  - 2 custom commands, 1 custom assertion
  - 6 helpers (timeouts, usuarios, constantes, sanitización, retry)
- **Reportes**: HTML (10.2 MB), screenshots por módulo, minimal_report.json
- **Tests saltados**: 12 (6 de login por inconsistencias de redirect, 6 de Libro Registro por sync multi-usuario)

### 7.3 Playwright (Framework en migración)
- **Estado**: Estructura de directorios preparada (`playwright/tests/` con 6 subdirectorios vacíos)
- **Paquete**: `@playwright/test` instalado
- **Tests activos**: Ninguno aún
- **Directorios preparados**: alumno/, course/, libroRegistro/, login/, pai/, school/

### 7.4 CI/CD Pipeline (Azure DevOps)
- **Pipelines**: 6 archivos YAML
  - `azure-pipelines.yml` — Principal (Build → Deploy, schedule 3 AM Chile)
  - `azure-pipelines-qa.yml` — QA completo
  - `azure-pipelines-qa-tests.yml` — Tests E2E focalizados
  - `azure-pipelines-qa-migration.yml` — E2E en PR migrations
  - `azure-pipelines-prod.yml` — Producción
  - `azure-pipelines-clon.yml` — Backup/clone
- **Test execution**: `npm run test:headless` (Nightwatch headless, Chrome, 1 worker)
- **Artefactos**: XML (Azure Test Results), HTML report, screenshots

### 7.5 Herramientas de calidad de código
- **Estado**: Mínimo
- **Ausentes**: PHPStan, Psalm, PHP CS Fixer, ESLint, Prettier
- **Sin** pipeline de linting en CI/CD

### 7.6 Limitaciones actuales
- No hay tests de integración con BD real
- Factories mínimas (solo User)
- Seeders vacíos
- No hay tests de API dedicados (ni Postman collections)
- 12 tests E2E saltados por flakiness en multi-usuario y redirects
- No hay análisis estático de código automatizado
- Migración a Playwright en progreso pero sin tests escritos

### 7.7 Procesos QA que se beneficiarían de un agente inteligente

| Proceso | Beneficio potencial |
|---------|--------------------|
| Generación de escenarios de prueba | Derivar casos de las 33 categorías NEE × 10 tipos PAI × 67 formularios |
| Análisis de regresiones | Identificar impacto de cambios en la cadena FUDEI→FUR→PAI→PACI |
| Validación de reglas de negocio | Verificar consistencia entre config/fur.php, estados_informe.php y lógica de servicios |
| Generación de datos de prueba | Crear fixtures coherentes para combinaciones diagnóstico/plan/período |
| Análisis de cobertura funcional | Mapear rutas no cubiertas por tests existentes |
| Interpretación de errores E2E | Analizar screenshots y logs de Nightwatch para diagnosticar fallos |

---

## 8. INTEGRACIONES

### 8.1 Azure DevOps
- **Pipelines**: 6 archivos de pipeline con deployment multi-slot
- **Variables**: Grupos de variables por ambiente (nodeVersion=22.x, PHP_VERSION=8.4)
- **Estrategia**: Anti-stale check, warmup ping en `/login`, ZIP con TZ=America/Santiago
- **Autenticación**: SSH keys para repositorio

### 8.2 APIs REST internas
- **Versión**: v1 bajo prefijo `/api/v1/`
- **Endpoints**: ~50+ endpoints
- **Módulos API**: FUR (save transitorio/permanente), Libro Registro (CRUD + calendario), PAI/PACI (autosave), Informes Progress (24+ endpoints), Data Transfer, Storage Transfer, Alumno Requiere Informe (upsert masivo)
- **Rate limiting**: 4000 req/min a nivel global
- **Autenticación API**: Token-based (legacy, no Sanctum/Passport)

### 8.3 Servicios externos

| Servicio | Uso | Configuración |
|----------|-----|---------------|
| **Intercom** | Comunicación con usuarios | `config/intercom.php`, rollout por RBD |
| **WhatsApp** | Canal alternativo de soporte | Integrado con Intercom, phone configurable |
| **Mixpanel** | Analítica de producto | `mixpanel/mixpanel-php`, EventTracker service |
| **Sentry** | Monitoreo de errores | `sentry/sentry-laravel`, con DataObfuscator |
| **Pusher** | WebSocket/Broadcasting | Notificaciones en tiempo real |
| **Google Drive** | Almacenamiento de documentos | Driver custom vía `GoogleDriveServiceProvider` |
| **Azure Blob** | Almacenamiento primario | Retry: 3 intentos, 500ms backoff exponencial |
| **Inteduc API** | Plataforma educativa interna | Multi-user API + SignalR para sincronización real-time |
| **DomPDF** | Generación PDF | `barryvdh/laravel-dompdf` |
| **PHPWord** | Generación Word | Fork Inteduc de `phpoffice/phpword` |
| **Google Docs Viewer** | Preview de formularios | Integración para vista previa |

### 8.4 Documentación técnica
- **Directorio**: `docs/` (83 archivos)
- **Guía PHP 8**: `PHP8-COMPATIBILITY-GUIDE.md`
- **Scripts de diagnóstico**: `diagnostico-docker.sh`, `verificar-setup.sh`
- **Sin** Swagger/OpenAPI para las APIs

---

## 9. CONOCIMIENTO TÉCNICO DISPONIBLE

### 9.1 Conocimiento general reutilizable (dominio público / normativa MINEDUC)
- Sistema de clasificación NEE (Decreto 170/2009): 33 diagnósticos en 2 categorías
- Tipos de PAI por especialidad terapéutica/pedagógica
- Códigos de enseñanza del sistema educacional chileno
- Máquina de estados de documentos (flujo evaluativo)
- Estructura de períodos académicos (semestral/trimestral)
- Roles institucionales PIE (coordinador, UTP, director)
- Criterios de logro (L, L/A, N/L, N/T) para evaluación de avance

### 9.2 Lógica específica de plataforma (IntegratePIE)
- Rollout FUR 2026 con fases por porcentaje de RBD
- Regla de sustitución GArc→TEA
- Sistema PerPer de permisos (JSON en perfil por RBD)
- Doble clasificación PAI (Base + Funcional)
- Importación y deduplicación de Estado de Avance
- Taxonomía de tracking HDU (HDU1-HDU10+)
- Exclusiones de formularios por tipo de plan
- Motor de sugerencias (Strategy + Factory)
- Adapters para fuentes de datos FUR

### 9.3 Información confidencial / no exportable
- Listas específicas de RBD piloto
- Manejo de errores de sincronización MINEDUC
- Nombres de columnas y estructura detallada de BD
- Patrones de acceso DAEM coordinador
- Detalles de autenticación y sesión
- Credenciales de servicios externos
- Datos personales de estudiantes (RUT, nombres, información médica)

### 9.4 Escenarios de prueba derivables del código

| Fuente | Escenarios potenciales |
|--------|----------------------|
| 33 NEE × 10 PAI | ~330 combinaciones diagnóstico-plan |
| 67 formularios × 9 estados | ~603 transiciones de estado |
| 8 tipos FUR × fases rollout | ~32 escenarios de habilitación |
| 16 tipos de usuario | ~16 × N rutas de acceso |
| 5 secciones Libro Registro | ~25 escenarios CRUD |
| PACI 1.0 vs 2.0 | Escenarios de migración/compatibilidad |

---

## 10. RIESGOS Y RESTRICCIONES

### 10.1 Riesgos críticos de seguridad

| Riesgo | Severidad | Evidencia |
|--------|-----------|-----------|
| **CSRF deshabilitado** | CRÍTICO | `VerifyCsrfToken` comentado en Kernel — todas las request POST/PUT/DELETE vulnerables |
| **Backend auth no implementado** | CRÍTICO | `BackendAuthMiddleware` tiene TODO, sin validación de tokens inter-servicio |
| **Sesión sin encriptar** | ALTO | `encrypt = false` en config/session.php — datos personales en plaintext |
| **Datos personales en sesión** | ALTO | RUT, nombres, teléfono almacenados en archivos de sesión sin cifrar |

### 10.2 Riesgos altos

| Riesgo | Descripción |
|--------|-------------|
| **Sin políticas Eloquent** | Autorización vía helpers en lugar de gates/policies estandarizados |
| **Multi-tenancy por aplicación** | Sin row-level security — manipulación de sesión podría exponer datos cross-tenant |
| **RUT en rutas API** | Identificadores personales expuestos como parámetros de URL |
| **Sin validación MIME** | Solo validación de extensión en uploads, no verificación de contenido |
| **Debugbar en producción** | Potencial fuga de información |
| **Token auth legacy** | API sin Sanctum/Passport — sin expiración robusta de tokens |

### 10.3 Restricciones técnicas

- **Modelos mínimos**: Solo 4 modelos Eloquent para una BD con 368 migraciones — mucha lógica en queries directas
- **Controlador PAI de 201 KB**: Concentración excesiva de lógica
- **config/fur.php de 186 KB**: Archivo de configuración extremadamente grande
- **Cola sincrónica**: No hay procesamiento asíncrono activo
- **Sin scheduled tasks**: Console/Kernel vacío
- **Sin análisis estático**: No hay PHPStan, Psalm ni linting automatizado

### 10.4 Restricciones de la auditoría
- No se ejecutaron migraciones ni se accedió a la BD
- No se ejecutaron tests ni se verificó su estado actual
- No se accedió a servicios externos ni credenciales
- La estructura de tablas se infirió de migraciones y código, no de la BD real
- No se verificó el estado real de producción

---

## 11. CAPACIDADES POTENCIALES PARA JARVIS

### 11.1 Análisis de requerimientos
- **Necesidad**: Traducir requerimientos de negocio (ej. "nueva categoría NEE") en impacto técnico
- **Evidencia**: config/diagnosticos.php define 33 NEE con cascada a FUR, PAI, informes
- **Información requerida**: Documentación MINEDUC, config files, rutas, controladores
- **Sistemas**: Repositorio Git, Azure DevOps (work items)
- **Complejidad**: MEDIA — requiere comprensión del dominio educativo
- **Riesgo**: Interpretación incorrecta de normativa vs implementación

### 11.2 Generación de escenarios QA
- **Necesidad**: Generar casos de prueba para las ~330+ combinaciones NEE × PAI
- **Evidencia**: Solo 643 tests unitarios y 39 E2E para 67 tipos de formularios
- **Información requerida**: Reglas de negocio en config/, validaciones en services/, estados en estados_informe.php
- **Sistemas**: Repositorio, PHPUnit, Nightwatch/Playwright
- **Complejidad**: ALTA — combinatoria explosiva de estados y tipos
- **Riesgo**: Generar tests sin valor por falta de contexto funcional

### 11.3 Identificación de riesgos de regresión
- **Necesidad**: Ante un cambio en FUR, identificar impacto en PAI, PACI, Estado de Avance
- **Evidencia**: Cadena de dependencias FUDEI→FUR→PAI→PACI con 20 servicios FUR interconectados
- **Información requerida**: Grafo de dependencias, git diff, tests existentes
- **Sistemas**: Git, Azure DevOps (PRs)
- **Complejidad**: ALTA — servicios altamente acoplados
- **Riesgo**: Falsos positivos que generen ruido

### 11.4 Análisis de reglas de negocio
- **Necesidad**: Mantener documentación viva de las reglas de negocio distribuidas en código
- **Evidencia**: Reglas en config/ (fur.php 186KB), services/ (46 archivos), helpers/ (26 archivos)
- **Información requerida**: Código fuente, migraciones, configuración
- **Sistemas**: Repositorio
- **Complejidad**: MEDIA — extracción de reglas es mecánica, interpretación requiere dominio
- **Riesgo**: Reglas obsoletas o contradictorias no detectadas

### 11.5 Comprensión de código Laravel
- **Necesidad**: Asistir a desarrolladores en la navegación del codebase de 174K líneas
- **Evidencia**: Controlador PAI de 201 KB, 78 controladores, patrones heterogéneos
- **Información requerida**: Código fuente completo, documentación existente (83 docs)
- **Sistemas**: Repositorio, IDE
- **Complejidad**: BAJA — capacidad nativa de LLMs
- **Riesgo**: Mínimo

### 11.6 Generación de pruebas automatizadas
- **Necesidad**: Acelerar migración Nightwatch→Playwright y expandir cobertura
- **Evidencia**: 12 page objects, 60 fixtures JSON, 16 tipos de usuario ya definidos
- **Información requerida**: Page objects existentes, fixtures, patrones de testing
- **Sistemas**: Playwright, Nightwatch (referencia), Azure DevOps pipeline
- **Complejidad**: MEDIA — traducción mecánica + generación de nuevos tests
- **Riesgo**: Tests frágiles si no se entiende la UI dinámica

### 11.7 Interpretación de errores y diagnóstico
- **Necesidad**: Analizar errores de Sentry, logs de pipeline, screenshots E2E
- **Evidencia**: Sentry integrado con DataObfuscator, screenshots capturados en tests_output/
- **Información requerida**: Logs de Sentry, reportes HTML, screenshots, stack traces
- **Sistemas**: Sentry, Azure DevOps, repositorio
- **Complejidad**: MEDIA — correlación error↔código
- **Riesgo**: Datos sensibles en logs (requiere obfuscación)

### 11.8 Integración con Azure DevOps
- **Necesidad**: Crear/actualizar work items, analizar PRs, verificar pipelines
- **Evidencia**: 6 pipelines existentes, despliegue automático diario
- **Información requerida**: API tokens Azure DevOps, estructura de proyecto
- **Sistemas**: Azure DevOps API
- **Complejidad**: BAJA — APIs bien documentadas
- **Riesgo**: Acciones no autorizadas si los permisos no están bien delimitados
- **Dependencia**: Autorización explícita del equipo

### 11.9 Preparación de reportes QA
- **Necesidad**: Consolidar resultados de tests, cobertura, métricas de calidad
- **Evidencia**: minimal_report.json, HTML reports, screenshots por módulo
- **Información requerida**: Resultados de tests, métricas de pipeline, cobertura de código
- **Sistemas**: Azure DevOps, PHPUnit, Nightwatch/Playwright
- **Complejidad**: BAJA — agregación y formateo
- **Riesgo**: Mínimo

### 11.10 Análisis de evidencias y trazabilidad
- **Necesidad**: Vincular cambios de código con escenarios de prueba y evidencias
- **Evidencia**: Screenshots organizados por módulo, FurRegistroPieLogService para audit trail
- **Información requerida**: Git history, test results, screenshots, logs de auditoría
- **Sistemas**: Git, Azure DevOps, sistema de archivos
- **Complejidad**: MEDIA — requiere correlación multi-fuente
- **Riesgo**: Complejidad en mantener trazabilidad actualizada

---

## 12. COMPONENTES APROVECHABLES

| Componente | Uso para JARVIS |
|------------|----------------|
| **config/diagnosticos.php** | Base de conocimiento de 33 NEE con clasificación |
| **config/fur.php** (186 KB) | Reglas de rollout, tipos FUR, importaciones, tracking |
| **config/pai_config.php** | 10 tipos PAI, criterios de logro, períodos |
| **config/estados_informe.php** | Máquina de estados de documentos |
| **config/forms.php** | Catálogo de 67 formularios |
| **config/equipo_pie.php** | Roles y cargos institucionales |
| **config/codigos_ensenanza.php** | Códigos del sistema educativo chileno |
| **nightwatch/data/** (60 JSON) | Fixtures de datos de prueba reutilizables |
| **nightwatch/page-objects/** (12) | Abstracción de UI para tests |
| **nightwatch/helpers/usersTest.js** | 16 tipos de usuario con roles |
| **tests/Unit/** (43 archivos) | Patrones de testing y reglas validadas |
| **app/Services/** (46 archivos) | Lógica de negocio encapsulada |
| **docs/** (83 archivos) | Documentación técnica existente |

---

## 13. DEPENDENCIAS PARA JARVIS

| Dependencia | Tipo | Descripción |
|-------------|------|-------------|
| Acceso lectura al repositorio | Técnica | Para análisis de código y extracción de reglas |
| API Azure DevOps | Técnica | Para work items, PRs, pipelines |
| API Sentry | Técnica | Para análisis de errores |
| Conocimiento MINEDUC | Dominio | Decreto 170/2009, normativa PIE |
| Base de datos de prueba | Técnica | Para validación de escenarios (no producción) |
| Autorización del equipo | Organizacional | Para acciones en Azure DevOps y repositorio |
| LLM con contexto largo | Técnica | Para analizar archivos grandes (fur.php 186KB, PaiController 201KB) |
| Framework de testing | Técnica | Playwright (preferido) para generación de tests E2E |

---

## 14. LIMITACIONES

| Limitación | Impacto |
|-----------|---------|
| Modelos Eloquent mínimos (4) | Dificulta análisis automatizado de relaciones de datos |
| Sin Swagger/OpenAPI | No hay documentación formal de las ~50 APIs |
| Controlador PAI monolítico (201 KB) | Complejo de analizar y mantener |
| Lógica distribuida entre 26 helpers | Difícil trazabilidad de reglas de negocio |
| Sin análisis estático existente | No hay baseline de calidad de código |
| Multi-tenancy por sesión | Riesgo en automatización si el contexto de sesión no se maneja correctamente |
| Cola sincrónica | Limita capacidades de procesamiento paralelo |
| Credenciales de test en .env | Riesgo si se exponen fuera del ambiente local |

---

## 15. EVIDENCIAS VERIFICABLES

Cada hallazgo de esta auditoría está respaldado por archivos del repositorio. Referencia de evidencias principales:

| Hallazgo | Evidencia (archivo) |
|----------|-------------------|
| PHP 8.4 / Laravel 8.83 | `composer.json` |
| 78 controladores | `app/Http/Controllers/` (conteo de archivos) |
| 46 servicios | `app/Services/` (conteo de archivos) |
| 33 categorías NEE | `config/diagnosticos.php` |
| 67 tipos de formularios | `config/forms.php` |
| 9 estados de informe | `config/estados_informe.php` |
| 10 tipos PAI | `config/pai_config.php` |
| Rollout FUR 2026 | `config/fur.php`, migraciones recientes |
| Regla GArc→TEA | `app/Services/Fur/FurDiagnosticoGarcTeaService.php` |
| CSRF deshabilitado | `app/Http/Kernel.php` (middleware comentado) |
| Backend auth no implementado | `app/Http/Middleware/BackendAuthMiddleware.php` (TODO) |
| Sesión sin encriptar | `config/session.php` (encrypt = false) |
| 643 métodos de test | `tests/Unit/` (conteo de métodos @test) |
| 12 tests E2E | `tests/e2e/` (conteo de archivos) |
| 6 pipelines Azure | `azure-pipelines*.yml` (conteo de archivos) |
| Estructura Playwright vacía | `playwright/tests/` (directorios sin archivos .spec) |
| 368 migraciones | `database/migrations/` (conteo de archivos) |
| Multi-tenancy por RBD | `app/Http/Middleware/SessionAuxiliar.php`, controllers con WHERE rbd |
| Tracking HDU | `config/fur.php` sección tracking |

---

## MATRIZ DE CAPACIDADES POTENCIALES PARA JARVIS

| Capacidad potencial | Necesidad | Evidencia | Complejidad | Prioridad sugerida |
|---------------------|-----------|-----------|-------------|-------------------|
| **Generación de escenarios QA** | Cobertura insuficiente para 67 formularios × 33 NEE × 10 PAI | 643 unit tests + 39 E2E para sistema con ~330+ combinaciones | ALTA | **P1 — CRÍTICA** |
| **Identificación de riesgos de regresión** | Cadena FUDEI→FUR→PAI→PACI con alto acoplamiento | 20 servicios FUR interconectados, 46 servicios total | ALTA | **P1 — CRÍTICA** |
| **Generación de pruebas automatizadas** | Migración NW→PW en curso, 12 page objects + 60 fixtures disponibles | Estructura Playwright preparada pero vacía | MEDIA | **P1 — CRÍTICA** |
| **Interpretación de errores** | Diagnóstico manual de fallos E2E y errores Sentry | Screenshots, DataObfuscator, minimal_report.json | MEDIA | **P2 — ALTA** |
| **Análisis de reglas de negocio** | Reglas dispersas en config/ (186KB fur.php), services/ (46), helpers/ (26) | Lógica no centralizada ni documentada formalmente | MEDIA | **P2 — ALTA** |
| **Comprensión de código Laravel** | Codebase de 174K líneas, controlador PAI de 201KB | 78 controladores, patrones heterogéneos | BAJA | **P2 — ALTA** |
| **Preparación de reportes QA** | Consolidación manual de resultados de múltiples fuentes | minimal_report.json, HTML reports, pipeline artifacts | BAJA | **P3 — MEDIA** |
| **Integración Azure DevOps** | Gestión manual de work items, PRs, pipelines | 6 pipelines, deployment diario, PRs duales (L8+L5) | BAJA | **P3 — MEDIA** |
| **Análisis de requerimientos** | Traducción requerimiento→impacto técnico manual | 33 NEE con cascada a múltiples módulos | MEDIA | **P3 — MEDIA** |
| **Análisis de evidencias y trazabilidad** | Vinculación manual cambio→test→evidencia | Git history, screenshots por módulo, audit trail | MEDIA | **P4 — BAJA** |

### Leyenda de clasificación

- **Hallazgo comprobado** (verificado): Verificado directamente en archivos del repositorio
- **Inferencia** (~): Derivado de patrones en código, migraciones o configuración sin acceso a BD real
- **No verificable** (?): Requiere acceso a ambiente runtime, BD o servicios externos

| Tipo | Hallazgos |
|------|-----------|
| Comprobado | Stack tecnológico, estructura de archivos, reglas en config/, controllers, services, middleware, pipelines, tests, dependencias |
| Inferido | Estructura de tablas BD (de migraciones), flujos de negocio completos (de rutas+controllers), uso real de cola/eventos |
| No verificable | Estado real de producción, datos en BD, rendimiento, uso efectivo de features, estado de sincronización MINEDUC |

---

*Auditoría realizada el 2026-10-24. Exclusivamente de lectura — no se modificaron archivos, no se ejecutaron comandos destructivos, no se accedió a bases de datos reales ni se utilizaron credenciales. Este informe sirve como insumo para una evaluación posterior sobre la viabilidad de JARVIS.*
