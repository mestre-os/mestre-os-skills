#!/usr/bin/env python3
"""telegram-bot-troca.py — troca o modelo e o esforço da janela do bot pelo Telegram (MestreOS, PASSO 7A). Mac e Windows.

A janela do bot é uma conversa do Claude Code, e ela não troca o próprio modelo enquanto roda. A troca grava as opções
novas, espera o turno acabar, fecha a janela, e o atalho meubot (que é um laço) abre de novo com --model e --effort
novos, retomando a MESMA conversa (--resume). A primeira mensagem da conversa reaberta pede ao agente o aviso "✅ pronto"
no Telegram, já assinado com o modelo novo. Se o modelo novo falhar logo na primeira resposta (um modelo que a conta não
tem, por exemplo), o gancho do turno devolve o de antes, uma vez só.

Uso (o agente da janela chama; a mensagem do dono vai SEMPRE literal e inteira, sem reescrever):
  trocar --pedido "<mensagem do dono>" [--modelo <o que você entendeu>] [--esforco <idem>]
      mensagem clara digitada → OK (troca já) · áudio, recorte ou frase solta → CONFIRMAR (pergunte: sim ou não)
  confirmar --pedido "<resposta do dono>"   (a pergunta vale 3 minutos)
  entender "<frase>"                        (só mostra o que entenderia; não muda nada)
  status
  atalho [--inicio]                         (o meubot chama: imprime as opções validadas da próxima abertura)
  derrubar <pid> <desde_ms> · reverter <erro> · desistir <erro>   (internos, rodam desacoplados)

Travas contra troca sem querer (desenho testado por uma aluna em 20/10/2026, que usa muito áudio; endurecido pela
revisão de 2 modelos no mesmo dia):
  1. Só vale mensagem do dono (conversa privada, lista de acesso), mais nova que a última troca. O que o plugin cita da
     mensagem arrastada não é o dono falando. Texto que o agente reescreveu ou recortou nunca troca na hora.
  2. Troca na hora só quando a mensagem INTEIRA do dono é um comando claro: o verbo no começo e o valor logo depois
     ("troca pro Sonnet", "muda o esforço pra alto", "volta pro Opus", "modelo Haiku", "esforço máximo", "esforço
     padrão"), até 160 letras, sem pergunta e sem negação ("não", "para de", "sem"). Áudio, recorte e o resto confirmam.
  3. O modelo só troca por nome: a conversa retomada guarda o modelo dela, então "modelo padrão" não teria efeito.
  4. Uma troca por vez. A janela só fecha com o turno quieto (reconferido depois da espera, sem tarefa em segundo
     plano); se não aquietar em 10 min, a troca é cancelada e o dono é avisado.
Só funciona na janela do bot aberta pelo meubot: é o atalho que reabre a janela (sem ele, ela fecharia e ficaria
fechada). Arquivos em ~/.mestreos/telegram-bot/: opcoes (valem nas próximas aberturas), retomar (vale uma vez; o meubot
apaga ao ler), troca.json, pendente.json, troca.log.
"""
import json, os, re, signal, subprocess, sys, time, unicodedata

H = os.path.expanduser("~")
PASTA = os.environ.get("MESTREOS_TELEGRAM_BOT_DIR") or os.path.join(H, ".mestreos", "telegram-bot")
OPCOES, RETOMAR, TROCA, PENDENTE, LOG = (os.path.join(PASTA, n) for n in
                                         ("opcoes", "retomar", "troca.json", "pendente.json", "troca.log"))
SECO = os.environ.get("MESTREOS_TELEGRAM_TROCA_SECO") == "1"   # testes: não derruba nem reabre nada
VALIDADE = 180     # s que a pergunta de confirmação vale
ESPERA_FIM = float(os.environ.get("MESTREOS_TELEGRAM_TROCA_ESPERA") or 600)   # s que a derrubada espera o turno aquietar
SEM_JANELA = 0x08000000

MODELOS = {"fable": "fable", "feible": "fable", "feibol": "fable", "opus": "opus", "opos": "opus", "sonnet": "sonnet",
           "sonet": "sonnet", "soneto": "sonnet", "sonete": "sonnet", "sonic": "sonnet", "haiku": "haiku",
           "haicai": "haiku", "haico": "haiku", "haiko": "haiku"}   # inclui erros comuns de ditado
