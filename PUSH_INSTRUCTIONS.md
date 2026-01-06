# Instrucciones para subir a GitHub

## Opción 1: Usar Personal Access Token (PAT) - RECOMENDADA

1. **Crear un Personal Access Token en GitHub:**
   - Ve a: https://github.com/settings/tokens
   - Click en "Generate new token" → "Generate new token (classic)"
   - Nombre: "Excel Uploader App"
   - Selecciona scope: `repo` (acceso completo)
   - Click en "Generate token"
   - **Copia el token** (solo se muestra una vez)

2. **Configurar el remote con el token:**
   ```bash
   git remote set-url origin https://TU_TOKEN@github.com/diego21ruiz-desarrollos/excel_uploader_storage.git
   ```
   (Reemplaza TU_TOKEN con el token que copiaste)

3. **Hacer push:**
   ```bash
   git push -u origin main
   ```

## Opción 2: Usar GitHub CLI (si está instalado)

```bash
gh auth login
git push -u origin main
```

## Opción 3: Configurar credenciales de Git

```bash
git config --global credential.helper store
git push -u origin main
```
(Te pedirá usuario y contraseña/token la primera vez)

## Verificar estado actual

```bash
git status
git remote -v
git log --oneline
```

