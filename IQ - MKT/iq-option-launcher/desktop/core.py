"""Chrome session and configuration; Tk widgets stay on the main thread."""
import json
import os
from pathlib import Path
import queue
import re
import sys
import threading
import traceback
from datetime import datetime
from urllib.parse import urlsplit

from selenium import webdriver
from selenium.common.exceptions import NoSuchWindowException, TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


RESOURCE_DIR = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
DATA_DIR = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'IQVisualLauncher'
SELECTOR = re.compile(r"(?:\.[a-zA-Z_][\w-]*|\[data-[\w-]+=['\"][\w-]+['\"]\]|\[class\*=['\"](?:profit|loss|pnl|balance|amount|value|result)['\"]\])\Z")


def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [IQ Visual] {message}", flush=True)


def read_config(path):
    config = json.loads(Path(path).read_text(encoding='utf-8'))
    if not config.get('themes') or not config.get('platforms'):
        raise ValueError('Configuração sem temas ou plataformas.')
    theme_ids = set()
    for theme in config['themes']:
        if theme['id'] in theme_ids:
            raise ValueError('IDs de tema duplicados.')
        theme_ids.add(theme['id'])
        for role in ('value', 'caption', 'profit', 'loss'):
            if not re.fullmatch(r'#[0-9a-fA-F]{6}', theme['colors'][role]):
                raise ValueError('As cores devem usar hexadecimal #RRGGBB.')
    for platform in config['platforms']:
        if not platform['origins'] or not platform['routes']:
            raise ValueError('Defina origens e rotas da plataforma.')
        for origin in platform['origins']:
            url = urlsplit(origin)
            if url.scheme != 'https' or not url.hostname or url.username or url.password or url.path or url.query or url.fragment:
                raise ValueError('Origem inválida: use https://dominio sem caminho.')
        for route in platform['routes']:
            if not route.startswith('/') or '?' in route or '#' in route or '*' in route:
                raise ValueError('Rota inválida.')
        for role, selectors in platform['targets'].items():
            if role not in ('value', 'caption', 'profit', 'loss'):
                raise ValueError('Tipo de alvo inválido.')
            for selector in selectors:
                if not SELECTOR.fullmatch(selector):
                    raise ValueError('Use uma classe específica ou atributo data-* como seletor: ' + selector)
    return config


def initialize_data():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / 'config.json'
    bundled_path = RESOURCE_DIR / 'config.json'
    bundled = read_config(bundled_path)
    current_version = -1
    if path.exists():
        try:
            current_version = int(json.loads(path.read_text(encoding='utf-8')).get('schemaVersion', 0))
        except (OSError, ValueError, TypeError):
            current_version = -1
    if current_version < int(bundled.get('schemaVersion', 1)):
        if path.exists():
            (DATA_DIR / 'config.previous.json').write_bytes(path.read_bytes())
        path.write_bytes(bundled_path.read_bytes())
        log(f"Configuração local atualizada para a versão {bundled.get('schemaVersion', 1)}.")
    return read_config(path)


def chrome_options(profile=None, headless=False):
    options = Options()
    for base in (os.environ.get('PROGRAMFILES'), os.environ.get('PROGRAMFILES(X86)'), os.environ.get('LOCALAPPDATA')):
        if base and (candidate := Path(base) / 'Google/Chrome/Application/chrome.exe').is_file():
            options.binary_location = str(candidate)
            break
    if profile:
        options.add_argument('--user-data-dir=' + str(profile))
    options.add_argument('--remote-debugging-pipe')
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    options.add_argument('--window-size=1280,900')
    if headless:
        options.add_argument('--headless=new')
    return options


def injection_source(config):
    return (RESOURCE_DIR / 'injector.js').read_text(encoding='utf-8') + '\nwindow.__iqVisualLauncher_v1?.configure(' + json.dumps(config, ensure_ascii=True) + ');'


def make_runtime_config(platform, theme, enabled):
    return {'origins': platform['origins'], 'routes': platform['routes'], 'verified': platform.get('verified', False),
            'themeName': theme['name'], 'enabled': enabled,
            'canvasColors': {'profit': theme['colors']['profit'], 'loss': theme['colors']['loss']},
            'rules': [{'selector': selector, 'color': theme['colors'][role]}
                      for role, selectors in platform['targets'].items() for selector in selectors]}


