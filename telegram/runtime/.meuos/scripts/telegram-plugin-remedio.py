#!/usr/bin/env python3
"""telegram-plugin-remedio.py — remédios pra defeitos do plugin oficial de Telegram do Claude Code (MestreOS, PASSO 7A).

1. "undefined" (visto 09/09/2026): depois de uma compactação automática, a sessão chama a ferramenta `reply` com o campo
   `message` em vez de `text`; o plugin manda "undefined" pro celular. O remédio aceita `message`/`texto` como sinônimo.
2. Emoji partido (provado 23/09/2026): resposta acima de 4096 é cortada por posição; se o corte cai no meio de um emoji,
   o Telegram recusa aquele pedaço inteiro (400 "strings must be encoded in UTF-8") e a resposta chega pela metade.
   O remédio recua o corte 1 posição quando ele partiria o emoji.
3. Texto formatado (visto 06/10/2026): texto longo com lista/título chega como `rich_message`, sem `text`; nenhum handler
   do plugin casava e a mensagem sumia calada. O remédio achata em texto simples; tipo que ninguém lê vira nota honesta.
4. Conversa (relatório de aluna, 20/10/2026): o plugin não contava ao agente a mensagem que o aluno arrastou pra
   responder, ignorava localização e reação com emoji, e só reagia na chegada se o agente lembrasse. O remédio faz igual
   à janela da Dupla (7D): o texto entregue começa dizendo qual mensagem ele arrastou; localização vira endereço com
   link (a ao vivo grava a posição mais nova); reação do dono ganha 👀; a chegada ganha ✍ (áudio) ou 👀, o agente troca
   pela pertinente com `react` e, se responder sem trocar, vira 👌. Localização e reação só valem do dono, com a mesma
   régua do gate() do plugin (privado, canal ligado, lista de acesso), conferida ANTES de gravar ou consultar o mapa.
5. Digitando (mesmo relatório): o plugin avisa "digitando" uma vez só e o Telegram apaga em ~5 s; tarefa longa ficava
   no escuro. O remédio repete o aviso a cada 4 s até o FIM DO TURNO, que os ganchos da janela do bot marcam (Stop e
   StopFailure); turno que some sem fim marcado apaga depois de 20 min sem sinal de vida.
6. Assinatura (mesmo relatório): cada resposta leva no fim o modelo e o esforço da conversa, gravados pelo gancho de
   início de turno. Texto que começa com [[limpo]] (pra mandar a outra pessoa) sai sem a marca e sem assinatura.

Cada remédio só entra se TODOS os trechos EXATOS dele forem reconhecidos (tudo ou nada: remédio pela metade quebraria
o plugin); trecho desconhecido não é tocado (✗, exige auditoria). Idempotente, com backup e reversão. Mac e Windows.
Uso: python3 telegram-plugin-remedio.py [--check | --revert]
"""
import os, sys, glob, shutil
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="replace")

