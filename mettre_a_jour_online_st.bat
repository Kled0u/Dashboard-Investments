@echo off
title Mise a jour du Dashboard

echo =========================================
echo  MISE A JOUR DU DASHBOARD VERS GITHUB
echo =========================================
echo.

echo --- Etape 1: Ajout des fichiers modifies...
git add .
echo OK.
echo.

echo --- Etape 2: Creation du commit automatique...
git commit -m "Mise a jour du %date% a %time%"
echo OK.
echo.

echo --- Etape 3: Envoi des changements sur GitHub...
git push origin main
echo.

echo =========================================
echo    Mise a jour terminee !
echo =========================================
echo.
pause