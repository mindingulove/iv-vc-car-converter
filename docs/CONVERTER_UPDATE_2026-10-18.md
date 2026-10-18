# Converter update validation — 2026-10-18

Live toolkit and source repository are synchronized. No native game source/renderer files, game binaries, settings or installed car packages were changed during this converter-only work.

Implemented: separate door/rear pane export; report windscreen and selected-extra glass with native support requirements; preserve structural inner bonnet geometry; compact sparse extras into six native slots and reject excess independent parts; preserve detected paint selectors; exclude upholstery/glass/specular masks; refuse invalid mip counts; destination changes invalidate the prior GUI installation target. Native support checks recognize the installed full-pane binaries and compatible unstripped FPS rebuilds without modifying either runtime.

Validation: 18 converter policy/options/capability tests passed. Real sources Infernus, Feltzer, Mesa and Police expose the expected glass/optional metadata. Patriot, Rapid GT and Sabre Turbo retain attached bonnet parts and paint-only recolouring changes only material colour bytes. Across 123 real sources, 112 exports pass the existing independent native CPU model/texture/hierarchy fixture. Eleven are explicitly refused because more than six independent optional components require manual combination grouping: airtaxi, ardent, benson, blista_gpx, blistac, bobcat, deluxo, moonbeam, mule, spand, yankee.

These are converter/streaming checks, not gameplay, GUI interaction or performance acceptance. The rejected sources were not installed or silently altered. Existing installed fleet remains untouched. Renderer work belongs to Claude; see DEFERRED_PAINT_DAMAGE_PLAN.md for the user's rejected zebra-pattern scratches and the later contact-driven correction.