H = os.path.expanduser("~")
BASE = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(H, ".claude")
# 3º remédio (09/10/2026): entra DEPOIS de todos os handlers do plugin (âncora = a declaração logo abaixo do último),
# então só recebe a mensagem que nenhum handler leu. Texto entra pelo handleInbound normal: allowlist e pareamento valem.
RICH_BLOCO = r'''// MESTREOS-REMEDIO-RICH: o Telegram manda texto longo formatado (listas, títulos) como `rich_message`, sem `text`;
// nenhum handler acima casava e a mensagem sumia calada. Aqui ela vira texto simples, e tipo que ninguém lê vira nota.
function mestreosRichTexto(rm: any): string {
  const linhas: string[] = []
  const anda = (b: any, pre = ''): void => {
    if (b == null) return
    if (Array.isArray(b)) { for (const x of b) anda(x, pre); return }
    if (typeof b !== 'object') return
    if (Array.isArray(b.items)) {
      for (const it of b.items) {
        const rot = it?.label != null ? String(it.label) + ' ' : '• '
        const antes = linhas.length
        anda(it?.blocks ?? it, pre + '   ')
        if (linhas.length > antes) linhas[antes] = pre + rot + linhas[antes].trimStart()
      }
      return
    }
    if (typeof b.text === 'string' && b.text.trim()) linhas.push(pre + b.text)
    else if (Array.isArray(b.text)) linhas.push(pre + b.text.map((t: any) => typeof t === 'string' ? t : t?.text ?? '').join(''))
    for (const k of ['blocks', 'children', 'content']) if (b[k]) anda(b[k], pre)
  }
  anda(rm?.blocks ?? rm)
  return linhas.join('\n\n').trim()
}

const MESTREOS_TIPOS_LIDOS = ['text', 'caption', 'photo', 'document', 'voice', 'audio', 'video', 'video_note', 'sticker']
const MESTREOS_META = ['message_id', 'from', 'chat', 'date', 'reply_to_message', 'forward_origin', 'is_topic_message',
  'message_thread_id', 'link_preview_options', 'entities', 'edit_date', 'sender_chat', 'via_bot', 'has_protected_content']
bot.on('message', async ctx => { // MESTREOS-REMEDIO-RICH: só chega aqui o que nenhum handler acima leu
  const m: any = ctx.message
  if (!m || MESTREOS_TIPOS_LIDOS.some(k => m[k] != null)) return
  const texto = m.rich_message ? mestreosRichTexto(m.rich_message) : ''
  if (texto) { await handleInbound(ctx, texto, undefined); return }
  const tipo = Object.keys(m).filter(k => !MESTREOS_META.includes(k)).slice(0, 4).join(', ') || 'vazia'
  process.stderr.write(`telegram channel: mensagem de tipo desconhecido (${tipo}) virou nota\n`)
  await handleInbound(ctx, `[nota do MestreOS: chegou uma mensagem de um tipo que este Telegram não sabe ler (${tipo}). Diga isso com honestidade, não invente o conteúdo, e peça pro dono mandar de outro jeito.]`, undefined)
})

'''

