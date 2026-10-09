# IQ Visual Launcher — sem extensão

Aplicativo Windows que abre o Google Chrome com um perfil exclusivo e injeta um tema de cores via Selenium/Chrome DevTools Protocol. O tema é mantido após recarregamentos, navegação e mudanças de conteúdo, inclusive em novas abas. A aplicação acompanha alvos de leitura e componentes com Shadow DOM aberto a cada 800 ms.

## Usar

1. Dê dois cliques em `Iniciar.cmd`: ele abre a IQ Option automaticamente, mantém o console visível e exibe os logs. Para abrir apenas a interface, execute `dist/IQ-Visual-Launcher-console.exe` sem argumento.
2. O único ambiente é `https://iqoption.com/traderoom`.
3. Escolha **Azul e laranja** ou **Alto contraste** e clique em **Abrir Chrome exclusivo**.
4. Use **Restaurar original** para remover o tema. Marque **Aplicar tema automaticamente** para reativá-lo.
5. **Encerrar Chrome** fecha apenas a sessão criada pelo aplicativo. Fechar o aplicativo também encerra essa sessão.

Na primeira abertura, a IQ Option pode mostrar a tela de login porque o aplicativo usa um perfil separado do seu Chrome habitual. Faça login nessa janela uma vez; a sessão será mantida no perfil exclusivo. O launcher não copia senhas nem credenciais do Chrome normal.

O Google Chrome deve estar instalado. A primeira execução pode precisar de internet para o Selenium Manager baixar o ChromeDriver compatível. O `.exe` inclui Python e as bibliotecas: não é necessário instalar Python para utilizá-lo. O executável não tem assinatura digital.

## Objetivos preservados da extensão

- Alteração local e reversível de cores, com dois temas.
- Domínios e rotas definidos por plataforma; navegação fora deles remove o tema.
- Diagnóstico de estado, quantidade de alvos e Shadow DOM aberto.
- Perfil persistente e separado do Chrome habitual, em `%LOCALAPPDATA%/IQVisualLauncher/chrome-profile`.
- Configuração e preferência de tema locais; sem edição de saldos, resultados, textos ou automação de operações.

O aplicativo pode recolorir qualquer elemento que corresponda aos seletores configurados, incluindo controles interativos. Não acessa iframes nem Shadow DOM fechado. Gráficos desenhados em canvas não podem ser recoloridos por esse mecanismo. Ele não solicita nem registra credenciais: o login, se necessário, ocorre diretamente na plataforma dentro do Chrome. O navegador conserva a sessão no perfil exclusivo.

## Estado da integração IQ Option

**Os seletores da plataforma ainda precisam de validação dentro da sala autenticada.** A configuração contém candidatos (`.profit`, `.loss`, `.pnl-positive`, `.pnl-negative`) e aponta somente para `https://iqoption.com/traderoom`. O console mostra o carregamento e a estrutura real da página, incluindo canvas e WebGL. A interface mostra o aviso de seletores ainda não validados mesmo se encontrar candidatos.

Se a plataforma usar outro domínio, rota ou estrutura, clique em **Abrir pasta de configuração**, edite `config.json` e reinicie o aplicativo. Ajuste `origins`, `routes` e `targets` para elementos de leitura verificados. A configuração já inclui correspondências controladas para classes que contenham `profit`, `loss` e `pnl`. Para novos alvos, use uma classe específica ou um atributo `data-*` com valor exato. Marque `verified` como `true` somente depois de conferir os alvos na sala da corretora.

Exemplo de alvo: `"profit": [".classe-especifica-de-lucro"]`. As cores usam `#RRGGBB`. Configurações inválidas impedem a abertura e mostram o motivo. Uma nova versão da configuração é migrada automaticamente e guarda o arquivo anterior em `config.previous.json`.

## Desenvolvimento e verificação

```powershell
python -m pip install -r requirements.txt
python launcher.py
python -m unittest test_launcher -v
.\build.ps1
```

Execute na pasta `desktop`. O teste de integração abre somente a IQ Option real, com um perfil temporário e Chrome headless. Ele verifica a inicialização e o diagnóstico estrutural; se a plataforma redirecionar ao login, isso não valida o tema dentro da sala autenticada. Este aplicativo não depende do build Vite.

## Como detecta o carregamento

O launcher registra o JavaScript via `Page.addScriptToEvaluateOnNewDocument` antes da navegação. Ele não usa IA, OCR ou reconhecimento visual: consulta o DOM e os seletores configurados. O Selenium espera o carregamento do documento por até 25 segundos; depois o diagnóstico é atualizado a cada segundo, e os elementos são acompanhados a cada 800 ms.

O console informa `document.readyState`, URL, rota, total de nós DOM, canvas, contextos WebGL observados, iframes e Shadow DOM aberto. `documentoCompleto` indica o evento de carregamento do documento; `superficieCorretora` indica a presença de canvas ou alvos na rota da sala. Nenhum dos dois garante que o motor interno terminou todos os downloads ou que uma operação está disponível. Os contextos WebGL são observados quando a própria plataforma chama `canvas.getContext()`, sem criar contextos adicionais.

Cada seletor correspondente recebe uma regra CSS de `color`. Na superfície canvas/WebGL, o launcher aplica um filtro gráfico à imagem final: tons predominantemente verdes são convertidos na cor de lucro do tema, e tons predominantemente vermelhos na cor de perda. Como esse tratamento ocorre sobre o canvas inteiro, outros pixels com as mesmas características também podem mudar.

Arquitetura: `launcher.py` contém a interface Tk; `core.py` executa os comandos do navegador em uma fila de trabalho; `injector.js` acompanha o documento e injeta folhas de estilo identificadas, removidas na restauração; `config.json` define plataformas, alvos e temas. O perfil separado segue a [orientação do Chrome sobre depuração remota](https://developer.chrome.com/blog/remote-debugging-port). A injeção usa a [API CDP do Selenium](https://www.selenium.dev/selenium/docs/api/py/selenium_webdriver_remote/selenium.webdriver.remote.webdriver.html).
