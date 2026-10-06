# Protected settings — ArduPilot & PX4 (v0.1 draft)

**LDTT = Linked Drone Tool Trust** · **Phase 2** shared draft · Expands Stamp Spec §2.1  
**Status:** Draft for creator → Corrector — **not final**  
**Date:** 2026-10-06
**Creator locks applied:** widen draft list (`FENCE_*`, `GF_*`, `CBRK_*`, …); no schema bump.

A connector that can **change** any of these cannot be stamped at any level in v0.1. Names feed the schema `protectedParam` denylist pattern and review (E9). Wildcards in `param_allowlist` that match these are forbidden.

> Autopilot parameter sets drift by version. This list is a **starting denylist** for review, not an exhaustive certification catalog.

---

## 1. Categories (spec §2.1)

1. Geofence enable/disable / breach action  
2. Failsafe settings  
3. Arming checks (incl. force-arm)  
4. Remote ID disable/degrade  
5. Generic param write/reset bypass (`MAV_CMD_DO_SET_PARAMETER`, `MAV_CMD_PREFLIGHT_STORAGE`)

Also: `MAV_CMD_DO_FENCE_ENABLE` is a protected **command**.

---


## 2.1 Widened draft denylist patterns (Phase 2 creator lock — draft list only, no schema bump)

Proposed union for v0.2 schema / review (do **not** bump schema until asked):

```
FENCE_.*
GF_.*
CBRK_.*
FS_.*
BATT_FS_.*
ARMING_.*
DID_.*
COM_ARM_.*
COM_ODID_.*
NAV_DLL_ACT
NAV_RCL_ACT
COM_LOW_BAT_ACT
COM_OBL_ACT
COM_OBL_RC_ACT
BRD_SAFETY.*
```

Geometry params under `operate:geofence` (edit items, never disable) remain an open Corrector question.

## 2. ArduPilot (Copilot / Plane / Rover — common)

### Geofence
| Param | Notes |
|---|---|
| FENCE_ENABLE | Enable/disable fence |
| FENCE_ACTION | Breach action |
| FENCE_TYPE | Which fence types active |
| FENCE_ALT_MIN / FENCE_ALT_MAX | Altitude fence bounds (edit vs disable — treat disable-capable combos carefully) |
| FENCE_RADIUS / FENCE_MARGIN | |
| FENCE_TOTAL | |
| FENCE_OPTIONS | |

### Failsafe
| Param | Notes |
|---|---|
| FS_* | Throttle, GCS, ekf, crash, etc. (pattern `FS_*`) |
| BATT_FS_* | Battery failsafe actions/thresholds |
| FS_THR_ENABLE / FS_GCS_ENABLE / FS_EKF_ACTION / FS_CRASH_CHECK | Explicit common ones |
| RTL_ALT / RTL_* when used as failsafe path config | Review: many RTL_* are mission prefs; flag failsafe-linked ones in review |

### Arming
| Param | Notes |
|---|---|
| ARMING_CHECK | Bitmask of checks |
| ARMING_REQUIRE | |
| ARMING_MIS_ITEMS | |
| ARMING_OPTIONS | |

### Remote ID
| Param | Notes |
|---|---|
| DID_* | All Remote ID / OpenDroneID (F9) |
| DID_ENABLE | |

### Schema pattern today
`^(FENCE_ENABLE|FENCE_ACTION|GF_ACTION|ARMING_CHECK|FS_.*|BATT_FS_.*|NAV_DLL_ACT|NAV_RCL_ACT|COM_ARM_.*|DID_.*)$`

**Proposed ArduPilot additions for v0.2 schema pattern (draft):**  
`FENCE_TYPE`, `FENCE_OPTIONS`, `ARMING_REQUIRE`, `ARMING_OPTIONS`, `BRD_SAFETY*` (safety switch bypasses), `DISARM_DELAY` (review), `SIM_*` N/A for stamps.

---

## 3. PX4

### Geofence
| Param | Notes |
|---|---|
| GF_ACTION | Breach action (§2.1) |
| GF_MAX_HOR_DIST / GF_MAX_VER_DIST | |
| GF_SOURCE | |

### Failsafe / RC / data link loss
| Param | Notes |
|---|---|
| NAV_DLL_ACT | Data link loss action |
| NAV_RCL_ACT | RC loss action |
| COM_DL_LOSS_T / COM_RC_LOSS_T | Timers (review: changing may degrade failsafe) |
| COM_OBL_ACT / COM_OBL_RC_ACT | |
| COM_LOW_BAT_ACT | Battery failsafe |
| COM_QC_ACT | |

### Arming
| Param | Notes |
|---|---|
| COM_ARM_* | All arm prechecks (§2.1 pattern) |
| COM_ARM_WO_GPS / COM_ARM_CHK_ESCS / COM_ARM_SDCARD / … | |
| CBRK_ARM_CHK / CBRK_* | Circuit breakers that skip safety — **propose protect all CBRK_*** |

### Remote ID
| Param | Notes |
|---|---|
| COM_ARM_ODID | OpenDroneID arm requirement (§2.1) |
| COM_ODID_* if present | Treat as Remote ID family |

**Proposed PX4 additions for v0.2 schema pattern (draft):**  
`GF_.*` (or listed GF_*), `CBRK_.*`, `COM_LOW_BAT_ACT`, `COM_ODID_.*`, expand beyond `COM_ARM_.*` alone for failsafe actions already partly listed.

---

## 4. Commands (both stacks)

| Command | Status |
|---|---|
| MAV_CMD_DO_FENCE_ENABLE | Protected X |
| MAV_CMD_DO_SET_PARAMETER | Protected X |
| MAV_CMD_PREFLIGHT_STORAGE | Protected X |
| MAV_CMD_DO_FLIGHTTERMINATION | Command in v0.1; propose protect v0.2 (see mapping draft) |
| MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN | Command in v0.1; propose protect/gate v0.2 |
| MAV_CMD_DO_MOTOR_TEST | Command in v0.1; propose protect when armed |

---

## 5. Open questions for Corrector (via creator)

1. Widen schema `protectedParam` regex in v0.2 to `FENCE_.*`, `GF_.*`, `CBRK_.*`, `DID_.*`, `COM_ARM_.*`, `FS_.*`, `BATT_FS_.*` plus explicit NAV_/COM_ failsafe acts?
2. Are geofence **geometry** params (`FENCE_RADIUS`, vertices via mission/fence items) allowed under `operate:geofence` while enable/action stay protected? (Spec says edit items, never disable.)
3. Version pinning: maintain per-AP major version matrices, or one conservative union denylist?
4. Circuit breakers (`CBRK_*`) — protect all?

---
*Phase 2 draft · Linked Drone Tool Trust · not final*
