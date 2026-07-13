# ADR 0002: Renderer adapter boundary

## Status

Accepted

## Date

2026-06-30

## Context

Maya Pipeline Inspector must support multiple renderer families. The initial targets are Common Maya, V-Ray, and Arnold. Future targets may include RenderMan, Redshift, USD, and MaterialX inspection.

Renderer-specific behavior includes:

- material node types;
- texture node types;
- displacement nodes and plugs;
- semantic meaning of material inputs;
- color/data texture slot classification;
- renderer-specific optimization expectations;
- graph complexity weights;
- supported/deprecated node types;
- renderer-specific default rules.

If the core validator hardcodes renderer node names and plug semantics, cross-renderer support will become fragile and expensive to maintain. Adding another renderer would require editing central validation logic instead of adding an isolated adapter and rules.

## Decision

Renderer-specific knowledge will live behind renderer adapters.

The core engine will not hardcode V-Ray, Arnold, RenderMan, Redshift, USD, or MaterialX node behavior. Instead, the core will ask registered adapters to classify nodes, identify semantic texture slots, expose displacement slots, provide complexity weights, and list default rule packs.

Initial adapter locations:

```text
src/pipeline_inspector/adapters/base.py
src/pipeline_inspector/adapters/common_maya.py
src/pipeline_inspector/adapters/vray.py
src/pipeline_inspector/adapters/arnold.py
```

Renderer adapters may classify data such as:

- `base_color`
- `roughness`
- `metalness`
- `normal`
- `bump`
- `displacement`
- `opacity`
- `emission`
- `mask`
- `unknown`

The core validator may use semantic labels. It must not need to know that, for example, a given V-Ray plug or Arnold plug produced that semantic label.

## Adapter Responsibilities

A renderer adapter should be responsible for:

- identifying supported node types;
- classifying nodes into material, texture, utility, displacement, or unknown roles;
- mapping destination plugs to semantic texture slots;
- defining displacement-related plugs and nodes;
- providing graph complexity weights;
- listing renderer-specific rule packs;
- gracefully handling missing renderer plugins.

A renderer adapter should not:

- mutate the Maya scene;
- perform UI work;
- apply fixes directly;
- bypass rule/profile policy;
- require the renderer plugin to be installed for pure unit tests.

## Alternatives Considered

### 1. Hardcode renderer behavior in rule engine

Pros:

- simple for the first V-Ray-only prototype;
- fewer modules at the start.

Cons:

- core becomes renderer-specific;
- Arnold and future renderers become invasive changes;
- harder to test and maintain;
- rule authors cannot reason cleanly about renderer boundaries.

Rejected.

### 2. Put all renderer behavior in JSON rules only

Pros:

- maximum data-driven behavior;
- less Python code for simple mappings.

Cons:

- complex graph semantics become awkward in JSON;
- slot classification may require procedural logic;
- difficult to express adapter availability and version behavior;
- rules become too complex for contributors.

Rejected as the only mechanism. JSON rules remain important, but adapters provide semantic classification.

### 3. Adapter boundary plus data-driven rules

Pros:

- clean separation of renderer knowledge;
- core stays renderer-agnostic;
- rules can target semantic labels instead of renderer-specific plugs;
- future renderer support is additive;
- adapters can be tested with snapshot fixtures.

Cons:

- requires adapter interface design;
- adapter and rule pack versions must be kept aligned;
- unknown/ambiguous semantics need clear reporting.

Accepted.

## Consequences

### Positive

- Adding a renderer should not require rewriting the core validator.
- Rule packs can use semantic concepts like `roughness` or `displacement`.
- Common checks can work across V-Ray and Arnold.
- Renderer plugins are not required for pure Python adapter tests.
- Unknown renderer nodes can be reported instead of silently ignored.

### Negative / Tradeoffs

- Adapter interface must be stable enough for contributors.
- Semantic mapping may be incomplete in early versions.
- Some renderer-specific edge cases will require adapter-specific fixtures.
- Rule authors must understand the difference between node type matching and semantic slot matching.

## Implementation Notes

Expected base interface shape:

```python
class RendererAdapter:
    id: str
    display_name: str

    def supported_node_types(self) -> set[str]: ...
    def classify_node(self, node) -> list[str]: ...
    def texture_slot_semantics(self) -> dict[str, str]: ...
    def displacement_slots(self) -> list[str]: ...
    def complexity_weights(self) -> dict[str, float]: ...
    def default_rule_packs(self) -> list[str]: ...
```

The final implementation may use `Protocol`, abstract base classes, or dataclasses as appropriate.

A registry should allow tests to register fake adapters.

Initial adapters:

- Common Maya adapter;
- V-Ray adapter MVP;
- Arnold adapter MVP.

Future adapters must include tests and documented unsupported behavior.

## Related

- Issue: `#016 - Define renderer adapter protocol`
- Issue: `#017 - Implement Common Maya adapter`
- Issue: `#018 - Implement V-Ray adapter MVP`
- Issue: `#019 - Implement Arnold adapter MVP`
- Issue: `#020 - Implement semantic texture slot resolver`
- Document: `docs/ARCHITECTURE.md`
- Document: `docs/RULE_AUTHORING.md`
