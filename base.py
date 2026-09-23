import time, os, sys, math, random, shutil, subprocess, socket, getpass, platform

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

R = '\033[0m'
def fg(n): return f'\033[38;5;{n}m'

C = {
    'border': fg(240), 'btitle': fg(81),  'label':  fg(245),
    'value':  fg(231), 'green':  fg(82),  'yellow': fg(220),
    'red':    fg(203), 'blue':   fg(39),  'magenta':fg(207),
    'dim':    fg(238), 'cyan':   fg(51),
    'py_blue': fg(33), 'py_yellow': fg(220), 'py_eye': fg(231),
}

USER = getpass.getuser()
try:    HOST = socket.gethostname()
except: HOST = 'linux-on-python'

IS_ANDROID = 'ANDROID_ROOT' in os.environ or 'ANDROID_DATA' in os.environ \
             or 'android' in platform.platform().lower()
IS_ROOT    = hasattr(os, 'geteuid') and os.geteuid() == 0
PSUTIL_OK  = HAS_PSUTIL and not IS_ANDROID

SISTEMA = "Linux on Python beta1.0"

PY_LOGO_RAW = r"""
                                .::::::::::.
                              .::``::::::::::.
                              :::..:::::::::::
                              ````````::::::::
                      .::::::::::::::::::::::: iiiiiii,
                   .:::::::::::::::::::::::::: iiiiiiiii.
                   ::::::::::::::::::::::::::: iiiiiiiiii
                   ::::::::::::::::::::::::::: iiiiiiiiii
                   :::::::::: ,,,,,,,,,,,,,,,,,iiiiiiiiii
                   :::::::::: iiiiiiiiiiiiiiiiiiiiiiiiiii
                   `::::::::: iiiiiiiiiiiiiiiiiiiiiiiiii`
                      `:::::: iiiiiiiiiiiiiiiiiiiiiii`
                              iiiiiiii,,,,,,,,
                              iiiiiiiiiii''iii
                              `iiiiiiiiii..ii`
                                `iiiiiiiiii`
""".strip('\n')

def _colorize_py_line(line):
    out = []; n = len(line)
    for i, ch in enumerate(line):
        if ch == "'":
            out.append(f"{C['py_eye']}{ch}"); continue
        if ch == '.':
            lb = line[max(0,i-2):i]; la = line[i+1:min(n,i+3)]
            if 'i' in lb and 'i' in la:
                out.append(f"{C['py_eye']}{ch}"); continue
            out.append(f"{C['py_blue']}{ch}"); continue
        if ch in 'i,':   out.append(f"{C['py_yellow']}{ch}")
        elif ch in ':`': out.append(f"{C['py_blue']}{ch}")
        else:            out.append(ch)
    out.append(R); return ''.join(out)

_LINES_RAW = PY_LOGO_RAW.split('\n')
_LOGO_W    = max(len(l) for l in _LINES_RAW)
PY_LOGO    = [_colorize_py_line(l.ljust(_LOGO_W)) for l in _LINES_RAW]
BLANK      = " " * _LOGO_W

def _read(path):
    try:
        with open(path, 'r', errors='ignore') as f: return f.read()
    except Exception: return None

def real_cpu_count():
    if HAS_PSUTIL:
        try:
            n = psutil.cpu_count(logical=True)
            if n: return n
        except Exception: pass
    try:
        txt = _read('/proc/cpuinfo') or ''
        n = sum(1 for l in txt.splitlines() if l.lower().startswith('processor'))
        if n: return n
    except Exception: pass
    return os.cpu_count() or 4

def real_cpu_name():
    txt = _read('/proc/cpuinfo') or ''
    for line in txt.splitlines():
        if 'model name' in line or 'Hardware' in line or 'model' in line.lower():
            try: return line.split(':',1)[1].strip()
            except Exception: pass
    return platform.processor() or platform.machine() or 'Unknown CPU'

def real_mem():
    if HAS_PSUTIL:
        try:
            v = psutil.virtual_memory()
            return v.total, v.total-v.available, v.available, getattr(v,'cached',0), v.percent
        except Exception: pass
    txt = _read('/proc/meminfo')
    if txt:
        vals = {}
        for line in txt.splitlines():
            p = line.split(':')
            if len(p) == 2:
                k = p[0].strip(); v = p[1].strip().split()[0]
                try: vals[k] = int(v) * 1024
                except ValueError: pass
        total = vals.get('MemTotal',0); free = vals.get('MemFree',0)+vals.get('Buffers',0)
        cached= vals.get('Cached',0)+vals.get('SReclaimable',0)
        avail = vals.get('MemAvailable', free+cached)
        if total:
            used = total-avail
            return total, used, avail, cached, used/total*100
    return 0,0,0,0,0.0

def real_swap():
    if HAS_PSUTIL:
        try:
            s = psutil.swap_memory(); return s.total, s.used, s.percent
        except Exception: pass
    txt = _read('/proc/swaps') or ''
    total = used = 0
    for line in txt.splitlines()[1:]:
        p = line.split()
        if len(p) >= 4:
            try: total += int(p[2])*1024; used += int(p[3])*1024
            except ValueError: pass
    return total, used, (used/total*100) if total else 0

def real_uptime():
    if HAS_PSUTIL:
        try: return time.time() - psutil.boot_time()
        except Exception: pass
    txt = _read('/proc/uptime')
    if txt:
        try: return float(txt.split()[0])
        except Exception: pass
    return 0.0

def real_net():
    if HAS_PSUTIL:
        try:
            n = psutil.net_io_counters(); return n.bytes_recv, n.bytes_sent
        except Exception: pass
    txt = _read('/proc/net/dev')
    if txt:
        r = s = 0
        for line in txt.splitlines()[2:]:
            p = line.split()
            if len(p) >= 10 and ':' in p[0]:
                try: r += int(p[1]); s += int(p[9])
                except ValueError: pass
        return r, s
    return None

def real_procs():
    if HAS_PSUTIL and not IS_ANDROID:
        try:
            out = []
            for p in psutil.process_iter(['pid','name','username','memory_info','num_threads']):
                try:
                    i = p.info
                    out.append({'pid':i['pid'],'name':(i['name'] or '?')[:30],
                                'user':(i['username'] or '?')[:10],'cpu':p.cpu_percent(),
                                'mem_mb':(i['memory_info'].rss/1024/1024) if i['memory_info'] else 0,
                                'mem_pct':0.0,'thr':i['num_threads'] or 0})
                except Exception: continue
            if out: return out
        except Exception: pass
    nomes = ['init','system_server','surfaceflinger','zygote','zygote64',
             'com.android.systemui','com.android.launcher3','logd','servicemanager',
             'netd','vold','healthd','adbd','wpa_supplicant','rild','media.codec',
             'media.swcodec','com.android.phone','com.android.settings','pydroid']
    return [{'pid':random.randint(300,30000),'name':n,'user':'root' if i<8 else USER,
             'cpu':random.uniform(0,8),'mem_mb':random.uniform(10,300),
             'mem_pct':random.uniform(0.3,3.0),'thr':random.randint(1,25)}
            for i, n in enumerate(nomes)]

SIM = {'cores': [random.uniform(5,25) for _ in range(8)]}

def safe_cpu_percpu(ncpu):
    if PSUTIL_OK:
        try:
            v = psutil.cpu_percent(percpu=True, interval=0)
            while len(v) < ncpu: v.append(0.0)
            return v[:ncpu]
        except Exception: pass
    while len(SIM['cores']) < ncpu: SIM['cores'].append(random.uniform(5,25))
    for i in range(ncpu):
        SIM['cores'][i] = max(1,min(99,SIM['cores'][i]+random.uniform(-10,10)))
    return SIM['cores'][:ncpu]

STAGES = [
    "Detecting hardware",
    "Partitioning /dev/sda",
    "Formatting as ext4",
    "Configuring swap",
    "Copying system files",
    "Installing Python kernel",
    "Configuring GRUB",
    "Installing drivers",
    "Configuring network",
    "Creating user",
    "Installing essential packages",
    "Graphical environment",
    "Optimizing system",
    f"Finalizing {SISTEMA}",
]
SPINNER = "|/-\\|/-\\"

def limpar_tela(): os.system("cls" if os.name == "nt" else "clear")

def term_width():
    try: return shutil.get_terminal_size((80,24)).columns
    except Exception: return 80

def barra(pct, width):
    pct = max(0,min(100,pct)); f = int(width*pct/100)
    return f"{C['green']}{'#'*f}{C['dim']}{'-'*(width-f)}{R}"

def instalar():
    limpar_tela()
    tw = term_width()

    # compact mode for very narrow terminals
    if tw < 26:
        print(f"{C['btitle']}{SISTEMA} - Installer{R}\n")
        for i, stage in enumerate(STAGES):
            pct = ((i + 1) / len(STAGES)) * 100
            nome = stage[:max(4, tw-8)]
            print(f"{C['value']}[{pct:3.0f}%]{R} {C['label']}{nome}{R}")
            time.sleep(0.35)
        print(f"\n{C['green']}[OK] {SISTEMA} installed successfully!{R}")
        time.sleep(0.4)
        if IS_ANDROID and not IS_ROOT:
            print(f"{C['yellow']}[i] Android detected - some data will be simulated.{R}")
        print(f"{C['label']}Type 'help' to see the commands.{R}\n")
        return

    # header
    W = min(tw, 70)
    print(f"{C['cyan']}{'='*W}{R}")
    print(f"{C['btitle']}{(' ' + SISTEMA + ' - Installer ').center(W)}{R}")
    print(f"{C['cyan']}{'='*W}{R}\n")
    time.sleep(0.6)

    total = len(STAGES)

    # adaptive layout:
    # [spinner 1] [sp 1] [bar bw] [sp 1] [pct% 6] [sp 1] [name nome_w]
    fixo   = 10
    disp   = max(15, tw - fixo - 1)
    nome_w = min(40, max(6, int(disp * 0.55)))
    bw     = max(6, disp - nome_w)
    # safety: never exceed terminal width
    while fixo + bw + nome_w > tw - 1:
        if bw > 6:       bw -= 1
        elif nome_w > 4: nome_w -= 1
        else: break

    # ── each stage goes from 0% to 100% ──
    for i, stage in enumerate(STAGES):
        nome = stage[:nome_w].ljust(nome_w)
        for t in range(21):                       # 21 frames: 0,5,...,100
            pct = (t / 20) * 100                  # per-stage progress
            sp  = SPINNER[t % len(SPINNER)]
            sys.stdout.write(
                f"\r{C['blue']}{sp}{R} {barra(pct, bw)} "
                f"{C['value']}{pct:5.1f}%{R} {C['label']}{nome}{R}"
            )
            sys.stdout.flush()
            time.sleep(random.uniform(0.015, 0.045))
        # completion line for this stage
        sys.stdout.write(
            f"\r{C['green']}+{R} {barra(100, bw)} "
            f"{C['value']}{100:5.1f}%{R} "
            f"{C['green']}{nome}{R}\n"
        )
        sys.stdout.flush()

    print(f"\n{C['green']}[OK] {SISTEMA} installed successfully!{R}")
    time.sleep(0.5)
    if IS_ANDROID and not IS_ROOT:
        print(f"{C['yellow']}[i] Android detected - some data will be simulated.{R}")
    print(f"{C['label']}Type 'help' to see the commands.{R}\n")

