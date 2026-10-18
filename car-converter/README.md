# Vice City Car Converter

Open **Convert Car.command** in the parent folder. The same launcher is available in `~/Documents/revc-metal-run/Car Converter.command`.

1. Choose a GTA IV `.wft` beside its matching `.wtd`, or a NextGen `vehicles.img` archive.
2. For an archive, click **Read models** and select its entry. Embedded labels may retain donor names: use the texture hints and review the converted preview.
3. Choose **Add a new car**, enter a custom name, and select an existing handling/collision donor; or choose **Replace an existing car** and select the stock model to replace.
4. Choose whether it appears in traffic and its relative frequency.
5. Click **Convert and preview**. This exports the model, textures, named collision, IDE/colours and a source manifest, then validates through the native Metal streaming loader.
6. Review the preview. Close Vice City and click **Install converted car**. Start the game normally. Added cars appear by name in F7's vehicle browser and enter their donor's traffic class. Traffic spawning remains probabilistic and depends on location/streaming, density and traffic settings.

Add mode allocates an unused ID from 6000–6499 and keeps stock cars. It requires the accompanying add-on-capable native reVC build. Add-on vehicle model capacity is 512 total; traffic tables allow up to 256 registered models per class. Existing game settings, GTA III and original game archives are preserved. Existing converted packages are backed up outside Modloader before updating.

## Supported input and limits

- GTA IV / IV-based NextGen **RSC5 WFT/WTD four-wheel rigid cars**. IMG directories may be encrypted: the tool recovers complete unencrypted resource payloads directly and records their source offsets/hashes. GTA IV need not be installed.
- Embedded models are selected by resource entry index, not by an assumed original encrypted archive filename.
- Moving body panels and original wheels are preserved. Existing `suspension_*` arm geometry is animated by the native port when present; cars without arm geometry still use normal physical wheel suspension.
- DXT1/3/5 blocks and existing mipmaps are copied without recompression. Other DDS rasters are decoded to RGBA for compatibility.
- **Not a universal format converter**: GTA V YFT/YTD, bikes, boats, aircraft, blended skin rigs and extra non-wheel fragments need additional importers or manual authoring. Unsupported inputs are rejected instead of silently producing incomplete cars.
- Collision retains the selected stock donor's shapes, fitted to the imported body bounds with clearance above the tyre contact plane. Pick a similar donor; authored IV collision is not imported. Driving, collisions and visual quality still require in-game review.
- There are no separately authored damaged-part mesh variants; the existing native LocalDent system supplies deformation.
- The preview is a software rendering of the exported DFF, not an in-game capture. Conversion checks are not proof of mission compatibility or gameplay performance.

## Command line

```sh
./"Convert Car.command" --source "/path/to/vehicles.img" --list
./"Convert Car.command" --source "/path/to/vehicles.img" --entry 54 \
  --mode add --name huntley --donor rancher --install
./"Convert Car.command" --source "/path/to/car.wft" \
  --mode replace --replace admiral --install
```

Each export is written under `exports/<name>` with `conversion.json`, `preview.png`, native validation logs, source information, DFF/TXD/COL and data fragments. Conversion alone does not install anything. Install refuses while Vice City is running.

This local tool uses GTA4Unity/RageLib via gta4-webmap for resource parsing and DragonFF for RenderWare output. Preserve those projects' licenses. Source asset copyrights/credits remain with their authors; converting local files does not grant redistribution rights.

## Extract whole archives

The **Extract archive(s)…** button extracts all resources without converting or installing them. You can also use `./"Convert Car.command" --source "/path/to/pack" --extract-all --output "/path/to/output"`. Multiple editions are placed in separate folders. See `extracted-packs/README.md` for the three archives already extracted from the two supplied packs.

## Suspension tuning

Enable **Fit authored wheel height** to centre the suspension at the imported wheel pivots. **Ride height cm**: negative lowers, positive raises the chassis. Spring strength, damping and travel are multipliers (1 is the donor value). These controls affect only this converted car; the original donor handling stays unchanged. Existing donor collision shapes are fitted at conversion to avoid an invisible chassis extending below the tyres.

To adjust an installed conversion, set the controls, click **Tune installed car…**, select its `modloader/Converted <name>` folder and restart Vice City. The game must be closed while applying the change; the previous package is backed up. The native suspension update is required.

```sh
./"Convert Car.command" --tune-package "/Users/jaymeeduardo/Documents/revc-metal-run/modloader/Converted huntley" --ride-height -3 --damping 1.15
```

The optional IDE suffix is `autoFit rideHeightMeters stiffness damping travel` after the standard 13 car fields. Old rows retain original behavior. Turning auto-fit off retains the donor suspension unchanged.

## Per-car handling and ride height

New conversions include a `data/cvh_<model>.cfg` profile. It starts with the native VC handling for the chosen vehicle class, scales mass and dimensions to the imported body, and fits suspension travel to tyre size. Native acceleration/braking/transmission units are preserved; GTA IV handling numbers are not copied directly. These profiles require the native per-car handling update and never modify the shared donor table.

The stored suspension limits are already centred on the authored wheel height, including when the optional auto-fit checkbox is off. Auto-fit permits the ride-height, spring and travel controls to recalculate that centre. Positive ride-height offsets raise the chassis; 0 follows the source geometry. In-game driving remains the final validation.

## Select the destination and paint colours

Use **Choose game folder…** to select the native Vice City installation or its `modloader` folder. The donor/replace list reloads from that game. Conversion, suspension tuning and installation all use this destination. It must have `data/default.ide`, Modloader, and the compatible native add-on/material/handling capabilities.

Convert once to inspect the source and preview it. The **Detected car colours** panel then shows only the channels present in the model: Primary, Secondary, Tertiary, Quaternary, or numbered additional selectors. Choose RGB colours and click **Apply colours and update preview**. The package passes native validation again before installation is enabled. **Restore source / donor colours** removes the overrides. Fixed liveries, seats, fabric and trim are excluded from paint detection. A baked livery cannot be recoloured as independent paint.

These are conversion-time RGB overrides stored in the material; they are fixed colours, not additional dynamic Pay 'n' Spray channels. Unchanged primary/secondary channels retain native donor repaint behaviour. The native engine has two dynamic paint channels; additional detected selectors can be given independent fixed colours by the converter.

```sh
./"Convert Car.command" --source /path/car.wft --runtime /path/native-vc \
  --mode add --name example --donor rancher --paint '1=#123456' --paint '2=#222222'
./"Convert Car.command" --recolor-package exports/example --paint '1=#AABBCC'
```

No game-wide colour palette is replaced. Selected RGB values matching the native paint sentinel colours are shifted by one RGB unit to prevent accidental remapping. Paint-only updates preserve the rest of the DFF byte for byte and validate a temporary package before replacing the output. Gameplay appearance still requires inspection.
