# Starforge × ERC-8004

**Monad Metropolis Hackathon** · Track: Trust, Identity & AI Infrastructure ($30K) · Deadline: 13 oct 2026

Agentes de IA con identidad on-chain **ERC-8004** que juegan **STARFORGE**
— arcade slot con RNG verificable y RTP publicado del 97.60% — de forma
autónoma. Cada partida liquidada se publica como **feedback de reputación
on-chain firmado por el propio contrato del juego**: un track record de
agente imposible de falsificar, con leaderboard por RTP real.

## Estado

Scaffold inicial (2026-09-18). Contratos escritos, sin desplegar.
Todo apunta a **Monad testnet**; $0 gastados, sin wallets reales.

## Estructura

```
contracts/
  StarforgeGame.sol        # matemática pura del juego (port 1:1 de Chain Jam)
  StarforgeArena.sol       # sesiones, escrow, payouts, hook de reputación
  AgentReputation.sol      # link wallet→agentId + feedback ERC-8004
  interfaces/IERC8004.sol  # subset Identity + Reputation Registry
  randomness/              # IRandomness + BlockhashRandomness (solo testnet)
agent/
  registration.json        # plantilla del archivo de registración ERC-8004
  play-agent.py            # bot demo (esqueleto; wiring web3.py en semana 2)
docs/
  ARCHITECTURE.md          # diseño completo + diagrama + flujos
  ERC8004_NOTES.md         # investigación ERC-8004 + preguntas abiertas
  MILESTONES.md            # plan semanal hasta el 13 oct
scripts/
  deploy-testnet.md        # pasos de deploy (manual, sin claves en repo)
```

## Quickstart (cuando llegue semana 2)

```bash
# 1. compilar
npx solc --bin --abi contracts/StarforgeGame.sol -o build/
# 2. desplegar en Monad testnet (ver scripts/deploy-testnet.md)
# 3. registrar agente + linkAgent + correr el bot
export AGENT_PRIVATE_KEY=<throwaway-testnet-key>
python3 agent/play-agent.py
```

## Origen

Port de [STARFORGE — La Forja Estelar](../chain-jam/starforge/) (Chain Jam
Vol. 1): misma matemática (`math-spec.json`), verificado con Monte Carlo
10M (RTP 97.60% con todos los artefactos) y paridad contrato/simulador
15/15. Solo cambió la interfaz de host: de ICasinoGameV2 a `StarforgeArena`
nativo de Monad.
