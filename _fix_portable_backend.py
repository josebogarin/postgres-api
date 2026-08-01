import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from safe_write import safe_patch_py

AB = 'backend/app/api/v1/endpoints/apostador_bets.py'
old_ps = (
    "    import subprocess, textwrap\n"
    "    ps_script = textwrap.dedent(r\"\"\"\n"
    "        $exe     = 'C:\\proyecto FAST API\\backend\\.venv\\Scripts\\python.exe'\n"
    "        $script  = 'C:\\proyecto FAST API\\sync_auto.py'\n"
    "        $workdir = 'C:\\proyecto FAST API'"
)
new_ps = (
    "    import os, subprocess, textwrap\n"
    "    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), \"..\", \"..\", \"..\", \"..\", \"..\"))\n"
    "    ps_script = textwrap.dedent(r\"\"\"\n"
    "        $exe     = '__EXE__'\n"
    "        $script  = '__SCRIPT__'\n"
    "        $workdir = '__WORKDIR__'"
)
old_end = "        Write-Output 'OK'\n    \"\"\").strip()"
new_end = (
    "        Write-Output 'OK'\n"
    "    \"\"\").strip().replace(\"__EXE__\", os.path.join(_root, \"backend\", \".venv\", \"Scripts\", \"python.exe\"))"
    ".replace(\"__SCRIPT__\", os.path.join(_root, \"sync_auto.py\")).replace(\"__WORKDIR__\", _root)"
)
safe_patch_py(AB, [(old_ps, new_ps), (old_end, new_end)])

for F in ('backend/app/api/v1/endpoints/admin.py',
          'backend/app/api/v1/endpoints/admin_extra.py'):
    safe_patch_py(F, [(
        '    bat_path = r"C:\\proyecto FAST API\\run_sync_auto.bat"',
        '    import os as _os\n'
        '    bat_path = _os.path.join(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", "..", "..", "..")), "run_sync_auto.bat")'
    )])

print("OK backend task-registration -> rutas derivadas de __file__")
