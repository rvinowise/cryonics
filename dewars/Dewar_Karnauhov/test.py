import ast;
from pathlib import Path;

source = Path('dewar_xb200_long_neck.py').read_text(encoding='utf-8');
tree = ast.parse(source);
stop = next(i for i, n in enumerate(tree.body) if
            isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'parts');
ns = {};
exec(compile(ast.Module(body=tree.body[:stop], type_ignores=[]), 'dewar_xb200_long_neck.py', 'exec'), ns);
neck = ns['neck_corrug'];
shell = ns['ves_shell'];
joined = shell.fuse(neck).removeSplitter();
print('Neck valid: %s; vessel valid: %s; distance: %.9f mm' % (neck.isValid(), shell.isValid(),
                                                               neck.distToShape(shell)[0]), flush=True);
print('Joined shape valid: %s; solid count: %d' % (joined.isValid(), len(joined.Solids)), flush=True);
print('Cuff length: %.3f mm; ribs: %d; pitch: %.3f mm' % (ns['z_c_rib_start'] - ns['z_c0'], ns['n_rib'], ns['pitch']),
      flush=True);
print('Cuff z: %.6f to %.6f' % (ns['z_c0'], ns['z_c_rib_start']), flush=True);
print('Joint face areas: %s' % [round(f.common(g).Area, 6) for f in shell.Faces for g in neck.Faces if
                                f.common(g).Area > 1e-6], flush=True);
assert joined.isValid() and len(joined.Solids) == 1;
assert neck.isValid() and shell.isValid();
cutter = ns['Part'].makeBox(4000, 2000, 6000, ns['VEC'](-2000, 0, -500));
section = joined.cut(cutter);
assert section.isValid() and len(section.Solids) == 1;
print('FreeCAD geometry and section-view checks: PASS', flush=True)