# 4º a 6º remédios (20/10/2026). As declarações moram logo depois de `const bot = new Bot(TOKEN)`, ANTES do
# `await mcp.connect(...)` do plugin: uma ferramenta chamada durante essa espera não pode achar Map/const ainda sem valor.
CONVERSA_BLOCO = r'''// MESTREOS-REMEDIO-CONVERSA: o que o dono FAZ com a mensagem também é conversa, igual na janela da Dupla (7D).
// Arrastou uma mensagem do agente pra responder: o texto entregue começa dizendo qual era. Mandou localização: vira
// endereço com link do mapa (a ao vivo grava a posição mais nova em ultima-localizacao.json). Reagiu com emoji numa
// mensagem do agente: ela ganha 👀 (= "vi"), sem acordar o agente. E toda mensagem dele ganha na chegada ✍ (áudio) ou 👀
// (resto); o agente troca pela pertinente com a ferramenta react, e se a resposta sair sem escolha vira 👌.
function mestreosDoDono(chat: any, from: any): boolean { // a régua do gate() pro privado, ANTES de qualquer efeito
  try {
    const a = loadAccess()
    return chat?.type === 'private' && a.dmPolicy !== 'disabled' && from?.id != null && a.allowFrom.includes(String(from.id))
  } catch { return false }
}
function mestreosArrastada(ctx: Context): string {
  const alvo: any = ctx.message?.reply_to_message
  if (!alvo?.from?.is_bot) return ''
  const rich = alvo.rich_message && typeof mestreosRichTexto === 'function' ? mestreosRichTexto(alvo.rich_message) : ''
  const t = String(alvo.text ?? alvo.caption ?? rich ?? '').replace(/\s+/g, ' ').replace(/»/g, '"').trim()
  return `[o dono respondeu arrastando esta sua mensagem: «${t.slice(0, 300) || 'mensagem sem texto'}»]\n`
}
const MESTREOS_LOCAL_ARQ = join(STATE_DIR, 'ultima-localizacao.json')
function mestreosLocalSalva(l: any, ao_vivo: boolean): void {
  try {
    const tmp = `${MESTREOS_LOCAL_ARQ}.tmp`
    writeFileSync(tmp, JSON.stringify({ lat: l.latitude, lon: l.longitude, precisao_m: l.horizontal_accuracy ?? null,
      ao_vivo, quando: new Date().toISOString() }), { mode: 0o600 })
    renameSync(tmp, MESTREOS_LOCAL_ARQ)
  } catch (err) { process.stderr.write(`telegram channel: não gravei a localização: ${err}\n`) }
}
async function mestreosEndereco(lat: number, lon: number): Promise<string> {
  try { // OpenStreetMap, sem chave, 4 s de teto (o mesmo da janela da Dupla); falhou = só coordenadas
    const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom=18&accept-language=pt-BR&lat=${lat}&lon=${lon}`
    const r = await fetch(url, { headers: { 'User-Agent': 'mestreos-telegram/1.0' }, signal: AbortSignal.timeout(4000) })
    if (!r.ok) return ''
    const d: any = await r.json()
    return String(d?.display_name ?? '').replace(/\s+/g, ' ').trim().slice(0, 200)
  } catch { return '' }
}
async function mestreosLocal(m: any): Promise<string> {
  const v = m.venue, l = v?.location ?? m.location
  const lat = Number(l?.latitude), lon = Number(l?.longitude)
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return ''
  const ao_vivo = Number(l.live_period) > 0
  mestreosLocalSalva(l, ao_vivo)
  const nome = v ? [v.title, v.address].filter(Boolean).map(x => String(x).replace(/\s+/g, ' ').replace(/[[\]«»]/g, '').trim())
    .join(' · ').slice(0, 200) : ''
  const end = nome || await mestreosEndereco(lat, lon)
  const prec = Number(l.horizontal_accuracy) > 0 ? ` (precisão ~${Math.round(l.horizontal_accuracy)} m)` : ''
  const vivo = ao_vivo ? ` Localização AO VIVO por ${Math.round(l.live_period / 60)} min: a posição mais nova fica em ${MESTREOS_LOCAL_ARQ}.` : ''
  return `[localização enviada pelo dono: ${end || 'endereço não encontrado'} · ${lat.toFixed(6)}, ${lon.toFixed(6)}${prec} · https://maps.google.com/?q=${lat},${lon}.${vivo}]`
}
const mestreosPendentes = new Map<string, Set<number>>() // mensagens com ✍/👀 de chegada que o agente ainda não trocou
function mestreosPendente(chat_id: string, mid: number): void {
  const s = mestreosPendentes.get(chat_id) ?? new Set<number>()
  s.add(mid); mestreosPendentes.set(chat_id, s)
}
function mestreosEscolheu(chat_id: string, mid: number): void { mestreosPendentes.get(chat_id)?.delete(mid) }
function mestreosFinaliza(chat_id: string): void {
  const s = mestreosPendentes.get(chat_id)
  if (!s) return
  for (const mid of s) void bot.api.setMessageReaction(chat_id, mid, [{ type: 'emoji', emoji: '👌' as ReactionTypeEmoji['emoji'] }]).catch(() => {})
  mestreosPendentes.delete(chat_id)
}
'''