FAKE_REPO      = {}
INSTALLED_FAKE = set()
COMANDOS       = {}
PACOTE_COMANDO = {}
HELP_CMD       = {}

PROMPT = f"{C['green']}{USER}@{HOST}{R} {C['blue']}~{R} {C['value']}${R} "

def cmd_neofetch():
    cpu = real_cpu_name(); ncpu = real_cpu_count()
    mem_t, mem_u, _, _, _ = real_mem(); up = real_uptime()
    def fmt_up(s):
        s = int(s); h,r = divmod(s,3600); m,_ = divmod(r,60)
        if h >= 24: d,h = divmod(h,24); return f"{d}d {h}h {m}m"
        return f"{h}h {m}m"
    def gb(b): return f"{b/1e9:.1f}GiB"
    def swap_str():
        st, su, _ = real_swap(); return f"{gb(su)} / {gb(st)}" if st else "none"
    titulo = f"{C['green']}{USER}{C['label']}@{C['green']}{HOST}{R}"
    sep    = f"{C['dim']}{'-'*26}{R}"
    info = [titulo, sep,
        f"{C['green']}OS{R}       {SISTEMA}",
        f"{C['green']}Base{R}     {platform.system()} {platform.release()}",
        f"{C['green']}Arch{R}     {platform.machine()}",
        f"{C['green']}Kernel{R}   {platform.version()[:38]}",
        f"{C['green']}Uptime{R}   {fmt_up(up) if up else 'n/a'}",
        f"{C['green']}Shell{R}    Python {platform.python_version()}",
        f"{C['green']}CPU{R}      {cpu[:42]}",
        f"{C['green']}Cores{R}    {ncpu}",
        f"{C['green']}Memory{R}   {gb(mem_u)} / {gb(mem_t)}",
        f"{C['green']}Swap{R}     {swap_str()}",
        f"{C['green']}Packages{R} {len(INSTALLED_FAKE)} / {len(FAKE_REPO)} (apt fake)",
        "",
        "".join(f"{fg(i)}o{R}" for i in
                (240,245,250,255,82,220,203,39,207,81,51,215,118))]
    print()
    for i in range(max(len(PY_LOGO), len(info))):
        esq  = PY_LOGO[i] if i < len(PY_LOGO) else BLANK
        dir_ = info[i]    if i < len(info)    else ""
        print(f"{esq}  {dir_}")
    print()

def _fake_sudo_auth():
    print(f"{C['label']}[sudo] password for {USER}:{R} ", end='', flush=True)
    try: _ = input()
    except (EOFError, KeyboardInterrupt): print(); return False
    time.sleep(0.4); print(); return True

def _pip_run(args):
    cmd = [sys.executable, '-m', 'pip'] + args
    try: return subprocess.run(cmd, check=False).returncode
    except FileNotFoundError:
        print(f"{C['red']}E: pip not available{R}\n"); return 1

def _fmt_kb(kb):
    if kb >= 1024*1024: return f"{kb/1024/1024:.1f} GB"
    if kb >= 1024:      return f"{kb/1024:.1f} MB"
    return f"{kb} kB"

def _apt_header():
    print(f"{C['label']}Reading package lists... Done{R}"); time.sleep(0.3)
    print(f"{C['label']}Building dependency tree... Done{R}"); time.sleep(0.3)
    print(f"{C['label']}Reading state information... Done{R}"); time.sleep(0.2)

def _apt_update():
    print(f"{C['label']}Get:1 http://archive.deepseek.org stable InRelease{R}")
    time.sleep(0.4)
    print(f"{C['green']}All packages are up to date.{R}\n")

def _apt_upgrade():
    _apt_header()
    print(f"{C['green']}0 upgraded, 0 newly installed, 0 to remove.{R}\n")

def _apt_autoremove():
    print(f"{C['label']}0 packages automatically removed.{R}\n")

def _apt_install(pacotes, via_sudo):
    if not pacotes:
        print(f"{C['red']}E: No packages specified{R}\n"); return
    if not via_sudo:
        print(f"{C['red']}E: You must be root to perform this operation "
              f"(try 'sudo apt-get install {' '.join(pacotes)}'){R}\n"); return
    fake = [p for p in pacotes if p in FAKE_REPO]
    real = [p for p in pacotes if p not in FAKE_REPO]
    _apt_header()
    ja = [p for p in fake if p in INSTALLED_FAKE]
    fake = [p for p in fake if p not in INSTALLED_FAKE]
    if ja: print(f"{C['label']}{' '.join(ja)} is/are already installed.{R}\n")
    if fake:
        total_kb = sum(FAKE_REPO[p][1] for p in fake)
        print(f"{C['label']}The following NEW packages will be installed:{R}")
        for p in fake: print(f"  {C['green']}{p}{R}")
        print(f"{C['label']}Need to get {_fmt_kb(total_kb)} of archives.{R}")
        print(f"{C['label']}After this operation, {_fmt_kb(int(total_kb*2.3))} "
              f"of additional disk space will be used.{R}")
        time.sleep(0.3)
        for i, p in enumerate(fake, 1):
            _, kb = FAKE_REPO[p]
            print(f"{C['label']}Get:{i} http://archive.deepseek.org stable/main "
                  f"amd64 {p} amd64 1.0-1 [{_fmt_kb(kb)}]{R}")
            time.sleep(random.uniform(0.1,0.25))
        for p in fake:
            print(f"{C['label']}Unpacking {p} (1.0-1) ...{R}"); time.sleep(0.1)
        for p in fake:
            print(f"{C['green']}Setting up {p} (1.0-1) ...{R}"); time.sleep(0.12)
            INSTALLED_FAKE.add(p)
        for g in ('man-db','hicolor-icon-theme','desktop-file-utils'):
            print(f"{C['label']}Processing triggers for {g} ...{R}"); time.sleep(0.1)
        print()
    if real:
        print(f"{C['label']}Downloading from pypi.org...{R}")
        ok, falha = [], []
        for p in real:
            time.sleep(0.25); print(f"\n{C['dim']}$ pip install {p}{R}")
            rc = _pip_run(['install', p]); (ok if rc == 0 else falha).append(p)
        print()
        if ok:
            print(f"{C['green']}Installed:{R}")
            for p in ok: print(f"  {C['green']}[+] {p}{R}")
        if falha: print(f"{C['red']}Failed: {' '.join(falha)}{R}")
        print()

def _apt_remove(pacotes, via_sudo):
    if not pacotes:
        print(f"{C['red']}E: No packages specified{R}\n"); return
    if not via_sudo:
        print(f"{C['red']}E: You must be root to perform this operation{R}\n"); return
    fake = [p for p in pacotes if p in INSTALLED_FAKE]
    real = [p for p in pacotes if p not in INSTALLED_FAKE]
    if fake:
        _apt_header()
        for p in fake:
            print(f"{C['label']}Removing {p} (1.0-1) ...{R}"); time.sleep(0.12)
            INSTALLED_FAKE.discard(p)
        print(f"{C['green']}Purging configuration files...{R}\n"); time.sleep(0.15)
    if real:
        _apt_header()
        for p in real:
            print(f"\n{C['dim']}$ pip uninstall -y {p}{R}")
            _pip_run(['uninstall', '-y', p])
        print()

def _apt_search(termos):
    if not termos:
        print(f"{C['red']}E: No search term{R}\n"); return
    termo = ' '.join(termos).lower()
    print(f"{C['label']}Searching archive.deepseek.org for '{termo}'...{R}\n")
    hits = [(n, FAKE_REPO[n][0]) for n in sorted(FAKE_REPO)
            if termo in n or termo in FAKE_REPO[n][0].lower()]
    if not hits:
        print(f"{C['dim']}(nothing found){R}\n"); return
    for n, d in hits:
        marca = f" {C['green']}[installed]{R}" if n in INSTALLED_FAKE else ""
        print(f"{C['value']}{n:<22}{R} {C['label']}{d}{R}{marca}")
    print()

def _apt_list():
    print(f"{C['label']}Installed ({len(INSTALLED_FAKE)}/{len(FAKE_REPO)}):{R}")
    if not INSTALLED_FAKE:
        print(f"  {C['dim']}(none){R}")
    else:
        for p in sorted(INSTALLED_FAKE):
            print(f"  {C['green']}{p:<22}{R} {C['value']}1.0-1{R}")
    print()

def _apt_show(pacotes):
    if not pacotes:
        print(f"{C['red']}E: No packages specified{R}\n"); return
    for p in pacotes:
        if p in FAKE_REPO:
            desc, kb = FAKE_REPO[p]
            print(f"{C['btitle']}Package: {p}{R}")
            print(f"{C['label']}Version: 1.0-1")
            print(f"Priority: optional")
            print(f"Section: universe/utils")
            print(f"Architecture: amd64")
            print(f"Installed-Size: {int(kb*2.3)} kB")
            print(f"Description: {desc}{R}\n")
        else:
            _pip_run(['show', p]); print()