class Session:
    def __init__(self, config, settings):
        self.config = config
        self.theme_id = settings.get('themeId', 'default')
        self.enabled = settings.get('enabled', True)
        self.commands = queue.Queue()
        self.events = queue.Queue()
        self.driver = None
        self.platform = self.config['platforms'][0]
        self.scripts = {}
        self.closing = False
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def command(self, name, value=None):
        self.commands.put((name, value))

    def theme(self):
        return next((t for t in self.config['themes'] if t['id'] == self.theme_id), self.config['themes'][0])

    def save(self):
        path = DATA_DIR / 'settings.json'
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'themeId': self.theme_id, 'enabled': self.enabled}), encoding='utf-8')
        temporary.replace(path)

    def install(self, replace=False):
        runtime = make_runtime_config(self.platform, self.theme(), self.enabled)
        source = injection_source(runtime)
        handles = self.driver.window_handles
        current = None
        try:
            current = self.driver.current_window_handle
        except NoSuchWindowException:
            pass
        for handle in handles:
            self.driver.switch_to.window(handle)
            if replace or handle not in self.scripts:
                if old := self.scripts.get(handle):
                    self.driver.execute_cdp_cmd('Page.removeScriptToEvaluateOnNewDocument', {'identifier': old})
                self.scripts[handle] = self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': source})['identifier']
                self.driver.execute_script(source)
        if current in handles:
            self.driver.switch_to.window(current)
        self.scripts = {h: s for h, s in self.scripts.items() if h in handles}

    def stop_browser(self):
        log('Encerrando Chrome exclusivo.')
        if self.driver:
            try:
                self.driver.quit()
            except WebDriverException:
                pass
            self.driver = None
        self.scripts.clear()
        self.events.put(('stopped', None))

    def start(self):
        if self.driver:
            return
        self.events.put(('starting', None))
        log('Preparando IQ Option.')
        url = self.platform['origins'][0] + self.platform['routes'][0]
        log('Abrindo URL: ' + url)
        os.environ['SE_AVOID_STATS'] = 'true'
        self.driver = webdriver.Chrome(options=chrome_options(DATA_DIR / 'chrome-profile'), service=Service(log_output=os.devnull))
        self.driver.set_page_load_timeout(25)
        self.driver.set_script_timeout(10)
        self.install()
        try:
            self.driver.get(url)
        except TimeoutException:
            self.events.put(('notice', 'A página continua carregando; o tema será verificado automaticamente.'))
        try:
            log('URL atual: ' + self.driver.current_url)
            if '/login' in urlsplit(self.driver.current_url).path:
                log('Login necessário no perfil exclusivo.')
                self.events.put(('login', 'Este Chrome usa um perfil separado. Faça login na IQ Option nesta janela uma vez; a sessão ficará salva neste perfil.'))
        except WebDriverException:
            pass
        self.events.put(('running', None))

    def run(self):
        while not self.closing:
            try:
                name, value = self.commands.get(timeout=1)
            except queue.Empty:
                name, value = 'poll', None
            try:
                if name == 'start':
                    self.start()
                elif name == 'stop':
                    self.stop_browser()
                elif name == 'close':
                    self.stop_browser()
                    self.closing = True
                elif name in ('theme', 'enabled', 'refresh'):
                    if name == 'theme':
                        self.theme_id = value
                    elif name == 'enabled':
                        self.enabled = value
                    self.save()
                    if self.driver:
                        self.install(replace=True)
                if self.driver:
                    self.install()
                    snapshot = self.driver.execute_script('return window.__iqVisualLauncher_v1?.snapshot() || null')
                    if snapshot:
                        status_signature = (snapshot.get('status'), snapshot.get('url'), snapshot.get('readyState'), snapshot.get('elementsChanged'), snapshot.get('domElements'), snapshot.get('canvasElements'), snapshot.get('webglCanvases'), snapshot.get('iframeElements'), snapshot.get('openShadowRoots'), tuple(str(w) for w in snapshot.get('warnings', [])))
                        if status_signature != getattr(self, '_last_status_signature', None):
                            log('URL: ' + snapshot.get('url', ''))
                            log(f"Página: readyState={snapshot.get('readyState')} documentoCompleto={snapshot.get('documentLoaded')} superficieCorretora={snapshot.get('platformSurfaceDetected')} modo={snapshot.get('renderMode')} DOM={snapshot.get('domElements')} canvas={snapshot.get('canvasElements')} WebGL={snapshot.get('webglCanvases')} iframes={snapshot.get('iframeElements')} shadow={snapshot.get('openShadowRoots')}")
                            log(f"Tema: status={snapshot.get('status')} alvos={snapshot.get('elementsChanged')} rota={snapshot.get('routeSupported')} avisos={len(snapshot.get('warnings', []))}")
                            self._last_status_signature = status_signature
                        self.events.put(('diagnostics', snapshot))
            except WebDriverException as error:
                log('WebDriver: ' + type(error).__name__)
                log(str(error))
                if name == 'start':
                    self.stop_browser()
                    self.events.put(('error', 'Não foi possível iniciar o Chrome. Feche outra instância deste aplicativo e confira o Chrome e sua conexão. Detalhes: ' + type(error).__name__))
                else:
                    try:
                        alive = self.driver and bool(self.driver.window_handles)
                    except WebDriverException:
                        alive = False
                    if not alive:
                        self.stop_browser()
                    else:
                        self.events.put(('notice', 'Aguardando o navegador terminar a navegação.'))
            except Exception as error:
                log('ERRO: ' + type(error).__name__)
                traceback.print_exc()
                self.stop_browser()
                self.events.put(('error', 'Falha no aplicativo: ' + type(error).__name__ + ': ' + str(error)))
        self.events.put(('closed', None))