CONVERSA_HANDLERS = r'''bot.on('message', async (ctx, next) => { // MESTREOS-REMEDIO-CONVERSA: localização (ponto, lugar ou ao vivo), antes do genérico
  const m: any = ctx.message
  if (!m || !(m.location || m.venue) || !mestreosDoDono(m.chat, m.from)) return next()
  const texto = await mestreosLocal(m)
  if (!texto) return next()
  await handleInbound(ctx, m.caption ? `${texto}\n${m.caption}` : texto, undefined)
})

bot.on('edited_message', async (ctx, next) => { // MESTREOS-REMEDIO-CONVERSA: localização ao vivo andando = só regrava
  const m: any = ctx.editedMessage
  if (!m?.location || !mestreosDoDono(m.chat, m.from)) return next()
  mestreosLocalSalva(m.location, true)
})

bot.on('message_reaction', async ctx => { // MESTREOS-REMEDIO-CONVERSA: o dono reagiu numa mensagem do agente → 👀 (= "vi")
  const r = ctx.messageReaction
  const user = r?.user
  if (!r || !user || !mestreosDoDono(r.chat, user)) return
  const antes = new Set(r.old_reaction.filter(x => x.type === 'emoji').map(x => (x as any).emoji as string))
  if (!r.new_reaction.some(x => x.type === 'emoji' && !antes.has((x as any).emoji))) return
  void bot.api.setMessageReaction(String(r.chat.id), r.message_id, [{ type: 'emoji', emoji: '👀' as ReactionTypeEmoji['emoji'] }]).catch(() => {})
})

'''

DIGITANDO_BLOCO = r'''// MESTREOS-REMEDIO-DIGITANDO: o Telegram apaga o "digitando" uns 5 s depois de cada aviso, e o plugin avisava 1 vez só:
// tarefa longa ficava no escuro. Aqui o aviso vira batimento de 4 s até o FIM DO TURNO, que os ganchos da janela do bot
// marcam (telegram-bot-turno.py grava turn-start, turn-end e tool-activity nesta pasta). Uma resposta no meio NÃO encerra:
// o agente manda um "tô nisso" e segue trabalhando. Sem os ganchos, vale a 1ª resposta ou um teto de tempo. Turno que
// some sem fim marcado (Esc na janela) apaga depois de 20 min sem sinal de vida; erro de API marca o fim (StopFailure).
const MESTREOS_BATIDA_MS = Number(process.env.MESTREOS_TELEGRAM_BATIDA_MS ?? 4_000) // a variável só existe no teste
const MESTREOS_SEM_GANCHO_MS = 10 * 60_000
const MESTREOS_RABO_MS = 3 * 60_000
const MESTREOS_MUDO_MS = Number(process.env.MESTREOS_TELEGRAM_MUDO_MS ?? 20 * 60_000) // idem
const MESTREOS_TETO_MS = 3 * 60 * 60_000
const mestreosBatidas = new Map<string, ReturnType<typeof setInterval>>()
function mestreosParaDigitando(chat_id: string): void {
  const t = mestreosBatidas.get(chat_id)
  if (t !== undefined) { clearInterval(t); mestreosBatidas.delete(chat_id) }
}
function mestreosMarca(nome: string): number { // instante gravado pelo gancho (ms), ou a data do arquivo; 0 = não existe
  try {
    const f = join(STATE_DIR, nome)
    const raw = readFileSync(f, 'utf8').replace(/[^0-9]/g, '')
    return raw.length >= 12 ? Number(raw) : statSync(f).mtimeMs
  } catch { return 0 }
}
function mestreosComGanchos(): boolean { return mestreosMarca('turn-start') > 0 }
function mestreosDigitando(chat_id: string, semGanchoMs: number = MESTREOS_SEM_GANCHO_MS): void {
  mestreosParaDigitando(chat_id)
  const inicio = Date.now()
  let falhas = 0
  const bate = (): void => {
    void bot.api.sendChatAction(chat_id, 'typing').then(() => { falhas = 0 }, () => { if (++falhas >= 5) mestreosParaDigitando(chat_id) })
  }
  bate()
  const timer = setInterval(() => {
    const agora = Date.now(), ini = mestreosMarca('turn-start'), fim = mestreosMarca('turn-end')
    if (fim > inicio && fim >= ini) { mestreosParaDigitando(chat_id); return } // o turno acabou e nenhum outro abriu
    const turnoAberto = ini > 0 && ini >= fim
    const pulso = Math.max(inicio, ini, mestreosMarca('tool-activity'))
    const ferramenta = agora - mestreosMarca('tool-activity') < 5 * 60_000
    const venceu = turnoAberto ? agora - pulso > MESTREOS_MUDO_MS || agora - inicio > MESTREOS_TETO_MS
      : (agora - inicio > semGanchoMs && !ferramenta) || agora - inicio > MESTREOS_TETO_MS
    if (venceu) { mestreosParaDigitando(chat_id); return }
    bate()
  }, MESTREOS_BATIDA_MS)
  timer.unref?.()
  mestreosBatidas.set(chat_id, timer)
}
'''

