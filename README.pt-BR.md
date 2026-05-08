# SPD Party Bot

[English](README.md)

SPD Party Bot é um bot para Discord criado para organizar parties, squads e eventos rápidos em servidores de comunidade.

Com ele, membros autorizados podem criar convites de party por formulário, definir vagas, horário, descrição e imagem. Os jogadores respondem com botões interativos como **Vou**, **Talvez** e **Não vou**. Quando a party lota, o bot coloca novos participantes em uma fila automática.

## ✨ Recursos

- Hub de parties com botões interativos.
- Criação de party por formulário/modal.
- Respostas rápidas:
  - ✅ Vou
  - ❔ Talvez
  - ❌ Não vou
- Sistema de vagas.
- Fila automática quando a party está cheia.
- Painel de gerenciamento privado para host/staff.
- Edição e encerramento de parties.
- Canal de convites configurável por servidor.
- Canal de logs configurável por servidor.
- Cargo Host configurável.
- Cargo Staff configurável.
- Opção para permitir que todos criem parties.
- Opção para marcar `@everyone` ao criar party.
- Suporte a imagem por link.
- Suporte a horários com timestamps do Discord.
- Mostra quanto falta para começar, quando começou, quando termina, quando terminou e a duração.
- Configuração de fuso horário por servidor.
- Suporte a múltiplos servidores.
- Idiomas:
  - Português do Brasil
  - English
- Salvamento em JSON.
- Suporte a `DATA_DIR` para usar volume persistente em hospedagens como Railway.

## 🎮 Como funciona

A staff cria um Hub com:

```txt
/party hub
```

Depois os membros usam o botão **Criar Party**.

O bot abre um formulário com:

- Título da party
- Número de vagas
- Horário
- Descrição
- Link de imagem

Depois disso, o convite aparece no canal configurado.

Exemplo de convite:

```txt
🎮 Lego Party - 4 Jogadores

Horário
Hoje 18:30 - 20:30
Começa em 2 horas
Duração: 2h

✅ Vou (1/4)
❔ Talvez (0/4)
❌ Não vou (0)

Status: Aberta
Organizador: @usuario
```

## 🧩 Comandos

### `/party hub`

Cria o Hub de Parties no canal atual.

Apenas staff ou usuários com permissão **Gerenciar servidor** podem usar.

### `/party config`

Abre o painel de configuração do servidor.

Permite configurar:

- Canal de convites
- Canal de logs
- Cargo Host
- Cargo Staff
- Idioma
- Fuso horário
- Cor do embed
- Ping `@everyone`
- Se todos podem criar parties

### `/party lista`

Lista as parties abertas no servidor atual.

### `/party limpar`

Remove do banco as parties encerradas do servidor atual.

## ⚙️ Configuração inicial

Depois de adicionar o bot ao servidor, use:

```txt
/party config
```

Configure:

1. Canal de convites
2. Canal de logs
3. Cargo Host
4. Cargo Staff
5. Idioma
6. Fuso horário

Depois vá até o canal onde deseja deixar o Hub e use:

```txt
/party hub
```

## 🔐 Permissões recomendadas

O bot precisa das permissões:

- Ver canais
- Enviar mensagens
- Ler histórico de mensagens
- Inserir links
- Usar comandos de aplicativo
- Mencionar `@everyone`, opcional

Para canais privados, adicione o cargo do bot nas permissões do canal.

## 🌎 Idiomas

O bot possui suporte para:

- `pt-BR` — Português do Brasil
- `en-US` — English

O idioma pode ser alterado por servidor no painel de configuração.

## 🕒 Horários suportados

O campo de horário aceita exemplos como:

```txt
hoje 18:30
amanhã 19:00
08/05/2026 18:30
08/05/2026 18:30 - 20:30
08/05/2026 18:30 - 09/05/2026 01:00
```

Quando o horário é reconhecido, o bot mostra timestamps automáticos do Discord, como:

- Começa em X horas
- Começou há X minutos
- Termina em X horas
- Terminou há X minutos
- Duração da party

## 🗂️ Arquivos principais

```txt
bot.py
config.example.json
parties.example.json
requirements.txt
README.md
README.pt-BR.md
LICENSE
```

## 📦 requirements.txt

```txt
discord.py>=2.4.0
```

## 🔧 config.example.json

Modelo recomendado:

```json
{
  "token": "",
  "guilds": {}
}
```

Copie para `config.json` apenas em ambiente local.

Não publique `config.json` com dados reais de servidores ou tokens.

## 🚀 Hospedagem no Railway

No Railway, configure a variável:

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

Assim o bot salva configurações e parties em um local persistente.

## ▶️ Start Command

```bash
python bot.py
```

## 🔒 Segurança

Nunca publique o token do bot no GitHub.

Use variável de ambiente:

```txt
DISCORD_TOKEN
```

Se o token vazar, gere outro imediatamente no Discord Developer Portal.

O repositório público não deve incluir:

```txt
config.json
parties.json
.env
data/
```

Use os arquivos de exemplo no lugar:

```txt
config.example.json
parties.example.json
```

## 📝 Logs

Quando configurado, o canal de logs registra ações como:

- Party criada
- Usuário marcou Vou
- Usuário marcou Talvez
- Usuário marcou Não vou
- Usuário entrou na fila
- Party editada
- Party encerrada
- Configurações alteradas

## 👥 Multi-servidor

O bot salva configurações separadas para cada servidor.

Cada servidor pode ter:

- Canal de convites próprio
- Canal de logs próprio
- Cargo Host próprio
- Cargo Staff próprio
- Idioma próprio
- Fuso horário próprio
- Cor de embed própria

## 💜 Apoiadores

Obrigado a todos que apoiam este projeto!

### Project Boosters



<!-- Adicione apoiadores de $30 aqui -->

### Community Supporters



<!-- Adicione apoiadores de $15 aqui -->

### Supporters



<!-- Adicione apoiadores de $5 aqui -->

## 📌 Status do projeto

Em desenvolvimento ativo.

## 💡 Ideias futuras

- Banco de dados PostgreSQL.
- Expiração automática de parties.
- Criação automática de canal de voz temporário.
- Templates/presets de jogos.
- Dashboard web.
- Histórico de parties.
- Ranking de participação.
- Notificações automáticas antes do horário marcado.

## 📄 Licença

Este projeto está licenciado sob a licença MIT.
