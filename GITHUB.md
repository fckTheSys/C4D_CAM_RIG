# Публикация репозитория на GitHub

Рекомендуемое **имя репозитория**: `C4D_CAM_RIG`  
**Краткое описание (About)**:

> Orbital camera rig for Cinema 4D: User Data, portable Python Tag, reset & bake (Break).

## Вариант A: через веб-интерфейс

1. На GitHub: **New repository** → имя `C4D_CAM_RIG` → без автогенерации README (или с README — тогда см. слияние ниже).
2. Локально в папке `C4D_CAM_RIG`:

```powershell
cd путь\к\C4D_CAM_RIG
git init
git add .
git commit -m "Initial commit: Cam Rig Builder v1.4.0"
git branch -M main
git remote add origin https://github.com/YOUR_USER/C4D_CAM_RIG.git
git push -u origin main
```

3. На странице репозитория: **Settings** → включите при желании **Issues**, **Discussions**, добавьте **Topics**: `cinema-4d`, `python`, `camera-rig`, `redshift`.

## Вариант B: GitHub CLI (`gh`)

```powershell
cd путь\к\C4D_CAM_RIG
git init
git add .
git commit -m "Initial commit: Cam Rig Builder v1.4.0"
gh repo create C4D_CAM_RIG --public --source=. --remote=origin --push
```

Требуется `gh auth login`.

## Теги релизов (по желанию)

```powershell
git tag -a v1.4.0 -m "Cam Rig Builder 1.4.0"
git push origin v1.4.0
```

На GitHub: **Releases** → создать релиз с вложением ZIP исходников.
