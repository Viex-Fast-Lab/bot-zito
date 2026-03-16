## Rotação imediata recomendada

1. Rotacionar `DISCORD_TOKEN`.
2. Rotacionar `GITHUB_TOKEN`.
3. Rotacionar `GEMINI_API_KEY`.
4. Rotacionar `NOTION_API_KEY`.
5. Rotacionar `FIREFLIES_API_KEY` se ela tiver sido exposta fora do ambiente seguro.
6. Conferir se algum token foi publicado em backup, VPS, prints ou mensagens.
7. Atualizar apenas o arquivo `.env` local da máquina e os segredos da VPS.

## Estado do projeto

- O repositório agora usa `.env.example` como referência segura.
- Bancos locais de memória (`*.db`, `*.sqlite3`) estão ignorados no Git.