def _apt_help():
    print(f"{C['btitle']}Usage: apt-get <subcommand> [packages]{R}")
    for s, d in [('update','update package lists'),
                 ('upgrade','upgrade installed packages'),
                 ('install <pkg>','install package (requires sudo)'),
                 ('remove <pkg>','remove package (requires sudo)'),
                 ('autoremove','remove orphan packages'),
                 ('list','list installed packages'),
                 ('show <pkg>','show package details'),
                 ('search <term>','search repository'),
                 ('help','this help')]:
        print(f"  {C['green']}{s:<18}{R} {C['label']}{d}{R}")
    print()

def cmd_apt(args, via_sudo=False):
    partes = args.split()
    if not partes: _apt_help(); return
    sub, resto = partes[0], partes[1:]
    if   sub == 'update':                    _apt_update()
    elif sub in ('upgrade','dist-upgrade'):  _apt_upgrade()
    elif sub == 'autoremove':                _apt_autoremove()
    elif sub == 'install':                   _apt_install(resto, via_sudo)
    elif sub in ('remove','purge'):          _apt_remove(resto, via_sudo)
    elif sub == 'search':                    _apt_search(resto)
    elif sub in ('list','list-installed'):   _apt_list()
    elif sub == 'show':                      _apt_show(resto)
    elif sub in ('help','--help','-h'):      _apt_help()
    else:
        print(f"{C['red']}E: Unknown subcommand '{sub}'{R}\n"); _apt_help()

def cmd_pip(args):
    partes = args.split()
    if not partes: _pip_run(['--help']); return
    sub = partes[0]
    if sub == 'install':     _pip_run(partes)
    elif sub == 'uninstall': _pip_run(['uninstall','-y']+partes[1:])
    elif sub in ('list','freeze','show','index','check','download','cache'):
        _pip_run(partes)
    elif sub in ('--version','-V'): _pip_run(['--version'])
    else:
        print(f"{C['red']}pip: unknown command '{sub}'{R}\n")

def cmd_sudo(args):
    if not args:
        print(f"{C['red']}usage: sudo <command> [args...]{R}\n"); return
    if not _fake_sudo_auth():
        print(f"{C['red']}sudo: authentication failed{R}\n"); return
    partes = args.split(); cmd, resto = partes[0], ' '.join(partes[1:])
    if cmd in ('apt','apt-get'):   cmd_apt(resto, via_sudo=True)
    elif cmd in ('pip','pip3'):    cmd_pip(resto)
    elif cmd == 'whoami':          print(f"{C['value']}root{R}\n")
    elif cmd == 'reboot':
        print(f"{C['yellow']}Broadcast message: system is restarting...{R}")
        time.sleep(1.2); print(f"{C['dim']}(blocked){R}\n")
    else:
        if cmd in COMANDOS:
            pacote = PACOTE_COMANDO.get(cmd)
            if pacote is None or pacote in INSTALLED_FAKE:
                try: COMANDOS[cmd](resto)
                except Exception as e: print(f"{C['red']}{cmd}: {e}{R}\n")
                return
        print(f"{C['red']}sudo: {cmd}: command not found{R}\n")

def executar_btop():
    real = shutil.which('btop')
    if real:
        try: subprocess.run([real], check=False); return
        except Exception: pass
    subprocess.run([sys.executable, os.path.abspath(__file__), '--btop'], check=False)

# ===== CONTINUA NA PARTE 2 =====



