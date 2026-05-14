# SPD Party Bot

[English](README.md)

**SPD Party Bot** é um bot gratuito e open source para Discord, feito para organizar parties, squads e eventos rápidos em comunidades gamer.

Ele oferece um Hub de Parties onde membros podem criar convites, entrar por botões, gerenciar vagas e fila, receber lembretes e, opcionalmente, usar calls privadas temporárias para cada party.

> [!TIP]
> Comandos de staff/configuração exigem **Gerenciar servidor** ou o cargo Staff configurado.

> [!IMPORTANT]
> O SPD Party **não** precisa de permissão de Administrador.

![Discord Bots](https://top.gg/api/widget/1502116547009970347.svg)

[TOP.GG](https://top.gg//bot/1502116547009970347)

## ✨ Funções

- Hub de Parties com botões interativos
- Criação de party por formulário/modal
- Título, vagas, horário, descrição e imagem por link
- Respostas rápidas: **Vou**, **Talvez** e **Não vou**
- Clicar na mesma resposta de novo remove você daquela lista
- Sistema de fila quando a party está cheia
- Promoção automática da fila quando alguém sai de **Vou**
- Painel privado de gerenciamento para host e staff
- Editar e encerrar parties
- Lembretes automáticos antes do horário marcado
- Encerramento automático depois que a party termina
- Suporte a timestamps do Discord em horários reconhecidos
- Configuração separada por servidor
- Idioma por servidor: `pt-BR` e `en-US`
- Fuso horário por servidor
- Status dinâmico do bot
- Temas de embed e cores personalizadas
- Imagem padrão de party por servidor
- Banners salvos por servidor
- Ping opcional de `@everyone` ao criar party
- Cargo Host opcional
- Cargo Staff opcional
- Restrição opcional de canal para `/party hub`
- Calls privadas temporárias para parties
- Cargo temporário para acesso à call
- Limpeza automática da call e do cargo

## 🎮 Como funciona

A staff cria um Hub com:

```txt
/party hub
```

Os membros usam o botão **Criar Party**. O bot abre um formulário com:

- Título da party
- Número de vagas
- Horário
- Descrição
- Link da imagem

Depois de enviar, o convite aparece no canal configurado.

Os membros podem clicar em:

```txt
✅ Vou
❔ Talvez
❌ Não vou
```

Clicar no mesmo botão novamente remove o membro daquela lista. Se alguém confirmado sair de **Vou**, o próximo membro da fila é puxado automaticamente.

## 🔊 Calls temporárias de party

O SPD Party pode criar uma call privada temporária para cada party.

Quando a party começa, ou quando host/staff usa **Gerenciar → Criar call**, o bot pode:

- Criar um cargo temporário para a party
- Criar uma call privada
- Dar acesso somente ao host e aos membros marcados como **Vou**
- Usar o formato de canal: `Jogando┇🎮 Nome da Party`
- Criar o canal dentro da categoria configurada/padrão
- Remover o acesso quando alguém sai de **Vou**
- Dar acesso ao próximo membro puxado da fila
- Apagar a call e o cargo quando a party termina
- Esperar todo mundo sair da call antes de apagar

Permissões necessárias para essa função opcional:

- Gerenciar canais
- Gerenciar cargos

> [!IMPORTANT]
> O cargo do bot precisa estar acima dos cargos temporários que ele cria, senão o Discord bloqueia adicionar/remover cargos.

## 🎨 Personalização visual

A staff pode personalizar o bot em `/party config`.

Opções visuais disponíveis:

- Cor do embed
- Temas rápidos de embed
- Idioma do servidor
- Fuso horário do servidor
- Imagem padrão de party
- Banners salvos
- Escolher banner salvo
- Limpar banners salvos

Temas rápidos atuais:

- SPD Neon
- Lime Green
- Ocean Blue
- Crimson Red
- Golden
- Cyber Pink
- Dark Steel
- Ice Cyan

## 🌎 Idiomas

O SPD Party atualmente suporta:

- `pt-BR` — Português do Brasil
- `en-US` — English

O idioma pode ser alterado por servidor em `/party config`.

## 🧩 Comandos

### `/party hub`

Cria o Hub de Parties no canal atual.

Pode ser usado por staff, usuários com **Gerenciar servidor**, ou pelo cargo Host configurado no canal permitido.

### `/party config`

Abre o painel de configuração do servidor.

Permite configurar:

- Canal de convites
- Canal de logs
- Canal de comandos
- Cargo Host
- Cargo Staff
- Idioma
- Fuso horário
- Cor do embed
- Tema do embed
- Imagem padrão de party
- Banners salvos
- Ping `@everyone`
- Se todos podem criar parties
- Lembretes automáticos
- Encerramento automático

### `/party lista`

Lista as parties abertas no servidor atual.

### `/party limpar`

Remove parties encerradas do banco local do servidor atual.

> [!TIP]
> `/party config`, `/party hub` e `/party limpar` são comandos de staff/setup.

## ⚙️ Configuração inicial

Depois de adicionar o bot ao servidor, use:

```txt
/party config
```

Configure:

1. Canal de convites
2. Canal de logs
3. Canal de comandos, opcional
4. Cargo Host, opcional
5. Cargo Staff, opcional
6. Idioma
7. Fuso horário
8. Visual, opcional

Depois vá até o canal onde deseja deixar o Hub e use:

```txt
/party hub
```

## 🔐 Permissões recomendadas

O SPD Party não precisa de Administrador.

Permissões recomendadas:

- Ver canais
- Enviar mensagens
- Ver histórico de mensagens
- Inserir links
- Usar comandos de aplicativo
- Mencionar todos, opcional e configurável
- Gerenciar canais, necessário apenas para calls temporárias
- Gerenciar cargos, necessário apenas para cargos temporários das calls

> [!NOTE]
> `Mencionar todos` só é usado se estiver ativado na configuração do servidor.

## 🕒 Formatos de horário aceitos

Exemplos:

```txt
hoje 18:30
amanhã 19:00
08/05/2026 18:30
08/05/2026 18:30 - 20:30
08/05/2026 18:30 - 09/05/2026 01:00
```

Quando o horário é reconhecido, o bot mostra timestamps do Discord como:

- Começa em X horas
- Começou há X minutos
- Termina em X horas
- Terminou há X minutos
- Duração

## 🚀 Hospedagem no Railway

Configure a variável obrigatória:

```txt
DISCORD_TOKEN=SEU_TOKEN_DO_BOT
```

Opcional, mas recomendado para persistência:

```txt
DATA_DIR=/data
```

Se usar `DATA_DIR=/data`, crie um Volume no Railway montado em:

```txt
/data
```

Assim as configurações dos servidores e dados das parties continuam salvos entre deploys.

## 💻 Rodando localmente

Instale as dependências:

```bash
pip install -r requirements.txt
```

Rode com variáveis de ambiente.

### Windows CMD

```bat
set DISCORD_TOKEN=SEU_TOKEN_DO_BOT
set DATA_DIR=%cd%\data
python bot.py
```

### PowerShell

```powershell
$env:DISCORD_TOKEN="SEU_TOKEN_DO_BOT"
$env:DATA_DIR="$PWD\data"
python bot.py
```

O bot salva dados locais em:

```txt
data/config.json
data/parties.json
```

Não envie arquivos locais de dados para o GitHub.

## 📁 `.gitignore` sugerido

```gitignore
config.json
parties.json
.env
data/
__pycache__/
*.pyc
```

## 🧪 Notas para reviewers

O SPD Party é gratuito e open source.

O bot não exige permissão de Administrador. As funções principais ficam disponíveis sem pagamento. Comandos de setup/staff exigem **Gerenciar servidor** ou o cargo Staff configurado.

Funções opcionais de call temporária exigem **Gerenciar canais** e **Gerenciar cargos**. Se essas permissões não forem concedidas, as funções principais de party continuam funcionando.

Ponto de entrada recomendado:

```txt
/party hub
```

## 💜 Apoie o projeto

O SPD Party é gratuito e open source.

O apoio é totalmente opcional e ajuda a manter o bot online, atualizado e recebendo melhorias.

Apoiadores podem receber benefícios de comunidade, como:

- Nome listado no README
- Prioridade na análise de sugestões
- Prévia antecipada de funções planejadas, quando disponível
- Cargo/badge de apoiador no servidor de suporte, se disponível

As funções principais do bot não ficam bloqueadas por pagamento.

### Project Boosters

<!-- Adicione apoiadores de $30 aqui -->

### Community Supporters

<!-- Adicione apoiadores de $15 aqui -->

### Supporters

<!-- Adicione apoiadores de $5 aqui -->

## 🛣️ Ideias futuras

- Banco PostgreSQL
- Dashboard web
- Templates e presets de jogos
- Parties recorrentes
- Histórico de parties
- Ranking de participação
- Mais presets visuais
- Automação avançada de parties

## 📄 Licença

Este projeto está licenciado sob a licença MIT.
