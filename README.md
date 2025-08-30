# Coordenação Escolar – v5 (Render Blueprint + PostgreSQL + Auto-Seed)

**Zero configuração** no Render: este `render.yaml` cria **Web Service** + **PostgreSQL** e já conecta `DATABASE_URL` automaticamente.

## Como publicar (GitHub → Render Blueprint)
1. Suba estes arquivos em um repositório GitHub (raiz do repo).
2. No Render, clique em **New → Blueprint** e selecione o repositório.
3. Confirme o `render.yaml` e clique em **Apply**.
4. Aguarde o build. O app sobe com **AUTO_SEED=1**, criando usuários, componentes e ~40 planos aleatórios.

## Acessos demo
- **CGPG**: `cgpg` / `master123`
- **CGPAC**: `cgpac1` / `area123`, `cgpac2` / `area123`
- **Docentes**: `docente01` .. `docente08` / `doc123`

## Observação
- Botão **Administração → Recriar dados de demonstração** (CGPG) repovoa a base.
- Para uso real, altere as senhas em **Administração → Usuários** ou desative o `AUTO_SEED` no `render.yaml`.