FAKE_REPO.update({
    'firefox':('Mozilla Firefox',62000),'chrome':('Google Chrome',88000),
    'chromium':('Chromium',74000),'brave-browser':('Brave',95000),
    'opera':('Opera',82000),'vivaldi':('Vivaldi',88000),'lynx':('navegador texto',1900),
    'w3m':('navegador texto',1400),'tor-browser':('Tor Browser',72000),
    'vim':('editor vi',3800),'neovim':('vim moderno',6400),'nano':('editor simples',800),
    'emacs':('GNU Emacs',42000),'micro':('editor moderno',2400),'helix':('editor Rust',3200),
    'code':('VS Code',95000),'sublime-text':('Sublime',42000),'kate':('editor KDE',18000),
    'gedit':('editor GNOME',6500),'geany':('IDE leve',9800),
    'bash':('Bourne Again Shell',1400),'zsh':('Z shell',2400),'fish':('Friendly shell',3200),
    'dash':('shell POSIX',120),'ksh':('Korn shell',1400),'nushell':('shell Rust',8500),
    'tmux':('multiplexador',950),'screen':('GNU screen',780),'zellij':('multiplexador Rust',3400),
    'byobu':('wrapper tmux',580),'alacritty':('terminal GPU',4200),'kitty':('terminal GPU',5800),
    'wezterm':('terminal Rust',9800),'konsole':('terminal KDE',6500),
    'gnome-terminal':('terminal GNOME',4200),'xterm':('X classico',850),
    'htop':('visualizador processos',350),'btop':('monitor moderno',1200),
    'bashtop':('monitor bash',480),'bpytop':('monitor Python',980),
    'glances':('monitor curses',2400),'gotop':('monitor Go',2400),
    'nmon':('monitor Nigel',950),'iotop':('monitor I/O',420),
    'iostat':('estatisticas I/O',850),'vmstat':('estatisticas memoria',280),
    'dstat':('estatisticas sistema',380),'iftop':('banda por conexao',680),
    'nethogs':('banda por processo',580),'neofetch':('info sistema',250),
    'fastfetch':('neofetch C',980),'screenfetch':('neofetch bash',420),
    'pfetch':('neofetch minimal',45),'inxi':('info detalhada',1800),
    'lshw':('listagem hardware',3200),'dmidecode':('SMBIOS',950),
    'hwinfo':('info hardware',5800),'lm-sensors':('sensores',850),
    'smartmontools':('S.M.A.R.T.',2400),'acpi':('bateria',380),
    'powertop':('consumo energia',4500),'stress':('teste carga',180),
    'sysbench':('benchmark',1800),'fio':('benchmark I/O',4200),
    'memtester':('teste RAM',380),
    'curl':('transferencia HTTP',480),'wget':('baixador',950),
    'aria2':('baixador multi',1800),'httpie':('cliente HTTP',1400),
    'xh':('HTTPie Rust',2400),'hey':('carga HTTP',1800),'ab':('Apache Bench',780),
    'wrk':('benchmark HTTP',580),'rsync':('sincronizador',2400),
    'openssh-client':('cliente SSH',2800),'openssh-server':('servidor SSH',3200),
    'sshfs':('FS via SSH',950),'mosh':('SSH movel',1400),
    'netcat':('canivete TCP/IP',380),'ncat':('netcat nmap',780),
    'socat':('relay',580),'telnet':('cliente telnet',240),
    'tcpdump':('captura pacotes',1800),'wireshark':('analise trafego',88000),
    'nmap':('scanner portas',4200),'masscan':('scanner massivo',2800),
    'mtr':('traceroute+ping',480),'traceroute':('rastreador rota',380),
    'iputils-ping':('ping',420),'dnsutils':('dig/nslookup',680),
    'whois':('consulta WHOIS',180),'iperf3':('teste banda',780),
    'net-tools':('ifconfig/netstat',1100),'iproute2':('ip/ss/tc',1800),
    'ethtool':('config NICs',580),'iw':('ferramentas Wi-Fi',780),
    'lsof':('arquivos abertos',420),'fuser':('usuarios de arquivos',180),
    'git':('controle versao',15000),'git-lfs':('Git LFS',4200),
    'gh':('GitHub CLI',18000),'svn':('Subversion',9800),
    'mercurial':('Mercurial',5800),
    'gcc':('compilador C',45000),'g++':('compilador C++',52000),
    'clang':('LLVM C/C++',68000),'llvm':('LLVM',95000),
    'cmake':('build system',18000),'meson':('build moderno',4200),
    'ninja':('build rapido',680),'make':('automacao build',1200),
    'autoconf':('configure',1200),'automake':('Makefile.in',950),
    'gdb':('debugger GNU',12000),'valgrind':('vazamentos',23000),
    'strace':('rastreio syscalls',680),'ltrace':('rastreio libs',580),
    'perf':('profiling',18000),'binutils':('ld/as/objdump',9800),
    'ccache':('cache compilacao',2400),
    'python3':('Python 3',28000),'python3-pip':('pip',2400),
    'python3-venv':('venv',980),'python2':('Python 2 legado',22000),
    'pypy3':('Python JIT',38000),'uv':('Python Rust',9800),
    'poetry':('deps Python',4200),'pipx':('apps Python',1400),
    'nodejs':('Node.js',32000),'npm':('npm',8800),'yarn':('Yarn',5800),
    'pnpm':('pnpm',4200),'bun':('Bun',42000),'deno':('Deno',95000),
    'typescript':('TypeScript',9800),'ruby':('Ruby',12000),
    'gem':('gem',2400),'rails':('Rails',18000),'bundler':('bundler',1400),
    'perl':('Perl',24000),'php':('PHP',22000),'composer':('Composer',3400),
    'java':('OpenJDK',68000),'kotlin':('Kotlin',22000),'scala':('Scala',45000),
    'gradle':('Gradle',45000),'maven':('Maven',38000),
    'go':('Go',120000),'rustc':('Rust',68000),'cargo':('Cargo',12000),
    'rustup':('toolchains Rust',9800),'lua5.4':('Lua',980),'luajit':('LuaJIT',1800),
    'r-base':('R',32000),'julia':('Julia',88000),'ghc':('Haskell',180000),
    'swift':('Swift',140000),'dotnet-sdk':('SDK .NET',120000),
    'elixir':('Elixir',18000),'erlang':('Erlang',45000),'zig':('Zig',45000),
    'dart':('Dart',88000),'nim':('Nim',12000),'crystal':('Crystal',22000),
    'sqlite3':('SQLite',980),'mysql-server':('MySQL',58000),
    'mariadb-server':('MariaDB',52000),'postgresql':('PostgreSQL',42000),
    'mongodb':('MongoDB',95000),'redis-server':('Redis',9800),
    'memcached':('Memcached',2400),'cassandra':('Cassandra',180000),
    'influxdb':('InfluxDB',68000),'etcd':('etcd',45000),
    'nginx':('Nginx',1400),'apache2':('Apache',9800),'caddy':('Caddy',9800),
    'haproxy':('HAProxy',3400),'traefik':('Traefik',38000),
    'gunicorn':('Gunicorn',1800),'uwsgi':('uWSGI',2400),
    'docker':('Docker',85000),'docker-compose':('compose',12000),
    'podman':('Podman',68000),'containerd':('containerd',45000),
    'kubernetes':('Kubernetes',180000),'kubectl':('kubectl',45000),
    'minikube':('Kubernetes local',120000),'k9s':('TUI K8s',9800),
    'helm':('Helm',18000),'vagrant':('Vagrant',120000),
    'virtualbox':('VirtualBox',180000),'qemu':('QEMU',45000),
    'libvirt':('libvirt',18000),'lxc':('LXC',12000),'lxd':('LXD',38000),
    'ffmpeg':('FFmpeg',32000),'ffprobe':('analise midia',9800),
    'vlc':('VLC',48000),'mpv':('mpv',8500),'mplayer':('mplayer',9800),
    'cmus':('player TUI',1800),'mpd':('MPD',2400),'ncmpcpp':('cliente MPD',3400),
    'audacity':('Audacity',32000),'gimp':('GIMP',62000),
    'inkscape':('Inkscape',45000),'krita':('Krita',88000),
    'blender':('Blender',220000),'imagemagick':('ImageMagick',18000),
    'exiftool':('EXIF',9800),'sox':('SOX',3400),'lame':('MP3',980),
    'flac':('FLAC',780),'opus-tools':('Opus',480),'optipng':('otim PNG',280),
    'jpegoptim':('otim JPEG',180),
    'steam':('Steam',220000),'lutris':('Lutris',18000),'wine':('Wine',120000),
    'dosbox':('DOSBox',6800),'scummvm':('SCUMMVM',9800),'mame':('MAME',180000),
    'retroarch':('RetroArch',45000),'supertuxkart':('SuperTuxKart',180000),
    'openttd':('OpenTTD',45000),'nethack':('Nethack',2400),
    'gnugo':('GNU Go',1800),'gnuchess':('GNU Chess',1400),
    'libreoffice':('LibreOffice',280000),'abiword':('AbiWord',9800),
    'gnumeric':('Gnumeric',12000),'texlive':('TeX Live',450000),
    'pandoc':('Pandoc',22000),'calibre':('Calibre',68000),
    'mupdf':('MuPDF',4200),'zathura':('Zathura',2400),'evince':('Evince',5800),
    'okular':('Okular',9800),'poppler-utils':('poppler',2400),
    'ghostscript':('Ghostscript',12000),
    'zip':('ZIP',380),'unzip':('unzip',240),'tar':('tar',780),
    'gzip':('gzip',180),'bzip2':('bzip2',180),'xz-utils':('xz',580),
    'zstd':('zstd',1200),'lz4':('lz4',580),'p7zip-full':('7-Zip',1400),
    'unrar':('unrar',380),'cabextract':('CAB',180),
    'grep':('GNU grep',780),'ripgrep':('ripgrep',3200),'ack':('ack',280),
    'silversearcher-ag':('ag',680),'ugrep':('ugrep',1800),'fzf':('fzf',580),
    'peco':('peco',980),'jq':('jq',890),'yq':('yq',1800),'gron':('gron',380),
    'xmllint':('validador XML',980),'figlet':('figlet',210),'toilet':('toilet',280),
    'cowsay':('vaca ASCII',45),'cowthink':('vaca pensa',45),
    'lolcat':('arco-iris',140),'sl':('trem ASCII',35),'cmatrix':('Matrix',95),
    'asciiquarium':('aquario',180),'pv':('progresso pipe',280),
    'banner':('banner',85),'boxes':('caixas',180),'fortune':('frases',1100),
    'thefuck':('thefuck',2400),'bat':('bat',1400),'exa':('exa',1800),
    'eza':('eza',1800),'lsd':('lsd',1400),'ranger':('ranger',3400),
    'nnn':('nnn',280),'lf':('lf',2400),'vifm':('vifm',1400),'mc':('Midnight',5800),
    'yazi':('yazi',5800),'broot':('broot',3400),
    'rclone':('rclone',22000),'borgbackup':('borg',12000),'restic':('restic',9800),
    'duplicity':('duplicity',3400),'timeshift':('timeshift',6800),
    'syncthing':('syncthing',18000),'unison':('unison',4200),
    'ufw':('ufw',1800),'iptables':('iptables',2400),'nftables':('nftables',3400),
    'fail2ban':('fail2ban',4200),'clamav':('ClamAV',18000),
    'rkhunter':('rkhunter',1400),'lynis':('lynis',1400),'openssl':('OpenSSL',3400),
    'gnupg':('GnuPG',9800),'age':('age',980),'pass':('pass',280),
    'keepassxc':('KeePassXC',22000),'tor':('Tor',18000),'proxychains':('proxychains',380),
    'hashcat':('Hashcat',38000),'john':('John',9800),'hydra':('hydra',1400),
    'sqlmap':('sqlmap',22000),'nikto':('nikto',2400),'gobuster':('gobuster',3400),
    'ffuf':('ffuf',2400),'metasploit':('Metasploit',380000),
    'aircrack-ng':('Aircrack',9800),
    'aptitude':('apt ncurses',3400),'apt-file':('apt-file',680),
    'dpkg-dev':('.deb dev',12000),'debootstrap':('debootstrap',2400),
    'alien':('alien',980),'checkinstall':('checkinstall',680),
    'flatpak':('Flatpak',22000),'snapd':('Snap',45000),
    'nix':('Nix',180000),'stow':('stow',580),'chezmoi':('chezmoi',9800),
    'tree':('arvore dirs',120),'pstree':('arvore procs',85),
    'dos2unix':('dos2unix',180),'unix2dos':('unix2dos',180),
    'bc':('calculadora',280),'qalc':('calculadora avancada',2400),
    'units':('unidades',680),'parallel':('GNU parallel',1800),
    'watch':('watch',180),'at':('at',280),'cron':('cron',980),
    'logrotate':('logrotate',380),'rsyslog':('rsyslog',2400),
    'systemd':('systemd',120000),'supervisor':('supervisor',2400),
    'procps':('ps/free/top',850),'coreutils':('GNU coreutils',2400),
    'util-linux':('lscpu/lsblk/dmesg',4500),'bsdmainutils':('cal/col',980),
    'xclip':('xclip',180),'wl-clipboard':('clipboard Wayland',280),
    'notify-send':('notificacoes',85),'scrot':('screenshot',180),
    'maim':('maim',280),'flameshot':('screenshot anotado',4200),
    'xdotool':('automacao X',480),'wmctrl':('controle janelas',180),
})

# ===== COMANDOS =====
def cmd_ls(args):
    print(f"{C['blue']}Documentos{R}  {C['blue']}Downloads{R}  {C['blue']}Imagens{R}  "
          f"{C['blue']}Musica{R}  {C['blue']}Videos{R}  {C['dim']}.config{R}\n")

def cmd_pwd(args): print(f"{C['value']}{os.path.expanduser('~')}{R}\n")
def cmd_whoami(args): print(f"{C['value']}{USER}{R}\n")
def cmd_hostname(args): print(f"{C['value']}{HOST}{R}\n")
def cmd_id(args): print(f"uid=1000({USER}) gid=1000({USER}) groups=1000({USER}),27(sudo)\n")

def cmd_echo(args):
    print(f"{C['value']}{args if args else ''}{R}\n")

def cmd_cat(args):
    if not args:
        print(f"{C['red']}cat: faltando operando{R}\n"); return
    print(f"{C['red']}cat: {args}: Arquivo ou diretorio inexistente{R}\n")

def cmd_uname(args):
    if '-a' in args:
        print(f"Linux {HOST} {platform.release()} #1 SMP PREEMPT {platform.machine()} GNU/Linux\n")
    else: print(f"{platform.system()}\n")

def cmd_date(args): print(f"{time.strftime('%a %b %d %H:%M:%S %Z %Y')}\n")

def cmd_uptime(args):
    up = real_uptime(); h,r = divmod(int(up),3600); m,_ = divmod(r,60)
    print(f" {time.strftime('%H:%M:%S')} up {h}:{m:02d}, 1 user, load average: "
          f"{random.uniform(0.1,2.5):.2f}, {random.uniform(0.1,2.0):.2f}, {random.uniform(0.1,1.5):.2f}\n")

def cmd_env(args):
    for k in ['HOME','USER','SHELL','PATH','LANG','TERM','PWD','HOSTNAME']:
        v = os.environ.get(k, f'/{k.lower()}')
        print(f"{C['value']}{k}{R}={v}")
    print()

def cmd_which(args):
    if not args: return
    for c in args.split():
        if c in COMANDOS: print(f"{C['green']}/usr/bin/{c}{R}")
        else: print(f"{C['dim']}{c} nao encontrado{R}")
    print()

def cmd_type(args):
    for c in args.split():
        if c in COMANDOS:
            pac = PACOTE_COMANDO.get(c)
            if pac and pac not in INSTALLED_FAKE:
                print(f"{c}: comando nao encontrado (instale {pac})")
            else:
                print(f"{c} e um comando do shell (Linux on Python)")
    print()

def cmd_history(args): print(f"{C['dim']}(historico nao persistente){R}\n")

def cmd_sleep(args):
    try: t = float(args.split()[0]) if args else 1
    except: t = 1
    time.sleep(min(t, 5)); print()

def cmd_seq(args):
    try:
        p = args.split()
        if len(p) == 1: a, b = 1, int(p[0])
        else: a, b = int(p[0]), int(p[1])
        print(' '.join(str(i) for i in range(a, b+1)) + "\n")
    except: print(f"{C['red']}seq: args invalidos{R}\n")

