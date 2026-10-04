# 🎨 PyQPSTricks Studio

**PyQPSTricks Studio** es un fork de **PyQTikz Studio** orientado a **PSTricks** y a los puentes **pdftricks** / **auto-pst-pdf**.

Aplicación de escritorio multiplataforma (Linux y Windows) desarrollada en Python con **PySide6 (Qt6)** que permite editar diagramas PSTricks con vista previa en vivo, resaltado de sintaxis, compilación asíncrona y exportación a PNG/PDF.

---

## 🌟 Características

- ⚡ **Live Preview** con renderizado de alta calidad vía **PyMuPDF** (`fitz`).
- 📝 Editor con resaltado de sintaxis **PSTricks / LaTeX**, números de línea y `Ctrl+/` para comentar.
- 📚 Biblioteca de snippets PSTricks (formas, nodos, plots, árboles, envoltorio pdftricks…).
- ⚙️ Varios modos de compilación:
  | Modo | Motor recomendado | Notas |
  |------|-------------------|-------|
  | **auto-pst-pdf** | `pdflatex` | Requiere `-shell-escape`. Recomendado. |
  | **pdftricks** | `pdflatex` | El código debe ir en `\begin{pdfpic}…\end{pdfpic}`. |
  | **Xe/Lua directo** | `xelatex` / `lualatex` | PSTricks nativo, sin paquetes extra. |
  | **Clásico** | `latex` | Pipeline `latex → dvips → ps2pdf`. |
- 🛑 Consola de log + lista de errores con salto a línea.
- 🖼️ Exportación a **PNG**, **PDF** y **SVG**.
- 🔤 Configuración de **familia y tamaño de fuente** del editor.
- 📜 Preámbulo personalizado: elegir ruta/nombre del archivo `.pgs` y abrirlo con un **editor externo** desde Preferencias.
- 🌗 Temas oscuro / claro y fondo de cuadrícula transparente.

---

## 🚀 Instalación

### 1. Dependencias Python

```bash
pip install -r requirements.txt
```

(`PySide6`, `PyMuPDF`, `pyqtdarktheme`)

### 2. Motor TeX

Necesitas una distribución TeX con los paquetes **pstricks**, **pst-plot**, **pst-node**, **auto-pst-pdf** (y/o **pdftricks**), **dvips** y **Ghostscript** (`ps2pdf`).

- **TeX Live** o **MiKTeX** (recomendado).
- Para `auto-pst-pdf` / `pdftricks` con `pdflatex` es obligatorio activar **`-shell-escape`** (opción disponible en la barra de herramientas y en Preferencias).

### 3. Ejecutar

```bash
python main.py
```

---

## 📦 Uso rápido

1. Elige el **modo** en la barra de herramientas (por defecto `auto-pst-pdf`).
2. Escribe código PSTricks en la pestaña **Código** (solo el cuerpo del diagrama, o un documento completo).
3. Opcionalmente personaliza el **Preámbulo** (paquetes, `\psset`, etc.).
4. Pulsa **F5** o espera al live-preview.
5. Exporta el resultado con los botones PNG / PDF.

### Ejemplo mínimo (modo auto-pst-pdf)

```latex
\begin{pspicture}(-2,-2)(2,2)
  \pscircle[linewidth=1.5pt,linecolor=blue](0,0){1.5}
  \psline[arrowsize=4pt]{->}(-1.8,0)(1.8,0)
\end{pspicture}
```

### Ejemplo con pdftricks

Cambia el modo a **pdftricks** y escribe:

```latex
\begin{pdfpic}
\begin{pspicture}(0,0)(4,3)
  \psframe[linewidth=1.5pt](0.2,0.2)(3.8,2.8)
  \rput(2,1.5){Hola}
\end{pspicture}
\end{pdfpic}
```

---

## 🗂 Estructura del proyecto

```
pyqpstricks/
├── main.py
├── preamble.pgs          # Preámbulo por defecto (editable)
├── requirements.txt
├── README.md
└── app/
    ├── core/
    │   ├── compiler.py   # Worker asíncrono + pipeline clásico
    │   ├── settings.py
    │   └── template.py   # Plantillas auto-pst-pdf / pdftricks / …
    ├── gui/
    │   ├── main_window.py
    │   ├── editor.py
    │   ├── syntax.py     # Resaltado PSTricks
    │   ├── preview.py
    │   ├── log_viewer.py
    │   ├── preferences_dialog.py
    │   └── snippets_dock.py
    └── resources/
        ├── snippets.json
        └── templates.json
```

---

## 🔧 Notas técnicas

- **auto-pst-pdf** genera en segundo plano un PDF con las figuras PSTricks y las reinserta; por eso necesita `-shell-escape` y un poco más de tiempo.
- En modo **clásico** el worker ejecuta `latex` → `dvips` → `ps2pdf` automáticamente.
- El marcador de plantilla es `<PSTRICKS_CODE>` (también se acepta el antiguo `<TIKZ_CODE>` al cargar preámbulos).
- Si abres un `.tex` completo, la aplicación intenta extraer solo el cuerpo del diagrama para el editor.

---

## Licencia / origen

Fork funcional de **PyQTikz Studio** adaptado a PSTricks y pdftricks/auto-pst-pdf.
Basado en PySide6 y PyMuPDF.
