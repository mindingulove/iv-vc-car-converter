# Deferred paint damage correction — GTA III and Vice City

Status: **current scratch effect FAILED user gameplay review**. The procedural stripes look like uniform zebra lines across the paint. Do not describe that effect as finished or accepted. Dirt also remains subject to gameplay acceptance.

**Do not implement now.** Claude owns FPS/renderer work in both game source trees. Codex is restricted to converter work during that period. Start this correction only after the performance handoff and integration review; keep world/VC/III map conversion and airports behind the acceptance gate.

## Required behaviour

- Scratches appear only where the vehicle touches an abrasive surface. A wall scrape while driving, including gentle continuous contact without a crash, creates a local trail that follows the movement and contact shape.
- Remove the periodic striped paint effect. Scratch shape, direction, length and coverage come from physical contact, not a uniform sine pattern or a vehicle-wide repeated texture.
- Abrasion removes the top paint locally, exposing underlying primer/undercoat and, with stronger abrasion, metal. Do not substitute a full-panel colour change or universal white/zebra lines.
- Repeated contact accumulates in the same affected region; untouched paint stays intact. Doors, bonnet and other moving/deforming panels retain correctly anchored marks.
- Dirt, dents and scratches have separate state. Clean removes dirt; repair restores the damaged paint and vehicle components. Glass, upholstery, tyres, badges and lamp lenses must not receive body-paint scratches.
- Apply the behaviour to both native games. The converter classifies paint versus glass/interior; it does not bake crash marks into source textures.

## Planned implementation work, after Claude

1. Record matched gameplay reproductions in both games: gentle side contact while sliding along a wall, a sustained scrape, a short glancing hit, and a frontal crash. Preserve settings and Claude's FPS baseline.
2. Trace continuous collision contacts and relative sliding speed/contact distance. Do not rely solely on LocalDent's discrete crash episode or an impulse threshold; those omit low-impact wall abrasion.
3. Design bounded per-vehicle paint-damage storage. Evaluate a contact-projected damage mask/decal atlas anchored to each panel, including deformation and moving parts. Verify seam/UV handling and avoid marks appearing on the opposite panel or interior. Decide how masks follow deformation before implementation.
4. Sweep each abrasive contact between successive contact positions. Use contact normal, sliding direction, pressure/force and travelled distance to determine the local footprint and paint removal. A short impact produces a local mark; a long scrape produces a continuous path, without evenly spaced stamp gaps.
5. Shade the paint/undercoat/metal layers from that mask. Any fine irregularity stays inside the contact footprint and must not create repeated stripes across untouched paint. Preserve reflection detail and Claude's rendering settings.
6. Bound memory, contact processing and mask updates; release state safely at vehicle/render-object teardown. Avoid new per-frame allocations or geometry-wide CPU work. Compare measured CPU/GPU costs against the FPS baseline, without promising a free effect.
7. Connect Clean/Repair/reset and define save persistence explicitly. Preserve door/glass/lamp damage behaviour and fix regressions without undoing Claude's changes.

## Acceptance tests before maps

- Both sides of multiple vehicles: a low-speed wall scrape makes a local directional mark even without a crash episode; continuous scraping follows the contact path.
- A frontal hit affects only the contacted area; the rear, roof and opposite side do not acquire repeated lines.
- Repeated scrapes accumulate locally and reveal the underlying layers; doors/bonnet opening and deformation do not leave marks floating or duplicated.
- Glass/interiors stay unaffected; Clean retains scratches; Repair clears them; destroying vehicles and exiting the game remain safe.
- Test sunlight/rain, light/dark paint and multiple camera distances. Check temporal stability and FPS using the same scene/settings as Claude's baseline.
- User explicitly accepts the appearance and behaviour in **both** games before this item is closed. Build, pixel and native component tests alone are insufficient.
