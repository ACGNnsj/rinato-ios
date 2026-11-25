# Rinato iOS execution model: already AOT, no JIT needed

Verified in upstream tree (audit @ 551228c); this reverses the JIT-blocked narrative.

## Mechanism (loader.c map_image + gen_embed.py)

- patch_nso rewrites modules OFFLINE (Mac). gen_embed.py packs each rewritten module into the app binary: x0/x1/x2 (code incl. all patch areas) into __TEXT sections (__dm<name>x0/x1/x2), W (data) into __DM section.
- At runtime map_image vm_remaps with copy=FALSE for X sections: shared mapping of the SIGNED __TEXT pages, executable with no JIT entitlement, no streamer, no debugger. Only W is copied (TRUE) as RW.
- NRO modules ride the same way via packed __TEXT,__dm_nro_x0 / __DM_NRO_W / __TEXT,__dm_nro_x1 + table.
- jit_slot() is address-layout only (reservation inside the JIT address plan), not runtime codegen.

## Why Rinato never needs runtime codegen

- MAP_JIT/pthread_jit_write_protect exist only in hle_jit.c: the GAME'S OWN JIT plugin path (N64 emulators etc.).
- Rinato main 944 imports contain zero nn::jit symbols (pack script uses_jit() false) -> no JIT capture route, no DDI mount dependency for the game path.
- The M0 probe JIT row tested an irrelevant capability; its PARKED status does not constrain the port. iOS 27 JIT restrictions (SideStore Jun 2026) do not touch this route.

## Remaining iOS-27/A13 risks (unchanged)

- 5GB virtual-address reservation on 4GB device (VA, not resident; measured 2.04GiB avail + 256MB alloc OK). Decided at first boot, not by JIT.
- Movie demux-open #if 0; per-title bring-up REDs.

## Consequence

Critical path is ONLY: Mac chain (rewrite + embed + sign + sideload) -> first boot. No streamer, no StikJIT, no DDI mount in the loop.
