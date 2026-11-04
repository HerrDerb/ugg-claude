@echo off
rem entry point on Windows: cavewall [board|popup|seed|hook]
set "PYTHONPATH=%~dp0"
where py >nul 2>nul && (py -3 -m cavewall %*) || (python -m cavewall %*)
