# Deploy en Monad testnet — semana 2

> Sin claves en el repo. Usar wallet throwaway solo para testnet.
> Nada de mainnet.

Monad testnet: chainId **10143**, RPC `https://rpc.ankr.com/monad_testnet`
(verificado 2026-09-18; el oficial `testnet-rpc.monad.xyz` no respondía).

## Registros ERC-8004: usar los oficiales (verificado on-chain 2026-09-18)

NO desplegar registros propios. Ambos son proxies ERC1967 ya desplegados:
- Identity: `0x8004A818BFB912233c491871b3d84c89A494BD9e`
- Reputation: `0x8004B663056A597Dffe9eCcC1965A193B7388713`

## Deploy automatizado

```bash
export DEPLOYER_KEY=<throwaway-testnet-key>   # nunca una wallet real
python3 scripts/deploy.py
```

Despliega: `StarforgeGame` → `BlockhashRandomness` →
`AgentReputation(identity, reputation)` → `StarforgeArena(game, randomness)`,
luego el wiring `setArena` / `setReputation` (one-time, solo owner).
Escribe `deployments/testnet.json` + `deployments/abis.json`.

## BLOQUEO ACTUAL: faucet

La wallet throwaway `0x129198ABEcbAcca464eD9Da7f9AC3be397A463fA` necesita MON
de testnet. Opciones (todas gratuitas, $0):
- https://www.alchemy.com/faucets/monad-testnet — sin cuenta, solo pegar
  dirección + Turnstile (30s desde el teléfono).
- https://faucet.quicknode.com/monad/testnet — sin cuenta, con verificación.
- El faucet oficial (faucet.monad.xyz) exige 10 MON en mainnet o 0.001 ETH
  en L1/L2 — no aplica a wallets nuevas.

## Registro del agente demo

8. `identityRegistry.register(dataURI)` → `agentId`
   (data-URI con `agent/registration.json`, rellenar agentId + registry).
9. `identityRegistry.setMetadata(agentId, "starforge_player", 0x01)`.
10. `agentReputation.linkAgent(agentId)` desde la wallet del bot.

## Prueba end-to-end

11. `arena.openSession(0x07)` con 0.001 MON → esperar 3+ bloques →
    `fulfillSpin(1)` → si supernova: `submitPicks(1, [0,1,2,3,4], false)`.
12. Verificar `SessionSettled` + feedback en el Reputation Registry
    (`readFeedback(agentId, arena, 0)`).
13. Correr `agent/play-agent.py` en loop y observar el leaderboard.
