# Pipeline Inspector shelf and menu icons

Contributor-provided PNGs for Maya menu/shelf entry points and panel header buttons.

| PNG basename | Entry |
| --- | --- |
| `pipeline_inspector_main.png` | Open Pipeline Inspector (first menu/shelf item) |
| `pipeline_inspector_settings.png` | Settings |
| `pipeline_inspector_validate_scene.png` | Validate Scene |
| `pipeline_inspector_reports.png` | Reports |
| `pipeline_inspector_readiness_check.png` | Readiness Check |
| `pipeline_inspector_farm_check.png` | Farm Check |
| `pipeline_inspector_wiki.png` | Documentation (menu/shelf + panel header button) |
| `pipeline_inspector_check_for_updates.png` | Check for Updates |
| `pipeline_inspector_close.png` | Close Pipeline Inspector (menu only) |
| `pipeline_inspector_report_bug.png` | Report Plugin Bug (panel header only) |

## Panel header

- Settings gear keeps the Unicode gear label (`⚙`), not `pipeline_inspector_settings.png`.
- Documentation and Report Plugin Bug buttons load `pipeline_inspector_wiki.png` and `pipeline_inspector_report_bug.png`.

## Maya wiring

- `pipeline_inspector.mod` declares `icons: icons`, so Maya adds this folder to icon lookup.
- Shelf buttons use `image1="<basename>"`.
- Menu items use `image="<basename>"` when the PNG exists.

Replace placeholder PNGs with studio artwork using the same filenames, then run `install_ui()` or restart Maya.