ASSINATURA_BLOCO = r'''// MESTREOS-REMEDIO-ASSINATURA: a resposta leva no fim o modelo e o esforço ("🟣 Claude · Opus 5.5 · alto"), lidos do
// arquivo que o gancho de início de turno grava (telegram-bot-turno.py). Zero token: o modelo não escreve nada.
// Texto pra mandar a outra pessoa começa com [[limpo]]: a marca sai e a assinatura não entra. No format markdownv2 o
// ponto e o hífen são reservados: a assinatura entra escapada, senão o Telegram recusa a resposta inteira (400).
function mestreosAssina(text: string, parseMode?: string): string {
  const t = String(text ?? '')
  if (/^\s*\[\[limpo\]\]/.test(t)) return t.replace(/^\s*\[\[limpo\]\]\s*/, '')
  if (!t.trim()) return t
  try {
    let s = readFileSync(join(STATE_DIR, 'assinatura'), 'utf8').trim().slice(0, 60)
    if (parseMode === 'MarkdownV2') s = s.replace(/[_*[\]()~`>#+\-=|{}.!\\]/g, '\\$&')
    return s ? `${t}\n\n${s}` : t
  } catch { return t }
}
'''

BOT = "const bot = new Bot(TOKEN)\n"
# Remédio = (nome, marca, [(trecho original, trecho remediado), ...], sinal de conserto EQUIVALENTE já presente, ex.: patch
# do dono). Todos os trechos de um remédio entram juntos ou nenhum entra.
REMEDIOS = [
    ("undefined", "// MESTREOS-REMEDIO-UNDEFINED",
     [("        const text = args.text as string\n",
       "        const text = (args.text ?? (args as Record<string, unknown>).message ?? (args as Record<string, unknown>).texto) as string // MESTREOS-REMEDIO-UNDEFINED\n")],
     "(args as Record<string, unknown>).message"),
    ("emoji partido", "// MESTREOS-REMEDIO-EMOJI",
     [("    out.push(rest.slice(0, cut))\n",
       "    if (cut > 1 && rest.charCodeAt(cut - 1) >= 0xd800 && rest.charCodeAt(cut - 1) <= 0xdbff) cut-- // MESTREOS-REMEDIO-EMOJI\n"
       "    out.push(rest.slice(0, cut))\n")],
     "rest.charCodeAt(cut - 1) >= 0xd800"),
    ("texto formatado", "// MESTREOS-REMEDIO-RICH",
     [("type AttachmentMeta = {\n", RICH_BLOCO + "type AttachmentMeta = {\n")],
     "rich_message"),
    ("conversa (arrastar, reagir, localização)", "// MESTREOS-REMEDIO-CONVERSA",
     [(BOT, BOT + CONVERSA_BLOCO),
      ("bot.on('message:text', async ctx => {\n", CONVERSA_HANDLERS + "bot.on('message:text', async ctx => {\n"),
      ("      content: text,\n      meta: {\n",
       "      content: mestreosArrastada(ctx) + text, // MESTREOS-REMEDIO-CONVERSA: a mensagem que ele arrastou pra responder\n"
       "      meta: {\n"),
      ("  if (access.ackReaction && msgId != null) {\n"
       "    void bot.api\n"
       "      .setMessageReaction(chat_id, msgId, [\n"
       "        { type: 'emoji', emoji: access.ackReaction as ReactionTypeEmoji['emoji'] },\n",
       "  const mestreosRecebi = access.ackReaction === '' ? '' : (attachment?.kind === 'voice' || attachment?.kind === 'audio') ? '✍' : (access.ackReaction ?? '👀') // MESTREOS-REMEDIO-CONVERSA: ✍ áudio, 👀 resto ('' no access.json desliga)\n"
       "  if (mestreosRecebi && msgId != null) {\n"
       "    mestreosPendente(chat_id, msgId)\n"
       "    void bot.api\n"
       "      .setMessageReaction(chat_id, msgId, [\n"
       "        { type: 'emoji', emoji: mestreosRecebi as ReactionTypeEmoji['emoji'] },\n"),
      ("      case 'react': {\n        assertAllowedChat(args.chat_id as string)\n",
       "      case 'react': {\n        assertAllowedChat(args.chat_id as string)\n"
       "        mestreosEscolheu(args.chat_id as string, Number(args.message_id)) // MESTREOS-REMEDIO-CONVERSA: a escolha do agente vale\n"),
      ("        const result =\n          sentIds.length === 1\n",
       "        mestreosFinaliza(chat_id) // MESTREOS-REMEDIO-CONVERSA: respondeu sem trocar a reação de chegada = 👌\n"
       "        const result =\n          sentIds.length === 1\n"),
      ("      await bot.start({\n        onStart: info => {\n",
       "      await bot.start({\n"
       "        allowed_updates: ['message', 'edited_message', 'callback_query', 'message_reaction'], // MESTREOS-REMEDIO-CONVERSA: reação e localização ao vivo só chegam se pedir\n"
       "        onStart: info => {\n")],
     "message_reaction"),
    ("digitando contínuo", "// MESTREOS-REMEDIO-DIGITANDO",
     [(BOT, BOT + DIGITANDO_BLOCO),
      ("  // Typing indicator — signals \"processing\" until we reply (or ~5s elapses).\n"
       "  void bot.api.sendChatAction(chat_id, 'typing').catch(() => {})\n",
       "  // Typing indicator — batimento até o fim do turno (MESTREOS-REMEDIO-DIGITANDO).\n"
       "  mestreosDigitando(chat_id)\n"),
      ("        const result =\n          sentIds.length === 1\n",
       "        if (mestreosComGanchos()) mestreosDigitando(chat_id, MESTREOS_RABO_MS) // MESTREOS-REMEDIO-DIGITANDO: o turno costuma continuar\n"
       "        else mestreosParaDigitando(chat_id)\n"
       "        const result =\n          sentIds.length === 1\n"),
      ("      case 'edit_message': {\n        assertAllowedChat(args.chat_id as string)\n",
       "      case 'edit_message': {\n        assertAllowedChat(args.chat_id as string)\n"
       "        if (mestreosComGanchos()) mestreosDigitando(args.chat_id as string, MESTREOS_RABO_MS) // MESTREOS-REMEDIO-DIGITANDO: progresso = turno vivo\n"),
      ("    pendingPermissions.set(request_id, { tool_name, description, input_preview })\n",
       "    pendingPermissions.set(request_id, { tool_name, description, input_preview })\n"
       "    for (const c of [...mestreosBatidas.keys()]) mestreosParaDigitando(c) // MESTREOS-REMEDIO-DIGITANDO: esperando o dono aprovar\n"),
      ("  pendingPermissions.delete(request_id)\n",
       "  pendingPermissions.delete(request_id)\n"
       "  { const pchat = ctx.callbackQuery.message?.chat?.id; if (pchat != null) mestreosDigitando(String(pchat)) } // MESTREOS-REMEDIO-DIGITANDO: respondeu pelo botão, o turno voltou\n"),
      ("    if (msgId != null) {\n      const emoji = permMatch[1]!.toLowerCase().startsWith('y') ? '✅' : '❌'\n",
       "    mestreosDigitando(chat_id) // MESTREOS-REMEDIO-DIGITANDO: respondeu a permissão em texto\n"
       "    if (msgId != null) {\n      const emoji = permMatch[1]!.toLowerCase().startsWith('y') ? '✅' : '❌'\n")],
     "function startTyping("),
    ("assinatura", "// MESTREOS-REMEDIO-ASSINATURA",
     [(BOT, BOT + ASSINATURA_BLOCO),
      ("        const chunks = chunk(text, limit, mode)\n",
       "        const chunks = chunk(mestreosAssina(text, parseMode), limit, mode) // MESTREOS-REMEDIO-ASSINATURA\n")],
     "join(STATE_DIR, 'assinatura')"),
]

