import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import webbrowser
ROOT=Path(__file__).resolve().parent
PIDFILE=ROOT/'work'/'servers.json'
SERVICES=[('map',8000,['-m','uvicorn','backend:app','--host','127.0.0.1','--port','8000'])]

def healthy(port):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/'+'api/health',timeout=2) as r:
            return r.status==200
    except Exception:return False

def main():
    if len(sys.argv)>1 and sys.argv[1]=='stop':
        # Only stop PIDs launched by this project and whose command line still matches.
        if PIDFILE.exists():
            for info in json.loads(PIDFILE.read_text()).values():
                pid=int(info['pid'])
                check=f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}'; if ($p -and $p.CommandLine -like '*{ROOT}*' -and ($p.CommandLine -like '*uvicorn*' -or $p.CommandLine -like '*streamlit*')) {{ Stop-Process -Id {pid} }}"
                subprocess.run(['powershell','-NoProfile','-Command',check],check=False)
            PIDFILE.unlink()
        print('Stopped project services.');return
    (ROOT/'work').mkdir(exist_ok=True)
    existing=json.loads(PIDFILE.read_text()) if PIDFILE.exists() else {}
    for name,port,args in SERVICES:
        if healthy(port):
            print(f'Port {port} is already running; leaving it unchanged.');continue
        with (ROOT/'work'/f'{name}.log').open('a',encoding='utf-8') as log:
            proc=subprocess.Popen([sys.executable,*args],cwd=ROOT,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        existing[name]={'pid':proc.pid,'port':port}
    PIDFILE.write_text(json.dumps(existing))
    for _ in range(35):
        if all(healthy(p) for _,p,_ in SERVICES):break
        time.sleep(1)
    for _,port,_ in SERVICES:
        if healthy(port):
            print(f'Ready: http://127.0.0.1:{port}')
            if '--no-browser' not in sys.argv:webbrowser.open(f'http://127.0.0.1:{port}')
        else:print(f'Port {port} failed to start. See work/*.log.')

if __name__=='__main__':main()