def cmd_head(args): print(f"{C['red']}head: leitura de stdin nao suportada{R}\n")
def cmd_tail(args): print(f"{C['red']}tail: leitura de stdin nao suportada{R}\n")

def cmd_wc(args):
    if not args: return
    n = len(args.replace(" ", "")); print(f"{n} 1 {n+1} {args[:20]}\n")

def cmd_sort(args):
    for l in sorted(args.split()): print(f"{C['value']}{l}{R}")
    print()

def cmd_uniq(args):
    prev = None
    for l in args.split():
        if l != prev: print(f"{C['value']}{l}{R}"); prev = l
    print()

def cmd_grep(args):
    if not args: print(f"{C['red']}Uso: grep PADRAO{R}\n"); return
    print(f"{C['red']}grep: leitura de arquivos nao suportada{R}\n")

def cmd_rev(args): print(f"{C['value']}{args[::-1]}{R}\n")

def cmd_tac(args):
    for l in reversed(args.split()): print(f"{C['value']}{l}{R}")
    print()

def cmd_base64(args):
    import base64 as b64
    if args.startswith('-d') or args.startswith('--decode'):
        try: print(f"{C['value']}{b64.b64decode(args.split(maxsplit=1)[1]).decode()}{R}\n")
        except: print(f"{C['red']}base64: entrada invalida{R}\n")
    else:
        print(f"{C['value']}{b64.b64encode(args.encode()).decode()}{R}\n")

def cmd_md5sum(args):
    import hashlib
    print(f"{C['value']}{hashlib.md5(args.encode()).hexdigest()}{R}  {C['dim']}(arg){R}\n")

def cmd_sha256sum(args):
    import hashlib
    print(f"{C['value']}{hashlib.sha256(args.encode()).hexdigest()}{R}  {C['dim']}(arg){R}\n")

def cmd_xxd(args):
    data = args.encode()[:64]
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hexs = ' '.join(f"{b:02x}" for b in chunk)
        txt  = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"{C['dim']}{i:08x}{R}: {hexs:<47}  {C['value']}{txt}{R}")
    print()

def cmd_factor(args):
    try:
        n = int(args.split()[0]); orig = n; fs = []
        d = 2
        while d * d <= n:
            while n % d == 0: fs.append(d); n //= d
            d += 1
        if n > 1: fs.append(n)
        print(f"{C['value']}{orig}:{' '.join(str(f) for f in fs)}{R}\n")
    except: print(f"{C['red']}factor: argumento invalido{R}\n")

def cmd_cal(args):
    import calendar
    print(f"{C['value']}{calendar.TextCalendar().formatmonth(time.localtime().tm_year, time.localtime().tm_mon)}{R}")

def cmd_man(args):
    c = args.split()[0] if args else None
    if not c: print(f"{C['red']}O que voce quer?{R}\n"); return
    d = HELP_CMD.get(c, f"comando {c} do Linux on Python")
    print(f"{C['btitle']}NAME{R}\n    {c} - {d}\n")
    print(f"{C['btitle']}SYNOPSIS{R}\n    {c} [opcoes]\n")

def cmd_free(args):
    t, u, a, c, p = real_mem()
    st, su, _ = real_swap()
    def m(b): return f"{b/1024/1024:>9.0f}"
    print(f"{C['label']}              total        used        free      shared  buff/cache   available{R}")
    print(f"Mem:      {m(t)}  {m(u)}  {m(a)}  {C['value']}{0:>10}{R}  {m(c)}  {m(a)}")
    print(f"Swap:     {m(st)}  {m(su)}  {m(st-su)}\n")

def cmd_df(args):
    t, u, a, _, p = real_mem()
    print(f"{C['label']}Sist.Arq.     Tam.Usado Disp. Uso% Montado em{R}")
    print(f"/dev/root      {u/1e9:>6.1f}G {a/1e9:>6.1f}G {p:>4.0f}% /")
    print(f"tmpfs          {t/4/1e9:>6.1f}G    0G    0% /tmp")
    print(f"/dev/sda1      {t/1e9:>6.1f}G {u/2/1e9:>6.1f}G {p/2:>4.0f}% /home\n")

def cmd_du(args):
    print(f"{random.randint(2,80)}M\t{C['value']}.{R}")
    print(f"{random.randint(1,20)}M\t{C['value']}.config{R}")
    print(f"{random.randint(1,15)}M\t{C['value']}Documentos{R}\n")

def cmd_ps(args):
    for p in real_procs()[:15]:
        t = f"00:00:{random.randint(0,59):02d}"
        print(f"{p['pid']:>5} ?        {t} {C['value']}{p['name']}{R}")
    print()

def cmd_lscpu(args):
    n = real_cpu_count(); cpu = real_cpu_name()
    print(f"{C['label']}Architecture:        {C['value']}{platform.machine()}{R}")
    print(f"{C['label']}CPU(s):              {C['value']}{n}{R}")
    print(f"{C['label']}Model name:          {C['value']}{cpu[:50]}{R}")
    print(f"{C['label']}Thread(s) per core:  {C['value']}{2 if n > 1 else 1}{R}")
    print(f"{C['label']}CPU MHz:             {C['value']}{random.uniform(1500,3500):.3f}{R}\n")

def cmd_lsblk(args):
    print(f"{C['btitle']}NAME   MAJ:MIN RM   SIZE RO TYPE MOUNTPOINT{R}")
    print(f"sda      8:0    0  {random.randint(120,1000)}G  0 disk")
    print(f"|-sda1   8:1    0  {random.randint(50,500)}G  0 part /")
    print(f"`-sda2   8:2    0  {random.randint(20,200)}G  0 part /home\n")

def cmd_dmesg(args):
    for l in [
        f"[    0.000000] Linux version {platform.release()}",
        f"[    0.012340] Memory: {real_mem()[0]//1024//1024}M available",
        f"[    0.123456] CPU: {real_cpu_name()[:40]}",
        f"[    0.234567] ACPI: Core revision 20230331",
        f"[    1.000000] systemd[1]: Detected architecture {platform.machine()}",
        f"[    2.100000] systemd[1]: Reached target Basic System",
    ]: print(f"{C['dim']}{l}{R}")
    print()

def cmd_tree(args):
    print(f"{C['blue']}.{R}")
    print(f"|-- {C['blue']}Documentos{R}")
    print(f"|   |-- projeto.py")
    print(f"|   `-- notas.txt")
    print(f"|-- {C['blue']}Downloads{R}")
    print(f"|   `-- arquivo.zip")
    print(f"`-- {C['dim']}.config{R}\n")

def cmd_cowsay(args):
    msg = args or "Moo!"
    borda = '-' * (len(msg) + 2)
    print(f" {borda}")
    print(f"< {C['value']}{msg}{R} >")
    print(f" {borda}")
    print(r"        \   ^__^")
    print(r"         \  (oo)\_______")
    print(r"            (__)\       )\/\ ")
    print(r"                ||----w |")
    print(r"                ||     ||")
    print()

def cmd_cowthink(args):
    msg = args or "Moo?"
    borda = '-' * (len(msg) + 2)
    print(f" {borda}")
    print(f"( {C['value']}{msg}{R} )")
    print(f" {borda}")
    print(r"        o   ^__^")
    print(r"         o  (oo)\_______")
    print(r"            (__)\       )\/\ ")
    print(r"                ||----w |")
    print(r"                ||     ||")
    print()

def cmd_sl(args):
    frames = [
        "     ====        ________",
        " _D _|  |_______/        \\__",
        "|   |  |   |   |          |",
        "|___|__|___|___|__________|",
        "",
        "         ====        ________",
        "     _D _|  |_______/        \\__",
        "    |   |  |   |   |          |",
        "    |___|__|___|___|__________|",
    ]
    for f in frames:
        sys.stdout.write(f"\r{C['red']}{f}{R}")
        sys.stdout.flush(); time.sleep(0.12)
    print("\n")

def cmd_fortune(args):
    frases = [
        "A melhor maneira de prever o futuro e inventa-lo.",
        "Simplicidade e o ultimo grau de sofisticacao.",
        "Falar e facil. Mostre-me o codigo.",
        "Programas devem ser escritos para pessoas lerem.",
        "Bugs sao apenas features nao documentadas.",
        "Nao e um bug, e uma feature.",
        "99 bugs no codigo, tira um, corrige, 127 bugs.",
        "Um dia eu vou aprender regex. Provavelmente nao.",
    ]
    print(f"{C['yellow']}{random.choice(frases)}{R}\n")

def cmd_figlet(args):
    if not args: return
    letras = {
        'A':"  _  \n /_\\ \n/ _ \\", 'B':" __ \n| _ )\n| _ \\", 'C':" ___ \n/ __|\n\\__ \\",
        'D':" __ \n|  \\\n| |) |", 'E':" ___ \n| __|\n|___|", 'F':" ___ \n| __|\n|_  ",
        'G':" ___ \n/ __|\n\\__|", 'H':" _  _ \n| || |\n| __ |", 'I':" _ \n| |\n|_|",
        'J':"  _ \n | |\n_| |", 'K':" _  __\n| |/ /\n| ' /", 'L':" _    \n| |   \n| |___",
        'M':" __  __\n|  \\/  |\n| |\\/| |", 'N':" _  _ \n| \\| |\n| .` |",
        'O':"  ___  \n / _ \\ \n \\___/ ", 'P':" ___ \n| _ \\\n|  _/", 'Q':"  ___ \n / _ \\\n \\_  )",
        'R':" ___ \n| _ \\\n|   /", 'S':" ___ \n/ __|\n\\__ \\", 'T':" _____ \n|_   _|\n  |_|",
        'U':" _   _ \n| | | |\n| |_| |", 'V':" __   __\n \\ \\ / /\n  \\ V /",
        'W':" __      __\n \\ \\    / /\n  \\_/\\_/ ", 'X':"__  __\n\\ \\/ /\n >  <",
        'Y':"__   __\n\\ \\ / /\n \\ V / ", 'Z':"___\n|_  )\n /_/ ", ' ':"   \n   \n   ",
    }
    linhas = ["", "", ""]
    for ch in args.upper()[:8]:
        if ch in letras:
            for i, l in enumerate(letras[ch].split("\n")):
                if i < 3: linhas[i] += l + "  "
    print(f"{C['green']}")
    for l in linhas: print(l)
    print(f"{R}")