NOME_MODELO = {"fable": "Fable", "opus": "Opus", "sonnet": "Sonnet", "haiku": "Haiku"}
ESFORCOS = {"baixo": "low", "baixa": "low", "low": "low", "medio": "medium", "media": "medium", "medium": "medium",
            "alto": "high", "alta": "high", "high": "high", "altissimo": "xhigh", "altissima": "xhigh", "xhigh": "xhigh",
            "maximo": "max", "maxima": "max", "max": "max"}
ESFORCOS_2 = {"muito alto": "xhigh", "extra alto": "xhigh"}
NOME_ESFORCO = {"low": "baixo", "medium": "médio", "high": "alto", "xhigh": "altíssimo", "max": "máximo"}
PADRAO = {"padrao", "default", "original"}
MODELO_PADRAO = "padrao"   # sentinela: "modelo padrão" é recusado (a conversa retomada restaura o modelo dela)
VERBOS = {"troca", "trocar", "troque", "muda", "mudar", "mude", "passa", "passar", "passe", "volta", "voltar", "volte",
          "coloca", "colocar", "coloque", "bota", "botar", "bote", "poe", "ponha", "usa", "usar", "use", "altera",
          "alterar", "altere", "liga", "ligar", "ligue", "deixa", "deixe"}
LIGACAO = {"para", "pra", "pro", "o", "a", "os", "as", "em", "no", "na", "ao", "nivel", "modo", "um", "uma", "de", "do",
           "da", "pelo", "pela"}
NEGA = {"nao", "nunca", "jamais", "nem", "sem"}
NEGA_2 = {"para de", "pare de", "parar de", "deixa de", "deixe de", "chega de"}   # "para" sozinho é preposição
SIM = {"sim", "pode", "confirmo", "confirma", "isso", "ok", "okay", "beleza", "manda", "bora", "claro", "positivo",
       "certo", "fechado", "quero", "troca"}
NAO = {"nao", "cancela", "cancelar", "negativo", "esquece", "deixa", "nada", "pare"}
CANAL = re.compile(r'<channel source="(?:plugin:)?telegram[^"]*"([^>]*)>(.*?)</channel>', re.S)
ARRASTADA = re.compile(r'^\s*\[o dono respondeu arrastando esta sua mensagem: «[^»]*»\]\s*')   # o plugin cita o agente
UUID = re.compile(r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}")
AVISO_TROCA = re.compile(r"MESTREOS_TROCA_(CONCLUIDA|FALHOU)_-?\d{1,20}")


def pasta_canal():
    """A mesma pasta que o plugin e os ganchos usam (TELEGRAM_STATE_DIR > CLAUDE_CONFIG_DIR > ~/.claude)."""
    if os.environ.get("TELEGRAM_STATE_DIR"):
        return os.environ["TELEGRAM_STATE_DIR"]
    return os.path.join(os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(H, ".claude"), "channels", "telegram")


