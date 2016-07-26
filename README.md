# mkdim
mkdim.py for DAZ Studio

Usage:
```./mkdim.py --source=ro --part=1 --id=115061 --name="FD Pencil Dress for G3F"  FD_PencilDress_1of5_188796.zip 
```
The 'id' comes from the product URL, 'source' is an abbreviation for the store where the item was purchased.

Currently supported sources:

|Code | Store
|-----|-------------
|DAZ  | DAZ_3D
|WDC  | Wilmap
|HW   | Hivewire3D
|RDNA | RuntimeDNA
|MDC  | Most-Digital
|SCG  | ShareCG
|RO   | Renderosity
|RE   | Renderotica
|ME   | Esemwy

At this time 'source' only prepends a number to the 'id' such that products can be separated by vendor
in DIM. When better functionality is ready, a script will be provided to convert old packages to new.

