// Draco-compress GLBs in place with glTF-Transform's encoder (draco3dgltf): blender/common.py export_glb writes them
// uncompressed and runs this. At the same quantization the Blender exporter's own Draco comes out about a fifth
// larger after gzip (campus_buildings.glb 11.5 -> 9.9 MB, campus_landmarks.glb 6.7 -> 5.0 MB), and decodes no faster.
//   node tools/draco_glb.mjs [--normal N] <file.glb>...   (--normal: the normals' bits, the people's 12)
//   node tools/draco_glb.mjs --decode <in.glb> <out.glb>  (written uncompressed: for the tools that parse a GLB
//                                                          themselves, tools/glb_plain.py)
// A file that is already Draco-compressed is decoded and encoded again at these bits.
// Needs web/'s devDependencies (cd web && npm install).
//
// The bits (over each primitive's own range) are those export_glb asked of the Blender exporter. None has room to
// spare:
//  POSITION 16  the landmarks' long primitives (kerbs, lamps, lines along the roads) span up to 1.5 km: 24 mm a step
//               at 16 bits, 96 mm at 14
//  TEXCOORD 14  the uv are metres in world coordinates (common.auto_uv): a primitive's range is ~760 m (median),
//               4.6 cm a step at 14 bits, 19 cm at 12 (the tiles' joints would step at the corners)
//  GENERIC 16   _EDGE (blender/bake.py): 0 - 128 m, 2 mm a step; the wear at an arris is 2 - 6 cm wide
//  NORMAL 10, COLOR 10 (a float colour; COLOR_0 is uint16 in every file now, and integers are not quantized)
// The people (blender/characters.py, --normal 12): a person is under 2 m, 0.03 mm a step at 16 bits; the face's and the
// hair's shading reads the normals up close; the skin weights, _LEG and _OCC are integers (not quantized)
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
const req = createRequire(path.join(here, '../web/package.json'));
const { NodeIO } = req('@gltf-transform/core');
const { ALL_EXTENSIONS, KHRDracoMeshCompression } = req('@gltf-transform/extensions');
const draco3d = req('draco3dgltf');

const BITS = { POSITION: 16, NORMAL: 10, TEX_COORD: 14, COLOR: 10, GENERIC: 16 };

const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({
  'draco3d.decoder': await draco3d.createDecoderModule(),
  'draco3d.encoder': await draco3d.createEncoderModule(),
});

const args = process.argv.slice(2);
if (args[0] === '--decode') {
  const doc = await io.read(args[1]);
  for (const e of doc.getRoot().listExtensionsUsed()) if (e.extensionName === KHRDracoMeshCompression.EXTENSION_NAME) e.dispose();
  fs.writeFileSync(args[2], await io.writeBinary(doc));
  process.exit(0);
}
const bits = { ...BITS };
if (args[0] === '--normal') { bits.NORMAL = Number(args[1]); args.splice(0, 2); }
for (const file of args) {
  const before = fs.statSync(file).size;
  const doc = await io.read(file);
  const ext = doc.getRoot().listExtensionsUsed().find((e) => e.extensionName === KHRDracoMeshCompression.EXTENSION_NAME)
    ?? doc.createExtension(KHRDracoMeshCompression);
  // edgebreaker, speed 4 (the exporter's compression level 6): 0 - 2 come out larger, 6 as large as the exporter's own
  ext.setRequired(true).setEncoderOptions({
    method: KHRDracoMeshCompression.EncoderMethod.EDGEBREAKER, encodeSpeed: 4, decodeSpeed: 4, quantizationBits: bits,
  });
  fs.writeFileSync(file, await io.writeBinary(doc));
  console.log('draco', path.basename(file), Math.round(before / 1024), '->', Math.round(fs.statSync(file).size / 1024), 'KB');
}
