@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" amd64 >nul 2>&1

cd /d "%~dp0"

echo Compilando fco_cpp...
rem /utf-8: fontes e mensagens (com acento) em UTF-8.
cl.exe /utf-8 /O2 /EHsc /std:c++17 /MD /LD /DNDEBUG ^
    /I"C:\Users\gusta\AppData\Local\Programs\Python\Python313\Include" ^
    /I"C:\Users\gusta\AppData\Local\Programs\Python\Python313\Lib\site-packages\pybind11\include" ^
    src\geometry.cpp src\constitutive.cpp src\equilibrium.cpp src\solver.cpp src\verifier.cpp src\bindings.cpp ^
    /Fe:_fco_native.cp313-win_amd64.pyd ^
    /link /LIBPATH:"C:\Users\gusta\AppData\Local\Programs\Python\Python313\libs" python313.lib > build_log.txt 2>&1

if %ERRORLEVEL% EQU 0 (
    echo BUILD OK >> build_log.txt
    echo BUILD OK
    del /q *.obj 2>nul
) else (
    echo BUILD FAILED >> build_log.txt
    echo BUILD FAILED
)
type build_log.txt