def alvos():
    return sorted(glob.glob(os.path.join(BASE, "plugins", "cache", "claude-plugins-official", "telegram", "*", "server.ts")))

def ler(f):
    """Lê SEM traduzir fim de linha: arquivo CRLF (Windows) continua CRLF; só as linhas remediadas mudam. O fim de linha
    é o da maioria: uma linha CRLF solta num arquivo LF (editor do Windows) não pode virar o arquivo inteiro (prova no
    Windows, 20/10/2026: a reversão não achava os trechos e o remédio ficava preso)."""
    s = open(f, encoding="utf-8", newline="").read()
    crlf = s.count("\r\n")
    return s, ("\r\n" if crlf > s.count("\n") - crlf else "\n")

def gravar(f, s):
    open(f, "w", encoding="utf-8", newline="").write(s)

def trechos(nl):
    return [(nome, mark, [(old.replace("\n", nl), new.replace("\n", nl)) for old, new in edits], equiv)
            for nome, mark, edits, equiv in REMEDIOS]

def aplica(s, edits):
    """Todos os trechos ou nenhum: devolve o texto novo, ou None se algum trecho não estiver lá exatamente 1 vez."""
    for old, new in edits:
        if s.count(old) != 1: return None
        s = s.replace(old, new)
    return s

def desfaz(s, edits):
    """O inverso do aplica, também tudo ou nada: None se algum trecho remediado não estiver lá exatamente 1 vez."""
    for old, new in reversed(edits):
        if s.count(new) != 1: return None
        s = s.replace(new, old)
    return s

