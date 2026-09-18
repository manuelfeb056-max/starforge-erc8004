# Deploy en Monad testnet — pasos manuales (semana 2)

> Sin claves en el repo. Usar wallet throwaway solo para testnet.
> Nada de mainnet.

Monad testnet: chainId **10143**, RPC `https://testnet-rpc.monad.xyz`.

## Orden de deploy

1. **Registros ERC-8004** — primero revisar si ya existe deployment oficial
   en Monad testnet (ver `docs/ERC8004_NOTES.md`). Si no:
   desplegar la implementación de referencia
   (BillionsNetwork/erc-8004-contracts): `IdentityRegistry`,
   `ReputationRegistry`. Anotar direcciones.
2. `StarforgeGame` — sin args.
3. `BlockhashRandomness` — sin args.
4. `AgentReputation(identityRegistry, reputationRegistry)` — sin arena aún.
5. `StarforgeArena(game, randomness)` — sin reputation aún.
6. Wiring (owner = deployer):
   - `AgentReputation.setArena(arena)`
   - `StarforgeArena.setReputation(agentReputation)`
7. Verificar wiring: `arena.reputation()`, `agentReputation.arena()`.

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
