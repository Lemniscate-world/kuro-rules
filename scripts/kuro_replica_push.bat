@echo off
REM Push replica kuro.db -> serveur standby (toutes les 5 min via planificateur).
C:\Python314\python.exe C:\Users\Utilisateur\Documents\kuro-rules\scripts\kuro_replica_push.py >> "%USERPROFILE%\.kuro\replica-push.log" 2>&1
