# Implementation 1.0.3.1 reporting correction

The 1.0.3 engine constant was correct, but its scoped report returned a stale literal 1.0.2. This immutable successor imports and uses the engine's shared implementation constant on both report paths. No scientific gate, source, claim, reviewer approval, policy or study value changes.

All 126 predecessor tests remain, with four new shared-version and metadata-lineage regressions. The unchanged actual pilot was recomputed from its immutable input, not relabeled by hand. Complete parsed reports differ only in implementation_version; report hashes change accordingly. Old reports and 1.0.3 remain preserved in their predecessor package.

Policy 1.1.0 is unchanged. Private final implementation external review remains pending specific authorization. No prior JEV receipt certifies this reporting successor.
