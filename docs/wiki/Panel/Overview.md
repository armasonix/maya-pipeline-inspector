# Panel overview

The **Maya Pipeline Inspector** panel is a dockable Qt UI — the primary product surface ([ADR 0005](../../adr/0005-gui-first-product-philosophy.md)).

## Layout

```text
+------------------------------------------------------------------+
| Maya Pipeline Inspector  v0.6.0+    [Wiki] [Bug] [Updates] [X] |
| [Validate][Waivers][Fixes][Reports][Readiness][Farm]  [Settings]|
+------------------------------------------------------------------+
|  Active tab content                                               |
+------------------------------------------------------------------+
```

All tabs share one validation pipeline: `maya.validation_pipeline` → core engine. The UI never forks rule evaluation ([`ARCHITECTURE.md`](../../ARCHITECTURE.md)).

## Tab guide

| Tab | Wiki page | One-line purpose |
| --- | --- | --- |
| Validate | [Validate tab](Validate-Tab) | Scan, triage, jump to scene |
| Waivers | [Fixes & waivers](Fixes-and-Waivers) | Exception management |
| Fixes | [Fixes & waivers](Fixes-and-Waivers) | Safe auto-fix queue |
| Reports | [Reports tab](Reports-Tab) | Export & tracker handoff |
| Readiness | [Readiness tab](Readiness-Tab) | Workstation probes |
| Farm | [Farm tab](Farm-Tab) | Deadline preflight & submit |
| Settings | [Settings hub](Settings-Hub) | Gear overlay — config & connectors |

## Entry points outside the panel

| Entry | Opens |
| --- | --- |
| Menu **Pipeline Inspector** | Panel (Validate) |
| **Pipeline Inspector Farm Check** | Farm tab + preflight |
| **Readiness Check** | Readiness tab |

Install details: [`MAYA_INSTALL.md`](../../MAYA_INSTALL.md)

## Themes

User preference **Classic** / **Dark** in Settings → Basic. QSS themes ship in package data.

## Async validation

**Validate Scene** runs off the UI thread. Status line shows progress; cancel where supported. Large scenes may take tens of seconds — health summary updates when complete.

## Related

- Full UI spec: [`USER_GUIDE.md` — Maya UI Layout](../../USER_GUIDE.md#maya-ui-layout)
- UX audit backlog: [`MAYA_UX_AUDIT_v0.4.md`](../../MAYA_UX_AUDIT_v0.4.md)