def log(msg):
    try:
        os.makedirs(PASTA, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%d/%m %H:%M:%S ") + msg + "\n")
    except OSError:
        pass


def ler_json(caminho):
    try:
        with open(caminho, encoding="utf-8") as f:
            o = json.load(f)
        return o if isinstance(o, dict) else {}
    except (OSError, ValueError):
        return {}


def grava(caminho, texto, ascii_=False):
    """Troca atômica. opcoes e retomar vão em ASCII com o fim de linha do sistema. No Windows o os.replace falha
    (PermissionError) se o gancho estiver lendo naquele instante: tenta de novo algumas vezes."""
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    tmp = caminho + ".tmp%d" % os.getpid()
    with open(tmp, "w", encoding="ascii" if ascii_ else "utf-8", newline="\r\n" if os.name == "nt" else "\n") as f:
        f.write(texto + "\n")
    for tentativa in range(20):
        try:
            os.replace(tmp, caminho)
            return
        except PermissionError:
            if tentativa == 19:
                raise
            time.sleep(0.05)


def apaga(caminho):
    try:
        os.remove(caminho)
    except OSError:
        pass


# ---------- entender a frase

def normalizar(texto):
    t = unicodedata.normalize("NFKD", str(texto or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", t).split())


def canonico(texto):
    """Normaliza e corrige só a grafia dos modelos ditados ("SONET" → sonnet)."""
    return " ".join(MODELOS.get(p, p) for p in normalizar(texto).split())


def apos(w, i, pula=()):
    """Índice da 1ª palavra depois de i que não é de ligação (nem das palavras em `pula`)."""
    j = i + 1
    while j < len(w) and (w[j] in LIGACAO or w[j] in pula):
        j += 1
    return j


def esforco_em(w, j):
    """(nível, quantas palavras) do esforço que começa em j, ou (None, 0)."""
    if j + 1 < len(w) and w[j] + " " + w[j + 1] in ESFORCOS_2:
        return ESFORCOS_2[w[j] + " " + w[j + 1]], 2
    if j < len(w) and w[j] in ESFORCOS:
        return ESFORCOS[w[j]], 1
    return None, 0


def negada(w):
    return bool(set(w) & NEGA) or any(a + " " + b in NEGA_2 for a, b in zip(w, w[1:]))


def ler_frase(texto):
    """→ (mudanças, clara). mudanças: {"modelo": alias|MODELO_PADRAO, "esforco": nível|None} (esforço None = padrão).
    clara = comando no começo, cada valor logo depois do seu gatilho, sem pergunta e sem negação; senão confirma."""
    w = canonico(texto).split()
    sem_ressalva = len(texto) <= 160 and "?" not in texto and not negada(w)
    mud, ancoras = {}, []
    if "tudo" in w and PADRAO & set(w):
        return {"modelo": MODELO_PADRAO, "esforco": None}, False
    modelos = [i for i, p in enumerate(w) if p in NOME_MODELO]
    if len(set(w[i] for i in modelos)) == 1:
        k = modelos[0]
        mud["modelo"] = w[k]
        ancoras.append(any(apos(w, a, ("modelo",)) == k for a in range(k) if w[a] in VERBOS or w[a] == "modelo"))
        nivel, n = esforco_em(w, apos(w, k, tuple(p for p in w if p.isdigit())))   # "opus 5 5 alto"
        if nivel and "esforco" not in w:
            mud["esforco"] = nivel
            ancoras.append(True)
    elif len(set(w[i] for i in modelos)) > 1:
        return {}, False                       # "troca o sonnet pelo opus": dois modelos, a confirmação esclarece
    for a, p in enumerate(w):
        if p == "modelo" and "modelo" not in mud and apos(w, a) < len(w) and w[apos(w, a)] in PADRAO:
            mud["modelo"] = MODELO_PADRAO
            ancoras.append(True)
        if p == "esforco":
            j = apos(w, a)
            nivel, n = esforco_em(w, j)
            if nivel:
                mud["esforco"] = nivel
                ancoras.append(True)
            elif j < len(w) and w[j] in PADRAO:
                mud["esforco"] = None
                ancoras.append(True)
            else:
                ancoras.append(False)
    comando = any(p in VERBOS or p in ("modelo", "esforco") for p in w[:4])
    clara = bool(mud) and comando and all(ancoras) and sem_ressalva
    return mud, clara


def leitura_do_agente(modelo_ia, esforco_ia):
    """O que o agente entendeu (vale no áudio, sempre com confirmação): "Sonnet 5.5" → sonnet, "esforço médio" → medium."""
    mud = {}
    m = [MODELOS[p] for p in canonico(modelo_ia).split() if p in MODELOS]
    if m:
        mud["modelo"] = m[0]
    elif PADRAO & set(normalizar(modelo_ia).split()):
        mud["modelo"] = MODELO_PADRAO
    e = [p for p in normalizar(esforco_ia).replace("esforco", " ").split()]
    nivel, _ = esforco_em(e, 0) if e else (None, 0)
    if nivel:
        mud["esforco"] = nivel
    elif PADRAO & set(e):
        mud["esforco"] = None
    return mud


# ---------- opções da janela

def ler_tokens(caminho):
    try:
        with open(caminho, encoding="ascii") as f:
            return f.read().split()
    except (OSError, UnicodeDecodeError):
        return None


def tokens_de_opcoes(w):
    """As opções que ficam, só se o arquivo inteiro for válido: pares --model <alias> e --effort <nível>."""
    if not w:
        return []
    if len(w) % 2 or len(w) > 4:
        return None
    ok = {"--model": NOME_MODELO, "--effort": NOME_ESFORCO}
    pares = [(w[i], w[i + 1]) for i in range(0, len(w), 2)]
    if len({k for k, _ in pares}) != len(pares) or not all(k in ok and v in ok[k] for k, v in pares):
        return None
    return w


def tokens_de_retomar(w):
    """Vale uma vez: exatamente --resume <conversa> MESTREOS_TROCA_(CONCLUIDA|FALHOU)_<chat>."""
    if not w:
        return []
    if len(w) == 3 and w[0] == "--resume" and UUID.fullmatch(w[1]) and AVISO_TROCA.fullmatch(w[2]):
        return w
    return None


def ler_opcoes():
    """(modelo, esforço) que o meubot passa hoje; None = padrão da conta."""
    w = tokens_de_opcoes(ler_tokens(OPCOES) or [])
    w = w or []
    d = dict(zip(w[::2], w[1::2]))
    return [d.get("--model"), d.get("--effort")]


def grava_opcoes(par):
    m, e = (list(par or []) + [None, None])[:2]
    partes = (["--model", m] if m in NOME_MODELO else []) + (["--effort", e] if e in NOME_ESFORCO else [])
    if partes:
        grava(OPCOES, " ".join(partes), ascii_=True)
    else:
        apaga(OPCOES)


def aplica(atual, mud):
    return [mud.get("modelo", atual[0]), mud.get("esforco", atual[1])]


def descreve(par):
    m, e = (list(par or []) + [None, None])[:2]
    return "%s · esforço %s" % (NOME_MODELO.get(m, "modelo padrão da conta"), NOME_ESFORCO.get(e, "padrão"))


def cmd_atalho(inicio):
    """O meubot pergunta o que passar ao claude. Só sai palavra da lista (alias, nível, conversa, aviso): qualquer
    coisa a mais nos arquivos (uma flag escrita por outro programa, um & no Windows) é ignorada e registrada."""
    if inicio:   # abertura pelo dono: um retomar que sobrou de uma troca interrompida não vale mais
        apaga(RETOMAR)
    opc = tokens_de_opcoes(ler_tokens(OPCOES) or [])
    if opc is None:
        log("opcoes com conteúdo fora da lista: ignoradas nesta abertura")
        opc = []
    ret = [] if inicio else tokens_de_retomar(ler_tokens(RETOMAR) or [])
    if ret is None:
        log("retomar com conteúdo fora da lista: ignorado")
        ret = []
    apaga(RETOMAR)
    print(" ".join(opc + ret))
    return 0


# ---------- a janela e a mensagem do dono

def cauda(caminho, limite=1_000_000):
    try:
        with open(caminho, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - limite))
            return f.read().decode("utf-8", "ignore")
    except (OSError, TypeError):
        return ""


def instante(iso):
    try:
        from datetime import datetime
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return 0.0


def do_dono():
    """Quem fala com o bot: a lista de acesso do plugin (access.json, só números)."""
    lista = ler_json(os.path.join(pasta_canal(), "access.json")).get("allowFrom") or []
    return {str(x) for x in lista if re.fullmatch(r"-?\d{1,20}", str(x))}


def textos_de(conteudo):
    if isinstance(conteudo, str):
        return [conteudo]
    return [x.get("text", "") for x in (conteudo or []) if isinstance(x, dict) and x.get("type") == "text"]


def mensagens_do_dono(transcript):
    """As mensagens que o dono mandou pelo Telegram nesta conversa, da mais velha pra mais nova: texto (sem a citação da
    mensagem arrastada), se é áudio, quando, chat. Chegam como linha "user" (janela parada) ou como anexo da fila
    "queued_command" de origem "channel" (janela trabalhando). Resumo de compactação não conta."""
    dono, lista = do_dono(), []
    for linha in cauda(transcript).splitlines():
        if "<channel" not in linha:
            continue
        try:
            o = json.loads(linha)
        except ValueError:
            continue
        if not isinstance(o, dict):
            continue
        if o.get("type") == "user" and not o.get("isCompactSummary"):
            partes, quando = textos_de((o.get("message") or {}).get("content")), o.get("timestamp")
        elif o.get("type") == "attachment" and (o.get("attachment") or {}).get("type") == "queued_command" \
                and ((o["attachment"].get("origin") or {}).get("kind") == "channel"):
            partes, quando = textos_de(o["attachment"].get("prompt")), o["attachment"].get("timestamp") or o.get("timestamp")
        else:
            continue
        for p in partes:
            for m in CANAL.finditer(str(p)):
                attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
                chat, uid = attrs.get("chat_id", ""), attrs.get("user_id", attrs.get("chat_id", ""))
                if chat != uid or uid not in dono:   # só a conversa privada com quem está na lista de acesso
                    continue
                lista.append({"texto": ARRASTADA.sub("", m.group(2).strip()).strip(), "quando": instante(quando),
                              "audio": attrs.get("attachment_kind") in ("voice", "audio"), "chat": chat})
    return lista


def novas(s, depois_de):
    """Até 3 mensagens do dono mais novas que `depois_de` (rajada: o pedido pode vir junto com uma foto)."""
    return [m for m in mensagens_do_dono(s["transcript"]) if m["quando"] > depois_de][-3:]


def janela():
    """(sessão, motivo da recusa). Só a janela do bot aberta pelo meubot pode trocar o próprio modelo."""
    s = ler_json(os.path.join(pasta_canal(), "sessao.json"))
    if not s.get("sid") or not s.get("transcript"):
        return None, "os ganchos da janela do bot não estão instalados (PASSO 7A.4)."
    if not UUID.fullmatch(str(s["sid"])):
        return None, "não reconheci a conversa desta janela."
    if not os.environ.get("CLAUDE_PID") or os.environ["CLAUDE_PID"] != str(s.get("pid")):
        return None, "isto só funciona dentro da janela do bot."
    if os.environ.get("MESTREOS_MEUBOT") != "1":
        return None, ("esta janela não foi aberta pelo atalho meubot, e é ele que reabre a janela com o modelo novo. "
                      "Peça ao dono pra fechar a janela e abrir de novo com meubot num terminal novo.")
    return s, ""


def contem(mensagem, pedido):
    alvo = canonico(pedido)
    return bool(alvo) and (" " + alvo + " ") in (" " + canonico(mensagem) + " ")


def em_andamento():
    """Uma troca por vez: outra pedida ou fechando a janela agora (antes de a janela reabrir) atrapalharia o 'de antes'."""
    t = ler_json(TROCA)
    return t.get("estado") in ("pedido", "reiniciando", "revertendo") and time.time() - float(t.get("t") or 0) < ESPERA_FIM + 120


RECUSA_PADRAO = ("RECUSADO: o modelo eu só troco por nome (Fable, Opus, Sonnet ou Haiku): a conversa retomada guarda o "
                 "modelo dela, então \"modelo padrão\" não teria efeito. O esforço volta pro padrão com \"esforço "
                 "padrão\". Pergunte ao dono qual modelo ele quer. Nada mudou.")


# ---------- troca

def desacoplado(*args):
    """Roda este script por fora da janela (ele vai fechá-la). Desenho do Windows provado por uma aluna em 20/10/2026."""
    exe = sys.executable
    if os.name == "nt":
        w = os.path.join(os.path.dirname(exe), "pythonw.exe")
        exe = w if os.path.exists(w) else exe
        for fl in (0x01000208 | SEM_JANELA, 0x00000208 | SEM_JANELA):   # desacoplado, grupo novo; tenta sair do job
            try:
                subprocess.Popen([exe, os.path.abspath(__file__)] + list(args), creationflags=fl, close_fds=True,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except OSError:
                continue
        return False
    try:
        subprocess.Popen([exe, os.path.abspath(__file__)] + list(args), start_new_session=True, close_fds=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError:
        return False


def executar(s, atual, alvo, chat, quando_msg, origem):
    grava_opcoes(alvo)
    grava(RETOMAR, "--resume %s MESTREOS_TROCA_CONCLUIDA_%s" % (s["sid"], chat or "0"), ascii_=True)
    grava(TROCA, json.dumps({"estado": "pedido", "de": atual, "para": alvo, "sid": s["sid"], "chat": chat or "0",
                             "t": time.time(), "t_msg": quando_msg, "pid": str(s["pid"])}, ensure_ascii=False))
    apaga(PENDENTE)
    log("troca (%s): %s -> %s" % (origem, descreve(atual), descreve(alvo)))
    if not SECO and not desacoplado("derrubar", str(s["pid"]), str(int(time.time() * 1000))):
        grava_opcoes(atual)
        apaga(RETOMAR)
        print("ERRO: não consegui preparar o reinício. Nada mudou.")
        return 1
    print('OK: troca aceita, de %s para %s. Mande AGORA pelo reply: "⏳ Trocando pra %s. Volto em uns 30 segundos, '
          'na mesma conversa." e encerre o turno sem fazer mais nada: a janela fecha e abre sozinha.'
          % (descreve(atual), descreve(alvo), descreve(alvo)))
    return 0


def cmd_trocar(pedido, modelo_ia="", esforco_ia=""):
    s, motivo = janela()
    if not s:
        print("RECUSADO: " + motivo)
        return 2
    if em_andamento():
        print("RECUSADO: já tem uma troca em andamento. Espere a janela voltar e peça de novo. Nada mudou.")
        return 2
    cands = novas(s, float(ler_json(TROCA).get("t_msg") or 0))
    if not cands:
        print("RECUSADO: não achei mensagem nova do dono pedindo a troca (e uma mensagem só vale uma troca). Nada mudou.")
        return 2
    inteira = next((m for m in reversed(cands) if not m["audio"] and canonico(m["texto"]) == canonico(pedido)), None)
    digitada = inteira or next((m for m in reversed(cands) if not m["audio"] and contem(m["texto"], pedido)), None)
    audio = next((m for m in reversed(cands) if m["audio"]), None)
    if not digitada and not audio:
        log("recusado (não é a mensagem literal do dono): %r" % str(pedido)[:80])
        print("RECUSADO: esse texto não está nas últimas mensagens do dono. Passe a mensagem dele literal, sem "
              "reescrever. Nada mudou.")
        return 2
    atual = ler_opcoes()
    mud, clara = ler_frase(inteira["texto"] if inteira else pedido)   # o juízo é sobre o que o dono escreveu
    if inteira and clara:
        if mud.get("modelo") == MODELO_PADRAO:
            print(RECUSA_PADRAO)
            return 2
        alvo = aplica(atual, mud)
        if alvo == atual:
            print("IGUAL: a janela já está em %s. Nada a reiniciar." % descreve(atual))
            return 0
        return executar(s, atual, alvo, inteira["chat"], inteira["quando"], "frase clara")
    mud = {**mud, **leitura_do_agente(modelo_ia, esforco_ia)}   # áudio, recorte ou frase solta: vale com o "sim" do dono
    if mud.get("modelo") == MODELO_PADRAO:
        print(RECUSA_PADRAO)
        return 2
    if not mud:
        print("RECUSADO: não achei modelo nem esforço nesse pedido. Nada mudou. Pergunte ao dono qual modelo (Fable, "
              "Opus, Sonnet, Haiku) ou esforço (baixo, médio, alto, altíssimo, máximo, padrão) ele quer.")
        return 2
    alvo = aplica(atual, mud)
    if alvo == atual:
        print("IGUAL: a janela já está em %s. Nada a reiniciar." % descreve(atual))
        return 0
    grava(PENDENTE, json.dumps({"para": alvo, "t": time.time(), "chat": (digitada or audio)["chat"]}))
    log("confirmação pedida: %s -> %s (%r)" % (descreve(atual), descreve(alvo), str(pedido)[:80]))
    print('CONFIRMAR: nada mudou ainda. Pergunte ao dono, exatamente: "Entendi: trocar pra %s. Confirma? Responda sim '
          'ou não." Quando ele responder, rode: telegram-bot-troca.py confirmar --pedido "<resposta dele, literal>". '
          'A pergunta vale 3 minutos.' % descreve(alvo))
    return 3


def cmd_confirmar(resposta):
    s, motivo = janela()
    if not s:
        print("RECUSADO: " + motivo)
        return 2
    p = ler_json(PENDENTE)
    if not p:
        print("RECUSADO: não há troca esperando confirmação. Nada mudou.")
        return 2
    if time.time() - float(p.get("t") or 0) > VALIDADE:
        apaga(PENDENTE)
        print("EXPIRADO: a pergunta passou de 3 minutos e foi descartada. Nada mudou; se ele ainda quiser, pede de novo.")
        return 2
    if em_andamento():
        print("RECUSADO: já tem uma troca em andamento. Espere a janela voltar. Nada mudou.")
        return 2
    depois = novas(s, float(p.get("t") or 0))
    if not depois:
        print("RECUSADO: o dono ainda não respondeu à pergunta. A troca continua esperando.")
        return 2
    msg = depois[-1]   # vale só a mensagem mais nova dele depois da pergunta, lida inteira
    if not msg["audio"] and not contem(msg["texto"], resposta):
        print("RECUSADO: essa resposta não é a última mensagem do dono. Passe a resposta literal dele. A troca continua "
              "esperando.")
        return 2
    texto = resposta if msg["audio"] else msg["texto"]
    w = canonico(texto).split()
    sim, nao = set(w) & SIM, set(w) & NAO
    if "?" in texto or len(w) > 8:   # pergunta ou conversa não é resposta de sim ou não
        sim = nao = set()
    if nao and not sim:
        apaga(PENDENTE)
        log("confirmação negada: %s" % descreve(p.get("para")))
        print("CANCELADO: o dono disse não. Nada mudou. Confirme a ele em uma linha.")
        return 0
    if sim and not nao:
        return executar(s, ler_opcoes(), p.get("para"), msg["chat"] or p.get("chat"), msg["quando"],
                        "confirmada pelo dono")
    print('AMBIGUO: não ficou claro se é sim ou não. Pergunte de novo: "Confirma trocar pra %s? Responda sim ou não." '
          'A troca continua esperando.' % descreve(p.get("para")))
    return 3


# ---------- reinício (desacoplado da janela)

def marca(nome):
    try:
        with open(os.path.join(pasta_canal(), nome), encoding="utf-8") as f:
            v = re.sub(r"[^0-9]", "", f.read())
        return int(v) if len(v) >= 12 else 0
    except (OSError, ValueError):
        return 0


def quieto(desde):
    """O turno acabou depois do pedido, nenhum outro abriu, e o último fim não deixou tarefa em segundo plano."""
    ini, end = marca("turn-start"), marca("turn-end")
    if not (end > int(desde) and end >= ini):
        return False
    plano = ler_json(os.path.join(pasta_canal(), "segundo-plano.json"))
    return not (int(plano.get("n") or 0) > 0 and int(plano.get("ts") or 0) >= end - 5000)


def e_claude(pid):
    """Confere que o número ainda é o processo do Claude Code (número de processo se reaproveita)."""
    try:
        if os.name == "nt":
            r = subprocess.run(["tasklist", "/FI", "PID eq %d" % int(pid), "/FO", "CSV", "/NH"], capture_output=True,
                               text=True, timeout=30, creationflags=SEM_JANELA)
            nome = r.stdout.split(",")[0].strip().strip('"')
        else:
            # -ww: caminho inteiro (sem ele o ps corta e o nome some); o nome é o do atalho aberto ("claude")
            r = subprocess.run(["ps", "-ww", "-o", "comm=", "-p", str(int(pid))], capture_output=True, text=True, timeout=10)
            nome = os.path.basename(r.stdout.strip())
        return nome.lower() in ("claude", "claude.exe", "node", "node.exe", "bun", "bun.exe")
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def encerra(pid):
    pid = int(pid)
    if os.name == "nt":   # /T leva junto o plugin e o que mais a janela abriu
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=60, creationflags=SEM_JANELA)
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return
    for _ in range(40):   # até 10 s pra sair sozinho; depois, à força
        time.sleep(0.25)
        try:
            os.kill(pid, 0)
        except OSError:
            return
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass


def avisa_dono(texto):
    envio = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telegram_send.py")
    if not os.path.exists(envio) or SECO:
        return
    try:
        subprocess.run([sys.executable.replace("pythonw.exe", "python.exe"), envio, texto], capture_output=True,
                       timeout=60, creationflags=SEM_JANELA if os.name == "nt" else 0)
    except (OSError, subprocess.SubprocessError):
        pass


def cancela(t, motivo):
    """A janela não aquietou: não fecha nada, desfaz as opções novas e avisa o dono."""
    if t.get("estado") == "pedido":
        grava_opcoes(t.get("de"))
    apaga(RETOMAR)
    t["estado"], t["t"] = "cancelada", time.time()
    grava(TROCA, json.dumps(t, ensure_ascii=False))
    log("troca cancelada: " + motivo)
    avisa_dono("⚠️ Não troquei o modelo: a janela do bot continuou trabalhando. Peça de novo quando ela terminar.")


def cmd_derrubar(pid, desde, estado="reiniciando"):
    """Espera o turno aquietar (o agente mandou o aviso e encerrou), reconfere depois de uma folga e só então fecha a
    janela; o meubot reabre. Nunca fecha no meio de um turno, nem de tarefa em segundo plano."""
    fim = time.time() + ESPERA_FIM
    while time.time() < fim:
        if quieto(desde):
            time.sleep(1.5)   # folga pro Claude Code terminar de gravar; mensagem nova nesse intervalo abre turno
            if quieto(desde):
                break
        time.sleep(0.5)
    else:
        cancela(ler_json(TROCA), "a janela não aquietou em %d s" % ESPERA_FIM)
        return 0
    t = ler_json(TROCA)
    if str(ler_json(os.path.join(pasta_canal(), "sessao.json")).get("pid")) != str(pid):
        apaga(RETOMAR)
        log("a janela %s já não é a janela do bot; nada fechado" % pid)
        return 0
    if SECO:
        t["estado"], t["t"] = estado, time.time()
        grava(TROCA, json.dumps(t, ensure_ascii=False))
        log("teste: fecharia a janela (processo %s) pra reabrir: %s" % (pid, estado))
        return 0
    if not e_claude(pid):
        apaga(RETOMAR)
        log("o processo %s não é mais o Claude Code; nada fechado" % pid)
        return 0
    t["estado"], t["t"] = estado, time.time()   # só agora: a janela reaberta lê isto no SessionStart
    grava(TROCA, json.dumps(t, ensure_ascii=False))
    log("fechando a janela (processo %s) pra reabrir: %s" % (pid, estado))
    encerra(pid)
    return 0


def cmd_reverter(erro):
    """O modelo novo falhou na 1ª resposta: volta às opções de antes e reabre, uma vez só."""
    t = ler_json(TROCA)
    if t.get("estado") != "voltou":
        return 0
    grava_opcoes(t.get("de"))
    grava(RETOMAR, "--resume %s MESTREOS_TROCA_FALHOU_%s" % (t.get("sid"), t.get("chat") or "0"), ascii_=True)
    t["erro"] = re.sub(r"[^a-z_ ]", "", str(erro or "").lower())[:40] or "erro do Claude"
    grava(TROCA, json.dumps(t, ensure_ascii=False))
    log("o modelo novo falhou (%s); voltando pra %s" % (t["erro"], descreve(t.get("de"))))
    return cmd_derrubar(t.get("pid"), 0, "revertendo")


def cmd_desistir(erro):
    """Nem o modelo de antes respondeu (limite do plano, internet): para de reabrir e avisa pelo robô, se houver."""
    t = ler_json(TROCA)
    if t.get("estado") != "voltou-antes":
        return 0
    t["estado"] = "falhou"
    grava(TROCA, json.dumps(t, ensure_ascii=False))
    log("a janela não respondeu depois de voltar ao modelo de antes (%s); parei de reabrir" % str(erro)[:40])
    avisa_dono("⚠️ A janela do bot não conseguiu responder depois da troca de modelo. No computador, feche a janela do "
               "bot e abra de novo com meubot.")
    return 0


def cmd_status():
    print("opções da janela: %s" % descreve(ler_opcoes()))
    t = ler_json(TROCA)
    if t:
        print("última troca: %s → %s (%s)" % (descreve(t.get("de")), descreve(t.get("para")), t.get("estado")))
    try:
        with open(LOG, encoding="utf-8", errors="replace") as f:
            print("\n".join(f.read().splitlines()[-6:]))
    except OSError:
        pass
    return 0


def main():
    if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):   # desacoplado (pythonw) não tem console
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    opcao = lambda nome: a[a.index(nome) + 1] if nome in a and a.index(nome) + 1 < len(a) else ""
    if a[:1] == ["trocar"]:
        return cmd_trocar(opcao("--pedido"), opcao("--modelo"), opcao("--esforco"))
    if a[:1] == ["confirmar"]:
        return cmd_confirmar(opcao("--pedido"))
    if a[:1] == ["entender"]:
        mud, clara = ler_frase(" ".join(a[1:]))
        if mud.get("modelo") == MODELO_PADRAO:
            print("RECUSADO: modelo só por nome")
            return 0
        print(("CLARA: " if clara else "CONFIRMAR: " if mud else "NADA") + (descreve(aplica(ler_opcoes(), mud)) if mud else ""))
        return 0
    if a[:1] == ["atalho"]:
        return cmd_atalho("--inicio" in a)
    if a[:1] == ["status"]:
        return cmd_status()
    if a[:1] == ["derrubar"] and len(a) >= 3:
        return cmd_derrubar(a[1], a[2])
    if a[:1] == ["reverter"]:
        return cmd_reverter(a[1] if len(a) > 1 else "")
    if a[:1] == ["desistir"]:
        return cmd_desistir(a[1] if len(a) > 1 else "")
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