def cmd_banner(args): cmd_figlet(args)

def cmd_lolcat(args):
    if not args: return
    cores = [196, 202, 208, 214, 220, 226, 190, 118, 82, 46, 51, 45, 39, 33, 129, 165, 201]
    out = "".join(f"{fg(cores[i % len(cores)])}{ch}" for i, ch in enumerate(args))
    print(f"{out}{R}\n")

def cmd_cmatrix(args):
    try: dur = float(args) if args else 3
    except: dur = 3
    dur = min(dur, 8)
    tw = term_width()
    t0 = time.time()
    try:
        sys.stdout.write('\033[?25l')
        while time.time() - t0 < dur:
            linha = "".join(random.choice("01 ") for _ in range(min(tw, 80)))
            cor = C['green'] if random.random() < 0.3 else C['dim']
            print(f"{cor}{linha}{R}")
            time.sleep(0.04)
            if time.time() - t0 > 1 and random.random() < 0.3:
                limpar_tela()
    finally:
        sys.stdout.write('\033[?25h')

def cmd_ping(args):
    host = args.split()[0] if args else 'localhost'
    try: ip = socket.gethostbyname(host)
    except: ip = '127.0.0.1'
    print(f"PING {host} ({ip}) 56(84) bytes of data.")
    try:
        for i in range(4):
            t = random.uniform(5, 80)
            print(f"64 bytes from {ip}: icmp_seq={i+1} ttl=64 time={t:.2f} ms")
            time.sleep(0.4)
        print(f"\n--- {host} ping statistics ---")
        print(f"4 packets transmitted, 4 received, 0% packet loss\n")
    except KeyboardInterrupt:
        print()

def cmd_curl(args):
    url = args.split()[-1] if args else ''
    if not url: print(f"{C['red']}curl: URL faltando{R}\n"); return
    print(f"{C['dim']}$ curl {url}{R}")
    print(f"  % Total    % Received   Time")
    for p in range(0, 101, 20):
        sys.stdout.write(f"\r  {p:>3}%      {(p*2.4):>6.1f}k     {p/100*1.2:.2f}s")
        sys.stdout.flush(); time.sleep(0.1)
    print(f"\n\n{C['green']}OK Recebido{R}\n")

