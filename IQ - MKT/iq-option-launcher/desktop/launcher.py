"""IQ Visual: desktop launcher without a Chrome extension."""
import argparse
import json
import os
import queue
import sys
import tkinter as tk
from tkinter import messagebox, ttk
from core import DATA_DIR, Session, initialize_data


class App:
    def __init__(self, root, config, auto_start=False):
        self.root = root
        self.config = config
        try:
            settings = json.loads((DATA_DIR / 'settings.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            settings = {}
        if not isinstance(settings, dict):
            settings = {}
        self.session = Session(config, settings)
        root.title('IQ Visual • Launcher')
        root.geometry('640x810')
        root.minsize(590, 800)
        root.configure(bg='#0b1120')
        self.closing = False
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TCombobox', fieldbackground='#1b2940', background='#24344e', foreground='#eef3ff', padding=8)
        root.option_add('*TCombobox*Listbox.background', '#1b2940')
        root.option_add('*TCombobox*Listbox.foreground', '#eef3ff')
        self.panel = tk.Frame(root, bg='#0b1120', padx=32, pady=26)
        self.panel.pack(fill='both', expand=True)
        self.label('IQ VISUAL  /  SEM EXTENSÃO', 10, '#7fa9ef')
        self.label('Um Chrome. Seu tema.', 26, '#f0f5ff', pady=12)
        self.label('Perfil exclusivo, cores personalizáveis e restauração em um clique.', 10, '#98abc7')
        self.label('TEMA VISUAL', 10, '#98abc7', pady=18)
        self.theme = ttk.Combobox(self.panel, values=[t['name'] for t in config['themes']], state='readonly', font=('Segoe UI', 11))
        self.theme.current(next((i for i, t in enumerate(config['themes']) if t['id'] == self.session.theme_id), 0))
        self.theme.pack(fill='x')
        self.theme.bind('<<ComboboxSelected>>', lambda _: self.session.command('theme', config['themes'][self.theme.current()]['id']))
        self.enabled = tk.BooleanVar(value=self.session.enabled)
        tk.Checkbutton(self.panel, text='Aplicar tema automaticamente', variable=self.enabled, command=self.toggle,
                       bg='#0b1120', fg='#d6e2f5', selectcolor='#1b2940', activebackground='#0b1120', activeforeground='#ffffff', font=('Segoe UI', 11)).pack(anchor='w', pady=15)
        self.open_button = self.button('Abrir Chrome exclusivo', self.start, '#2563eb')
        row = tk.Frame(self.panel, bg='#0b1120')
        row.pack(fill='x', pady=10)
        self.restore_button = self.button('Restaurar original', self.restore, '#1b2940', row)
        self.stop_button = self.button('Encerrar Chrome', lambda: self.session.command('stop'), '#1b2940', row)
        self.card = tk.Frame(self.panel, bg='#141e30', padx=18, pady=16)
        self.card.pack(fill='x', pady=12)
        self.status = tk.Label(self.card, text='Pronto para abrir', bg='#141e30', fg='#8db6ff', font=('Segoe UI Semibold', 14), anchor='w')
        self.status.pack(fill='x')
        self.stats = tk.Label(self.card, text='0 elementos • 0 componentes Shadow DOM', bg='#141e30', fg='#9aacc7', font=('Segoe UI', 10), anchor='w')
        self.stats.pack(fill='x', pady=8)
        self.detail = tk.Label(self.card, text='O console mostrará como a sala da IQ Option foi carregada.', bg='#141e30', fg='#9aacc7', font=('Segoe UI', 10), wraplength=500, justify='left', anchor='w')
        self.detail.pack(fill='x')
        self.button('Abrir pasta de configuração', lambda: os.startfile(str(DATA_DIR)), '#1b2940')
        self.label('Ao fechar o aplicativo, o Chrome exclusivo também será encerrado.', 9, '#7c90af', pady=12)
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(150, self.poll)
        if auto_start:
            root.after(300, self.start)

    def label(self, text, size, color, pady=0):
        tk.Label(self.panel, text=text, bg='#0b1120', fg=color, font=('Segoe UI', size), anchor='w', wraplength=560, justify='left').pack(fill='x', pady=pady)

    def button(self, text, command, background, parent=None):
        button = tk.Button(parent or self.panel, text=text, command=command, bg=background, fg='#eef4ff',
                           activebackground='#355c95', activeforeground='white', relief='flat', borderwidth=0,
                           padx=14, pady=12, cursor='hand2', font=('Segoe UI Semibold', 10))
        if parent:
            button.pack(side='left', expand=True, fill='x', padx=3)
        else:
            button.pack(fill='x')
        return button

    def toggle(self):
        self.session.command('enabled', self.enabled.get())

    def restore(self):
        self.enabled.set(False)
        self.toggle()

    def start(self):
        self.open_button.configure(state='disabled')
        self.status.configure(text='Iniciando Chrome…')
        self.detail.configure(text='Na primeira abertura, o driver compatível pode ser baixado automaticamente.')
        self.session.command('start')

    def close(self):
        if self.closing:
            return
        self.closing = True
        self.status.configure(text='Encerrando Chrome…')
        self.open_button.configure(state='disabled')
        self.session.command('close')

    def poll(self):
        try:
            while True:
                kind, value = self.session.events.get_nowait()
                if kind == 'closed':
                    self.root.destroy()
                    return
                if kind == 'stopped' and not self.closing:
                    self.open_button.configure(state='normal')
                    self.status.configure(text='Chrome encerrado')
                    self.stats.configure(text='0 elementos • 0 componentes Shadow DOM')
                    self.detail.configure(text='O perfil exclusivo será reutilizado na próxima abertura.')
                elif kind == 'diagnostics' and not self.closing:
                    labels = {'active': 'Tema aplicado', 'disabled': 'Cores originais', 'incompatible': 'Página sem alvos compatíveis'}
                    self.status.configure(text=labels.get(value['status'], 'Verificando página'))
                    self.stats.configure(text=f"{value['elementsChanged']} alvos • {value.get('domElements', 0)} DOM • {value.get('canvasElements', 0)} canvas")
                    details = list(value['warnings'])
                    if not value['domainAuthorized']:
                        details.append('O domínio atual não está configurado para receber o tema.')
                    elif not value['routeSupported']:
                        details.append('Esta rota não está configurada para receber o tema.')
                    load = f"Carregamento: {value.get('readyState', '?')} • modo {value.get('renderMode', '?')} • WebGL {value.get('webglCanvases', 0)} • iframes {value.get('iframeElements', 0)}"
                    self.detail.configure(text='\n'.join([load, *details]) if details else load + '\nTema: ' + value['themeName'])
                elif kind == 'notice':
                    print('[IQ Visual] ' + str(value), flush=True)
                    self.detail.configure(text=value)
                elif kind == 'login':
                    print('[IQ Visual] ' + str(value), flush=True)
                    self.status.configure(text='Login necessário neste perfil')
                    self.detail.configure(text=value)
                elif kind == 'error':
                    self.status.configure(text='Não foi possível abrir')
                    self.detail.configure(text=value)
                    messagebox.showerror('IQ Visual', value)
        except queue.Empty:
            pass
        self.root.after(150, self.poll)


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description='IQ Visual Launcher')
    parser.add_argument('--auto', action='store_true', help='abre a IQ Option automaticamente')
    args = parser.parse_args()
    root = tk.Tk()
    try:
        config = initialize_data()
    except Exception as error:
        root.withdraw()
        messagebox.showerror('Configuração inválida', str(error) + '\n\nArquivo: ' + str(DATA_DIR / 'config.json'))
        root.destroy()
        return
    app = App(root, config, args.auto)
    print('[IQ Visual] Plataforma: https://iqoption.com/traderoom', flush=True)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print('[IQ Visual] Interrupção recebida. Encerrando a sessão.', flush=True)
        app.session.command('close')
        app.session.thread.join(15)
        root.destroy()


if __name__ == '__main__':
    main()
