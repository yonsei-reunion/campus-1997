"""A GLB's bytes without Draco, for the tools that parse a GLB themselves (tools/nose_profile.py,
tools/metamoa_character.py): a Draco-compressed file (the people since 2026-11-27, blender/characters.py) is
decoded by tools/draco_glb.mjs --decode into a temporary file first. Needs node and web/'s devDependencies."""
import json, os, struct, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def read_bytes(path):
    b = open(path, 'rb').read()
    jlen = struct.unpack_from('<I', b, 12)[0]
    if 'KHR_draco_mesh_compression' not in json.loads(b[20:20 + jlen]).get('extensionsUsed', []):
        return b
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, 'plain.glb')
        subprocess.run(['node', os.path.join(HERE, 'draco_glb.mjs'), '--decode', str(path), out], check=True)
        return open(out, 'rb').read()
