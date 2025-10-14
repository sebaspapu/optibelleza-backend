# Ecommerce Website - Guía de Ejecución Local

Este proyecto contiene un backend (FastAPI). Aquí tienes los pasos y detalles para levantarlo en tu máquina sin depender de servicios externos.

---

## Requisitos previos
- Python 3.11+ (recomendado)
- Git

---

## 1. Clonar el repositorio
```bash
git clone <URL_DEL_REPO>
cd <carpeta_del_repo>
```

---

### a) Crear y activar entorno virtual
```bash
Usar pyenv (recomendado)
pyenv local 3.11.9

python -m venv .venv
# En Windows PowerShell:
.venv\Scripts\Activate.ps1
# En bash:
source .venv/bin/activate
```

### b) Ingresar a la carpeta app
```bash
cd .\app\
```

### c) Instalar dependencias
```bash
pip install -r requirements.txt
```

### d) Ejecutar el backend
```bash
uvicorn main:app --reload
```
- El backend quedará corriendo en: http://127.0.0.1:8000

---