def cmd_wget(args):
    url = args.split()[-1] if args else ''
    if not url: print(f"{C['red']}wget: URL faltando{R}\n"); return
    print(f"--{time.strftime('%H:%M:%S')}--  {url}")
    print(f"Salvando em: 'arquivo'")
    for p in range(0, 101, 10):
        bar = '=' * (p//4) + '>' if p < 100 else '='*25
        sys.stdout.write(f"\r{p:>3}%[{bar:<25}] {(p*15):>7}  --.-K/s")
        sys.stdout.flush(); time.sleep(0.08)
    print(f"\n\n{C['green']}'arquivo' salvo.{R}\n")

def cmd_docker(args):
    p = args.split()
    if not p:
        print("Usage: docker [OPTIONS] COMMAND"); return
    if p[0] == 'run':
        img = p[-1] if len(p) > 1 else 'hello-world'
        print(f"Unable to find image '{img}' locally")
        print(f"{C['dim']}Pulling from library/{img}{R}")
        for i in range(3):
            sys.stdout.write(f"\r{C['dim']}{'#'*(i*10+5)}{R}")
            sys.stdout.flush(); time.sleep(0.2)
        print()
        print(f"\nHello from Docker! (fake)")
    elif p[0] == 'ps':
        print(f"{C['btitle']}CONTAINER ID   IMAGE     COMMAND   STATUS{R}")
        print(f"{C['dim']}(nenhum container){R}")
    else:
        print(f"{C['red']}docker: '{p[0]}' nao suportado{R}")
    print()

def cmd_git(args):
    p = args.split()
    if not p:
        print("usage: git <command> [<args>]"); return
    if p[0] == 'status':
        print(f"On branch main")
        print(f"Your branch is up to date with 'origin/main'.")
        print(f"\nnothing to commit, working tree clean\n")
    elif p[0] == 'log':
        for i in range(3):
            print(f"{C['yellow']}commit {random.randrange(16**7):07x}{R}")
            print(f"Author: {USER} <{USER}@linux-on-python>")
            print(f"Date:   {time.ctime()}")
            print(f"\n    commit fake #{i+1}\n")
    elif p[0] == 'branch':
        print("* main")
    else:
        print(f"{C['red']}git: '{p[0]}' nao implementado{R}")
    print()

def cmd_cargo(args):
    p = args.split()
    if not p: print("Cargo commands..."); return
    print(f"{C['green']}    Updating crates.io index{R}")
    for _ in range(3):
        print(f"{C['dim']}  Downloading fake-crate v0.1.0{R}"); time.sleep(0.2)
    print(f"{C['green']}   Compiling {p[-1] if len(p)>1 else 'project'} v0.1.0{R}")
    time.sleep(0.4)
    print(f"{C['green']}    Finished{R} release target(s) in {random.uniform(0.5,3):.2f}s\n")

def cmd_npm(args):
    p = args.split()
    if not p: print("Usage: npm <command>"); return
    if p[0] in ('install','i'):
        for _ in range(3):
            print(f"{C['dim']}added {random.randint(3,20)} packages{R}"); time.sleep(0.15)
        print(f"{C['green']}added {random.randint(20,200)} packages in {random.uniform(0.5,2):.1f}s{R}\n")
    else:
        print(f"{C['red']}npm: '{p[0]}' nao implementado{R}\n")

def cmd_yes(args):
    txt = args or 'y'
    try:
        for _ in range(20): print(txt)
    except KeyboardInterrupt: pass
    print(f"{C['dim']}(mostrados 20){R}\n")

def _reg():
    builtin = {
        'ls':(cmd_ls,'lista arquivos'),'pwd':(cmd_pwd,'diretorio atual'),
        'whoami':(cmd_whoami,'usuario'),'hostname':(cmd_hostname,'nome da maquina'),
        'id':(cmd_id,'id do usuario'),'echo':(cmd_echo,'imprime texto'),
        'cat':(cmd_cat,'concatena'),'uname':(cmd_uname,'info kernel'),
        'date':(cmd_date,'data/hora'),'uptime':(cmd_uptime,'tempo ligado'),
        'env':(cmd_env,'variaveis ambiente'),'which':(cmd_which,'localiza comando'),
        'type':(cmd_type,'tipo do comando'),'history':(cmd_history,'historico'),
        'sleep':(cmd_sleep,'espera N segundos'),'seq':(cmd_seq,'sequencia numeros'),
        'head':(cmd_head,'primeiras linhas'),'tail':(cmd_tail,'ultimas linhas'),
        'wc':(cmd_wc,'contagem'),'sort':(cmd_sort,'ordena'),'uniq':(cmd_uniq,'deduplica'),
        'grep':(cmd_grep,'busca texto'),'rev':(cmd_rev,'inverte string'),
        'tac':(cmd_tac,'inverte linhas'),'base64':(cmd_base64,'codifica base64'),
        'md5sum':(cmd_md5sum,'hash MD5'),'sha256sum':(cmd_sha256sum,'hash SHA-256'),
        'xxd':(cmd_xxd,'hexdump'),'factor':(cmd_factor,'fatoracao'),
        'cal':(cmd_cal,'calendario'),'man':(cmd_man,'manual'),
    }
    pkgs = {
        'tree':(cmd_tree,'arvore diretorios','tree'),
        'cowsay':(cmd_cowsay,'vaca ASCII','cowsay'),
        'cowthink':(cmd_cowthink,'vaca pensando','cowthink'),
        'sl':(cmd_sl,'trem ASCII','sl'),
        'fortune':(cmd_fortune,'frases','fortune'),
        'figlet':(cmd_figlet,'texto grande','figlet'),
        'banner':(cmd_banner,'banner','banner'),
        'lolcat':(cmd_lolcat,'arco-iris','lolcat'),
        'cmatrix':(cmd_cmatrix,'Matrix','cmatrix'),
        'free':(cmd_free,'memoria','procps'),
        'df':(cmd_df,'disco','coreutils'),
        'du':(cmd_du,'uso diretorios','coreutils'),
        'ps':(cmd_ps,'processos','procps'),
        'lscpu':(cmd_lscpu,'info CPU','util-linux'),
        'lsblk':(cmd_lsblk,'blocos','util-linux'),
        'dmesg':(cmd_dmesg,'logs kernel','util-linux'),
        'ping':(cmd_ping,'ping','iputils-ping'),
        'curl':(cmd_curl,'HTTP GET','curl'),
        'wget':(cmd_wget,'download','wget'),
        'docker':(cmd_docker,'Docker','docker'),
        'git':(cmd_git,'Git','git'),
        'cargo':(cmd_cargo,'Cargo','cargo'),
        'npm':(cmd_npm,'npm','npm'),
        'yes':(cmd_yes,'repete y','coreutils'),
    }
    for c, (f, h) in builtin.items():
        COMANDOS[c] = f; PACOTE_COMANDO[c] = None; HELP_CMD[c] = h
    for c, (f, h, p) in pkgs.items():
        COMANDOS[c] = f; PACOTE_COMANDO[c] = p; HELP_CMD[c] = h

_reg()



HELP_INFO = {
    'help':      (None,'basico','Mostra esta ajuda. Aceita help <comando> ou help <categoria>.','help cowsay'),
    'neofetch':  (None,'basico','Exibe informacoes do sistema com a logo do Python em ASCII.','neofetch'),
    'btop':      (None,'basico','Monitor de recursos interativo (CPU, RAM, rede, processos).','btop'),
    'clear':     (None,'basico','Limpa a tela do terminal.','clear'),
    'exit':      (None,'basico','Sai do shell e volta ao sistema real.','exit'),
    'apt':       (None,'basico','Repositorio de pacotes fake (~230 pacotes). Instala via pip se nao existir no repo fake.','sudo apt-get install cowsay'),
    'sudo':      (None,'basico','Executa um comando como root (senha fake).','sudo whoami'),
    'pip':       (None,'basico','pip real - instala pacotes do PyPI de verdade.','pip install requests'),
    'ls':        (None,'arquivos','Lista arquivos e pastas do diretorio atual.','ls'),
    'pwd':       (None,'arquivos','Mostra o caminho do diretorio atual.','pwd'),
    'cat':       (None,'arquivos','Concatena e mostra o conteudo de arquivos (simulado).','cat notas.txt'),
    'tree':      ('tree','arquivos','Exibe a arvore de diretorios em formato de galhos.','tree'),
    'du':        ('coreutils','arquivos','Mostra o uso de disco por pasta.','du'),
    'df':        ('coreutils','arquivos','Mostra o uso de disco dos sistemas de arquivos.','df'),
    'echo':      (None,'texto','Imprime o texto passado como argumento.','echo ola mundo'),
    'wc':        (None,'texto','Conta caracteres, palavras e linhas do texto.','wc uma frase aqui'),
    'sort':      (None,'texto','Ordena as palavras em ordem alfabetica.','sort banana uva maca'),
    'uniq':      (None,'texto','Remove palavras duplicadas consecutivas.','uniq a a b c c'),
    'rev':       (None,'texto','Inverte a ordem dos caracteres de uma string.','rev abc'),
    'tac':       (None,'texto','Inverte a ordem das palavras.','tac um dois tres'),
    'grep':      (None,'texto','Busca um padrao dentro de texto (simulado).','grep foo'),
    'base64':    (None,'texto','Codifica em base64. Use -d para decodificar.','base64 texto'),
    'cowsay':    ('cowsay','texto','Uma vaca em ASCII fala a mensagem que voce passar.','cowsay ola'),
    'cowthink':  ('cowthink','texto','Igual cowsay, mas a vaca pensa em vez de falar.','cowthink hmm'),
    'figlet':    ('figlet','texto','Transforma texto em letras grandes ASCII.','figlet oi'),
    'banner':    ('banner','texto','Igual ao figlet - imprime texto grande em ASCII.','banner ola'),
    'lolcat':    ('lolcat','texto','Coloriza o texto com arco-iris no terminal.','lolcat colorido'),
    'whoami':    (None,'sistema','Mostra o nome do usuario atual.','whoami'),
    'hostname':  (None,'sistema','Mostra o nome da maquina.','hostname'),
    'uname':     (None,'sistema','Mostra informacoes do kernel. Use -a para tudo.','uname -a'),
    'date':      (None,'sistema','Mostra a data e hora atuais.','date'),
    'uptime':    (None,'sistema','Mostra ha quanto tempo o sistema esta ligado.','uptime'),
    'id':        (None,'sistema','Mostra UID, GID e grupos do usuario.','id'),
    'env':       (None,'sistema','Lista as variaveis de ambiente.','env'),
    'history':   (None,'sistema','Mostra o historico de comandos.','history'),
    'free':      ('procps','sistema','Mostra o uso de memoria RAM e swap em tempo real.','free'),
    'ps':        ('procps','sistema','Lista os processos em execucao com PID e comando.','ps'),
    'lscpu':     ('util-linux','sistema','Detalhes da CPU: arquitetura, nucleos, modelo.','lscpu'),
    'lsblk':     ('util-linux','sistema','Lista os discos e particoes do sistema.','lsblk'),
    'dmesg':     ('util-linux','sistema','Mostra mensagens do kernel (simulado).','dmesg'),
    'cal':       (None,'sistema','Exibe o calendario do mes atual.','cal'),
    'which':     (None,'utilitarios','Diz onde um comando esta instalado.','which ls'),
    'type':      (None,'utilitarios','Diz se o comando e builtin, alias ou binario.','type ls'),
    'man':       (None,'utilitarios','Mostra o manual de um comando.','man ls'),
    'sleep':     (None,'utilitarios','Pausa o shell por N segundos.','sleep 2'),
    'seq':       (None,'utilitarios','Gera uma sequencia de numeros.','seq 1 10'),
    'factor':    (None,'utilitarios','Fatora um numero em primos.','factor 120'),
    'md5sum':    (None,'utilitarios','Calcula o hash MD5 de um texto.','md5sum texto'),
    'sha256sum': (None,'utilitarios','Calcula o hash SHA-256 de um texto.','sha256sum texto'),
    'xxd':       (None,'utilitarios','Faz um dump hexadecimal de um texto.','xxd hello'),
    'yes':       ('coreutils','utilitarios','Imprime y repetidamente (limitado a 20 aqui).','yes'),
    'fortune':   ('fortune','utilitarios','Mostra uma frase aleatoria do banco de frases.','fortune'),
    'ping':      ('iputils-ping','rede','Envia pacotes ICMP para testar conectividade.','ping google.com'),
    'curl':      ('curl','rede','Faz requisicao HTTP GET com barra de progresso.','curl https://exemplo.com'),
    'wget':      ('wget','rede','Baixa um arquivo da internet com barra de progresso.','wget https://exemplo.com/a.zip'),
    'sl':        ('sl','diversao','Um trem ASCII passa pela tela quando voce erra ls.','sl'),
    'cmatrix':   ('cmatrix','diversao','Chuva de caracteres estilo Matrix. Aceita duracao em segundos.','cmatrix 4'),
    'docker':    ('docker','dev','Docker simulado: pull fake e mensagem de hello-world.','docker run hello-world'),
    'git':       ('git','dev','Git simulado: status, log, branch.','git status'),
    'cargo':     ('cargo','dev','Cargo simulado: compila com saida de build.','cargo build'),
    'npm':       ('npm','dev','npm simulado: instala pacotes fake.','npm install'),
}

CATEGORIAS = {
    'basico':     'Comandos basicos do shell',
    'arquivos':   'Manipulacao de arquivos',
    'texto':      'Processamento de texto',
    'sistema':    'Informacoes do sistema',
    'utilitarios':'Ferramentas diversas',
    'rede':       'Rede e internet',
    'diversao':   'Comandos de diversao',
    'dev':        'Desenvolvimento / DevOps',
}

def _help_detalhe(cmd):
    info = HELP_INFO.get(cmd)
    if not info:
        print(f"{C['red']}help: nenhum topico para '{cmd}'{R}")
        print(f"{C['dim']}Dica: digite 'help' para listar tudo.{R}\n")
        return
    pkg, cat, desc, ex = info
    print(f"\n{C['btitle']}=== {cmd} ==={R}")
    print(f"{C['label']}Categoria:{R} {C['value']}{cat}{R}")
    print(f"{C['label']}O que faz:{R} {C['value']}{desc}{R}")
    print(f"{C['label']}Exemplo:{R}   {C['green']}{ex}{R}")
    if pkg:
        if pkg in INSTALLED_FAKE:
            print(f"{C['green']}Status:{R}   OK - instalado (pacote: {pkg})")
        else:
            print(f"{C['yellow']}Status:{R}   requer o pacote '{pkg}'")
            print(f"         instale: {C['value']}sudo apt-get install {pkg}{R}")
    else:
        print(f"{C['green']}Status:{R}   sempre disponivel")
    print()

def _help_categoria(cat):
    cat = cat.lower()
    itens = [(c, i) for c, i in HELP_INFO.items() if i[1].lower() == cat]
    if not itens:
        print(f"{C['red']}help: categoria '{cat}' nao existe{R}")
        print(f"{C['dim']}Categorias: {', '.join(CATEGORIAS.keys())}{R}\n")
        return
    print(f"\n{C['btitle']}=== {cat.upper()} - {CATEGORIAS.get(cat,'')} ==={R}\n")
    for cmd, (pkg, _, desc, ex) in sorted(itens):
        if pkg is None or pkg in INSTALLED_FAKE:
            status = f"{C['green']}[+]{R}"
        else:
            status = f"{C['dim']}[-]{R}"
        print(f" {status} {C['green']}{cmd:<12}{R} {C['value']}{desc}{R}")
        print(f"   {C['dim']}ex: {ex}{R}")
    print()

def cmd_help(args=""):
    args = args.strip().lower()
    if args in CATEGORIAS:
        _help_categoria(args); return
    if args:
        _help_detalhe(args); return

    instalados = INSTALLED_FAKE
    W = 70
    print(f"\n{C['btitle']}+{'-' * (W - 2)}+{R}")
    print(f"{C['btitle']}|{'Linux on Python - Ajuda'.center(W - 2)}|{R}")
    print(f"{C['btitle']}+{'-' * (W - 2)}+{R}")

    por_cat = {}
    for cmd, (pkg, cat, desc, ex) in HELP_INFO.items():
        por_cat.setdefault(cat, []).append((cmd, pkg, desc, ex))

    for cat in CATEGORIAS:
        itens = por_cat.get(cat, [])
        if not itens: continue
        print(f"\n{C['btitle']}> {cat.upper()}{R} {C['dim']}- {CATEGORIAS[cat]}{R}")
        for cmd, pkg, desc, ex in sorted(itens):
            if pkg is None or pkg in instalados:
                status = f"{C['green']}[+]{R}"
            else:
                status = f"{C['dim']}[-]{R}"
            print(f"  {status} {C['green']}{cmd:<12}{R} {C['value']}{desc}{R}")
            print(f"      {C['dim']}ex: {ex}{R}")

    print(f"\n{C['btitle']}> Como usar:{R}")
    print(f"  {C['green']}help{R}                lista tudo isso")
    print(f"  {C['green']}help <comando>{R}      detalhes de um comando (ex: help cowsay)")
    print(f"  {C['green']}help <categoria>{R}    filtra por categoria (ex: help rede)")
    print(f"  {C['dim']}[+] = pronto    [-] = instale com: sudo apt-get install <pacote>{R}")
    print()

def shell():
    while True:
        try: linha = input(PROMPT).strip()
        except (EOFError, KeyboardInterrupt): print(); break
        if not linha: continue
        partes = linha.split(); cmd = partes[0]; args = ' '.join(partes[1:])

        if cmd in ('exit','quit','logout'):
            print(f"{C['label']}Ate logo!{R}\n"); break
        elif cmd == 'help':                    cmd_help(args)
        elif cmd == 'neofetch':                cmd_neofetch()
        elif cmd == 'clear':                   limpar_tela()
        elif cmd in ('apt','apt-get'):         cmd_apt(args)
        elif cmd == 'sudo':                    cmd_sudo(args)
        elif cmd in ('pip','pip3'):            cmd_pip(args)
        elif cmd == 'btop':
            try: executar_btop()
            except Exception as e: print(f"{C['red']}btop: {e}{R}\n")
            print(f"{C['label']}Voltando ao shell...{R}\n")
        elif cmd in COMANDOS:
            pacote = PACOTE_COMANDO.get(cmd)
            if pacote is None or pacote in INSTALLED_FAKE:
                try: COMANDOS[cmd](args)
                except Exception as e:
                    print(f"{C['red']}{cmd}: {e}{R}\n")
            else:
                print(f"{C['red']}{cmd}: comando nao encontrado{R}")
                print(f"{C['dim']}Dica: sudo apt-get install {pacote}{R}\n")
        else:
            print(f"{C['red']}{cmd}: comando nao encontrado{R}\n")

class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.cells = [[(' ', '') for _ in range(w)] for _ in range(h)]
    def put(self, x, y, text, color=''):
        if y < 0 or y >= self.h: return
        for i, ch in enumerate(text):
            xx = x + i
            if 0 <= xx < self.w: self.cells[y][xx] = (ch, color)
    def box(self, x, y, w, h, title=''):
        if w < 2 or h < 2: return
        self.put(x, y, '+' + '-'*(w-2) + '+', C['border'])
        for i in range(1, h-1):
            self.put(x, y+i, '|', C['border']); self.put(x+w-1, y+i, '|', C['border'])
        self.put(x, y+h-1, '+' + '-'*(w-2) + '+', C['border'])
        if title: self.put(x+2, y, f'[ {title} ]', C['btitle'])
    def render(self):
        out = []
        for row in self.cells:
            parts, cur = [], None
            for ch, col in row:
                if col != cur: parts.append(R+col); cur = col
                parts.append(ch)
            parts.append(R); out.append(''.join(parts))
        return '\n'.join(out)

BLOCKS = ' .:-=+*#%@'
def draw_bar(c, x, y, w, pct, color=None):
    pct = max(0,min(100,pct)); f = int(w*pct/100)
    if color is None: color = C['green'] if pct<60 else C['yellow'] if pct<85 else C['red']
    c.put(x, y, '#'*f, color); c.put(x+f, y, '-'*(w-f), C['dim'])
def draw_spark(c, x, y, w, hist, color):
    data = hist[-w:]; data = [0.0]*(w-len(data)) + data
    for i, v in enumerate(data):
        v = max(0.0,min(1.0,v)); c.put(x+i, y, BLOCKS[int(v*9)], color)
def fmt_bytes(b):
    units = ['B','KiB','MiB','GiB','TiB']; i = 0
    while b >= 1024 and i < len(units)-1: b /= 1024; i += 1
    return f"{b:5.1f} {units[i]}"
def fmt_rate(bps): return f"{fmt_bytes(bps)}/s"
def fmt_uptime(s):
    s = int(s); h,r = divmod(s,3600); m,sec = divmod(r,60)
    if h >= 24: d,h = divmod(h,24); return f"{d}d {h:02d}:{m:02d}"
    return f"{h:02d}:{m:02d}:{sec:02d}"

class KeyReader:
    def __init__(self): self.is_win = os.name == 'nt'; self.old = None
    def __enter__(self):
        if not self.is_win:
            try:
                import termios, tty
                self.termios = termios; self.old = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())
            except Exception: self.old = None
        return self
    def __exit__(self, *a):
        if not self.is_win and self.old is not None:
            try: self.termios.tcsetattr(sys.stdin, self.termios.TCSADRAIN, self.old)
            except Exception: pass
    def get(self):
        try:
            if self.is_win:
                import msvcrt
                if msvcrt.kbhit(): return msvcrt.getch().decode('utf-8','ignore')
                return None
            import select
            dr,_,_ = select.select([sys.stdin], [], [], 0)
            return sys.stdin.read(1) if dr else None
        except Exception: return None

