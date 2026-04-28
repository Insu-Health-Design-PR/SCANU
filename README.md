This is the Repository for SCAN-U 



insu@insu-desktop:~$ cd ~/Desktop/SCANU-dev_adrian/software
bash: cd: /home/insu/Desktop/SCANU-dev_adrian/software: No such file or directory
insu@insu-desktop:~$ cd ~/Desktop/SCANU-dev_kpr-layer8
insu@insu-desktop:~/Desktop/SCANU-dev_kpr-layer8$ python3 -m pip install -r  layer8_ui/requirements.txt
Defaulting to user installation because normal site-packages is not writeable
ERROR: Could not open requirements file: [Errno 2] No such file or directory: 'layer8_ui/requirements.txt'
insu@insu-desktop:~/Desktop/SCANU-dev_kpr-layer8$ sudo apt update
[sudo] password for insu: 
Sorry, try again.
[sudo] password for insu: 
Get:1 https://pkgs.tailscale.com/stable/ubuntu focal InRelease
Hit:2 https://repo.download.nvidia.com/jetson/common r35.4 InRelease           
Hit:3 https://repo.download.nvidia.com/jetson/t234 r35.4 InRelease             
Hit:4 http://ports.ubuntu.com/ubuntu-ports focal InRelease              
Hit:5 http://ports.ubuntu.com/ubuntu-ports focal-updates InRelease
Hit:6 http://ports.ubuntu.com/ubuntu-ports focal-backports InRelease
Hit:7 http://ports.ubuntu.com/ubuntu-ports focal-security InRelease
Fetched 6,581 B in 1s (4,490 B/s)
Reading package lists... Done
Building dependency tree       
Reading state information... Done
390 packages can be upgraded. Run 'apt list --upgradable' to see them.
insu@insu-desktop:~/Desktop/SCANU-dev_kpr-layer8$ v4l2-ctl --list-devices
bash: v4l2-ctl: command not found
insu@insu-desktop:~/Desktop/SCANU-dev_kpr-layer8$ python3 -m venv .venv
The virtual environment was not created successfully because ensurepip is not
available.  On Debian/Ubuntu systems, you need to install the python3-venv
package using the following command.

    apt install python3.8-venv

You may need to use sudo with that command.  After installing the python3-venv
package, recreate your virtual environment.

Failing command: ['/home/insu/Desktop/SCANU-dev_kpr-layer8/.venv/bin/python3', '-Im', 'ensurepip', '--upgrade', '--default-pip']

insu@insu-desktop:~/Desktop/SCANU-dev_kpr-layer8$ source .venv/bin/activate
bash: .venv/bin/activate: No such file or directory
insu@insu-desktop:~/Desktop/SCANU-dev_kpr-layer8$ python3 -m pip install --upgrade pip
Defaulting to user installation because normal site-packages is not writeable
Requirement already satisfied: pip in /home/insu/.local/lib/python3.8/site-packages (25.0.1)
WARNING: Error parsing dependencies of distro-info: Invalid version: '0.23ubuntu1'
WARNING: Error parsing dependencies of python-debian: Invalid version: '0.1.36ubuntu1'
insu@insu-desktop:~/Desktop/SCANU-dev_kpr-layer8$ pip install -r layer8_ui/requirements.txt
Defaulting to user installation because normal site-packages is not writeable
ERROR: Could not open requirements file: [Errno 2] No such file or directory: 'layer8_ui/requirements.txt'
insu@insu-desktop:~/Desktop/SCANU-dev_kpr-layer8$ pip install -r layer1_radar/requirements.txt
Defaulting to user installation because normal site-packages is not writeable
ERROR: Could not open requirements file: [Errno 2] No such file or directory: 'layer1_radar/requirements.txt'
insu@insu-desktop:~/Desktop/SCANU-dev_kpr-layer8$ python3 - <<'PY'
> import torch
> print('torch:', torch.__version__)
> try:
>     import torchvision
>     print('torchvision:', torchvision.__version__)
> except Exception as exc:
>     print('torchvision import failed:', exc)
> PY
torch: 2.4.1
torchvision: 0.19.1
insu@insu-desktop:~/Desktop/SCANU-dev_kpr-layer8$ source .venv/bin/activate
bash: .venv/bin/activate: No such file or directory
insu@insu-desktop:~/Desktop/SCANU-dev_kpr-layer8$ python3 -m uvicorn layer8_ui.app:app --host 0.0.0.0 --port 8088
Traceback (most recent call last):
  File "/usr/lib/python3.8/runpy.py", line 194, in _run_module_as_main
    return _run_code(code, main_globals, None,
  File "/usr/lib/python3.8/runpy.py", line 87, in _run_code
    exec(code, run_globals)
  File "/home/insu/.local/lib/python3.8/site-packages/uvicorn/__main__.py", line 4, in <module>
    uvicorn.main()
  File "/usr/lib/python3/dist-packages/click/core.py", line 764, in __call__
    return self.main(*args, **kwargs)
  File "/usr/lib/python3/dist-packages/click/core.py", line 717, in main
    rv = self.invoke(ctx)
  File "/usr/lib/python3/dist-packages/click/core.py", line 956, in invoke
    return ctx.invoke(self.callback, **ctx.params)
  File "/usr/lib/python3/dist-packages/click/core.py", line 555, in invoke
    return callback(*args, **kwargs)
  File "/home/insu/.local/lib/python3.8/site-packages/uvicorn/main.py", line 412, in main
    run(
  File "/home/insu/.local/lib/python3.8/site-packages/uvicorn/main.py", line 579, in run
    server.run()
  File "/home/insu/.local/lib/python3.8/site-packages/uvicorn/server.py", line 65, in run
    return asyncio.run(self.serve(sockets=sockets))
  File "/usr/lib/python3.8/asyncio/runners.py", line 44, in run
    return loop.run_until_complete(main)
  File "uvloop/loop.pyx", line 1518, in uvloop.loop.Loop.run_until_complete
  File "/home/insu/.local/lib/python3.8/site-packages/uvicorn/server.py", line 69, in serve
    await self._serve(sockets)
  File "/home/insu/.local/lib/python3.8/site-packages/uvicorn/server.py", line 76, in _serve
    config.load()
  File "/home/insu/.local/lib/python3.8/site-packages/uvicorn/config.py", line 434, in load
    self.loaded_app = import_from_string(self.app)
  File "/home/insu/.local/lib/python3.8/site-packages/uvicorn/importer.py", line 22, in import_from_string
    raise exc from None
  File "/home/insu/.local/lib/python3.8/site-packages/uvicorn/importer.py", line 19, in import_from_string
    module = importlib.import_module(module_str)
  File "/usr/lib/python3.8/importlib/__init__.py", line 127, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "<frozen importlib._bootstrap>", line 1014, in _gcd_import
  File "<frozen importlib._bootstrap>", line 991, in _find_and_load
  File "<frozen importlib._bootstrap>", line 961, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 219, in _call_with_frames_removed
  File "<frozen importlib._bootstrap>", line 1014, in _gcd_import
  File "<frozen importlib._bootstrap>", line 991, in _find_and_load
  File "<frozen importlib._bootstrap>", line 973, in _find_and_load_unlocked
ModuleNotFoundError: No module named 'layer8_ui'
insu@insu-desktop:~/Desktop/SCANU-dev_kpr-layer8$ 
