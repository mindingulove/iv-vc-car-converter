# IV to native Vice City car converter

Local RSC5 WFT/WTD / NextGen IMG vehicle extraction and conversion for the compatible native reVC Metal port. No GTA IV installation is needed. This is not a universal GTA V YFT/YTD converter. Game files, source car packs and generated conversions are not included.

On macOS install Python 3 with Tk, .NET SDK 8 or newer, Git, and the native reVC Metal build tools. Run `./setup.sh`, then open `Convert Car.command`. The source-only setup downloads pinned DragonFF and GTA4Unity/RageLib dependencies and retains their licenses. For native validation, place a reVC Metal source checkout at `../revc-metal` or set `REVC_SOURCE` to its path; configure and build its `build-metal` target first. Native validation is required before installation.

Choose your game folder (or its Modloader folder), select an archive/model, choose Add or Replace, and convert. The detected paint controls appear after the initial preview. Choose independent RGB overrides only for channels the source provides, apply/revalidate, then install while the game is closed. Unchanged channels retain their donor/source behaviour. Additional paint selectors are conversion-time fixed colours; native dynamic painting remains two-channel. The converter also retains supported extras, glass/liveries and running gear and fits individual handling/collision profiles. Unsupported assets are rejected with errors.

Detailed workflow, CLI and limitations: [car-converter/README.md](car-converter/README.md). Appearance, damage behaviour, collisions and performance require gameplay review. The native port still has an open pane-depth/occupant reflection defect. No promise of universal compatibility.

Run `python3 -m unittest discover -s car-converter -p 'test_material_policy.py'` and `python3 -m unittest discover -s car-converter -p 'test_paint_options.py'`. A compatible native Metal fixture validates converted output before installation.

The parser source derives from luckeyfaraday/gta4-webmap (MIT; license retained). DragonFF and GTA4Unity/RageLib retain their own GPL licenses. Source vehicle copyrights and credits belong to their authors; do not redistribute their assets without permission.