HIST = 120
def btop():
    ncpu = real_cpu_count(); safe_cpu_percpu(ncpu)
    prev_net = real_net(); prev_t = time.time(); hist_dn = [0.0]*HIST
    with KeyReader() as kr:
        try:
            sys.stdout.write('\033[?1049h\033[?25l\033[2J'); sys.stdout.flush()
            while True:
                key = kr.get()
                if key in ('q','Q','\x1b','\x03'): break
                cores = safe_cpu_percpu(ncpu)
                mem_t, mem_u, mem_a, mem_c, mem_pct = real_mem()
                swap_t, swap_u, swap_pct = real_swap(); uptime = real_uptime()
                now = time.time(); net = real_net(); dt = max(0.01, now-prev_t)
                if net and prev_net:
                    dn = max(0,(net[0]-prev_net[0])/dt)
                    up = max(0,(net[1]-prev_net[1])/dt)
                else: dn = up = 0
                prev_net, prev_t = net, now
                hist_dn = (hist_dn + [min(1,dn/8e6)])[-HIST:]
                procs = real_procs()
                procs.sort(key=lambda x:(x['cpu'],x['mem_mb']), reverse=True)
                tw, th = shutil.get_terminal_size((80,24)); W, H = tw, max(20, th-1)
                c = Canvas(W, H)
                shown = min(ncpu,16); cpu_rows = math.ceil(shown/2); cpu_h = cpu_rows+2
                c.box(0, 0, W, cpu_h, f'cpu - {ncpu} cores')
                col_w = (W-2)//2; bar_w = max(6, col_w-12)
                for i in range(shown):
                    row, col = divmod(i,2); x = 1 + col*col_w; y = 1 + row
                    val = cores[i]
                    c.put(x, y, f"C{i:<2}", C['label']); draw_bar(c, x+4, y, bar_w, val)
                    colr = C['green'] if val<60 else C['yellow'] if val<85 else C['red']
                    c.put(x+4+bar_w+1, y, f"{val:3.0f}%", colr)
                info = f" {SISTEMA} - {time.strftime('%H:%M:%S')} - up {fmt_uptime(uptime)} "
                c.put(max(4, W-len(info)-3), 0, info, C['btitle'])
                iy = cpu_h; ih = 6; lw = W//2; rw = W-lw
                c.box(0, iy, lw, ih, 'mem'); c.box(lw, iy, rw, ih, 'net')
                tg = mem_t/1e9 if mem_t else 0; ug = mem_u/1e9 if mem_t else 0
                cg = mem_c/1e9 if mem_t else 0; ag = mem_a/1e9 if mem_t else 0
                bx = 11; bw = max(6, lw-bx-24); tx = bx+bw+2
                for i, (lbl, pct, col, txt) in enumerate([
                    ('Used', mem_pct, C['green'], f"{ug:5.1f}/{tg:.1f} GiB"),
                    ('Cache',(cg/tg*100) if tg else 0, C['yellow'], f"{cg:5.1f} GiB"),
                    ('Free',(ag/tg*100) if tg else 0, C['blue'], f"{ag:5.1f} GiB"),
                    ('Swap', swap_pct, C['magenta'], f"{swap_u/1e9:4.1f}/{swap_t/1e9:.1f} GiB")]):
                    y = iy+1+i; c.put(2, y, lbl, C['label'])
                    draw_bar(c, bx, y, bw, pct, col); c.put(tx, y, f"{txt} {pct:3.0f}%", C['value'])
                c.put(lw+2, iy+1, 'v', C['green']); c.put(lw+4, iy+1, fmt_rate(dn), C['value'])
                c.put(lw+2, iy+2, '^', C['blue']);  c.put(lw+4, iy+2, fmt_rate(up), C['value'])
                if net:
                    c.put(lw+2, iy+3, f"down {fmt_bytes(net[0])}", C['dim'])
                    c.put(lw+2, iy+4, f"up   {fmt_bytes(net[1])}", C['dim'])
                draw_spark(c, lw+2, iy+4, rw-4, hist_dn, C['green'])
                py = iy+ih; ph = H-py
                if ph >= 4:
                    c.box(0, py, W, ph, f'proc - {len(procs)}')
                    for txt, x in [('PID',2),('USER',9),('CPU%',19),('MEM',25),('THR',34),('COMMAND',40)]:
                        c.put(x, py+1, txt, C['btitle'])
                    for i, p in enumerate(procs[:ph-3]):
                        y = py+2+i
                        colr = C['green'] if p['cpu']<20 else C['yellow'] if p['cpu']<50 else C['red']
                        c.put(2, y, f"{p['pid']:>6}", C['dim'])
                        c.put(9, y, f"{p['user']:<9}", C['label'])
                        c.put(19, y, f"{p['cpu']:>5.1f}", colr)
                        c.put(25, y, f"{p['mem_mb']:>7.0f}M", C['magenta'])
                        c.put(35, y, f"{p['thr']:>3}", C['dim'])
                        c.put(40, y, p['name'], C['value'])
                fonte = "psutil" if PSUTIL_OK else ("/proc" if real_mem()[0] else "simulado")
                foot = f" q: sair - {SISTEMA} - fonte: {fonte} "
                c.put(max(2, W-len(foot)-2), H-1, foot, C['dim'])
                sys.stdout.write('\033[H' + c.render()); sys.stdout.flush()
                time.sleep(0.6)
        finally:
            sys.stdout.write('\033[?1049l\033[?25h\033[2J\033[H'); sys.stdout.flush()

def main():
    if '--btop' in sys.argv:
        try: btop()
        except Exception as e:
            sys.stdout.write('\033[?1049l\033[?25h'); print(f"{C['red']}btop: {e}{R}")
        return
    try:
        instalar(); shell()
    except KeyboardInterrupt:
        sys.stdout.write('\033[?1049l\033[?25h')
        print(f"\n{C['red']}[!] Interrompido.{R}\n")

if __name__ == '__main__':
    main()