def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "apply"
    files = alvos()
    if not files: print("plugin de Telegram não encontrado em", BASE); return 2
    rc = 0
    for f in files:
        ver = os.path.basename(os.path.dirname(f)); s, nl = ler(f); bak = f + ".pre-remedio"; R = trechos(nl)
        if modo == "--check":
            for nome, mark, edits, equiv in R:
                tem = mark in s or equiv in s
                print(("✓" if tem else "✗"), ver, nome, ("com remédio" if mark in s else "com conserto equivalente" if tem else "SEM remédio")); rc |= (0 if tem else 1)
            continue
        if modo == "--revert":
            achou = []
            for nome, mark, edits, equiv in reversed(R):  # ao contrário: remédio posterior pode estar encostado no anterior
                if mark not in s: continue
                volta = desfaz(s, edits)
                if volta is None:  # tudo ou nada também na volta: trecho meio editado fica como está, e avisa
                    print("✗", ver, nome, "não reverti: algum trecho do remédio foi mudado à mão; restaure o server.ts.pre-remedio"); rc = 1; continue
                s = volta; achou.append(nome)
            if achou: gravar(f, s); print("↩", ver, "revertido:", ", ".join(reversed(achou)), "(outras mudanças preservadas)")
            elif rc == 0: print("·", ver, "sem remédio aplicado, nada a reverter")
            continue
        mudou = False
        for nome, mark, edits, equiv in R:
            if mark in s: print("✓", ver, nome, "já com remédio"); continue
            if equiv in s: print("✓", ver, nome, "já tem conserto equivalente; não empilho outro"); continue
            novo = aplica(s, edits)
            if novo is None: print("✗", ver, nome, "trecho esperado não encontrado (plugin mudou?); nada feito nesse remédio"); rc = 1; continue
            s = novo; mudou = True; print("✓", ver, nome, "remédio aplicado")
        if mudou:
            if not os.path.exists(bak): shutil.copy(f, bak)
            gravar(f, s); print("  backup em server.ts.pre-remedio. Carregue na próxima sessão ociosa do bot; não interrompa trabalho ativo.")
    return rc

if __name__ == "__main__": sys.exit(main())
